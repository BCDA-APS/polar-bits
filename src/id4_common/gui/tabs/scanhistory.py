"""Plot a scan that has already finished, by number.

The Live plot tab follows whatever the beamline is doing; this one shows the
scan you ask for and stays there.  Two tabs rather than one tab with a mode:
nothing has to decide what a running scan should do to a plot you are reading,
because the answer is nothing.

Everything about the drawing is inherited from
:class:`~id4_common.gui.tabs.scanplot.ScanPlotTab` -- selectors, I0
normalisation, the derivative and its reference curve, the peak statistics and
their markers, and the 2D mesh rendering.  Only the source of the data differs:
:mod:`~id4_common.gui.scanreader` reads the run out of the catalog in this
process (see its docstring for why not the kernel), and the document handlers
are then fed by hand rather than by the live stream.

The "Go to" buttons are hidden here.  Driving the beamline onto a peak measured
in some earlier scan is not something this tab should offer.
"""

import logging

from qtpy.QtCore import QThread
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QSpinBox

from .. import scanreader
from .scanplot import PRIMARY
from .scanplot import ScanPlotTab

logger = logging.getLogger(__name__)

#: Highest scan number the spin box will take.  Scan ids are per-catalog and
#: run into the tens of thousands over a cycle.
MAX_SCAN_ID = 1_000_000

#: How long to let a reader finish at shutdown before giving up on it.
WORKER_SHUTDOWN_WAIT_MS = 8000


class _ReadWorker(QThread):
    """Read one scan off the catalog, away from the Qt thread.

    The first read also imports databroker and opens the catalog, about 6.7 s
    together; on the GUI thread that would be a visible freeze.  Modelled on
    ``flyscan_gui.ProcessWorker``, which is the pattern this package already
    uses for slow work.
    """

    done = Signal(int, object)  # generation, payload dict

    def __init__(self, generation, catalog, instrument, scan_id):
        """Read *scan_id*, tagging the reply with *generation*."""
        super().__init__()
        self._generation = generation
        self._catalog = catalog
        self._instrument = instrument
        self._scan_id = scan_id

    def run(self):
        """Fetch, and report the failure as a payload rather than raising."""
        try:
            payload = scanreader.read_scan(
                self._catalog,
                self._instrument,
                self._scan_id,
            )
        except Exception as exc:  # noqa: BLE001 - a thread must not die loudly
            logger.exception("Reading scan %s failed.", self._scan_id)
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        self.done.emit(self._generation, payload)


class ScanHistoryTab(ScanPlotTab):
    """Draw a finished scan fetched from the catalog."""

    title = "Scan plot"

    def __init__(self, parent=None):
        """Add the scan picker, and take the motor buttons away."""
        super().__init__(parent)

        self._wanted = None  # scan id asked for but not yet answered
        self._loaded = None  # scan id currently on the canvas
        self._payload = None  # last reply, so the view can be re-rendered
        # Which catalog, and which station's runs within it.  Both come off the
        # session metadata broadcast; until they do, a load would have to guess
        # the station, and scan ids repeat across stations.
        self._catalog_name = None
        self._instrument = None
        # Bumped per load, so a slow reply for a scan number the user has since
        # changed is dropped instead of overwriting the newer plot.
        self._generation = 0
        # Every reader in flight.  A set, not one attribute: two quick Loads
        # would otherwise drop the first thread's only reference while it ran,
        # which is the "QThread: Destroyed while thread is still running" abort.
        self._workers = set()
        app = QApplication.instance()
        if app is not None:
            # An embedded tab never gets a closeEvent, and a cold read can be
            # six seconds long -- without this, quitting can tear a live thread
            # down underneath itself.
            app.aboutToQuit.connect(self._shutdown)

        # Moving the real axis onto a peak from an old scan is not this tab's
        # business.  Hidden rather than removed: the inherited peak row still
        # enables and disables them by name.
        for button in self._peak_buttons.values():
            button.hide()

        self._insert_picker()
        self._status.setText("Enter a scan number and press Load.")

    # ---------------------------------------------------------------- widgets
    def _insert_picker(self):
        """Put the scan picker above the status line."""
        self._scan_spin = QSpinBox()
        self._scan_spin.setRange(1, MAX_SCAN_ID)
        self._scan_spin.setKeyboardTracking(False)
        self._scan_spin.setToolTip(
            "Scan number to plot.  The most recent scan with this number in "
            "this station's catalog is the one shown."
        )
        self._scan_spin.setMaximumWidth(120)

        self._load_button = QPushButton("Load")
        self._load_button.clicked.connect(self._on_load)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel("Scan #"))
        row.addWidget(self._scan_spin)
        row.addWidget(self._load_button)
        row.addStretch(1)

        # layout() is the QVBoxLayout built by ScanPlotTab; the status label is
        # its last row, so the picker goes directly above it.
        layout = self.layout()
        layout.insertLayout(layout.count() - 1, row)

    # ----------------------------------------------------------------- source
    def on_document(self, name, doc):
        """Ignore the live stream: this tab shows the scan you asked for."""

    def on_metadata(self, metadata):
        """Learn which catalog, and which station's runs within it.

        Broadcast once a second while the kernel is idle, and only when a value
        changes, so this arrives early and then stays put.  ``tabs/status.py``
        reads the same two keys for its display.
        """
        super().on_metadata(metadata)
        self._catalog_name = metadata.get("databroker_catalog")
        self._instrument = metadata.get("instrument_name")

    def _on_load(self):
        """Read the scan in the spin box, on a worker thread.

        Deliberately not gated on the kernel: the catalog is read here in the
        GUI process, so a running scan is no obstacle -- which is the point.
        """
        if not self._catalog_name:
            # Without the station filter a scan id is ambiguous: roughly half
            # the catalog belongs to other beamlines and the numbers repeat.
            self._status.setText(
                "Waiting for the session to report which catalog to read…"
            )
            return

        self._wanted = int(self._scan_spin.value())
        self._generation += 1

        if scanreader.is_connected(self._catalog_name, self._instrument):
            self._status.setText(f"Loading scan {self._wanted}…")
        else:
            # The first read imports databroker and opens the catalog.
            self._status.setText(
                f"Loading scan {self._wanted} (connecting to the catalog, "
                "this first one takes a few seconds)…"
            )

        worker = _ReadWorker(
            self._generation,
            self._catalog_name,
            self._instrument,
            self._wanted,
        )
        worker.done.connect(self._on_read)
        # finished, not done: done is emitted from inside run(), with the
        # thread still alive.
        worker.finished.connect(self._forget_worker)
        self._workers.add(worker)
        worker.start()

    def _forget_worker(self):
        """Drop a reader once Qt reports its thread has ended."""
        worker = self.sender()
        if worker is not None:
            self._workers.discard(worker)

    def _shutdown(self):
        """Let any reader finish before the process goes away."""
        for worker in list(self._workers):
            if worker.isRunning():
                worker.wait(WORKER_SHUTDOWN_WAIT_MS)

    def _on_read(self, generation, data):
        """Draw what the reader came back with, if it is still wanted."""
        if generation != self._generation:
            # The user has asked for a different scan since; this reply is for
            # the old one and must not overwrite the newer plot.
            return
        if not isinstance(data, dict):
            self._status.setText("Unexpected reply from the catalog reader.")
            return
        error = data.get("error")
        if error:
            self._status.setText(f"Scan {self._wanted}: {error}")
            return
        self._payload = data
        try:
            self._show_scan(data)
        except Exception:  # noqa: BLE001 - a bad payload must not kill the tab
            logger.exception("Failed to render scan history payload.")
            self._status.setText(f"Scan {self._wanted}: could not be plotted.")

    # ------------------------------------------------------------------ render
    def _show_scan(self, data):
        """Draw *data*, by feeding the inherited document handlers."""
        columns = data.get("columns") or {}
        if not columns:
            self._status.setText(
                f"Scan {data.get('scan_id', self._wanted)}: nothing plottable."
            )
            return

        # _on_start does the real work: resets state, clears the axes, sets the
        # title, picks the x axis and works out any mesh geometry.
        self._on_start(
            {
                "scan_id": data.get("scan_id"),
                "plan_name": data.get("plan_name") or "scan",
                "time": data.get("time"),
                "hints": data.get("hints") or {},
                "shape": data.get("shape") or [],
                "extents": data.get("extents") or [],
            }
        )

        detectors = [f for f in (data.get("detectors") or []) if f in columns]
        self._on_descriptor(
            {
                "name": PRIMARY,
                "uid": f"history-{data.get('uid')}",
                "data_keys": {
                    field: {"dtype": "number", "shape": []} for field in columns
                },
                "hints": {"detectors": {"fields": detectors}},
            }
        )

        # Bulk fill rather than thousands of _on_event calls: same end state,
        # one redraw.
        x_field = self._x_field
        length = len(columns.get(x_field) or [])
        self._x_data = list(columns.get(x_field) or [])
        for field, series in self._series.items():
            values = columns.get(field) or []
            series["y"] = list(values[:length])

        if self._grid:
            self._fill_grid(columns, length)
        else:
            for field, series in self._series.items():
                if self._shown(series) and series["line"] is None:
                    self._create_line(field, series)
            self._sync_references()
            self._rescale()

        self._loaded = data.get("scan_id")
        # After _show_scan, never before: _on_start runs _reset_state, which
        # clears these.  The parent draws both streams; this tab only supplies
        # the data and lets the picker appear.
        self._dichro_columns = data.get("dichro") or {}
        if self._dichro_columns:
            self._stream_row.show()
        self._update_peak()
        self._update_status()

    def _fill_grid(self, columns, length):
        """Place every point of a mesh scan, then draw it."""
        slow = columns.get(self._grid["slow"]) or []
        fast = columns.get(self._grid["fast"]) or []
        self._grid_cells = []
        for index in range(min(length, len(slow), len(fast))):
            point = {
                self._grid["slow"]: slow[index],
                self._grid["fast"]: fast[index],
            }
            self._anchor_grid(point)
            cell = self._grid_indices(point)
            self._grid_cells.append(cell)
        self._rebuild_grid()

    def _update_status(self):
        """Say which scan is on screen, instead of the live tab's wording."""
        if self._stream != PRIMARY:
            # The parent says which stream and how many points; prefix the scan.
            super()._update_status()
            self._status.setText(f"Scan {self._loaded} — {self._status.text()}")
            return
        if self._loaded is None:
            return
        normalised = f", normalised by {self._monitor}" if self._monitor else ""
        self._status.setText(
            f"Scan {self._loaded} — {len(self._x_data)} points{normalised}."
        )
