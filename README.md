# 🎵 Lyrics on Wall

> Karaoke-style lyrics in your browser — for whatever's playing in the room.

Listens to ambient audio via microphone → recognizes the song → fetches time-synced lyrics → streams them live to a fullscreen browser tab, line by line.

---

## ✨ Features

- 🎤 **Passive listening** — no manual input, just plays in the background
- 🔍 **Auto song recognition** via [ACRCloud](https://www.acrcloud.com/) (free tier)
- 📜 **Synced lyrics** from [LRCLIB](https://lrclib.net/) — open, no API key needed
- 🌐 **Browser-based display** — open in Firefox, works on any screen
- ✨ **Smooth CSS animations** — lines fade in on change, dots pulse while listening
- 🔄 **Graceful fallbacks** — plain lyrics → title/artist → animated "Listening..."
- 🧵 **Non-blocking** — recognition runs in a background thread, stream never freezes

---

## 🖼️ Display

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                                                 │
│         previous line, small & dimmed           │
│                                                 │
│        CURRENT LINE, LARGE & WHITE              │
│                                                 │
│                                                 │
│                              Song Title         │
│                              Artist Name        │
└─────────────────────────────────────────────────┘
```

While no song is detected — three pulsing dots + "LISTENING" label.

---

## 🚀 Quick start

### 1. Clone & set up environment

```bash
git clone <repo-url> lyrics-on-wall
cd lyrics-on-wall
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Get ACRCloud credentials (free, no card)

1. Register at **[acrcloud.com](https://www.acrcloud.com/)**
2. Console → **Create Project** → type: *Audio & Video Recognition*
3. Copy **Host**, **Access Key**, **Access Secret**

### 3. Configure `.env`

```bash
cp .env.example .env
```

```ini
ACR_HOST=identify-eu-west-1.acrcloud.com
ACR_KEY=your_access_key_here
ACR_SECRET=your_access_secret_here
SAMPLE_RATE=44100
```

### 4. Run

```bash
.venv/bin/python main.py
```

Firefox opens automatically at `http://127.0.0.1:5500`.
Press **F11** for true fullscreen. Stop with **Ctrl+C** in the terminal.

---

## 📁 Project structure

```
lyrics-on-wall/
├── main.py          # entry point, main loop, state manager
├── recognizer.py    # ACRCloud audio recognition
├── lyrics.py        # LRCLIB fetch + LRC parser
├── server.py        # Flask server + SSE /stream endpoint
├── static/
│   └── index.html   # frontend (HTML + CSS + vanilla JS)
├── test_lyrics.py   # unit tests for LRC parser
├── .env.example     # credentials template
└── requirements.txt
```

---

## 🧪 Tests

```bash
.venv/bin/pytest test_lyrics.py -v
```

---

## ⚙️ How it works

```
Microphone
    │  (5s PCM, every 15s, background thread)
    ▼
ACRCloud API  ──►  artist / title / album
                        │
                        ▼  (on song change)
                   LRCLIB API  ──►  synced LRC lyrics
                                          │
                                          ▼  (every 200ms)
                                   Flask SSE /stream
                                          │
                                          ▼
                                  Firefox (index.html)
                              CSS fade-in on line change
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `sounddevice` | Microphone capture |
| `numpy` | Audio buffer handling |
| `requests` | HTTP — ACRCloud & LRCLIB |
| `flask` | Local web server + SSE stream |
| `python-dotenv` | `.env` config loading |
| `pytest` | Tests |

---

## 🐛 Troubleshooting

**No audio input / wrong device**
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```
Set the desired device index in `main.py` → `sd.rec(..., device=N)`.

**ACRCloud always returns no match**
- Microphone might not pick up room audio well enough
- Check credentials in `.env` are correct and the project type is *Audio & Video Recognition*

**Browser doesn't open automatically**
Navigate manually to `http://127.0.0.1:5500`

---

## 📄 License

MIT
