"""The console log keeps everything but progress bars, in split files.

Bluesky redraws a motor's progress bar several times a second, and with the
cursor movement stripped every redraw used to become a line of the log: one
session wrote ~2 GB of ``huber_euler: 100%|███…`` around a few hundred scan
rows.  :class:`~id4_common.gui.transcript.ConsoleTranscript` now leaves the
bars out, and spreads the rest over ``<prefix>_<date>_<NNN>.log`` files that
roll over by size and by date.
"""

from __future__ import annotations

import datetime
import io

import pytest
from id4_common.gui import transcript as transcript_module
from id4_common.gui.transcript import ConsoleTranscript
from id4_common.gui.transcript import log_file_name
from id4_common.utils.progress_bar import OneLineProgressBar
from id4_common.utils.progress_bar import set_console_columns

DAY = datetime.date(2026, 11, 1)


class FakeStatus:
    """The little of a status object a progress bar actually touches."""

    def __init__(self):
        self.done = False

    def watch(self, callback):
        """Accept the bar's update callback, as a real status would."""


@pytest.fixture
def today(monkeypatch):
    """Pin the transcript's idea of today; returns a setter to move it."""
    current = {"day": DAY}
    monkeypatch.setattr(transcript_module, "_today", lambda: current["day"])

    def _set(day):
        current["day"] = day

    return _set


@pytest.fixture
def log(tmp_path, today):
    """A transcript logging into ``tmp_path`` with prefix ``pre``."""
    transcript = ConsoleTranscript()
    assert transcript.start(tmp_path, "pre")
    yield transcript
    transcript.stop()


def _stream(transcript, text, name="stdout"):
    transcript.handle(
        {"msg_type": "stream", "content": {"name": name, "text": text}}
    )


def _text(transcript):
    return transcript.path.read_text(encoding="utf-8")


def _bar_output():
    """What a real bluesky progress bar writes over a short move."""
    set_console_columns(60)
    try:
        bar = OneLineProgressBar([FakeStatus(), FakeStatus()], delay_draw=0)
    finally:
        set_console_columns(None)
    bar.fp = io.StringIO()
    for step in range(5):
        bar.update(
            0,
            name="huber_euler",
            current=float(step),
            initial=0.0,
            target=4.0,
        )
        bar.update(1, name="scaler1")
    bar.clear()
    return bar.fp.getvalue()


# -- progress bars --------------------------------------------------------


def test_a_progress_bar_leaves_nothing_in_the_log(log):
    """Neither the meters, the fallback, nor the erasing blank lines."""
    before = _text(log)
    _stream(log, _bar_output())

    assert _text(log) == before


def test_a_bar_cut_across_messages_is_still_recognised(log):
    """The kernel flushes stream text wherever its buffer was, mid-line too."""
    before = _text(log)
    output = _bar_output()
    for i in range(0, len(output), 7):
        _stream(log, output[i : i + 7])
    log.handle({"msg_type": "status", "content": {"execution_state": "idle"}})

    assert _text(log) == before


def test_a_zero_length_move_leaves_nothing_either(log):
    """With no distance to cover tqdm draws no bar, only a count and a time.

    A real session logged 23k lines of ``huber_euler: 0.0 [00:00, ?/s]``.
    """
    before = _text(log)
    for step in range(3):
        _stream(log, f"\rhuber_euler: 0.0 [00:{step:02d}, ?/s]\n\x1b[A")
    _stream(log, "\rhuber_euler: 0.0units [1:01:40, ?units/s]\n\x1b[A")

    assert _text(log) == before


def test_output_around_a_bar_is_kept(log):
    """Scan rows printed between moves survive, in order, one per line."""
    _stream(log, "|   seq_num |       time |\n")
    _stream(log, _bar_output())
    _stream(log, "|         1 | 07:39:14.5 |\n")
    _stream(log, _bar_output())
    _stream(log, "|         2 | 07:39:17.0 |\n")

    text = _text(log)
    assert "%|" not in text
    assert "No progress bar" not in text
    assert (
        "|   seq_num |       time |\n"
        "|         1 | 07:39:14.5 |\n"
        "|         2 | 07:39:17.0 |\n"
    ) in text


# -- everything else is kept --------------------------------------------------


def test_errors_and_warnings_are_kept(log):
    """Tracebacks and stderr are the most important part of the log."""
    _stream(log, "UserWarning: 50% of the beam is gone\n", name="stderr")
    log.handle(
        {
            "msg_type": "error",
            "content": {
                "traceback": ["\x1b[31mTraceback\x1b[0m", "ValueError: bad"]
            },
        }
    )

    text = _text(log)
    assert "UserWarning: 50% of the beam is gone\n" in text
    assert "Traceback\nValueError: bad\n" in text


def test_a_line_that_merely_looks_like_a_bar_is_kept(log):
    """Only a line a carriage return led into can be a redraw."""
    _stream(log, "done: 100%| all of it\n")

    assert "done: 100%| all of it\n" in _text(log)


def test_crlf_and_split_lines_are_joined(log):
    """``\\r\\n`` is one line ending; a line split in two is one line."""
    _stream(log, "first\r\nsec")
    _stream(log, "ond\n")

    assert "first\nsecond\n" in _text(log)


def test_a_partial_line_is_written_when_the_cell_ends(log):
    """``print(..., end="")`` must not wait for output that never comes."""
    _stream(log, "no newline")
    assert "no newline" not in _text(log)

    log.handle({"msg_type": "status", "content": {"execution_state": "idle"}})

    assert _text(log).endswith("no newline")


def test_input_follows_pending_output(log):
    """A new cell writes what was waiting before its own prompt."""
    _stream(log, "pending")
    log.handle(
        {
            "msg_type": "execute_input",
            "content": {"code": "mv(x, 1)", "execution_count": 3},
        }
    )

    assert "pending\nIn [3]: mv(x, 1)\n" in _text(log)


# -- naming -------------------------------------------------------------------


def test_files_are_named_by_prefix_date_and_number(log, tmp_path):
    """The user chooses the directory and prefix; the rest is added."""
    assert log.path == tmp_path / "pre_2026-11-01_001.log"
    assert log_file_name("pre", DAY) == "pre_2026-11-01_NNN.log"


def test_starting_again_appends_to_the_newest_file(tmp_path, today):
    """A relaunch keeps one experiment in one file while it has room."""
    first = ConsoleTranscript()
    first.start(tmp_path, "pre")
    _stream(first, "before restart\n")
    first.stop()

    second = ConsoleTranscript()
    second.start(tmp_path, "pre")
    try:
        assert second.path == first.path
        assert "before restart" in _text(second)
    finally:
        second.stop()


def test_a_full_newest_file_is_not_reopened(tmp_path, today):
    """Past the limit, starting opens the next number instead."""
    (tmp_path / "pre_2026-11-01_001.log").write_text("x" * 100)
    (tmp_path / "pre_2026-11-01_002.log").write_text("x" * 100)
    (tmp_path / "other_2026-11-01_009.log").write_text("x")

    transcript = ConsoleTranscript()
    transcript.start(tmp_path, "pre", max_bytes=100)
    try:
        assert transcript.path.name == "pre_2026-11-01_003.log"
    finally:
        transcript.stop()


# -- splitting ----------------------------------------------------------------


def test_a_full_file_continues_in_the_next(tmp_path, today):
    """Past the size limit, the next line goes to the next number."""
    transcript = ConsoleTranscript()
    transcript.start(tmp_path, "pre", max_bytes=200)
    for i in range(20):
        _stream(transcript, f"line {i:02d} " + "." * 20 + "\n")
    transcript.stop()

    files = sorted(tmp_path.glob("pre_2026-11-01_*.log"))
    assert len(files) > 1
    texts = [f.read_text(encoding="utf-8") for f in files]
    assert f"continued in {files[1].name}" in texts[0]
    assert f"continued from {files[0].name}" in texts[1]
    # Every line written exactly once, never cut in half.
    joined = "".join(texts)
    for i in range(20):
        assert joined.count(f"line {i:02d} " + "." * 20 + "\n") == 1


def test_a_new_day_starts_a_new_file(log, tmp_path, today):
    """Midnight rolls over to the new date's first file."""
    _stream(log, "late\n")
    today(DAY + datetime.timedelta(days=1))
    _stream(log, "early\n")

    assert log.path == tmp_path / "pre_2026-11-02_001.log"
    assert "early\n" in _text(log)
    assert "late\n" in (tmp_path / "pre_2026-11-01_001.log").read_text()


def test_the_limit_can_change_while_logging(log, tmp_path):
    """The Session tab's spin box applies at once."""
    _stream(log, "x" * 50 + "\n")
    log.max_bytes = 10
    _stream(log, "next\n")

    assert log.path == tmp_path / "pre_2026-11-01_002.log"


def test_a_failed_write_stops_logging(log):
    """A full disk must not raise into the poll timer."""

    class Broken:
        def write(self, text):
            raise OSError("disk full")

        def close(self):
            pass

    log._file = Broken()
    _stream(log, "lost\n")

    assert not log.active
    assert log.error == "disk full"
