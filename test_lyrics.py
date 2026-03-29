from lyrics import parse_lrc, get_current_line


SAMPLE_LRC = """\
[00:12.34] First line
[00:24.00] Second line
[01:05.50] Third line
[01:30.00] Fourth line
"""


def test_parse_valid_lrc():
    lines = parse_lrc(SAMPLE_LRC)
    assert len(lines) == 4
    assert lines[0] == (12.34, "First line")
    assert lines[1] == (24.00, "Second line")
    assert abs(lines[2][0] - 65.50) < 0.001
    assert lines[3][0] == 90.00


def test_parse_empty_input():
    assert parse_lrc("") == []


def test_parse_lines_without_timestamps():
    raw = "[ti:Some Song]\n[ar:Artist]\nThis line has no timestamp\n[00:05.00] Real line"
    lines = parse_lrc(raw)
    # Only the properly timestamped line should be included
    assert len(lines) == 1
    assert lines[0] == (5.0, "Real line")


def test_parse_millisecond_timestamps():
    raw = "[00:10.500] Half-second\n[00:20.000] Twenty"
    lines = parse_lrc(raw)
    assert abs(lines[0][0] - 10.5) < 0.001
    assert lines[1][0] == 20.0


def test_get_current_line_before_start():
    lines = [(5.0, "A"), (10.0, "B"), (15.0, "C"), (20.0, "D"), (25.0, "E")]
    prev2, prev1, current, next1, next2 = get_current_line(lines, elapsed=2.0)
    assert current == "A"
    assert prev1 == "" and prev2 == ""
    assert next1 == "B" and next2 == "C"


def test_get_current_line_mid_song():
    lines = [(5.0, "A"), (10.0, "B"), (15.0, "C"), (20.0, "D"), (25.0, "E")]
    prev2, prev1, current, next1, next2 = get_current_line(lines, elapsed=16.0)
    assert current == "C"
    assert prev1 == "B" and prev2 == "A"
    assert next1 == "D" and next2 == "E"


def test_get_current_line_empty():
    assert get_current_line([], elapsed=10.0) == ("", "", "", "", "")
