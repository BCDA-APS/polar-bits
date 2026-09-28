"""Common base class for tabs in the Bluesky GUI upper pane.

To add a tab: subclass :class:`BaseTab`, set ``title``, override whichever
update hooks you need, then add the class to ``TABS`` in ``id4_common.gui.app``.
The window wires the poller signals to every tab automatically, so a tab only
has to say what it does with the values.
"""

from qtpy.QtCore import Qt
from qtpy.QtGui import QFontDatabase
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QWidget

#: Shown when a value has not been read yet, so "pending" is visually distinct
#: from a value that is genuinely empty.
PLACEHOLDER = "—"


def fixed_font(widget):
    """Return the system monospace font at *widget*'s current point size.

    ``QFontDatabase.systemFont`` carries the desktop's own size, which
    ignores the application font set in ``app.main``.  Left alone, every
    monospace value stays at the desktop default while the labels around it
    scale, so the size is copied off the widget -- which has already
    inherited the application font -- before the family is swapped.
    """
    size = widget.font().pointSize()
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    if size > 0:
        font.setPointSize(size)
    return font


def value_label(text=PLACEHOLDER):
    """Return a monospace, selectable label for a displayed value."""
    label = QLabel(text)
    label.setFont(fixed_font(label))
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


class BaseTab(QWidget):
    """A tab in the upper pane.

    Subclasses override the hooks they care about; the defaults do nothing so a
    tab need only implement what it uses.
    """

    #: Text shown on the tab bar.
    title = "Tab"

    #: When True, MainWindow lets the tab be pulled out into its own window by
    #: double-clicking its label, and put back by closing that window.  Worth
    #: setting for a tab you would want to watch while working in another one
    #: -- a live plot, typically -- and not for the rest, where a stray
    #: double-click on the tab bar would just be a surprise.
    detachable = False

    #: When True, MainWindow puts the tab inside a scroll area.  Without this a
    #: tall page pins the whole splitter open -- the pages' minimum heights are
    #: what stop the console from getting its half of the window.  Set False
    #: for tabs that scroll themselves, or whose content must fill the pane
    #: (a matplotlib canvas).
    scrollable = True

    #: Set by MainWindow after the poller exists; lets a tab ask the kernel an
    #: occasional one-off question via :meth:`request`.
    poller = None

    #: Set by MainWindow to a callable running code *visibly* in the console.
    #: Used for anything with real-world consequence -- a diffractometer move,
    #: say -- so it lands in the session history like a typed command.
    console_execute = None

    #: Set by MainWindow to the kernel's working directory, where the data and
    #: the RunEngine metadata file live.  Tabs that read or write files should
    #: default to somewhere under it rather than to the GUI process's cwd.
    session_cwd = None

    #: Set by MainWindow to the shared :class:`~id4_common.gui.transcript.
    #: ConsoleTranscript`, which appends the console's traffic to a file.  The
    #: Session tab drives it; other tabs may read ``transcript.path`` and
    #: ``transcript.active`` to report on it.
    transcript = None

    def run_in_console(self, code):
        """Run *code* in the console, as though the user had typed it."""
        if self.console_execute is None:
            return False
        self.console_execute(code)
        return True

    def request(self, expressions):
        """Ask the kernel to evaluate *expressions* on the next idle poll.

        Results arrive in :meth:`on_kernel_values` keyed the same way.
        """
        if self.poller is not None:
            self.poller.request_once(expressions)

    def on_metadata(self, metadata):
        """Handle a fresh read of the session's ``RE.md`` identity fields.

        Called only when one of them changes, and only while the kernel is
        idle enough to answer the poll -- a tab that needs to move during a
        scan wants :meth:`on_document` instead.
        """

    def on_kernel_values(self, values):
        """Handle evaluated ``user_expressions``.

        Only called while the kernel is idle.  Keys whose expression raised are
        absent from *values*.
        """

    def on_kernel_state(self, state):
        """Handle a kernel state change: ``"idle"``, ``"busy"`` or ``"dead"``."""
