"""The motor-move progress bar has to stay on one row.

Bluesky measures the terminal once per bar, and inside an IPython kernel that
measurement fails and falls back to 79 characters.  In the GUI console, which
is usually narrower, the line wrapped onto a second display row and the
redraw -- one newline and one cursor-up per meter -- then counted rows wrong
and left a trail of half-erased bars behind the moving motor.
"""

from __future__ import annotations

import io

import pytest
from id4_common.utils.progress_bar import MIN_COLUMNS
from id4_common.utils.progress_bar import OneLineProgressBar
from id4_common.utils.progress_bar import console_columns
from id4_common.utils.progress_bar import progress_bar_manager
from id4_common.utils.progress_bar import set_console_columns


class FakeStatus:
    """The little of a status object a progress bar actually touches."""

    def __init__(self):
        self.done = False
        self.callback = None

    def watch(self, callback):
        """Register the bar's update callback, as a real status would."""
        self.callback = callback


@pytest.fixture
def no_reported_width():
    """Leave the module's width unset, whatever the test did to it."""
    yield
    set_console_columns(None)


@pytest.fixture
def bar(no_reported_width):
    """A bar drawing into a buffer, as if the console were 40 wide.

    ``delay_draw=0`` both skips the 0.2 s wait before the first draw and
    keeps the watchdog thread from starting, so every write here is one the
    test asked for.
    """
    set_console_columns(40)
    drawn = OneLineProgressBar([FakeStatus()], delay_draw=0)
    drawn.fp = io.StringIO()
    return drawn


def test_the_reported_width_is_the_width_drawn(bar):
    """The GUI's measurement wins over bluesky's failed one."""
    assert bar.ncols == 40


def _rows_written(bar):
    """Every run of text the bar put on a row of the console."""
    return [
        row
        for chunk in bar.fp.getvalue().split("\n")
        for row in chunk.split("\r")
        if row.strip()
    ]


def test_a_long_motor_name_cannot_widen_the_bar(bar):
    """tqdm honours ncols for the bar; the prefix is ours to clip."""
    bar.update(
        0,
        name="a_very_long_motor_name_of_the_kind_4idb_actually_has",
        current=1.0,
        initial=0.0,
        target=10.0,
    )

    assert len(bar.meters[0]) <= 40
    rows = _rows_written(bar)
    assert rows, "the bar should have drawn something"
    assert all(len(row) <= 40 for row in rows)


def test_the_no_bar_fallback_is_clipped_too(bar):
    """A status with no position reports text tqdm never formats."""
    bar.update(0, name="a_very_long_motor_name_with_no_position_to_show")

    assert bar.meters[0]
    assert len(bar.meters[0]) <= 40
    assert all(len(row) <= 40 for row in _rows_written(bar))


def test_an_unreported_width_leaves_bluesky_alone(no_reported_width):
    """Off a tty bluesky measures correctly; do not second-guess it."""
    set_console_columns(None)
    bar = OneLineProgressBar([FakeStatus()], delay_draw=0)
    bar.fp = io.StringIO()

    assert console_columns() is None
    # Whatever bluesky decided -- 79 with no tty, the real width with one.
    assert bar.ncols > 0


def test_an_absurd_width_is_refused(no_reported_width):
    """Two characters of bar is worse than a wrapped line."""
    set_console_columns(2)

    assert console_columns() == MIN_COLUMNS


def test_a_bad_width_is_ignored(no_reported_width):
    """A measurement that is not a number must not break the next move."""
    set_console_columns(60)
    set_console_columns("not a number")

    assert console_columns() == 60


def test_the_manager_builds_one_line_bars(no_reported_width):
    """What run_engine_init hands to RE.waiting_hook."""
    manager = progress_bar_manager()
    manager([FakeStatus()])
    # Before the watchdog thread wakes and draws to the real stdout.
    manager.pbar.done = True
    manager.pbar.fp = io.StringIO()

    assert isinstance(manager.pbar, OneLineProgressBar)
