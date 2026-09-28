"""Main window and entry point for the POLAR Bluesky GUI.

Layout is a vertical splitter: parameter tabs on top, a full IPython console
below.  The console is a real Jupyter front end, so everything that works in
``ipython -i -c "from id4_common.startup import *"`` works here too.

Run with the ``polar-gui`` console script.
"""

import argparse
import logging
import os
import sys

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtpy.QtCore import QSettings
from qtpy.QtCore import Qt
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QComboBox
from qtpy.QtWidgets import QDialog
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QMainWindow
from qtpy.QtWidgets import QMessageBox
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QScrollArea
from qtpy.QtWidgets import QSizePolicy
from qtpy.QtWidgets import QSpinBox
from qtpy.QtWidgets import QSplitter
from qtpy.QtWidgets import QTabWidget
from qtpy.QtWidgets import QToolBar
from qtpy.QtWidgets import QVBoxLayout
from qtpy.QtWidgets import QWidget

from ..mcp_server.bridge import ECHO_PREFIX as LLM_ECHO_PREFIX
from . import config
from .docstream import DocumentStream
from .kernel import KernelSession
from .kernel import StatusPoller
from .tabs.agent import AgentTab
from .tabs.detectors import DetectorsTab
from .tabs.devices import DevicesTab
from .tabs.flyscanplot import FlyscanPlotTab
from .tabs.hkl import HklTab
from .tabs.macro import MacroTab
from .tabs.scan import ScanTab
from .tabs.scanhistory import ScanHistoryTab
from .tabs.scanplot import ScanPlotTab
from .tabs.status import DEFAULT_LOG_NAME
from .tabs.status import LOG_ENABLED_KEY
from .tabs.status import LOG_PATH_KEY
from .tabs.status import StatusTab
from .transcript import ConsoleTranscript

logger = logging.getLogger(__name__)

#: Tabs shown in the upper pane, in order.  Add new BaseTab subclasses here.
TABS = [
    StatusTab,
    AgentTab,
    ScanTab,
    MacroTab,
    ScanPlotTab,
    ScanHistoryTab,
    HklTab,
    DetectorsTab,
    DevicesTab,
    FlyscanPlotTab,
]

#: Console font size limits, in points.
MIN_FONT_POINTS = 6
MAX_FONT_POINTS = 32

#: Used only when Qt reports a pixel-sized font, so there is no point size to
#: adopt as the starting value.
FALLBACK_FONT_POINTS = 10

#: Point size for the rest of the window -- tabs, tables, toolbar, labels.
#: Qt's desktop default is small on the hutch displays, and unlike the
#: console there is no per-user control for it, so it is pinned here.  The
#: console is deliberately *not* covered: qtconsole owns its own font, sized
#: from the toolbar spin box and remembered in QSettings, so the two are set
#: independently.
UI_FONT_POINTS = 14

#: Console background choices, mapped to qtconsole ``set_default_style``
#: schemes.  "black" is the default: a dark console is easier on the eyes in a
#: dimmed hutch, and it matches the terminal sessions already in use.
BACKGROUNDS = {"black": "linux", "white": "lightbg"}
DEFAULT_BACKGROUND = "black"

#: Where console appearance choices are remembered between sessions.  From
#: ``gui/config.py`` so the four stations cannot drift into separate settings
#: scopes by an edit in one file and not the others.
SETTINGS_ORG = config.QSETTINGS_ORG
SETTINGS_APP = config.QSETTINGS_APP
FONT_SIZE_KEY = "console/font_size"
BACKGROUND_KEY = "console/background"

_STATE_TEXT = {
    "idle": "kernel: idle",
    "busy": "kernel: busy",
    "dead": "kernel: not running",
}


class _DetachedTab(QDialog):
    """A tab pulled out of the tab bar, living in its own window.

    A ``QDialog`` parented to the main window rather than a bare window, so it
    stays associated with the session it belongs to and is destroyed with it --
    quitting cannot leave a stray plot behind.  ``Qt.Window`` is what gives it
    a real title bar and a taskbar entry despite the parent.
    """

    def __init__(self, holder, title, parent, on_close):
        """Wrap *holder* in a window, calling *on_close* when it is closed."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self._on_close = on_close

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(holder)
        # removeTab() hides the page on its way out, and an explicitly hidden
        # child stays hidden when its new parent is shown -- without this the
        # window comes up empty.
        holder.show()
        self.resize(900, 600)

    def closeEvent(self, event):  # noqa: N802 - Qt naming
        """Hand the tab back to the tab bar."""
        self._on_close()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    """Bluesky session window: parameter tabs above, IPython console below."""

    def __init__(self, cwd, parent=None):
        """Start a kernel in *cwd* and build the window around it."""
        super().__init__(parent)
        # Four stations may be open at once on one desktop, so the title has
        # to say which one this is.
        self.setWindowTitle(
            config.WINDOW_TITLE.format(station=config.station())
        )
        self.resize(1100, 900)

        self.session = KernelSession(cwd)
        manager, client = self.session.start()

        # Set by _build_tabs() if the Agent tab is in TABS; the restart path
        # has to be able to disarm it whether or not it is.
        self._agent_tab = None
        # Detached tabs, keyed by the BaseTab: its window, the widget actually
        # taken out of the tab bar (the scroll-area holder, when there is one)
        # and the position to put it back in.
        self._detached = {}
        self._holders = {}
        self._closing = False
        self.console = self._build_console(manager, client)
        self.tabs, self._tab_widgets = self._build_tabs()

        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.addWidget(self.tabs)
        self._splitter.addWidget(self.console)
        # Equal halves, both resizable; the user can drag the divider.
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([450, 450])
        self._even_split_done = False
        self.setCentralWidget(self._splitter)

        self._build_toolbar()

        # Live plotting happens here, in the GUI process; the kernel only
        # publishes documents.  See docstream.py for why it cannot draw itself.
        self.docstream = DocumentStream(parent=self)
        self.docstream.document.connect(self._on_document)
        self.docstream.start()

        # Appends the console's traffic to a file.  Built before the poller, so
        # the very first drain of iopub -- which already holds everything the
        # bootstrap has printed -- has somewhere to go.
        self.transcript = ConsoleTranscript()
        self._resume_transcript(cwd)

        self.poller = StatusPoller(self.session, parent=self)
        self.poller.iopub_message.connect(self.transcript.handle)
        self.poller.iopub_message.connect(self._echo_llm)
        # Lets a tab request an occasional one-off expression, and run code
        # visibly in the console for anything with real consequence (see
        # BaseTab).
        for tab in self._tab_widgets:
            tab.poller = self.poller
            tab.console_execute = self.console.execute
            tab.session_cwd = cwd
            tab.transcript = self.transcript
            # The Session tab owns the log controls, and has to be told once
            # the transcript exists -- by then it may already be running.
            sync = getattr(tab, "sync_transcript", None)
            if sync is not None:
                sync()
        self.poller.metadata_changed.connect(self._on_metadata)
        self.poller.kernel_values_changed.connect(self._on_kernel_values)
        self.poller.kernel_state_changed.connect(self._on_kernel_state)

        # No kernel_restarted connection: that signal only fires for an
        # autorestart, which is disabled.  Deliberate restarts drive the
        # bootstrap from _do_restart() via the same ready handshake.
        self.session.ready.connect(self._on_kernel_ready)
        self.session.wait_until_ready()

    def _echo_llm(self, msg):
        """Show an MCP client's changes in the console, as they happen.

        The MCP server (:mod:`id4_common.mcp_server`) talks to this kernel on its
        own client, so nothing it does would otherwise appear in front of the
        operator.  Its dispatcher prints one ``[LLM]`` line per change, and
        this puts that line in the console.

        Driven from ``iopub_message`` rather than by setting qtconsole's
        ``include_other_output``: ``BaseFrontendMixin.from_here()`` compares
        **session** ids, not message ids, so that trait would also echo the
        status poller's empty cell as ``[remote] In [n]:`` once a second.  The
        session check below is what stops a ``_gui_mcp(...)`` call typed by
        hand in the console from being printed twice.
        """
        if msg.get("msg_type") != "stream":
            return
        text = (msg.get("content") or {}).get("text") or ""
        if not text.startswith(LLM_ECHO_PREFIX):
            return
        origin = (msg.get("parent_header") or {}).get("session")
        if origin and origin == self.console.kernel_client.session.session:
            return  # already on screen: the console asked for it itself
        self.console.append_stream(text)

    def _resume_transcript(self, cwd):
        """Restart console logging where the last session left it.

        Without this the ~40 s device-loading log -- the part of a session
        nobody is watching and everybody wants afterwards -- would only ever be
        captured by someone who pressed Start within seconds of launching.  A
        failed start is left to the Session tab to report; it must not stop the
        window from opening.
        """
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if not settings.value(LOG_ENABLED_KEY, False, type=bool):
            return
        path = settings.value(LOG_PATH_KEY, "", type=str)
        if not path:
            path = os.path.join(cwd, DEFAULT_LOG_NAME)
        self.transcript.start(path)

    def _on_kernel_ready(self):
        """Bootstrap Bluesky and begin polling, once the kernel can answer."""
        self.session.bootstrap(self.console, self.docstream.publisher_code())
        self.poller.start()
        self.restart_button.setEnabled(True)

    def _on_document(self, name, doc):
        """Forward a streamed document to every tab that wants one."""
        for tab in self._tab_widgets:
            handler = getattr(tab, "on_document", None)
            if handler is not None:
                handler(name, doc)

    def _build_console(self, manager, client):
        console = RichJupyterWidget()
        console.kernel_manager = manager
        console.kernel_client = client
        # The toolbar button runs its own confirmation dialog.
        console.confirm_restart = False
        console.clear_on_kernel_restart = True
        # No signature popup on "(": it appears over the line being typed,
        # which is exactly where the operator is looking while writing a move.
        # Tab completion and ``?`` still work, so the help is a keystroke away
        # when it is actually wanted.
        console.enable_calltips = False

        # Apply the background before the window is shown, so a dark console
        # never flashes white on startup.
        self._background = self._saved_background()
        console.set_default_style(BACKGROUNDS[self._background])
        return console

    def _build_tabs(self):
        tabs = QTabWidget()
        widgets = []
        for tab_class in TABS:
            tab = tab_class()
            if isinstance(tab, AgentTab):
                # A move waiting behind another tab is a move nobody approves.
                self._agent_tab = tab
                index = len(widgets)
                tab.request_arrived.connect(
                    lambda idx=index: self.tabs.setCurrentIndex(idx)
                )
            if tab.scrollable:
                # Without this the tallest page sets the tab widget's minimum
                # height (595 px with these tabs) and the splitter can never
                # give the console its half.
                holder = QScrollArea()
                holder.setWidget(tab)
                holder.setWidgetResizable(True)
                holder.setFrameShape(QScrollArea.NoFrame)
                tabs.addTab(holder, tab.title)
            else:
                holder = tab
                tabs.addTab(tab, tab.title)
            self._holders[holder] = tab
            if tab.detachable:
                tabs.setTabToolTip(
                    tabs.count() - 1,
                    "Double-click to open in a separate window.",
                )
            widgets.append(tab)
        tabs.tabBarDoubleClicked.connect(self._detach_tab)
        # Let the splitter shrink the whole stack; each page scrolls instead.
        tabs.setMinimumHeight(120)
        return tabs, widgets

    def _detach_tab(self, index):
        """Move a detachable tab into its own window, on double-click.

        The tab keeps receiving documents and poll results while it is out --
        ``_tab_widgets`` is what the broadcasts iterate, and that does not
        change with the widget's parent, which is the whole point of being able
        to watch a plot while working in another tab.
        """
        if index < 0:
            return
        holder = self.tabs.widget(index)
        tab = self._holders.get(holder)
        if tab is None or not tab.detachable or tab in self._detached:
            return
        self.tabs.removeTab(index)
        window = _DetachedTab(
            holder,
            f"{tab.title} — {self.windowTitle()}",
            self,
            lambda tab=tab: self._reattach_tab(tab),
        )
        self._detached[tab] = (window, holder, index)
        window.show()

    def _reattach_tab(self, tab):
        """Put a detached tab back where it came from."""
        entry = self._detached.pop(tab, None)
        if entry is None or self._closing:
            return
        _window, holder, index = entry
        # Out of the dialog's layout first, or insertTab inherits its parent.
        holder.setParent(None)
        index = min(index, self.tabs.count())
        self.tabs.insertTab(index, holder, tab.title)
        self.tabs.setTabToolTip(
            index, "Double-click to open in a separate window."
        )
        self.tabs.setCurrentIndex(index)

    def _build_toolbar(self):
        toolbar = QToolBar("Session")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.restart_button = QPushButton("Restart Bluesky")
        self.restart_button.clicked.connect(self._on_restart_clicked)
        # Enabled by _on_kernel_ready(); restarting a kernel that has not
        # finished starting leaves the session in a confusing half state.
        self.restart_button.setEnabled(False)
        toolbar.addWidget(self.restart_button)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Console font: "))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(MIN_FONT_POINTS, MAX_FONT_POINTS)
        self.font_spin.setSuffix(" pt")
        self.font_spin.setToolTip(
            "Console font size.  Ctrl+= / Ctrl+- inside the console work too."
        )
        self.font_spin.setValue(self._initial_font_points())
        self.font_spin.valueChanged.connect(self._on_font_spin_changed)
        toolbar.addWidget(self.font_spin)
        # Keep the spin box honest when the size is changed from the console
        # itself via Ctrl+= / Ctrl+-.
        self.console.font_changed.connect(self._on_console_font_changed)

        toolbar.addWidget(QLabel("  Background: "))
        self.background_combo = QComboBox()
        self.background_combo.addItem("Black", "black")
        self.background_combo.addItem("White", "white")
        self.background_combo.setToolTip("Console background colour.")
        index = self.background_combo.findData(self._background)
        self.background_combo.setCurrentIndex(max(0, index))
        self.background_combo.currentIndexChanged.connect(
            self._on_background_changed
        )
        toolbar.addWidget(self.background_combo)

        # Push the state readout to the right-hand end of the toolbar.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.state_label = QLabel("kernel: starting…")
        toolbar.addWidget(self.state_label)

    def _saved_background(self):
        """Return the remembered background name, defaulting to black."""
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        name = settings.value(BACKGROUND_KEY, DEFAULT_BACKGROUND, type=str)
        return name if name in BACKGROUNDS else DEFAULT_BACKGROUND

    def _on_background_changed(self, index):
        """Switch the console background and remember the choice."""
        name = self.background_combo.itemData(index)
        if name not in BACKGROUNDS:
            return
        self._background = name
        # Changing the style sheet does not disturb the font size.
        self.console.set_default_style(BACKGROUNDS[name])
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(BACKGROUND_KEY, name)

    def _initial_font_points(self):
        """Return the remembered console font size, or the current one."""
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        saved = settings.value(FONT_SIZE_KEY, 0, type=int)
        if MIN_FONT_POINTS <= saved <= MAX_FONT_POINTS:
            self._apply_font_points(saved)
            return saved
        current = self.console.font.pointSize()
        if current > 0:
            return current
        # pointSize() is -1 when Qt resolved a pixel-sized desktop font.  Pin a
        # real point size rather than just displaying one, so the spin box and
        # the console cannot disagree about the current size.
        self._apply_font_points(FALLBACK_FONT_POINTS)
        return FALLBACK_FONT_POINTS

    def _apply_font_points(self, points):
        """Set the console font size, leaving the family alone."""
        font = self.console.font
        if font.pointSize() == points:
            return
        font.setPointSize(points)
        self.console.font = font

    def _on_font_spin_changed(self, points):
        """Apply and remember a font size chosen in the toolbar."""
        self._apply_font_points(points)
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(FONT_SIZE_KEY, points)

    def _on_console_font_changed(self):
        """Mirror a console-side font change back into the spin box."""
        points = self.console.font.pointSize()
        if points <= 0 or points == self.font_spin.value():
            return
        # Guard against bouncing back into _on_font_spin_changed.
        blocked = self.font_spin.blockSignals(True)
        self.font_spin.setValue(points)
        self.font_spin.blockSignals(blocked)
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(FONT_SIZE_KEY, points)

    def _on_metadata(self, metadata):
        for tab in self._tab_widgets:
            tab.on_metadata(metadata)

    def _on_kernel_values(self, values):
        for tab in self._tab_widgets:
            tab.on_kernel_values(values)

    def _on_kernel_state(self, state):
        self.state_label.setText(_STATE_TEXT.get(state, f"kernel: {state}"))
        for tab in self._tab_widgets:
            tab.on_kernel_state(state)

    def _on_restart_clicked(self):
        answer = QMessageBox.question(
            self,
            "Restart Bluesky",
            "Restart the Bluesky kernel?\n\n"
            "Variables defined in the console will be lost and all EPICS\n"
            "connections will be rebuilt.  This takes roughly 40 seconds.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.restart_button.setEnabled(False)
        self.state_label.setText("kernel: restarting…")
        # Deferred so the disabled button and label repaint before
        # restart_kernel() blocks for a second or two spawning the process.
        QTimer.singleShot(0, self._do_restart)

    def _do_restart(self):
        """Restart the kernel; _on_kernel_ready() re-runs the bootstrap.

        The poller is stopped for the duration so that only the readiness
        handshake is reading the shell channel.
        """
        self.poller.stop()
        self.poller.reset()
        if self._agent_tab is not None:
            # The kernel holding the pending request is going away, and an auto
            # window armed against the old session must not carry into the new
            # one -- the operator armed it for work that no longer exists.
            self._agent_tab.clear_auto_mode()
        # The console is about to be wiped; the log is not, so leave a marker
        # explaining why the transcript jumps back to In [1].
        self.transcript.note("kernel restarted")
        self.session.restart()
        # Autorestart is off, so qtconsole does not clear the console for us.
        self.console.reset(clear=True)
        self.session.wait_until_ready()

    def showEvent(self, event):  # noqa: N802 - Qt naming
        """Split the window evenly once the real height is known.

        setSizes() before the first show is measured against size hints, not
        the final geometry, so the even split has to be (re)applied here.
        """
        super().showEvent(event)
        if not self._even_split_done:
            self._even_split_done = True
            half = max(1, self._splitter.height() // 2)
            self._splitter.setSizes([half, half])

    def closeEvent(self, event):  # noqa: N802 - Qt naming
        """Stop polling and shut the kernel down so none is left orphaned."""
        # Detached windows are children, so Qt closes them with this one; the
        # flag stops their closeEvent trying to dock back into a dying window.
        self._closing = True
        self.poller.stop()
        self.transcript.stop()
        self.docstream.stop()
        for tab in self._tab_widgets:
            shutdown = getattr(getattr(tab, "model3d", None), "shutdown", None)
            if shutdown is not None:
                shutdown()
        try:
            self.console.kernel_client = None
        except Exception:  # noqa: BLE001 - best effort during teardown
            logger.debug("Could not detach console client.", exc_info=True)
        self.session.shutdown()
        super().closeEvent(event)


def main(argv=None):
    """Entry point for the ``polar-gui`` console script."""
    parser = argparse.ArgumentParser(
        prog="polar-gui",
        description="Qt interface for the POLAR Bluesky session.",
    )
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help=(
            "Working directory for the kernel.  Determines where data "
            "files, the console log and the MCP pointer are written "
            "(default: current directory)."
        ),
    )
    parser.add_argument(
        "--station",
        default=None,
        help=(
            "Station package to start: id4_b, id4_g, id4_h or id4_raman.  "
            "One checkout serves all four, so this decides which startup the "
            "kernel runs, which devices exist, and the name of the kernel "
            "pointer file an MCP client discovers.  Defaults to $ID4_STATION, "
            f"then {config.DEFAULT_STATION}."
        ),
    )
    args = parser.parse_args(argv)

    # Set before anything reads it: config.station() is consulted by the
    # window title, the pointer filename and the kernel's bootstrap import.
    if args.station:
        os.environ["ID4_STATION"] = args.station

    logging.basicConfig(level=logging.INFO)

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(config.WINDOW_TITLE.format(station=config.station()))

    # Before the window exists, so every widget is built with it.
    ui_font = app.font()
    ui_font.setPointSize(UI_FONT_POINTS)
    app.setFont(ui_font)

    window = MainWindow(cwd=args.cwd)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
