"""Flyscan live viewer, embedded as a tab.

The viewer itself is :class:`~id4_common.gui.flyscan.flyscan_live_gui.
LiveMainWindow`, vendored from the beamline analysis folder -- this module only
hosts it and tells it where the data is.  It reads the scan's HDF5 files in
SWMR mode on its own timer, so it needs nothing from the RunEngine and cannot
disturb an acquisition.

Two things are deliberately not eager.  The viewer is built the first time the
tab is shown rather than at start-up, so the h5py/matplotlib import and two
matplotlib canvases are not paid for by a session that never opens it, and an
unreadable ``/gdata`` degrades to a message in this tab instead of a GUI that
will not start.  And the folder is defaulted from the session's experiment path
only until the user browses somewhere else -- after that the choice is theirs
and the poll stops overriding it.
"""

import logging
from pathlib import Path

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QVBoxLayout

from .base import BaseTab

logger = logging.getLogger(__name__)


class FlyscanPlotTab(BaseTab):
    """Host the flyscan live viewer, pointed at the experiment folder."""

    title = "Flyscan plot"

    #: The viewer fills the pane; it scrolls its own panels.
    scrollable = False

    #: A live map is worth a window of its own on a second screen.
    detachable = True

    def __init__(self, parent=None):
        """Show a placeholder; the viewer is built on first show."""
        super().__init__(parent)

        self._viewer = None
        self._exp_path = None
        self._applied = None
        self._user_picked = False
        self._failed = False

        self._layout = QVBoxLayout(self)
        self._placeholder = QLabel("Loading the flyscan viewer…")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._placeholder)

    # ---------------------------------------------------------------- hooks
    def on_kernel_values(self, values):
        """Track the session's experiment path and adopt it as the folder.

        ``exp_path`` is *absent* -- not empty -- until ``experiment_setup()``
        has run, because the kernel-side property raises until then and the
        poller keeps only expressions that evaluated cleanly.  The reply also
        arrives once a second whether anything changed or not, hence the
        comparison against the cached value.
        """
        path = values.get("exp_path")
        if not path or path == self._exp_path:
            return
        self._exp_path = path
        if self._viewer is not None and not self._user_picked:
            self._apply_folder(path)

    def showEvent(self, event):
        """Build the viewer the first time the tab is actually looked at."""
        super().showEvent(event)
        self._ensure_viewer()

    # --------------------------------------------------------------- viewer
    def _ensure_viewer(self):
        """Construct the viewer once, or explain why it could not be."""
        if self._viewer is not None or self._failed:
            return

        # Imported here rather than at module scope: this pulls in h5py,
        # hdf5plugin and two matplotlib canvases, and a failure must cost this
        # tab only -- app.py imports the class at start-up to build TABS.
        try:
            from ..flyscan.flyscan_live_gui import LiveMainWindow
        except Exception as exc:  # noqa: BLE001 -- one broken tab, not a GUI
            logger.exception("Flyscan viewer unavailable")
            self._failed = True
            self._placeholder.setText(
                f"Flyscan viewer unavailable:\n{exc}\n\n"
                "The viewer needs h5py, hdf5plugin and matplotlib."
            )
            return

        folder = self._default_folder()
        self._viewer = LiveMainWindow(initial_folder=folder)
        self._applied = self._viewer.folder

        # Connected after the viewer's own handler, so by the time this runs
        # the dialog has been accepted or cancelled and the folder is settled.
        self._viewer.browse_btn.clicked.connect(self._on_browse_clicked)

        # An embedded widget never gets a closeEvent, so the viewer's own
        # teardown -- poll timer, worker threads, open SWMR handles -- has to
        # be triggered from the application quitting instead.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown)

        self._layout.removeWidget(self._placeholder)
        self._placeholder.hide()
        self._layout.addWidget(self._viewer)

    def _default_folder(self):
        """The experiment path if the kernel has offered one, else a fallback.

        ``session_cwd`` is the kernel's *process* directory -- a source
        checkout in the live session -- so it is only a last resort that gives
        the Browse dialog somewhere sane to start.
        """
        if self._exp_path:
            return self._exp_path
        return str(self.session_cwd or Path.cwd())

    def _apply_folder(self, path):
        """Point the viewer at *path* and remember that we did."""
        self._viewer.set_folder(path)
        self._applied = self._viewer.folder

    def _on_browse_clicked(self):
        """Stop tracking the session once the user has chosen a folder."""
        if self._viewer.folder != self._applied:
            self._user_picked = True

    def _shutdown(self):
        """Close the viewer so its timer, threads and files are released."""
        if self._viewer is not None:
            self._viewer.close()
