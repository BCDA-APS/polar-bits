"""Live (mid-scan) flyscan viewer.

A Qt GUI that polls a flyscan's HDF5 files in SWMR mode and updates
the 2D map as data lands on disk. Reuses the Eiger and Vortex tab widgets
from :mod:`flyscan_gui` so the controls, previews, and map look identical
to the post-scan viewer.

The Eiger preview has a frame slider under it: dragging it steps through the
frames written so far, and a red circle on the position map below marks where
that frame was taken.

Run with::

    python flyscan_live_gui.py [--folder NdFeB] [--scan 244]
"""

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from qtpy import QtCore, QtWidgets

from .flyscan_gui import (
    DEFAULT_EIGER_ROI,
    DEFAULT_VORTEX_ROI,
    PROCESS_BATCH,
    EigerTab,
    ProcessWorker,
    VortexTab,
    _is_i0_usable,
    _read_eiger_frame,
    _read_vortex_spectrum,
    _resolve_h5,
)
from .live_flyscan import LiveScanReader, find_latest_scan
from .process_flyscan import (
    describe_partial_groups,
    display_roi_to_raw,
    group_for_frame,
    raw_roi_to_display,
    read_scan_geometry,
)


DEFAULT_POLL_MS = 1000
DEFAULT_IDLE_TIMEOUT_S = 30
# Dragging the frame slider emits a value per pixel; coalesce those into one
# HDF5 read once the user pauses for this long.
FRAME_LOAD_DEBOUNCE_MS = 120
# How long closeEvent gives a worker thread to finish before giving up on it.
WORKER_SHUTDOWN_WAIT_MS = 3000

#: Written by the post-scan dichro viewer in the experiment's analysis folder.
#: Shared rather than duplicated so an ROI set in either viewer is the one the
#: other starts from.
CONFIG_FILENAME = "flyscan_gui_dichro.config.json"

#: Spin boxes emit on every step while held, so the write is coalesced.
ROI_SAVE_DEBOUNCE_MS = 400


def _config_path(folder):
    """The shared config for the experiment *folder* belongs to, or None.

    The dichro viewer keeps it beside itself in the analysis directory and
    finds it with ``os.getcwd()``, which is no use here -- this GUI runs from
    the polar-bits checkout.  The analysis directory is a sibling of the data
    tree, so it is found by walking up from the sample folder instead.
    """
    if not folder:
        return None
    try:
        here = Path(folder).resolve()
    except OSError:
        return None
    for base in (here, *here.parents):
        analysis = base / "analysis"
        if analysis.is_dir():
            return analysis / CONFIG_FILENAME
    return None


def _load_config(folder):
    """Read the shared config, or an empty dict if it is missing or broken."""
    path = _config_path(folder)
    if path is None:
        return {}
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _update_config(folder, updates):
    """Merge *updates* into the shared config, leaving every other key alone.

    Read-modify-write rather than a plain dump: the file belongs to the dichro
    viewer as much as to this one, and it holds scan numbers, folder history
    and display settings that are none of our business.
    """
    path = _config_path(folder)
    if path is None:
        return False
    data = _load_config(folder)
    data.update(updates)
    try:
        with open(path, "w") as handle:
            json.dump(data, handle, indent=2)
    except OSError:
        return False
    return True


class _ElidingLabel(QtWidgets.QLabel):
    """A label that shortens its text rather than widening its window.

    A plain QLabel reports the full width of its text as its *minimum*, so a
    long data path pins the control bar -- and with it the whole viewer -- to a
    width the user cannot shrink below.  Here the path is elided in the middle
    instead, which keeps the sample folder at the end of it readable, and the
    untruncated path goes on the tooltip.
    """

    #: Enough to keep a useful fragment of a path visible.
    _MIN_WIDTH = 120

    def __init__(self, text="", parent=None):
        """Show *text*, elided to whatever width the layout ends up giving."""
        super().__init__(text, parent)
        self._full = text
        self.setMinimumWidth(self._MIN_WIDTH)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.setToolTip(text)

    def setText(self, text):  # noqa: N802 - Qt naming
        """Remember the full text, then show as much of it as fits."""
        self._full = text
        self.setToolTip(text)
        self._elide()

    def full_text(self):
        """The text as given, before elision."""
        return self._full

    def resizeEvent(self, event):  # noqa: N802 - Qt naming
        """Re-elide for the new width."""
        super().resizeEvent(event)
        self._elide()

    def minimumSizeHint(self):  # noqa: N802 - Qt naming
        """Ask only for the floor, never for the width of the whole text."""
        size = super().minimumSizeHint()
        size.setWidth(self._MIN_WIDTH)
        return size

    def _elide(self):
        """Fit ``_full`` into the current width, middle-elided."""
        room = max(self.width() - 4, 40)
        super().setText(self.fontMetrics().elidedText(
            self._full, QtCore.Qt.ElideMiddle, room,
        ))


class LiveMainWindow(QtWidgets.QMainWindow):
    def __init__(self, initial_folder=None):
        super().__init__()
        self.setWindowTitle("Flyscan live viewer")
        self.resize(1300, 900)

        self._folder = initial_folder or ""
        self._scan = None
        self._reader = None        # LiveScanReader, alive while live
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._tick_worker = None   # in-flight tick worker, if any
        # Every in-flight side job (previews, re-process), not just the last
        # one -- see _track_worker.
        self._side_workers = set()
        self._busy = False         # gate so we don't queue ticks on top of each other
        self._reprocess_pending = None  # ("eiger"|"vortex", roi) — handled after current tick
        self._pending_switch = None     # scan number to switch to after current tick
        self._auto_latest = False  # mirrors self.auto_chk.isChecked()
        self._waiting_no_scan = False   # auto mode, no scan file detected (or current idle)

        # State of the running scan.
        self._last_result = None
        self._eiger_preview_loaded = False
        self._vortex_preview_loaded = False
        self._eiger_preview_pending = False
        self._vortex_preview_pending = False
        self._start_time = None

        # Eiger frame browsing (slider under the preview).
        self._n_eiger_frames = 0
        self._frame_wanted = None   # index asked for but not yet read
        self._frame_busy = False    # a frame read is in flight
        self._frame_worker = None
        self._scan_gen = 0          # bumped on every reset, so a frame that
                                    # arrives late for an old scan is dropped
        self._frame_timer = QtCore.QTimer(self)
        self._frame_timer.setSingleShot(True)
        self._frame_timer.timeout.connect(self._maybe_load_frame)

        # Signature of the partial-exposure list currently on screen, so the
        # tables are only rebuilt when the flags actually change.
        self._partial_sig = None
        self._geometry_loaded = False
        self._geometry_worker = None

        # The naming convention for each stream is cached per-scan inside the
        # LiveScanReader; the GUI only needs the folder name for preview reads.

        # ---- Top control bar ---------------------------------------------
        self.folder_label = _ElidingLabel(self._folder or "(no folder)")
        self.folder_label.setStyleSheet("QLabel { color: #444; }")
        self.browse_btn = QtWidgets.QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse_folder)

        self.scan_spin = QtWidgets.QSpinBox()
        self.scan_spin.setMaximum(999_999)
        self.scan_spin.setValue(244)

        self.auto_chk = QtWidgets.QCheckBox("Auto: latest scan")
        self.auto_chk.toggled.connect(self._on_auto_toggled)

        self.start_btn = QtWidgets.QPushButton("Start Live")
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn = QtWidgets.QPushButton("Stop Live")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        self.reprocess_btn = QtWidgets.QPushButton("Re-process")
        self.reprocess_btn.setToolTip(
            "Re-process the scan with the ROI currently set in the tab below."
        )
        self.reprocess_btn.clicked.connect(self._on_reprocess)
        self.reprocess_btn.setEnabled(False)

        self.norm_chk = QtWidgets.QCheckBox("Normalize by I0")
        self.norm_chk.setEnabled(False)
        self.norm_chk.stateChanged.connect(self._redraw_current_map)

        self.style_combo = QtWidgets.QComboBox()
        self.style_combo.addItems(["Scatter", "Tricontourf"])
        self.style_combo.currentIndexChanged.connect(self._redraw_current_map)


        self.poll_spin = QtWidgets.QSpinBox()
        self.poll_spin.setRange(100, 10_000)
        self.poll_spin.setSingleStep(100)
        self.poll_spin.setValue(DEFAULT_POLL_MS)
        self.poll_spin.setSuffix(" ms")

        self.idle_spin = QtWidgets.QSpinBox()
        self.idle_spin.setRange(5, 3600)
        self.idle_spin.setValue(DEFAULT_IDLE_TIMEOUT_S)
        self.idle_spin.setSuffix(" s")

        # Two rows, not one: on a single row the controls set a minimum width
        # of ~1850 px, which the user cannot shrink the window below even
        # though the plots themselves need far less.  What picks the scan sits
        # with the folder; what runs and draws it goes underneath.
        top_first = QtWidgets.QHBoxLayout()
        top_first.setContentsMargins(0, 0, 0, 0)
        top_first.addWidget(QtWidgets.QLabel("Folder:"))
        top_first.addWidget(self.folder_label, 1)
        top_first.addWidget(self.browse_btn)
        top_first.addSpacing(12)
        top_first.addWidget(QtWidgets.QLabel("Scan #:"))
        top_first.addWidget(self.scan_spin)
        top_first.addWidget(self.auto_chk)
        top_first.addSpacing(12)
        top_first.addWidget(self.start_btn)
        top_first.addWidget(self.stop_btn)

        top_second = QtWidgets.QHBoxLayout()
        top_second.setContentsMargins(0, 0, 0, 0)
        top_second.addWidget(self.reprocess_btn)
        top_second.addSpacing(12)
        top_second.addWidget(self.norm_chk)
        top_second.addWidget(QtWidgets.QLabel("Style:"))
        top_second.addWidget(self.style_combo)
        top_second.addSpacing(12)
        top_second.addWidget(QtWidgets.QLabel("Poll:"))
        top_second.addWidget(self.poll_spin)
        top_second.addWidget(QtWidgets.QLabel("Idle:"))
        top_second.addWidget(self.idle_spin)
        top_second.addStretch(1)

        top = QtWidgets.QVBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addLayout(top_first)
        top.addLayout(top_second)

        top_widget = QtWidgets.QWidget()
        top_widget.setLayout(top)

        # ---- Tabs -------------------------------------------------------
        # Reuse the post-scan widgets; we never emit their `process_requested`
        # signal — Re-process is driven by our own top-bar button.
        self.tabs = QtWidgets.QTabWidget()
        self.eiger_tab = EigerTab()
        self.vortex_tab = VortexTab()
        # Hide the in-tab Process button to keep the controls unambiguous.
        self.eiger_tab.process_btn.hide()
        self.vortex_tab.process_btn.hide()
        self.eiger_tab.frame_requested.connect(self._on_frame_requested)
        self.tabs.addTab(self.eiger_tab, "Eiger")
        self.tabs.addTab(self.vortex_tab, "Vortex")
        self.tabs.currentChanged.connect(self._redraw_current_map)
        self.eiger_tab.redraw_requested.connect(self._redraw_current_map)
        self.vortex_tab.redraw_requested.connect(self._redraw_current_map)

        # ---- Central layout ---------------------------------------------
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.addWidget(top_widget)
        v.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        # ROI persistence, shared with the dichro viewer.
        self._pending_eiger_roi = None   # raw-coord ROI awaiting a frame
        self._roi_save_timer = QtCore.QTimer(self)
        self._roi_save_timer.setSingleShot(True)
        self._roi_save_timer.timeout.connect(self._save_rois)
        for spin in (
            self.vortex_tab.e_start, self.vortex_tab.e_stop,
            self.eiger_tab.x_cen, self.eiger_tab.y_cen,
            self.eiger_tab.x_width, self.eiger_tab.y_width,
        ):
            # Debounced: a spin box held down emits on every step.
            spin.valueChanged.connect(
                lambda _v: self._roi_save_timer.start(ROI_SAVE_DEBOUNCE_MS)
            )
        self._load_rois()

        self.status = self.statusBar()
        self.status.showMessage("Ready. Pick a folder and scan, then Start Live.")

    # ------------------------------------------------------- ROI persistence
    def _load_rois(self):
        """Restore both ROIs from the shared config, if it has them.

        The Vortex ROI is a channel range, so it carries over as written.  The
        Eiger ROI is stored in raw detector coordinates by the dichro viewer,
        which does not rotate its frames, so it has to be converted -- and
        that needs the raw column count, which is only known once a frame has
        been read.  It is therefore held until the first preview arrives.
        """
        config = _load_config(self._folder)

        vortex = config.get("vortex_roi") or {}
        try:
            start = int(vortex["e_start"])
            stop = int(vortex["e_stop"])
        except (KeyError, TypeError, ValueError):
            pass
        else:
            self.vortex_tab.e_start.setValue(start)
            self.vortex_tab.e_stop.setValue(stop)

        eiger = config.get("eiger_roi") or {}
        if all(k in eiger for k in ("x_cen", "y_cen", "width", "height")):
            self._pending_eiger_roi = eiger

    def _apply_pending_eiger_roi(self, n_cols):
        """Convert and apply the saved Eiger ROI, now that the width is known."""
        saved = self._pending_eiger_roi
        self._pending_eiger_roi = None
        if not saved:
            return
        try:
            values = raw_roi_to_display(
                float(saved["x_cen"]), float(saved["y_cen"]),
                float(saved["width"]), float(saved["height"]), n_cols,
            )
        except (KeyError, TypeError, ValueError):
            return
        tab = self.eiger_tab
        for widget, key in (
            (tab.x_cen, "x_cen"), (tab.y_cen, "y_cen"),
            (tab.x_width, "x_width"), (tab.y_width, "y_width"),
        ):
            widget.setValue(values[key])

    def _save_rois(self):
        """Write both ROIs back to the shared config."""
        updates = {
            "vortex_roi": {
                "e_start": int(self.vortex_tab.e_start.value()),
                "e_stop": int(self.vortex_tab.e_stop.value()),
            },
        }
        n_cols = self._raw_n_cols()
        if n_cols:
            tab = self.eiger_tab
            updates["eiger_roi"] = display_roi_to_raw(
                tab.x_cen.value(), tab.y_cen.value(),
                tab.x_width.value(), tab.y_width.value(), n_cols,
            )
        _update_config(self._folder, updates)

    def _raw_n_cols(self):
        """Raw column count, i.e. the rotated preview's height, or None."""
        frame = getattr(self.eiger_tab, "_preview", None)
        if frame is None:
            return None
        return int(frame.shape[0])

    # ------------------------------------------------------------------ UI
    @property
    def folder(self):
        """The sample folder currently being watched, ``""`` if unset."""
        return self._folder

    def set_folder(self, path):
        """Point the viewer at the sample folder *path*.

        Public so a host GUI can supply the folder without reaching into
        private state -- the Flyscan plot tab defaults it to the session's
        experiment path this way.
        """
        self._folder = str(path)
        self.folder_label.setText(self._folder)
        # A different experiment has a different shared config.
        self._load_rois()

    def _browse_folder(self):
        start = self._folder or os.getcwd()
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose sample folder", start
        )
        if path:
            self.set_folder(path)

    def _set_running_ui(self, running):
        """Enable/disable controls based on whether live polling is active."""
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.reprocess_btn.setEnabled(running)
        self.browse_btn.setEnabled(not running)
        # In auto mode the scan spin is always disabled (the GUI picks the
        # scan); otherwise it follows the running state.
        self.scan_spin.setEnabled((not running) and (not self.auto_chk.isChecked()))
        # Poll interval, idle timeout, and the auto checkbox can be edited
        # while running; the next QTimer tick / idle check uses the new value.

    def _on_auto_toggled(self, checked):
        """User flipped the Auto checkbox. Keeps the spinbox in sync; when
        live, the next poll will consult the folder for the latest scan."""
        self._auto_latest = bool(checked)
        # The spinbox is editable only when not auto AND not currently live.
        live = self.stop_btn.isEnabled()
        self.scan_spin.setEnabled((not live) and (not checked))

    # --------------------------------------------------------------- start
    def _reset_scan_ui(self):
        """Clear per-scan UI state (previews, maps, normalize chk).

        Used at Start Live and at every auto-mode scan switch.
        """
        self._last_result = None
        self._eiger_preview_loaded = False
        self._vortex_preview_loaded = False
        self._eiger_preview_pending = False
        self._vortex_preview_pending = False
        # Invalidate any frame read still in flight for the previous scan.
        self._scan_gen += 1
        self._frame_timer.stop()
        self._frame_wanted = None
        self._n_eiger_frames = 0
        self._partial_sig = None
        self._geometry_loaded = False
        self.eiger_tab.set_partial_report([])
        self.vortex_tab.set_partial_report([])
        self.eiger_tab.set_scan_geometry(None)
        self.vortex_tab.set_scan_geometry(None)
        self.eiger_tab.set_preview(None)
        self.eiger_tab.clear_map()
        self.vortex_tab.set_preview(None)
        self.vortex_tab.clear_map()
        self.norm_chk.setEnabled(False)
        self.norm_chk.setChecked(False)
        self.tabs.setTabEnabled(0, True)
        self.tabs.setTabEnabled(1, True)

    def _on_start(self):
        if not self._folder:
            self.status.showMessage("Pick a sample folder first.")
            return
        self._auto_latest = self.auto_chk.isChecked()
        self._busy = False
        self._pending_close = False
        self._reprocess_pending = None
        self._pending_switch = None
        self._start_time = time.monotonic()
        self._reset_scan_ui()

        if self._auto_latest:
            # Don't build a reader yet — the first poll will detect the
            # latest scan and call _switch_to_scan.
            self._reader = None
            self._scan = None
            self._waiting_no_scan = True
            self.status.showMessage(
                f"Auto: waiting for first scan in {self._folder}…"
            )
        else:
            self._scan = int(self.scan_spin.value())
            self._waiting_no_scan = False
            self._reader = LiveScanReader(
                self._folder, self._scan,
                self.eiger_tab.get_roi(), self.vortex_tab.get_roi(),
                batch=PROCESS_BATCH,
            )
            self.status.showMessage(
                f"Live: waiting for scan {self._scan} in {self._folder}…"
            )

        self._timer.start(int(self.poll_spin.value()))
        self._set_running_ui(True)

    def _switch_to_scan(self, n):
        """Close the current reader and start watching scan ``n`` instead.

        Defers if a tick is in flight; the tick's done-handler will call
        back into this method.
        """
        if self._busy:
            self._pending_switch = n
            return
        self._close_reader()
        self._reset_scan_ui()
        self._scan = int(n)
        # Reflect the new scan in the spinbox even though it's disabled.
        self.scan_spin.setValue(self._scan)
        self._reader = LiveScanReader(
            self._folder, self._scan,
            self.eiger_tab.get_roi(), self.vortex_tab.get_roi(),
            batch=PROCESS_BATCH,
        )
        self._waiting_no_scan = False
        self.status.showMessage(f"Auto: now watching scan {self._scan}")

    # ---------------------------------------------------------------- stop
    def _on_stop(self, reason=None):
        self._timer.stop()
        # Any deferred work (switch / reprocess) is moot once the user stops.
        self._pending_switch = None
        self._reprocess_pending = None
        self._waiting_no_scan = False
        # If a tick worker is still running, let it finish before closing the
        # reader (otherwise we'd close handles out from under it). The
        # finished_ok/failed slot will trigger the actual close.
        if self._busy:
            self._pending_close = True
        else:
            self._finalize_reader()
            self._close_reader()
        self._set_running_ui(False)
        if reason:
            self.status.showMessage(f"Stopped: {reason}")
        else:
            self.status.showMessage("Stopped.")

    def _finalize_reader(self):
        """Flush the reader's open trigger group and redraw with it.

        Returns the finalized snapshot, or None if there was nothing to close.
        Only touches the reader's accumulated arrays — no HDF5 — so it is safe
        to run on the GUI thread.
        """
        if self._reader is None:
            return None
        final = self._reader.finalize()
        if final is None:
            return None
        self._last_result = final
        self._draw_map(self.eiger_tab, final.eiger_z, final)
        self._draw_map(self.vortex_tab, final.vortex_z, final)
        self._update_frame_marker()
        self._refresh_partial_report(final)
        return final

    def _close_reader(self):
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass
            self._reader = None
        self._pending_close = False

    # ----------------------------------------------------------------- tick
    def _poll(self):
        """QTimer callback — every poll_spin.value() ms while live is active."""
        if self._auto_latest:
            # Always check the folder for a newer scan, regardless of whether
            # we currently have a reader (we may be between scans).
            latest = find_latest_scan(self._folder)
            if latest is None:
                # Pulse the status so the user sees the GUI is still alive.
                self.status.showMessage(
                    f"Auto: waiting for first scan in {self._folder}…"
                )
                return
            if latest != self._scan:
                # Either we've never opened any scan (startup), or a higher
                # number has appeared since the last poll. Switch.
                self._switch_to_scan(latest)
                # If the switch was deferred (busy), wait for the next poll.
                if self._reader is None:
                    return

        if self._reader is None:
            return
        # If we haven't even seen the pos_stream file yet, check for it before
        # spawning a worker (cheap stat).
        if not self._reader._pos_dset:
            pos_path, _ = _resolve_h5(self._folder, "pos_stream", self._scan)
            if pos_path is None:
                # No file yet; check idle timeout against the start time.
                self._check_startup_timeout()
                return
        if self._busy:
            return
        self._busy = True
        # tick() reads from h5py — must run on the worker thread.
        self._tick_worker = ProcessWorker(self._reader.tick, (), {})
        self._tick_worker.finished_ok.connect(self._on_tick_done)
        self._tick_worker.failed.connect(self._on_tick_failed)
        self._tick_worker.start()

    def _check_startup_timeout(self):
        """While waiting for pos_stream to appear, honour idle timeout.

        In auto-latest mode we never stop on this timeout — a newly-detected
        scan file may not be SWMR-ready yet, and the GUI should keep polling
        rather than tearing down.
        """
        if self._start_time is None or self._auto_latest:
            return
        if time.monotonic() - self._start_time > self.idle_spin.value():
            self._on_stop(reason=f"pos_stream not found within {self.idle_spin.value()}s")

    def _on_tick_done(self, result):
        self._busy = False
        self._last_result = result

        # Handle a deferred close from _on_stop().
        if getattr(self, "_pending_close", False):
            self._close_reader()
            return

        # Handle a deferred scan switch (auto-mode picked a new latest scan
        # while a tick was in flight).
        if self._pending_switch is not None:
            n = self._pending_switch
            self._pending_switch = None
            self._switch_to_scan(n)
            return

        # Handle a deferred reprocess request.
        if self._reprocess_pending is not None:
            stream, roi = self._reprocess_pending
            self._reprocess_pending = None
            self._launch_reprocess(stream, roi)
            return

        if not result.pos_available:
            # Still nothing; rely on the next poll.
            self._check_startup_timeout()
            return

        # Idle-timeout check based on actual data growth.
        idle = time.monotonic() - self._reader.last_growth_time
        if result.n_triggers_closed > 0 and idle > self.idle_spin.value():
            # Nothing more is coming, so close the last trigger group; without
            # this the scan's final frame never gets a position.
            result = self._finalize_reader() or result
            if self._auto_latest:
                # Don't stop the GUI; release the file handles and wait for
                # the next scan to appear. The map stays on screen as context.
                self._close_reader()
                self._waiting_no_scan = True
                self.status.showMessage(
                    f"scan {self._scan} idle for {int(idle)}s — waiting for next scan…"
                )
                return
            self._on_stop(reason=f"no new data for {int(idle)}s")
            return

        # Enable/disable tabs based on file availability.
        self.tabs.setTabEnabled(0, result.eiger_available)
        self.tabs.setTabEnabled(1, result.vortex_available)

        # Update the I0 normalize checkbox once we have something to look at.
        if result.n_triggers_closed > 0:
            usable = _is_i0_usable(result.i0s)
            self.norm_chk.setEnabled(usable)
            if not usable and self.norm_chk.isChecked():
                self.norm_chk.setChecked(False)

        # Grow the frame slider as frames land on disk (before loading the
        # preview, which passes the count on to the tab).
        if result.n_eiger_frames != self._n_eiger_frames:
            self._n_eiger_frames = result.n_eiger_frames
            self.eiger_tab.set_frame_count(self._n_eiger_frames)

        # Lazy-load detector previews the first time each stream is available.
        self._maybe_load_previews(result)
        self._maybe_load_geometry(result)

        # Redraw both tabs' maps when their data has grown — cheap and keeps
        # tab switches snappy.
        self._draw_map(self.eiger_tab, result.eiger_z, result)
        self._draw_map(self.vortex_tab, result.vortex_z, result)
        # The map redraw wipes the marker, and new positions may have arrived
        # for the frame currently on screen.
        self._update_frame_marker()
        self._refresh_partial_report(result)

        self.status.showMessage(self._status_string(result))

    def _on_tick_failed(self, msg):
        self._busy = False
        if getattr(self, "_pending_close", False):
            self._close_reader()
            return
        self.status.showMessage(f"Live tick failed: {msg}")

    def _track_worker(self, worker):
        """Keep a reference to *worker* until its thread has really finished.

        One slot per worker was enough while only one side job could be in
        flight, but a scan carrying *both* an Eiger and a Vortex stream starts
        two previews in the same pass.  The second assignment dropped the only
        reference to the first thread, Python collected a QThread that was
        still running, and Qt took the process down with it::

            QThread: Destroyed while thread is still running
            Aborted (core dumped)

        ``finished`` rather than ``finished_ok``/``failed``: those are emitted
        from inside ``run()``, so the thread is still going when they arrive.
        """
        self._side_workers.add(worker)
        worker.finished.connect(self._forget_worker)
        return worker

    def _forget_worker(self):
        """Drop a worker once Qt reports its thread has ended."""
        worker = self.sender()
        if worker is not None:
            self._side_workers.discard(worker)

    # ----------------------------------------------------------- previews
    def _maybe_load_previews(self, result):
        if (
            result.eiger_available
            and not self._eiger_preview_loaded
            and not self._eiger_preview_pending
            and result.n_eiger_frames > 0
        ):
            self._eiger_preview_pending = True
            w = ProcessWorker(_read_eiger_frame, (self._folder, self._scan), {})
            w.finished_ok.connect(self._on_eiger_preview)
            w.failed.connect(lambda m: self._on_preview_failed("eiger", m))
            self._track_worker(w)
            w.start()
        if (
            result.vortex_available
            and not self._vortex_preview_loaded
            and not self._vortex_preview_pending
            and result.n_vortex_frames > 0
        ):
            self._vortex_preview_pending = True
            w = ProcessWorker(_read_vortex_spectrum, (self._folder, self._scan), {})
            w.finished_ok.connect(self._on_vortex_preview)
            w.failed.connect(lambda m: self._on_preview_failed("vortex", m))
            self._track_worker(w)
            w.start()

    def _maybe_load_geometry(self, result):
        """Read the beam/detector geometry once, as soon as a frame exists.

        Same plain read-only open as the preview loader, on a worker thread —
        it touches the Eiger file's frame-0 attributes and the master file,
        neither of which the reader holds open.
        """
        if self._geometry_loaded or not result.eiger_available:
            return
        if result.n_eiger_frames <= 0:
            return
        self._geometry_loaded = True   # one attempt per scan
        gen = self._scan_gen
        w = ProcessWorker(read_scan_geometry, (self._folder, self._scan), {})
        w.finished_ok.connect(lambda geo, g=gen: self._on_geometry(g, geo))
        w.failed.connect(lambda m: self.status.showMessage(
            f"Scan geometry unavailable: {m}"))
        self._geometry_worker = w   # keep a reference so the thread isn't GC'd
        w.start()

    def _on_geometry(self, gen, geo):
        if gen != self._scan_gen:
            return
        self.eiger_tab.set_scan_geometry(geo)
        self.vortex_tab.set_scan_geometry(geo)

    def _on_eiger_preview(self, frame):
        self._eiger_preview_pending = False
        if frame is not None:
            self._eiger_preview_loaded = True
            self.eiger_tab.set_preview(frame, frame_count=self._n_eiger_frames)
            # The saved ROI is in raw coordinates; the frame is what says how
            # wide the detector is, so it can only be converted now.
            self._apply_pending_eiger_roi(int(frame.shape[0]))
            self._update_frame_marker(0)

    def _on_vortex_preview(self, spectrum):
        self._vortex_preview_pending = False
        if spectrum is not None:
            self._vortex_preview_loaded = True
            self.vortex_tab.set_preview(spectrum)

    def _on_preview_failed(self, which, msg):
        if which == "eiger":
            self._eiger_preview_pending = False
        else:
            self._vortex_preview_pending = False
        self.status.showMessage(f"{which} preview failed: {msg}")

    # -------------------------------------------------------- eiger frames
    def _on_frame_requested(self, index):
        """The frame slider moved.

        Move the map marker straight away (it costs nothing) and schedule the
        HDF5 read, which is debounced and coalesced so that dragging the
        slider doesn't queue up one full-frame read per intermediate stop.
        """
        index = int(index)
        self._update_frame_marker(index)
        self._frame_wanted = index
        self._frame_timer.start(FRAME_LOAD_DEBOUNCE_MS)

    def _maybe_load_frame(self):
        """Read the frame the slider is sitting on, if we aren't already busy.

        While live, the read goes through the reader's own SWMR handle so it
        sees frames the writer has only just flushed; that handle belongs to
        one thread at a time, so the read takes the same `_busy` gate as a
        tick. Once the reader is gone (stopped, or between scans in auto
        mode) the file is no longer being written and a plain open is fine.
        """
        if self._frame_wanted is None or self._frame_busy:
            return
        if not self._folder or self._scan is None:
            return
        reader = self._reader
        live = reader is not None and reader._eiger_dset is not None
        if live and self._busy:
            # A tick or a re-process owns the handles — come back shortly.
            self._frame_timer.start(FRAME_LOAD_DEBOUNCE_MS)
            return
        index = self._frame_wanted
        self._frame_wanted = None
        self._frame_busy = True
        gen = self._scan_gen
        if live:
            self._busy = True   # keep ticks off the reader until we're done
            w = ProcessWorker(reader.read_eiger_frame, (index,), {})
        else:
            w = ProcessWorker(
                _read_eiger_frame, (self._folder, self._scan, index), {}
            )
        w.finished_ok.connect(
            lambda fr, g=gen, i=index, lv=live: self._on_frame_loaded(g, i, fr, lv)
        )
        w.failed.connect(
            lambda m, i=index, lv=live: self._on_frame_failed(i, m, lv)
        )
        self._frame_worker = w   # keep a reference so the thread isn't GC'd
        w.start()

    def _release_frame_gate(self, live):
        self._frame_busy = False
        if not live:
            return
        self._busy = False
        # Honour a close that was deferred while we held the gate.
        if getattr(self, "_pending_close", False):
            self._close_reader()

    def _on_frame_loaded(self, gen, index, frame, live):
        self._release_frame_gate(live)
        if gen == self._scan_gen and frame is not None:
            self._eiger_preview_loaded = True
            self.eiger_tab.update_preview_frame(frame, index)
        # A newer index may have been asked for while this read was running.
        self._maybe_load_frame()

    def _on_frame_failed(self, index, msg, live):
        self._release_frame_gate(live)
        self.status.showMessage(f"Eiger frame {index} read failed: {msg}")
        self._maybe_load_frame()

    def _update_frame_marker(self, index=None):
        """Mark the map position at which the previewed Eiger frame was taken.

        Uses the same trigger-value lookup as the map itself, so the marker
        cannot drift out of step with the points it sits on. There is no
        marker while the frame's trigger group is still open (or absent).
        """
        if index is None:
            index = self.eiger_tab.frame_slider.value()
        result = self._last_result
        group = None if result is None else group_for_frame(result.trigs, index)
        if group is None:
            self.eiger_tab.set_frame_marker(None)
            return
        self.eiger_tab.set_frame_marker(
            (result.xs[group], result.ys[group]), index
        )

    def _refresh_partial_report(self, result):
        """Re-list the partial groups in both tabs' left bars.

        Runs every tick, so it skips the rebuild while the flags are unchanged
        — which is the normal case once a scan is under way.
        """
        dropped = int(np.sum(result.coverage - result.counts))
        sig = (tuple(np.flatnonzero(result.partial).tolist()), dropped,
               int(result.n_eiger_frames), int(result.n_vortex_frames))
        if sig == self._partial_sig:
            return
        self._partial_sig = sig
        n_groups = int(result.trigs.size)
        self.eiger_tab.set_partial_report(
            describe_partial_groups(result, result.n_eiger_frames),
            n_groups, dropped)
        self.vortex_tab.set_partial_report(
            describe_partial_groups(result, result.n_vortex_frames),
            n_groups, dropped)

    # ------------------------------------------------------------- drawing
    def _draw_map(self, tab, z, result):
        if z is None or z.size == 0 or result.xs.size == 0:
            return
        scatter = self.style_combo.currentText() == "Scatter"
        i0 = result.i0s if self.norm_chk.isChecked() else None
        tab.draw_map(result.xs, result.ys, z, i0, scatter,
                     result.trigs, result.partial, tab.drop_incomplete())

    def _redraw_current_map(self):
        if self._last_result is None:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._draw_map(self.eiger_tab, self._last_result.eiger_z, self._last_result)
            self._update_frame_marker()
        elif idx == 1:
            self._draw_map(self.vortex_tab, self._last_result.vortex_z, self._last_result)

    def _status_string(self, result):
        eiger_roi = self.eiger_tab.get_roi()
        vortex_roi = self.vortex_tab.get_roi()
        n_partial = int(result.partial.sum()) if result.partial.size else 0
        n_dropped = int(np.sum(result.coverage - result.counts))
        return (
            f"closed_trig={result.n_triggers_closed}  "
            f"incomplete_pos={n_partial}  dropped={n_dropped}  "
            f"eiger={result.n_eiger_frames}  vortex={result.n_vortex_frames}  "
            f"roi_e=(({eiger_roi[0][0]},{eiger_roi[0][1]}),({eiger_roi[1][0]},{eiger_roi[1][1]}))  "
            f"roi_v={vortex_roi}  updated {time.strftime('%H:%M:%S')}"
        )

    # -------------------------------------------------------- reprocess ROI
    def _on_reprocess(self):
        if self._reader is None or self._last_result is None:
            self.status.showMessage("Nothing to re-process yet.")
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            stream = "eiger"
            roi = self.eiger_tab.get_roi()
        else:
            stream = "vortex"
            roi = self.vortex_tab.get_roi()
        if self._busy:
            # Defer to after the current tick finishes.
            self._reprocess_pending = (stream, roi)
            self.status.showMessage(f"Re-process {stream} queued…")
            return
        self._launch_reprocess(stream, roi)

    def _launch_reprocess(self, stream, roi):
        self._busy = True  # block normal ticks while we reprocess
        if stream == "eiger":
            fn = self._reader.reprocess_eiger
        else:
            fn = self._reader.reprocess_vortex
        w = ProcessWorker(fn, (roi,), {})
        w.finished_ok.connect(lambda arr, s=stream: self._on_reprocess_done(s, arr))
        w.failed.connect(lambda m: self._on_reprocess_failed(m))
        self._track_worker(w)
        self.status.showMessage(f"Re-processing {stream} with ROI {roi}…")
        w.start()

    def _on_reprocess_done(self, stream, arr):
        self._busy = False
        # Update the cached result so a tab switch picks up the new sums.
        if self._last_result is not None:
            if stream == "eiger":
                self._last_result = dataclasses.replace(self._last_result, eiger_z=arr)
            else:
                self._last_result = dataclasses.replace(self._last_result, vortex_z=arr)
            self._redraw_current_map()
        self.status.showMessage(f"Re-processed {stream}: {arr.size} frames.")

    def _on_reprocess_failed(self, msg):
        self._busy = False
        self.status.showMessage(f"Re-process failed: {msg}")

    # ----------------------------------------------------------- shutdown
    def closeEvent(self, event):
        self._timer.stop()
        if self._roi_save_timer.isActive():
            self._roi_save_timer.stop()
        self._save_rois()
        # Closing while a preview or a tick is mid-read would destroy those
        # QThreads from under themselves -- the same abort _track_worker
        # exists to prevent, just at shutdown instead.  They only read HDF5,
        # so they finish quickly; the timeout is a backstop, not a plan.
        for worker in list(self._side_workers) + [
            self._tick_worker, self._frame_worker, self._geometry_worker,
        ]:
            if worker is not None and worker.isRunning():
                worker.wait(WORKER_SHUTDOWN_WAIT_MS)
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="Flyscan live viewer")
    parser.add_argument("--folder", default=None,
                        help="Sample folder (containing pos_stream/, eiger/, vortex/)")
    parser.add_argument("--scan", type=int, default=None,
                        help="Scan number to watch")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    win = LiveMainWindow(initial_folder=args.folder or os.getcwd())
    if args.scan is not None:
        win.scan_spin.setValue(args.scan)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
