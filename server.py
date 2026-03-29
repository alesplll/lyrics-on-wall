"""
Flask server — serves the frontend and streams state via SSE.
"""

import json
import time
import threading
from flask import Flask, Response, send_from_directory

app = Flask(__name__, static_folder="static")

# Shared state, written by main loop, read by SSE clients
_state: dict = {"status": "listening"}
_state_lock = threading.Lock()


def set_state(new_state: dict):
    with _state_lock:
        _state.clear()
        _state.update(new_state)


def get_state() -> dict:
    with _state_lock:
        return dict(_state)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/stream")
def stream():
    def event_generator():
        while True:
            state = get_state()
            data = json.dumps(state, ensure_ascii=False)
            yield f"data: {data}\n\n"
            time.sleep(0.2)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def run(host="0.0.0.0", port=5500):
    app.run(host=host, port=port, threaded=True, use_reloader=False)
