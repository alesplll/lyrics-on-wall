import re
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LRC_LINE_RE = re.compile(r"\[(\d{1,3}):(\d{2})\.(\d{2,3})\](.*)")


def parse_lrc(lrc_text: str) -> list[tuple[float, str]]:
    """Parse LRC format into list of (seconds, text) tuples, sorted by time."""
    result = []
    for line in lrc_text.splitlines():
        m = LRC_LINE_RE.match(line)
        if m:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            centis = m.group(3)
            # Handle both 2-digit (centiseconds) and 3-digit (milliseconds)
            frac = int(centis) / (1000 if len(centis) == 3 else 100)
            total = minutes * 60 + seconds + frac
            text = m.group(4).strip()
            result.append((total, text))
    result.sort(key=lambda x: x[0])
    return result


def fetch_lyrics(
    artist: str, title: str, album: str = ""
) -> tuple[list[tuple[float, str]], bool]:
    """
    Fetch lyrics from LRCLIB.
    Returns (lines, is_synced).
    lines is a list of (seconds, text) for synced, or [(0.0, text), ...] for plain.
    """
    params = {"artist_name": artist, "track_name": title}
    if album:
        params["album_name"] = album

    try:
        resp = requests.get(
            "https://lrclib.net/api/get", params=params, timeout=8
        )
        if resp.status_code == 404:
            logger.info("LRCLIB: no lyrics found for %s - %s", artist, title)
            return [], False
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("LRCLIB request failed: %s", e)
        return [], False

    synced_raw: Optional[str] = data.get("syncedLyrics")
    plain_raw: Optional[str] = data.get("plainLyrics")

    if synced_raw:
        parsed = parse_lrc(synced_raw)
        if parsed:
            return parsed, True

    if plain_raw:
        # Return plain lyrics as a list of (0.0, line) — no timing
        lines = [(0.0, line.strip()) for line in plain_raw.splitlines() if line.strip()]
        return lines, False

    return [], False


def get_current_line(
    lines: list[tuple[float, str]], elapsed: float
) -> tuple[str, str, str]:
    """
    Given synced lyric lines and elapsed seconds, return (current, prev, next).
    """
    if not lines:
        return "", "", ""

    current_idx = 0
    for i, (t, _) in enumerate(lines):
        if t <= elapsed:
            current_idx = i
        else:
            break

    current = lines[current_idx][1]
    prev    = lines[current_idx - 1][1] if current_idx > 0 else ""
    next_   = lines[current_idx + 1][1] if current_idx + 1 < len(lines) else ""
    return current, prev, next_
