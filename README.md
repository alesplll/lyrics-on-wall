# 🎵 Lyrics on Wall

> Karaoke-style lyrics in your browser — for whatever's playing in the room.

<img width="1385" height="899" alt="image" src="https://github.com/user-attachments/assets/8b11884f-9b0e-4197-80ac-6885b97b7efc" />

Listens to ambient audio via microphone → recognizes the song via [AudD](https://audd.io/) → fetches time-synced lyrics from [LRCLIB](https://lrclib.net/) → streams them live to a fullscreen browser tab.



---

## ✨ Features

- 🎤 **Passive listening** — no manual input, just plays in the background
- 🔍 **Song recognition** via [AudD](https://audd.io/) — free tier, no card required
- 📜 **Synced lyrics** from [LRCLIB](https://lrclib.net/) — open API, no key needed
- 🌐 **Browser display** — open in any browser, works on any screen or TV
- 🎞️ **5-line teleprompter view** — 2 past + current + 2 upcoming lines
- ⏱️ **Timecode sync** — uses AudD's timecode response to lock lyrics to actual song position
- 🔄 **Graceful fallbacks** — plain lyrics → title/artist → animated "Listening..."

---

## 🖼️ Display layout

```
  two lines back, small & dark
  one line back, medium & gray
  CURRENT LINE — large & white
  one line ahead, medium & gray
  two lines ahead, small & dark

                          Song Title  ←── bottom-right
                          Artist Name
```

---

## 🚀 Quick start

### 1. Clone & install

```bash
git clone <repo-url> lyrics-on-wall
cd lyrics-on-wall
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Get AudD token — free, no card

Register at **[dashboard.audd.io](https://dashboard.audd.io/)** → copy your API token.

### 3. Configure

```bash
cp .env.example .env
# edit .env and paste your token
```

```ini
AUDD_TOKEN=your_token_here
SAMPLE_RATE=44100
LYRIC_OFFSET=2.0        # seconds to add to sync compensation
# AUDIO_DEVICE=15       # optional: override mic device index
```

### 4. Run

```bash
.venv/bin/python main.py
```

Browser opens automatically at `http://localhost:5500`. Press **F11** for fullscreen. Stop with **Ctrl+C**.

---

## 🐳 Docker

```bash
docker compose up --build
```

The container uses your system's PulseAudio socket for microphone access. No `AUDIO_DEVICE` needed inside Docker — leave it unset in `.env`.

> Requires PipeWire or PulseAudio on the host. The socket at `/run/user/1000/pulse/native` is mounted automatically via `docker-compose.yml`.

---

## ⚙️ How it works

```
Microphone
    │  4s PCM audio, every 7s
    ▼
AudD API  ──►  artist / title / timecode
                    │
                    ├─ timecode used to calculate exact song position
                    │
                    ▼  (on new song)
               LRCLIB API  ──►  synced LRC lyrics
                                      │
                                      ▼  every 200ms
                               Flask SSE /stream
                                      │
                                      ▼
                           Browser (index.html)
                        5-line view + scroll animation
```

---

## 📁 Project structure

```
lyrics-on-wall/
├── main.py              # entry point — recognition loop + state manager
├── recognizer.py        # AudD song recognition (via curl subprocess)
├── lyrics.py            # LRCLIB fetch + LRC parser
├── server.py            # Flask server + SSE /stream endpoint
├── static/
│   └── index.html       # frontend — HTML + CSS + vanilla JS
├── scripts/
│   └── diagnose.py      # standalone mic + API diagnostic tool
├── test_lyrics.py       # unit tests for LRC parser
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## 🔧 Config reference

| Variable | Default | Description |
|---|---|---|
| `AUDD_TOKEN` | — | AudD API token (required) |
| `SAMPLE_RATE` | `44100` | Microphone sample rate |
| `LYRIC_OFFSET` | `2.0` | Seconds added to elapsed time for sync compensation |
| `AUDIO_DEVICE` | system default | PortAudio device index (bare-metal only) |
| `RECOGNIZE_EVERY` | `7` | Seconds between recognition cycles |

---

## 🧪 Tests

```bash
.venv/bin/pytest test_lyrics.py -v
```

---

## 🐛 Troubleshooting

**Mic not working / zero peak level**
```bash
# list devices
.venv/bin/python -c "import sounddevice; print(sounddevice.query_devices())"
# check mute status
pactl get-source-mute @DEFAULT_SOURCE@
pactl set-source-mute @DEFAULT_SOURCE@ 0
```

**Lyrics out of sync**
Adjust `LYRIC_OFFSET` in `.env`. Positive values shift lyrics forward (ahead of audio).

**AudD not recognizing**
Run the diagnostic tool with music playing:
```bash
.venv/bin/python scripts/diagnose.py
```

**Browser doesn't open**
Navigate manually to `http://localhost:5500`

---

## 📄 License

MIT
