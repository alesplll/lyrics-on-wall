"""
Lyrics on Wall — main entry point.

Listens to ambient audio, recognizes songs via AudD,
fetches synced lyrics from LRCLIB, and serves them to a browser via SSE.
"""

import os
import time
import logging
import threading
import queue
import webbrowser

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

from recognizer import AudDRecognizer
from lyrics import fetch_lyrics, get_current_line
from server import run as run_server, set_state

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

SAMPLE_RATE     = int(os.getenv("SAMPLE_RATE", "44100"))
AUDIO_DEVICE    = int(os.getenv("AUDIO_DEVICE")) if os.getenv("AUDIO_DEVICE") else None
RECORD_SECONDS  = 5
RECOGNIZE_EVERY = int(os.getenv("RECOGNIZE_EVERY", "15"))
LOOP_INTERVAL   = 0.2
SERVER_PORT     = 5500


def record_audio(sample_rate: int, duration: float) -> tuple[np.ndarray, float]:
    """Record audio and return (samples, monotonic timestamp when recording ended)."""
    frames = int(sample_rate * duration)
    audio = sd.rec(
        frames, samplerate=sample_rate, channels=1, dtype="float32",
        device=AUDIO_DEVICE,
    )
    sd.wait()
    return audio.flatten(), time.monotonic()


def recognition_worker(
    recognizer: AudDRecognizer,
    result_queue: queue.Queue,
    stop_event: threading.Event,
):
    while not stop_event.is_set():
        logger.info("Recording %ds of audio…", RECORD_SECONDS)
        try:
            audio, record_end_time = record_audio(SAMPLE_RATE, RECORD_SECONDS)
            info = recognizer.recognize(audio)
            if info is not None:
                info["record_end_time"] = record_end_time
        except Exception as e:
            logger.warning("Recognition error: %s", e)
            info = None

        result_queue.put(info)

        remaining = RECOGNIZE_EVERY - RECORD_SECONDS
        if remaining > 0:
            stop_event.wait(timeout=remaining)


def main():
    recognizer = AudDRecognizer(
        api_token=os.environ["AUDD_TOKEN"],
        sample_rate=SAMPLE_RATE,
    )

    server_thread = threading.Thread(
        target=run_server, kwargs={"port": SERVER_PORT}, daemon=True
    )
    server_thread.start()
    logger.info("Server running at http://127.0.0.1:%d", SERVER_PORT)

    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://127.0.0.1:{SERVER_PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    current_song: dict | None = None
    lyric_lines: list         = []
    is_synced: bool           = False
    song_start_time: float    = 0.0

    result_queue: queue.Queue = queue.Queue()
    stop_event                = threading.Event()

    worker = threading.Thread(
        target=recognition_worker,
        args=(recognizer, result_queue, stop_event),
        daemon=True,
    )
    worker.start()
    logger.info("Recognition worker started. Press Ctrl+C to stop.")

    try:
        while True:
            try:
                info = result_queue.get_nowait()
                if info is not None:
                    song_key = (info["artist"], info["title"])
                    cur_key  = (
                        (current_song["artist"], current_song["title"])
                        if current_song else None
                    )

                    # Recalculate song_start_time on every recognition using timecode
                    # record_end_time - timecode = when the song actually started
                    record_end_time = info.get("record_end_time", time.monotonic())
                    timecode        = info.get("timecode", 0.0)
                    song_start_time = record_end_time - timecode
                    logger.info(
                        "Timecode: %.0fs → song started %.0fs ago",
                        timecode, time.monotonic() - song_start_time,
                    )

                    if song_key != cur_key:
                        logger.info("New song: %s — %s", info["artist"], info["title"])
                        current_song = info
                        lyric_lines, is_synced = fetch_lyrics(
                            info["artist"], info["title"], info.get("album", "")
                        )
                        logger.info(
                            "Lyrics: %d lines, synced=%s", len(lyric_lines), is_synced
                        )
            except queue.Empty:
                pass

            if current_song is None:
                set_state({"status": "listening"})

            elif not lyric_lines:
                set_state({
                    "status": "no_lyrics",
                    "artist": current_song["artist"],
                    "title":  current_song["title"],
                })

            else:
                elapsed = time.monotonic() - song_start_time

                if is_synced:
                    current_line, prev_line, next_line = get_current_line(lyric_lines, elapsed)
                else:
                    idx          = min(int(elapsed / 4), len(lyric_lines) - 1)
                    current_line = lyric_lines[idx][1]
                    prev_line    = lyric_lines[idx - 1][1] if idx > 0 else ""
                    next_line    = lyric_lines[idx + 1][1] if idx + 1 < len(lyric_lines) else ""

                set_state({
                    "status":  "lyrics",
                    "artist":  current_song["artist"],
                    "title":   current_song["title"],
                    "current": current_line,
                    "prev":    prev_line,
                    "next":    next_line,
                })

            time.sleep(LOOP_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Stopping…")
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
