"""Common base class for tabs in the Bluesky GUI upper pane.

To add a tab: subclass :class:`BaseTab`, set ``title``, override whichever
update hooks you need, then add the class to ``TABS`` in ``id4_common.gui.app``.
The window wires the poller signals to every tab automatically, so a tab only
has to say what it does with the values.

A tab that cannot work at every POLAR station also overrides
:meth:`BaseTab.unavailable_reason`; the window then shows an
:class:`UnavailableTab` in its place, carrying the reason it gave.
"""

from qtpy.QtCore import Qt
from qtpy.QtGui import QFontDatabase
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QSizePolicy
from qtpy.QtWidgets import QVBoxLayout
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

    @classmethod
    def unavailable_reason(cls, profile):
        """Why this tab cannot work at *profile*'s station, or None if it can.

        Consulted once, before the tab is built.  A *reason* rather than a
        bool because the window puts it on screen: a tab that is simply
        absent, or present and grey with nothing said, is indistinguishable
        from a dead IOC or a broken GUI, and that ambiguity is the thing this
        exists to remove.

        This is for what the *station* cannot do -- no diffractometer in this
        hutch -- and is answered from the declared profile, not from the
        registry: every station instantiates the same ``devices.yml``, so
        finding a device proves nothing about whether it is here.  For
        something that is applicable but not ready yet -- an IOC down, the
        kernel still starting -- return None and let the real tab show its own
        waiting state.
        """
        return None

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


class UnavailableTab(BaseTab):
    """Stands in for a tab that cannot run here, and says why.

    Subclasses :class:`BaseTab` rather than being a bare ``QWidget`` because
    MainWindow calls ``on_metadata``, ``on_kernel_values`` and
    ``on_kernel_state`` on every tab without checking what it got; the
    inherited no-ops are what make that safe.

    Used for two different things, distinguished by *failed*: a tab the
    station profile says does not apply, and a tab whose constructor raised.
    The second keeps one broken tab from taking the window down with it, and
    puts the traceback where the person who can act on it will see it.
    """

    #: The reason is often several lines; a scroll area would hide the point
    #: behind a scrollbar on a panel with nothing else in it.
    scrollable = False

    def __init__(self, title, reason, failed=False):
        """Show *reason* under *title*, as unavailable or as a failure."""
        super().__init__()
        self.title = title
        self.reason = reason
        self.failed = failed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)

        heading = QLabel(
            f"{title} did not load" if failed else f"{title} is not available"
        )
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        body = QLabel(reason)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignCenter)
        # Selectable so a traceback can be copied into a bug report rather
        # than retyped off the screen.
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if failed:
            body.setFont(fixed_font(body))
            body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout.addWidget(body)

        layout.addStretch(1)
