"""
AudD diagnostic — records 5s and shows full API response.
Run: .venv/bin/python test_acr.py
"""

import os, io, wave, time, json, tempfile, subprocess
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

TOKEN  = os.environ["AUDD_TOKEN"]
SR     = int(os.getenv("SAMPLE_RATE", "44100"))
DEVICE = int(os.getenv("AUDIO_DEVICE")) if os.getenv("AUDIO_DEVICE") else None

print(f"Token  : {TOKEN[:8]}...")
print(f"Device : {DEVICE}")
print()

# ── 1. Record ──
print("Recording 5s... включи музыку")
audio = sd.rec(SR * 5, samplerate=SR, channels=1, dtype="float32", device=DEVICE)
sd.wait()
peak = np.abs(audio).max()
print(f"Peak level: {peak:.4f}")

# ── 2. Downsample + WAV ──
step  = SR / 8000
flat  = audio.flatten()
idx   = np.arange(0, len(flat), step).astype(np.int64)
pcm   = (flat[idx[idx < len(flat)]] * 32767).astype(np.int16)
buf   = io.BytesIO()
with wave.open(buf, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(8000)
    wf.writeframes(pcm.tobytes())
wav_bytes = buf.getvalue()
print(f"WAV size: {len(wav_bytes)/1024:.1f} KB")

# ── 3. Send via curl ──
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    f.write(wav_bytes)
    tmp = f.name

print(f"\nPOSTing to https://api.audd.io/ via curl ...")
t0 = time.time()
try:
    r = subprocess.run(
        ["curl", "-s", "--max-time", "30",
         "-F", f"api_token={TOKEN}",
         "-F", "return=artist,title,album",
         "-F", f"file=@{tmp}",
         "https://api.audd.io/"],
        capture_output=True, text=True, timeout=35,
    )
    print(f"Response in {time.time()-t0:.1f}s")
    data = json.loads(r.stdout)
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"FAILED after {time.time()-t0:.1f}s: {e}")
finally:
    os.unlink(tmp)
