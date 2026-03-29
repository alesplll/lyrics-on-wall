import io
import wave
import json
import logging
import tempfile
import subprocess
import numpy as np

logger = logging.getLogger(__name__)


class AudDRecognizer:
    def __init__(self, api_token: str, sample_rate: int = 44100):
        self.api_token = api_token
        self.sample_rate = sample_rate

    @staticmethod
    def _downsample(audio: np.ndarray, from_rate: int, to_rate: int = 8000) -> np.ndarray:
        if from_rate == to_rate:
            return audio
        step = from_rate / to_rate
        indices = np.arange(0, len(audio), step).astype(np.int64)
        return audio[indices[indices < len(audio)]]

    @staticmethod
    def _to_wav(pcm_int16: np.ndarray, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_int16.tobytes())
        return buf.getvalue()

    def recognize(self, audio: np.ndarray) -> dict | None:
        """
        Send audio (float32, mono) to AudD via curl subprocess.
        Returns dict with 'artist', 'title', 'album' on success, None otherwise.
        """
        downsampled = self._downsample(audio, self.sample_rate)
        pcm_int16 = (downsampled * 32767).astype(np.int16)
        wav_bytes = self._to_wav(pcm_int16, 8000)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [
                    "curl", "-s", "--max-time", "30",
                    "-F", f"api_token={self.api_token}",
                    "-F", "return=spotify",
                    "-F", f"file=@{tmp_path}",
                    "https://api.audd.io/",
                ],
                capture_output=True, text=True, timeout=35,
            )
            data = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.warning("AudD request failed: %s", e)
            return None
        finally:
            import os; os.unlink(tmp_path)

        if data.get("status") != "success" or not data.get("result"):
            logger.debug("AudD no match: %s", data.get("status"))
            return None

        r = data["result"]
        return {
            "artist": r.get("artist", ""),
            "title":  r.get("title", ""),
            "album":  r.get("album", ""),
        }
