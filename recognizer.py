import hashlib
import hmac
import base64
import time
import logging
import io
import wave
import requests
import numpy as np

logger = logging.getLogger(__name__)


class ACRCloudRecognizer:
    def __init__(self, host: str, key: str, secret: str, sample_rate: int = 44100):
        self.host = host
        self.key = key
        self.secret = secret
        self.sample_rate = sample_rate

    def _build_signature(self, timestamp: str) -> str:
        string_to_sign = "\n".join(
            ["POST", "/v1/identify", self.key, "audio", "1", timestamp]
        )
        hmac_digest = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha1,
        ).digest()
        return base64.b64encode(hmac_digest).decode("utf-8")

    @staticmethod
    def _downsample(audio: np.ndarray, from_rate: int, to_rate: int = 8000) -> np.ndarray:
        """Naive decimation downsample — good enough for fingerprinting."""
        if from_rate == to_rate:
            return audio
        step = from_rate / to_rate
        indices = np.arange(0, len(audio), step).astype(np.int64)
        indices = indices[indices < len(audio)]
        return audio[indices]

    @staticmethod
    def _to_wav(pcm_int16: np.ndarray, sample_rate: int) -> bytes:
        """Wrap int16 PCM samples in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)          # int16 = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_int16.tobytes())
        return buf.getvalue()

    def recognize(self, audio: np.ndarray) -> dict | None:
        """
        Send audio (float32, mono) to ACRCloud.
        Returns dict with 'artist', 'title', 'album' on success, None otherwise.
        """
        # Downsample to 8000 Hz — ~80 KB WAV vs ~430 KB at 44100 Hz
        TARGET_RATE = 8000
        downsampled = self._downsample(audio, self.sample_rate, TARGET_RATE)
        pcm_int16 = (downsampled * 32767).astype(np.int16)
        wav_bytes = self._to_wav(pcm_int16, TARGET_RATE)

        timestamp = str(int(time.time()))
        signature = self._build_signature(timestamp)

        data = {
            "access_key": self.key,
            "sample_bytes": str(len(wav_bytes)),
            "timestamp": timestamp,
            "signature": signature,
            "data_type": "audio",
            "signature_version": "1",
        }
        files = {"sample": ("sample.wav", wav_bytes, "audio/wav")}

        try:
            url = f"https://{self.host}/v1/identify"
            # tuple timeout: (connect_timeout, read_timeout) — fixes write/upload stalls
            resp = requests.post(url, data=data, files=files, timeout=(6, 15))
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            logger.warning("ACRCloud request failed: %s", e)
            return None

        status = result.get("status", {})
        if status.get("code") != 0:
            logger.debug("ACRCloud no match: %s", status.get("msg"))
            return None

        try:
            music = result["metadata"]["music"][0]
            artist = music["artists"][0]["name"]
            title = music["title"]
            album = music.get("album", {}).get("name", "")
            return {"artist": artist, "title": title, "album": album}
        except (KeyError, IndexError) as e:
            logger.warning("ACRCloud unexpected response shape: %s", e)
            return None
