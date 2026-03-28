"""
Standalone ACRCloud diagnostic — records 5s and shows full API response.
Run: .venv/bin/python test_acr.py
"""

import os, io, wave, time, hashlib, hmac, base64
import numpy as np
import sounddevice as sd
import requests
from dotenv import load_dotenv

load_dotenv()

HOST       = os.environ["ACR_HOST"]
KEY        = os.environ["ACR_KEY"]
SECRET     = os.environ["ACR_SECRET"]
SR         = int(os.getenv("SAMPLE_RATE", "44100"))
DEVICE     = int(os.getenv("AUDIO_DEVICE")) if os.getenv("AUDIO_DEVICE") else None

print(f"Host   : {HOST}")
print(f"Key    : {KEY[:8]}...")
print(f"Device : {DEVICE} (None = system default)")
print()

# ── 1. Record ──
print("Recording 5s... включи музыку")
audio = sd.rec(SR * 5, samplerate=SR, channels=1, dtype="float32", device=DEVICE)
sd.wait()
peak = np.abs(audio).max()
print(f"Peak level: {peak:.4f}")
if peak < 0.001:
    print("WARNING: уровень почти нулевой — возможно не тот микрофон")

# ── 2. Downsample to 8000 Hz + build WAV ──
TARGET_SR = 8000
step = SR / TARGET_SR
indices = np.arange(0, len(audio.flatten()), step).astype(np.int64)
downsampled = audio.flatten()[indices[indices < len(audio.flatten())]]
pcm = (downsampled * 32767).astype(np.int16)
buf = io.BytesIO()
with wave.open(buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(TARGET_SR)
    wf.writeframes(pcm.tobytes())
wav_bytes = buf.getvalue()
print(f"WAV size: {len(wav_bytes)/1024:.1f} KB  (downsampled {SR}→{TARGET_SR} Hz)")

# ── 3. Signature ──
timestamp = str(int(time.time()))
string_to_sign = "\n".join(["POST", "/v1/identify", KEY, "audio", "1", timestamp])
sig = base64.b64encode(
    hmac.new(SECRET.encode(), string_to_sign.encode(), digestmod=hashlib.sha1).digest()
).decode()

data = {
    "access_key": KEY,
    "sample_bytes": str(len(wav_bytes)),
    "timestamp": timestamp,
    "signature": sig,
    "data_type": "audio",
    "signature_version": "1",
}
files = {"sample": ("sample.wav", wav_bytes, "audio/wav")}

# ── 4. Send ──
url = f"https://{HOST}/v1/identify"
print(f"\nPOSTing to {url} ...")
t0 = time.time()
try:
    resp = requests.post(url, data=data, files=files, timeout=(10, 20))
    elapsed = time.time() - t0
    print(f"Response in {elapsed:.1f}s — HTTP {resp.status_code}")
    print(resp.text)
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED after {elapsed:.1f}s: {e}")
