"""A motor-move progress bar that always fits on one row.

Bluesky's ``TerminalProgressBar`` measures the terminal once, when the bar is
built::

    self.ncols = _screen_shape_wrapper()(sys.stdout)[0] or 79

Inside an IPython kernel -- the GUI's console -- ``sys.stdout`` is an
``ipykernel`` stream with no tty behind it, so that measurement fails and the
bar is drawn 79 characters wide no matter how wide the console really is.
Anything narrower wraps the line onto a second display row, and the redraw
(one ``\\n`` and one cursor-up per meter) then counts rows wrong and leaves a
trail of half-erased bars behind the moving motor.

A plain ``ipython`` terminal does not have this problem: there the ioctl
succeeds and the real width is used.  Only the GUI has to be told, which it
does through :func:`set_console_columns` -- see
``_gui_set_console_columns`` in :mod:`id4_common.gui.kernel`.
"""

import logging

from bluesky.utils import ProgressBarManager
from bluesky.utils import TerminalProgressBar

logger = logging.getLogger(__name__)

#: Bluesky reads ``delay_draw`` from its own factory; keep its value so a
#: move that finishes immediately still does not flash a bar.
DELAY_DRAW = 0.2

#: Narrower than this a bar says nothing, so refuse to shrink past it: better
#: a wrapped line in a console two inches wide than an unreadable stub.
MIN_COLUMNS = 20

#: Console width in characters, as last reported by the GUI.  ``None`` means
#: nobody has said, so bluesky's own measurement stands.
_columns = None


def set_console_columns(columns):
    """Tell the progress bar how wide the console is, in characters.

    Called from the GUI whenever the console is resized or its font changes.
    Pass ``None`` to go back to bluesky's own measurement.  Takes effect for
    the *next* bar: the width is read once per move, when the bar is built.
    """
    global _columns
    if columns is None:
        _columns = None
        return
    try:
        _columns = max(int(columns), MIN_COLUMNS)
    except (TypeError, ValueError):
        logger.warning("Ignoring bad console width %r.", columns)


def console_columns():
    """Return the width to draw at, or None to keep bluesky's measurement."""
    return _columns


class OneLineProgressBar(TerminalProgressBar):
    """A bluesky progress bar that never spills onto a second row."""

    def __init__(self, status_objs, delay_draw=DELAY_DRAW):
        """Build the bar, then narrow it to the console the GUI reported."""
        super().__init__(status_objs, delay_draw=delay_draw)
        columns = console_columns()
        if columns:
            self.ncols = columns

    def draw(self):
        """Clip every meter to one row, then draw as usual.

        The last word on width.  tqdm honours ``ncols`` for the bar it
        formats, but a long device name in the prefix can still push the line
        past it, and the "[In progress. No progress bar available.]" fallback
        is not formatted by tqdm at all.
        """
        # An RLock, so re-entering it in super().draw() is fine.
        with self.lock:
            self.meters = [meter[: self.ncols] for meter in self.meters]
            super().draw()


def progress_bar_manager():
    """Return a ``ProgressBarManager`` that builds one-line progress bars."""
    return ProgressBarManager(
        pbar_factory=lambda status_objs: OneLineProgressBar(
            status_objs, delay_draw=DELAY_DRAW
        )
    )
