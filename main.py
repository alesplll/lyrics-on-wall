"""
Lyrics on Wall — main entry point.

Listens to ambient audio, recognizes songs via ACRCloud,
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

from recognizer import ACRCloudRecognizer
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
RECOGNIZE_EVERY = int(os.getenv("RECOGNIZE_EVERY", "15"))  # override via .env for debugging
LOOP_INTERVAL   = 0.2  # seconds between state pushes
SERVER_PORT     = 5500


def record_audio(sample_rate: int, duration: float) -> np.ndarray:
    frames = int(sample_rate * duration)
    audio = sd.rec(
        frames, samplerate=sample_rate, channels=1, dtype="float32",
        device=AUDIO_DEVICE,
    )
    sd.wait()
    return audio.flatten()


def recognition_worker(
    recognizer: ACRCloudRecognizer,
    result_queue: queue.Queue,
    stop_event: threading.Event,
):
    while not stop_event.is_set():
        logger.info("Recording %ds of audio…", RECORD_SECONDS)
        try:
            audio = record_audio(SAMPLE_RATE, RECORD_SECONDS)
            info = recognizer.recognize(audio)
        except Exception as e:
            logger.warning("Recognition error: %s", e)
            info = None

        result_queue.put(info)

        remaining = RECOGNIZE_EVERY - RECORD_SECONDS
        if remaining > 0:
            stop_event.wait(timeout=remaining)


def main():
    acr_host   = os.environ["ACR_HOST"]
    acr_key    = os.environ["ACR_KEY"]
    acr_secret = os.environ["ACR_SECRET"]

    recognizer = ACRCloudRecognizer(
        host=acr_host, key=acr_key, secret=acr_secret, sample_rate=SAMPLE_RATE
    )

    # Start Flask server in background thread
    server_thread = threading.Thread(
        target=run_server, kwargs={"port": SERVER_PORT}, daemon=True
    )
    server_thread.start()
    logger.info("Server running at http://127.0.0.1:%d", SERVER_PORT)

    # Open browser after a short delay so Flask is ready
    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://127.0.0.1:{SERVER_PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    # State
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
            # Pull latest recognition result (non-blocking)
            try:
                info = result_queue.get_nowait()
                if info is not None:
                    song_key = (info["artist"], info["title"])
                    cur_key  = (
                        (current_song["artist"], current_song["title"])
                        if current_song else None
                    )
                    if song_key != cur_key:
                        logger.info("New song: %s — %s", info["artist"], info["title"])
                        current_song    = info
                        song_start_time = time.monotonic()
                        lyric_lines, is_synced = fetch_lyrics(
                            info["artist"], info["title"], info.get("album", "")
                        )
                        logger.info(
                            "Lyrics: %d lines, synced=%s", len(lyric_lines), is_synced
                        )
            except queue.Empty:
                pass

            # Build and push state to SSE clients
            if current_song is None:
                set_state({"status": "listening"})

            elif not lyric_lines:
                set_state({
                    "status": "no_lyrics",
                    "artist": current_song["artist"],
                    "title":  current_song["title"],
                })

            else:
                if is_synced:
                    elapsed = time.monotonic() - song_start_time
                    current_line, prev_line = get_current_line(lyric_lines, elapsed)
                else:
                    # Plain lyrics: no timing, just cycle through lines slowly
                    elapsed  = time.monotonic() - song_start_time
                    idx      = min(int(elapsed / 4), len(lyric_lines) - 1)
                    current_line = lyric_lines[idx][1]
                    prev_line    = lyric_lines[idx - 1][1] if idx > 0 else ""

                set_state({
                    "status":  "lyrics",
                    "artist":  current_song["artist"],
                    "title":   current_song["title"],
                    "current": current_line,
                    "prev":    prev_line,
                })

            time.sleep(LOOP_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Stopping…")
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
