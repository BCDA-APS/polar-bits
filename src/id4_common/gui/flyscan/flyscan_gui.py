"""Post-scan flyscan viewer.

Qt + matplotlib GUI that wraps the processing functions in
``process_flyscan.py``. Two tabs:

* **Eiger**  — rectangular pixel ROI on the Eiger camera images, summed per
  trigger.
* **Vortex** — energy-channel window on the Vortex fluorescence spectra,
  summed per trigger.

Each tab has a sample-frame preview (with the current ROI overlaid) and a
2D map of the per-image scalar value. The map can be normalized by I0 and
switched between scatter and tricontourf rendering.

The Eiger tab can also browse frames: an owner that reports a frame count to
``EigerTab.set_preview`` gets a frame slider under the preview (see
``frame_requested`` / ``update_preview_frame``) and can mark the map position
of the shown frame with ``set_frame_marker``. The live viewer uses both; the
post-scan window here only ever shows frame 0, so its slider stays hidden.

Run with::

    python flyscan_gui.py [--folder NdFeB] [--scan 238]
"""

import argparse
import os
import sys

import h5py
import hdf5plugin  # noqa: F401  -- registers HDF5 codecs (LZ4, Bitshuffle, ...)
import numpy as np

from qtpy import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .process_flyscan import (
    FNAME_FORMAT,
    describe_partial_groups,
    read_scan_geometry,
    groups_for_frames,
    process_images,
    process_vortex,
    raw_point_to_display,
    reduce_position_stream,
    rotate_eiger,
)

# Defaults that match the literals currently hardcoded in process_flyscan.py.
# In *display* coordinates, i.e. on the rotated frame -- see EIGER_ROT90_CCW.
# Centred on the peak of DefaultSample scan 110, which it captures 99.5% of;
# the previous default caught 0% of it, having been left behind by a detector
# move.  Maps back to raw rows 299..379, columns 672..752.
DEFAULT_EIGER_ROI = ((299, 379), (310, 390))   # ((x0, x1), (y0, y1))
DEFAULT_VORTEX_ROI = (800, 900)                # (channel_start, channel_stop)
PROCESS_BATCH = 100

# Some scans use a 6-digit-padded filename, others use unpadded — and the
# convention can even differ between streams for the same scan number. Probe
# both when locating a file.
_FNAME_PATTERNS = (
    "{}/{}/scan_{:06d}.h5",   # newer convention, matches the default in process_flyscan
    "{}/{}/scan_{:d}.h5",     # older convention, used for some scans in pos_stream
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_h5(folder, stream, scan_number):
    """Find the HDF5 file for a (stream, scan_number), supporting both naming
    conventions. Returns ``(path, fname_format)`` where ``fname_format`` is
    the pattern that matched (so it can be passed back to the
    ``process_*`` functions). Returns ``(None, None)`` if nothing matches.
    """
    for fmt in _FNAME_PATTERNS:
        path = fmt.format(folder, stream, scan_number)
        if os.path.exists(path):
            return path, fmt
    return None, None


def _read_eiger_frame(folder, scan_number, index=0):
    """Return one Eiger frame for the preview, or None if the file is missing."""
    path, _ = _resolve_h5(folder, "eiger", scan_number)
    if path is None:
        return None
    with h5py.File(path, "r") as f:
        frame = f["entry/data/data"][index].astype(np.float32)
    # Shown rotated, and every coordinate the user picks off it is in that
    # frame; raw_slice_for_roi maps them back for the summing paths.
    return rotate_eiger(frame)


def _read_vortex_spectrum(folder, scan_number, index=0):
    """Return one Vortex spectrum (summed across detector elements)."""
    path, _ = _resolve_h5(folder, "vortex", scan_number)
    if path is None:
        return None
    with h5py.File(path, "r") as f:
        frame = f["entry/data/data"][index]   # (n_elements, n_channels)
    return frame.astype(np.float64).sum(axis=0)


def _align_and_normalize(x, y, z, i0=None, trigs=None, partial=None):
    """Pair each detector frame with the position group it was taken in.

    Returns ``(xi, yi, zi, partial_i)``, all the same length, optionally
    with ``zi`` divided by ``i0`` element-wise.

    When ``trigs`` (the trigger value of each position group) is given, the
    pairing is made by trigger value — detector frame ``k`` belongs to
    trigger ``k + FIRST_TRIGGER``, which is what the MCS counter recorded —
    so a group missing from the stream drops that one frame instead of
    shifting every later frame by one. ``partial_i`` then reports, per
    plotted point, whether its group only saw part of an exposure.

    Without ``trigs`` the old positional convention is used: drop the first
    position sample (the detector skips the first trigger) and clip all the
    arrays from the right to the shortest, which is right only as long as
    the trigger values run consecutively.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    zi = np.asarray(z, dtype=np.float64).copy()
    i0 = None if i0 is None else np.asarray(i0)

    if trigs is not None and np.size(trigs):
        frames, groups = groups_for_frames(trigs, zi.size)
        xi, yi, zi = x[groups], y[groups], zi[frames]
        i0i = None if i0 is None or i0.size == 0 else i0[groups]
        pi = (np.zeros(frames.size, dtype=bool) if partial is None
              else np.asarray(partial, dtype=bool)[groups])
    else:
        xi, yi = x[1:], y[1:]
        n = min(xi.size, yi.size, zi.size)
        xi, yi, zi = xi[:n], yi[:n], zi[:n]
        # i0 is reduced per group just like x and y, so it needs the same
        # one-group shift before it lines up with the frames.
        i0i = None if i0 is None or i0.size == 0 else i0[1:1 + n]
        if i0i is not None and i0i.size != n:
            i0i = None
        pi = (np.zeros(n, dtype=bool) if partial is None
              else np.asarray(partial, dtype=bool)[1:1 + n])
        if pi.size != n:
            pi = np.zeros(n, dtype=bool)

    if i0i is not None and i0i.size == zi.size:
        with np.errstate(divide="ignore", invalid="ignore"):
            zi /= np.where(i0i != 0, i0i, np.nan)
    return xi, yi, zi, pi


def _drop_partial_points(xi, yi, zi, partial, drop):
    """Optionally remove the points whose position record is incomplete.

    Their intensity is sound but the position under it is not, so they are
    the ones that distort an interpolated map. Never drops everything: if the
    mask would leave nothing to plot, the points are kept so the map doesn't
    silently go blank.
    """
    if not drop or partial is None or not np.any(partial):
        return xi, yi, zi, partial
    keep = ~np.asarray(partial, dtype=bool)
    if not np.any(keep):
        return xi, yi, zi, partial
    return xi[keep], yi[keep], zi[keep], partial[keep]


def _mark_partial(ax, xi, yi, partial):
    """Ring points whose position record doesn't span their whole exposure.

    Nothing here is a statement about the detector: the Eiger integrated for
    its full frame time either way. What is short is the run of position
    samples recorded while it did, so the (x, y) plotted for that frame is a
    mean over only part of the travel.
    """
    if partial is None or not np.any(partial):
        return
    ax.scatter(
        xi[partial], yi[partial], s=60, facecolors="none", edgecolors="black",
        linewidths=0.9, zorder=4, label="incomplete positions",
    )
    ax.legend(loc="best", fontsize=7, framealpha=0.7)


def _is_i0_usable(i0):
    """Heuristic — older scans don't have I0, so the column is all zeros."""
    if i0 is None or i0.size == 0:
        return False
    return bool(np.any(np.isfinite(i0)) and np.nanmax(np.abs(i0)) > 0)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class ProcessWorker(QtCore.QThread):
    """Runs a processing function off the GUI thread."""

    finished_ok = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, func, args, kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._func(*self._args, **self._kwargs)
        except Exception as e:
            self.failed.emit(repr(e))
            return
        self.finished_ok.emit(result)


# ---------------------------------------------------------------------------
# Reusable canvas widget
# ---------------------------------------------------------------------------

class _Canvas(FigureCanvas):
    def __init__(self):
        fig = Figure(constrained_layout=True)
        super().__init__(fig)
        self.ax = fig.add_subplot(111)


class _Toolbar(NavigationToolbar):
    """NavigationToolbar with the cursor readout on its own full-width line.

    Over an image, matplotlib appends the pixel value to the cursor position
    with a *newline*, and gives its built-in readout label a size policy that
    ignores the label's height -- so two lines are drawn into a strip sized
    for one and come out clipped top and bottom.

    Widening the built-in label in place does not fix it: a full-detector
    reading such as ``x=2067.5 y=2067.5   [65535]`` needs about 260 px, the
    toolbar buttons already want 220 of the panel's 440, and what is left
    would push buttons into an overflow menu.  So the built-in label is turned
    off and the reading gets a row of its own under the buttons, where it has
    the whole panel width and only ever needs one line.
    """

    #: What the newline between position and pixel value becomes.
    _JOIN = "   "

    def __init__(self, canvas, parent=None):
        """Build the toolbar and the separate readout line that goes with it."""
        super().__init__(canvas, parent, coordinates=False)
        self.readout = QtWidgets.QLabel("")
        self.readout.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        # One line high and no more: the map panel adds its canvas without a
        # stretch factor, so a Preferred-height label soaks up the slack and
        # sits 146 px tall with one line of text floating in it.
        self.readout.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        # Worth being able to copy a pixel coordinate out of.
        self.readout.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )

    def set_message(self, s):
        """Show *s* on the readout line, any break flattened to a separator."""
        self.readout.setText(s.replace("\n", self._JOIN))


def _make_map_panel(canvas, parent):
    """Wrap a canvas with its NavigationToolbar in a vertical layout."""
    toolbar = _Toolbar(canvas, parent)
    box = QtWidgets.QWidget()
    v = QtWidgets.QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(toolbar)
    v.addWidget(toolbar.readout)
    v.addWidget(canvas)
    return box


def _make_preview_panel(canvas, controls, parent, bottom=None):
    """Stack a NavigationToolbar (for pan/zoom) and a controls strip above the canvas.

    ``bottom`` is an optional widget (e.g. a frame slider) placed underneath.
    """
    toolbar = _Toolbar(canvas, parent)
    box = QtWidgets.QWidget()
    v = QtWidgets.QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(toolbar)
    v.addWidget(toolbar.readout)
    v.addWidget(controls)
    v.addWidget(canvas, 1)
    if bottom is not None:
        v.addWidget(bottom)
    return box


def _make_frame_slider():
    """Slider + label for stepping through the frames of a scan.

    Returns ``(widget, slider, label)``; the caller owns the wiring. Mirrors
    the strip used by the dichro viewer so the two GUIs look the same.
    """
    widget = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(widget)
    h.setContentsMargins(0, 0, 0, 0)
    label = QtWidgets.QLabel("Frame: 0 / 0")
    label.setMinimumWidth(90)
    slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(0)
    slider.setValue(0)
    slider.setEnabled(False)
    h.addWidget(label)
    h.addWidget(slider, 1)
    return widget, slider, label


class _ScanGeometryPanel(QtWidgets.QWidget):
    """Beam and detector geometry for the loaded scan, read from frame 0.

    A value the acquisition never wrote comes through as 0 (the beam-centre
    parameters currently do), so those are greyed and marked rather than
    presented as a measurement.
    """

    ROWS = (("Beam center", "_beam"), ("Wavelength", "_lambda"),
            ("Distance", "_dist"))

    def __init__(self, parent=None):
        super().__init__(parent)
        title = QtWidgets.QLabel("Scan geometry")
        title.setStyleSheet("QLabel { font-weight: bold; }")

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)
        small = self.font()
        small.setPointSize(max(7, small.pointSize() - 1))
        self._values = {}
        for row, (label, key) in enumerate(self.ROWS):
            name = QtWidgets.QLabel(label)
            name.setFont(small)
            name.setStyleSheet("QLabel { color: #666; }")
            value = QtWidgets.QLabel("—")
            value.setFont(small)
            value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            self._values[key] = value
        grid.setColumnStretch(1, 1)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        v.addWidget(title)
        v.addLayout(grid)
        self.set_geometry(None)

    @staticmethod
    def _style(label, text, tip, unset=False):
        label.setText(text)
        label.setToolTip(tip)
        label.setStyleSheet(
            "QLabel { color: #b06000; }" if unset else "QLabel { color: #222; }"
        )

    def set_geometry(self, geo):
        """Show a :class:`ScanGeometry`, or clear the panel when given None."""
        if geo is None:
            for label in self._values.values():
                self._style(label, "—", "")
            return

        bx, by = geo.beam_center_x, geo.beam_center_y
        if bx is None and by is None:
            self._style(self._values["_beam"], "—", "not in the Eiger file")
        else:
            unset = not (bx or by)
            text = f"{bx:g}, {by:g}" if not unset else f"{bx:g}, {by:g}  (unset)"
            tip = ("EIG_DCD_beam_center_x / _y, read at frame 0"
                   + ("\nBoth read zero — the detector parameters were never set."
                      if unset else ""))
            if geo.beam_center_pv is not None:
                tip += f"\n4idgSoftX:Eiger:Center reads {geo.beam_center_pv:g}"
            self._style(self._values["_beam"], text, tip, unset)

        if geo.wavelength is None:
            self._style(self._values["_lambda"], "—", "no master file for this scan")
        else:
            unit = "\u00c5" if geo.wavelength_units.startswith("ang") else geo.wavelength_units
            tip = "from the master file's bluesky metadata (4idVDCM:BraggLambdaRdbkAO)"
            if geo.energy is not None:
                tip += f"\nenergy {geo.energy:.6g} {geo.energy_units}"
            self._style(self._values["_lambda"],
                        f"{geo.wavelength:.5g} {unit}".strip(), tip)

        if geo.detector_distance is None:
            self._style(self._values["_dist"], "—", "not in the Eiger file")
        else:
            unset = not geo.detector_distance
            self._style(
                self._values["_dist"], f"{geo.detector_distance:.7g}"
                + ("  (unset)" if unset else ""),
                "EIG_DCD_detector_distance, read at frame 0"
                "\nUnits are not recorded in the file.", unset)


class _PartialGroupsPanel(QtWidgets.QWidget):
    """Left-bar list of the trigger groups flagged as partial exposures.

    A row is a frame whose position samples don't span its whole exposure —
    the MCS started or stopped inside the frame, or lost its leading tick — so
    the (x, y) plotted for it is a mean over only part of the travel and sits
    off its true position. The Eiger's own exposure is unaffected: it
    integrated for the full frame time in every case listed here.

    Samples the MCS dropped from the middle of a frame are counted in the
    footer instead: those still span the whole exposure, so the position is
    only slightly noisier, not displaced. Double-clicking a row emits
    `frame_activated` with the frame it holds.
    """

    frame_activated = QtCore.Signal(int)
    drop_toggled = QtCore.Signal(bool)

    COLUMNS = ("Frame", "Trig", "ckIM", "Travel")
    MAX_TABLE_HEIGHT = 260

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = QtWidgets.QLabel()
        self.title.setStyleSheet("QLabel { font-weight: bold; }")
        self.title.setWordWrap(True)

        self.table = QtWidgets.QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        # Let the numeric columns take exactly what they need; only the last
        # one stretches, so no header label ends up clipped.
        for col in range(len(self.COLUMNS) - 1):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(
            len(self.COLUMNS) - 1, QtWidgets.QHeaderView.Stretch)
        header.setHighlightSections(False)
        small = self.table.font()
        small.setPointSize(max(7, small.pointSize() - 1))
        self.table.setFont(small)
        header.setFont(small)
        self.table.itemDoubleClicked.connect(self._on_double_click)

        self.footer = QtWidgets.QLabel()
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet("QLabel { color: #666; }")
        self.footer.setFont(small)

        # Lives here rather than in the top bar: it acts on exactly the rows
        # above it, and the top bar is already wider than the window.
        self.drop_chk = QtWidgets.QCheckBox("Drop these from the map")
        self.drop_chk.setFont(small)
        self.drop_chk.setToolTip(
            "Leave these points out of the map. Their intensity is sound but\n"
            "the position under it can be most of a step off, which scatter\n"
            "shows as one misplaced dot and tricontourf smears into a patch.\n"
            "Ignored if it would leave nothing to plot."
        )
        self.drop_chk.toggled.connect(self.drop_toggled)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        v.addWidget(self.title)
        v.addWidget(self.table)
        v.addWidget(self.footer)
        v.addWidget(self.drop_chk)
        v.addStretch(1)
        self.set_report([])

    def set_report(self, records, n_groups=0, dropped=0):
        """Fill the table from :func:`describe_partial_groups` output.

        ``dropped`` is the number of samples the MCS lost in groups that still
        cover their whole exposure; they get a footer note rather than a row.
        """
        records = list(records)
        self.table.setRowCount(0)
        if not records:
            self.title.setText(
                "Incomplete positions: none"
                + (f" ({dropped} sample(s) dropped)" if dropped else "")
            )
            self.table.setVisible(False)
            self.footer.setVisible(bool(dropped))
            if dropped:
                self.footer.setText(
                    f"{dropped} ckIM sample(s) not recorded, but every "
                    f"exposure is fully covered"
                )
            return

        total = f" of {n_groups}" if n_groups else ""
        self.title.setText(f"Incomplete positions: {len(records)}{total}")
        self.table.setVisible(True)
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            pct = (100.0 * r.span / r.full_span) if r.full_span else float("nan")
            cells = (
                str(r.frame) if r.frame >= 0 else "—",
                str(r.trig),
                f"{r.coverage} / {r.expected}",
                "—" if pct != pct else f"{pct:.0f}%",
            )
            # Only the scan's final group can have had its own exposure cut
            # short (the detector may be disarmed mid-frame); everywhere else
            # the detector integrated normally and only the record is short.
            detector_note = (
                "the Eiger's own exposure may be short too, if it was "
                "disarmed mid-frame" if r.last else
                "the Eiger still exposed for the full frame time"
            )
            tip = (
                f"group {r.group} · eigerTrig {r.trig}\n"
                f"positions cover {r.coverage} of {r.expected} ckIM ticks "
                f"({r.coverage - r.expected:+d}, "
                f"{100.0 * r.coverage / r.expected:.0f}% of the frame)\n"
                f"{detector_note}\n"
                f"x = {r.x:.6g}   y = {r.y:.6g}\n"
                f"motor travel {r.span:.4g} vs {r.full_span:.4g} typical"
                + (f"\n{r.dropped} sample(s) also dropped inside it" if r.dropped else "")
                + ("" if r.frame >= 0 else "\nnot plotted: no detector frame maps here")
            )
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setToolTip(tip)
                item.setData(QtCore.Qt.UserRole, r.frame)
                self.table.setItem(row, col, item)

        # Height the table to its rows (up to a cap, then it scrolls) so the
        # footer sits under the last row instead of below a block of blank grid.
        self.table.resizeRowsToContents()
        wanted = (self.table.horizontalHeader().height()
                  + sum(self.table.rowHeight(r) for r in range(len(records)))
                  + 2 * self.table.frameWidth())
        wanted = min(wanted, self.MAX_TABLE_HEIGHT)
        self.table.setMinimumHeight(wanted)
        self.table.setMaximumHeight(wanted)

        ref = records[0]
        self.footer.setVisible(True)
        note = (f" · {dropped} sample(s) dropped elsewhere, coverage intact"
                if dropped else "")
        self.footer.setText(
            f"full coverage: {ref.expected} ckIM ticks, travel "
            f"{ref.full_span:.4g}{note}"
        )

    def _on_double_click(self, item):
        frame = item.data(QtCore.Qt.UserRole)
        if frame is not None and frame >= 0:
            self.frame_activated.emit(int(frame))


# ---------------------------------------------------------------------------
# Eiger tab
# ---------------------------------------------------------------------------

class _SquareStart:
    """Open the plot panels square, then get out of the way.

    A map and a detector frame both read better square, so the axes box starts
    constrained to 1:1.  Keeping it that way would waste half of a wide panel,
    so the constraint is dropped the first time the user deliberately resizes
    the window or drags the splitter between the two plots.

    Qt emits several resize events of its own while the layout settles, which
    would look exactly like a user resize, so resizes only start counting a
    moment after the widget is first shown.
    """

    #: How long to let the layout settle before a resize counts as the user's.
    _SQUARE_ARM_MS = 400

    def _init_square(self, splitter):
        """Start square and evenly split, watching for the user taking over."""
        self.plot_split = splitter
        # Share any growth equally; without this the two plots keep whatever
        # ratio they were first given.
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        self._square_plots = True
        self._square_armed = False
        self._split_fixed = False
        splitter.splitterMoved.connect(self._release_square_plots)

    def _equalize_split(self):
        """Give the two plots the same width.

        ``setSizes`` before the splitter has been laid out cannot do this: with
        no geometry yet, both entries clamp to the panels' minimum widths --
        far apart, because only the preview carries a controls strip and a
        frame slider -- and the splitter then keeps that ratio as it grows.  So
        the split is set again here, once there is a real width to halve.
        """
        if self._split_fixed:
            return
        width = self.plot_split.width()
        if width <= 0:
            return
        half = width // 2
        self.plot_split.setSizes([half, width - half])

    def apply_square(self, ax):
        """Square *ax* off, or release it, according to the current default."""
        ax.set_box_aspect(1 if self._square_plots else None)

    def showEvent(self, event):  # noqa: N802 - Qt naming
        """Even the split, and arm the release once the layout has settled."""
        super().showEvent(event)
        self._equalize_split()
        if not self._square_armed:
            QtCore.QTimer.singleShot(self._SQUARE_ARM_MS, self._arm_square)

    def resizeEvent(self, event):  # noqa: N802 - Qt naming
        """A resize the user asked for hands the space back to the plots."""
        super().resizeEvent(event)
        if self._square_armed:
            self._release_square_plots()

    def _arm_square(self):
        """Take a last even split, then leave the geometry to the user."""
        self._equalize_split()
        self._split_fixed = True
        self._square_armed = True

    def _release_square_plots(self, *_args):
        """Drop the square constraint and redraw without it."""
        # A drag is the user taking the split over, even before arming.
        self._split_fixed = True
        if not self._square_plots:
            return
        self._square_plots = False
        self.redraw_requested.emit()


class EigerTab(_SquareStart, QtWidgets.QWidget):
    process_requested = QtCore.Signal()
    # Emitted when the user drags the frame slider; the owner is expected to
    # read that frame and hand it back via `update_preview_frame`.
    frame_requested = QtCore.Signal(int)
    # Emitted when a control that only affects rendering changes.
    redraw_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview = None
        self._rect_patch = None
        self._cbar = None
        # Flag so that view limits are reset on a fresh preview but preserved
        # across scale/vmax tweaks (so toolbar zooms aren't lost on every edit).
        self._reset_view_next = True
        self._current_frame = 0
        # Marker on the map showing where the previewed frame was taken.
        self._marker_artists = []
        self._marker_xy = None
        self._marker_index = None

        # ROI inputs
        # ROI as centre + width, matching the dichro viewer.
        self.x_cen = QtWidgets.QSpinBox(); self.x_cen.setMaximum(1_000_000)
        self.y_cen = QtWidgets.QSpinBox(); self.y_cen.setMaximum(1_000_000)
        self.x_width = QtWidgets.QSpinBox(); self.x_width.setMaximum(1_000_000)
        self.y_width = QtWidgets.QSpinBox(); self.y_width.setMaximum(1_000_000)
        (dx0, dx1), (dy0, dy1) = DEFAULT_EIGER_ROI
        self.x_cen.setValue((dx0 + dx1) // 2)
        self.y_cen.setValue((dy0 + dy1) // 2)
        self.x_width.setValue(dx1 - dx0)
        self.y_width.setValue(dy1 - dy0)
        for s in (self.x_cen, self.x_width, self.y_cen, self.y_width):
            s.valueChanged.connect(self._update_overlay)

        # When ticked, loading a scan recentres the ROI on that scan's beam
        # centre — but only when the scan actually records one. Otherwise the
        # centre is left alone, so it keeps whatever the previous scan set or
        # whatever was typed in by hand.
        self.follow_beam_chk = QtWidgets.QCheckBox("Update beam params from scan")
        self.follow_beam_chk.setChecked(True)
        # A point smaller so the label fits the left column without eliding.
        _cb_font = self.follow_beam_chk.font()
        _cb_font.setPointSize(max(7, _cb_font.pointSize() - 1))
        self.follow_beam_chk.setFont(_cb_font)
        self.follow_beam_chk.setToolTip(
            "Update beam parameters from scan.\n"
            "Recentre x_cen / y_cen on the beam centre recorded in the scan.\n"
            "Scans that don't record one (the parameters read 0) leave the "
            "current centre untouched."
        )

        self.process_btn = QtWidgets.QPushButton("Process")
        self.process_btn.clicked.connect(self.process_requested)

        form = QtWidgets.QFormLayout()
        form.addRow("x_cen", self.x_cen)
        form.addRow("x_width", self.x_width)
        form.addRow("y_cen", self.y_cen)
        form.addRow("y_width", self.y_width)
        form.addRow(self.follow_beam_chk)
        form.addRow(self.process_btn)

        form_widget = QtWidgets.QWidget()
        form_widget.setLayout(form)

        # Preview display controls (scale + vmax percentile).
        self.scale_combo = QtWidgets.QComboBox()
        self.scale_combo.addItems(["Linear", "Log"])     # Linear is the default
        self.vmax_spin = QtWidgets.QDoubleSpinBox()
        self.vmax_spin.setRange(50.0, 100.0)
        self.vmax_spin.setDecimals(1)
        self.vmax_spin.setSingleStep(0.5)
        self.vmax_spin.setValue(99.5)
        self.vmax_spin.setSuffix(" %")
        self.scale_combo.currentIndexChanged.connect(self._render_preview)
        self.vmax_spin.valueChanged.connect(self._render_preview)

        ctrl = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(ctrl); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QtWidgets.QLabel("Scale:")); h.addWidget(self.scale_combo)
        h.addSpacing(12)
        h.addWidget(QtWidgets.QLabel("vmax:")); h.addWidget(self.vmax_spin)
        h.addStretch(1)

        # Canvases
        self.preview_canvas = _Canvas()
        self.map_canvas = _Canvas()

        # Frame slider under the preview. It stays hidden until the owner
        # reports more than one frame, so viewers that only ever show frame 0
        # look exactly as they did before.
        self.frame_bar, self.frame_slider, self.frame_label = _make_frame_slider()
        self.frame_bar.setVisible(False)
        self.frame_slider.valueChanged.connect(self._on_frame_slider)

        # Left column: ROI form above the partial-exposure list. Double-clicking
        # a row jumps the frame slider (and so the map marker) to that frame.
        self.geometry_panel = _ScanGeometryPanel()
        self.partial_panel = _PartialGroupsPanel()
        self.partial_panel.frame_activated.connect(self.frame_slider.setValue)
        self.partial_panel.drop_toggled.connect(
            lambda _: self.redraw_requested.emit())
        left = QtWidgets.QWidget()
        left.setMaximumWidth(285)
        left_v = QtWidgets.QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.addWidget(form_widget)
        left_v.addWidget(self.geometry_panel)
        left_v.addWidget(self.partial_panel, 1)

        right = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        right.addWidget(_make_preview_panel(
            self.preview_canvas, ctrl, self, bottom=self.frame_bar,
        ))
        right.addWidget(_make_map_panel(self.map_canvas, self))
        right.setSizes([1, 1])
        self._init_square(right)

        outer = QtWidgets.QHBoxLayout(self)
        outer.addWidget(left)
        outer.addWidget(right, 1)

    def get_roi(self):
        """Current ROI as ``((x0, x1), (y0, y1))``, from centre and width.

        An odd width puts the extra pixel on the high side, and the low edges
        are clamped at 0 so a centre near the edge can't produce a negative
        slice bound.
        """
        xc, yc = self.x_cen.value(), self.y_cen.value()
        w, h = self.x_width.value(), self.y_width.value()
        return (
            (max(0, xc - w // 2), max(0, xc + (w - w // 2))),
            (max(0, yc - h // 2), max(0, yc + (h - h // 2))),
        )

    def set_partial_report(self, records, n_groups=0, dropped=0):
        self.partial_panel.set_report(records, n_groups, dropped)

    def drop_incomplete(self):
        """Whether incomplete-position points should be left off the map."""
        return self.partial_panel.drop_chk.isChecked()

    def set_scan_geometry(self, geo):
        """Show the scan's geometry and, if asked, follow its beam centre."""
        self.geometry_panel.set_geometry(geo)
        if self.follow_beam_chk.isChecked():
            self.apply_beam_center(geo)

    def apply_beam_center(self, geo):
        """Recentre the ROI on ``geo``'s beam centre, if it records one.

        Returns True when the centre moved. A scan with no geometry, or one
        whose beam-centre parameters were never written (they read 0, which
        would drag the ROI into the corner), leaves the spin boxes alone —
        so they keep the previous scan's centre, or a hand-typed one.
        """
        if geo is None:
            return False
        bx, by = geo.beam_center_x, geo.beam_center_y
        if bx is None or by is None or not (bx or by):
            return False
        # The scan records the beam centre in raw detector coordinates; the
        # ROI boxes are in the rotated frame the user sees.
        n_cols = self._raw_n_cols()
        if n_cols is None:
            return False
        dx, dy = raw_point_to_display(bx, by, n_cols)
        self.x_cen.setValue(int(round(dx)))
        self.y_cen.setValue(int(round(dy)))
        return True

    def _raw_n_cols(self):
        """Columns of the *raw* frame, i.e. the rotated preview's height."""
        if self._preview is None:
            return None
        return self._preview.shape[0]

    def set_preview(self, frame, frame_count=0):
        """Cache the frame, reset spinbox bounds, and render with current controls.

        ``frame_count`` is how many frames the scan has; the frame slider is
        shown (and `frame_requested` becomes live) once that exceeds one.
        """
        self._preview = frame
        self._current_frame = 0
        self._reset_view_next = True
        if frame is not None:
            ny, nx = frame.shape
            for spin, upper in ((self.x_cen, nx), (self.x_width, nx),
                                (self.y_cen, ny), (self.y_width, ny)):
                spin.setMaximum(upper)
        self.frame_slider.blockSignals(True)
        try:
            self.frame_slider.setValue(0)
        finally:
            self.frame_slider.blockSignals(False)
        self.set_frame_count(frame_count)
        self._render_preview()

    def set_frame_count(self, frame_count):
        """Update the slider's range, keeping the currently selected index.

        The live viewer calls this on every tick as frames land on disk, so it
        must not disturb whichever frame the user is looking at.
        """
        max_index = max(0, int(frame_count) - 1)
        value = min(self.frame_slider.value(), max_index)
        self.frame_slider.blockSignals(True)
        try:
            self.frame_slider.setMaximum(max_index)
            self.frame_slider.setValue(value)
        finally:
            self.frame_slider.blockSignals(False)
        self.frame_slider.setEnabled(max_index > 0)
        self.frame_bar.setVisible(max_index > 0)
        self.frame_label.setText(f"Frame: {value} / {max_index}")

    def _on_frame_slider(self, value):
        self.frame_label.setText(
            f"Frame: {value} / {self.frame_slider.maximum()}"
        )
        self.frame_requested.emit(int(value))

    def update_preview_frame(self, frame, index):
        """Swap in another frame without resetting the preview's pan/zoom."""
        self._preview = frame
        self._current_frame = int(index)
        self._render_preview()

    def _render_preview(self):
        """Draw the preview using the current Scale and vmax % controls.

        Preserves the pan/zoom view across scale/vmax tweaks; only resets it
        on a fresh ``set_preview``.
        """
        ax = self.preview_canvas.ax
        preserve = (not self._reset_view_next) and ax.has_data() and self._preview is not None
        if preserve:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.clear()
        self._rect_patch = None
        frame = self._preview
        if frame is None:
            ax.set_title("(no Eiger data for this scan)")
            self._reset_view_next = False
            self.preview_canvas.draw_idle()
            return
        pct = self.vmax_spin.value()
        vmax = float(np.percentile(frame, pct))
        if vmax <= 0:
            vmax = float(frame.max()) or 1.0
        if self.scale_combo.currentText() == "Log":
            positive = frame[frame > 0]
            vmin = float(positive.min()) if positive.size else 1.0
            if vmax <= vmin:
                vmax = vmin * 10.0
            ax.imshow(frame, origin="lower", cmap="viridis",
                      norm=LogNorm(vmin=vmin, vmax=vmax))
        else:
            ax.imshow(frame, origin="lower", vmin=0, vmax=vmax, cmap="viridis")
        ax.set_title(f"Eiger frame {self._current_frame}")
        self.apply_square(ax)
        self._rect_patch = Rectangle(
            (0, 0), 1, 1, edgecolor="red", facecolor="none", lw=1.5,
        )
        ax.add_patch(self._rect_patch)
        if preserve:
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
        self._reset_view_next = False
        self._update_overlay()

    def _update_overlay(self):
        if self._preview is None or self._rect_patch is None:
            return
        (x0, x1), (y0, y1) = self.get_roi()
        self._rect_patch.set_xy((x0, y0))
        self._rect_patch.set_width(x1 - x0)
        self._rect_patch.set_height(y1 - y0)
        self.preview_canvas.draw_idle()

    def set_frame_marker(self, xy, index=None):
        """Mark the map position at which the previewed frame was taken.

        ``xy`` is an ``(x, y)`` pair in map coordinates, or None to clear the
        marker. The position is remembered, so it is re-drawn after every
        `draw_map` (which clears the axes).
        """
        self._marker_xy = None if xy is None else (float(xy[0]), float(xy[1]))
        self._marker_index = index
        self._draw_frame_marker()

    def _draw_frame_marker(self):
        ax = self.map_canvas.ax
        for art in self._marker_artists:
            try:
                art.remove()
            except Exception:
                pass   # axes were cleared underneath us; the artist is orphaned
        self._marker_artists = []
        if self._marker_xy is not None and ax.has_data():
            x, y = self._marker_xy
            line, = ax.plot(
                [x], [y], linestyle="none", marker="o", markersize=12,
                markerfacecolor="none", markeredgecolor="red",
                markeredgewidth=1.8, zorder=5,
            )
            self._marker_artists.append(line)
            if self._marker_index is not None:
                self._marker_artists.append(ax.annotate(
                    f"#{self._marker_index}", (x, y), textcoords="offset points",
                    xytext=(9, 9), color="red", fontsize=8, zorder=5,
                ))
        self.map_canvas.draw_idle()

    def clear_map(self):
        ax = self.map_canvas.ax
        ax.clear()
        self._marker_artists = []
        self._marker_xy = None
        self._marker_index = None
        if self._cbar is not None:
            try:
                self._cbar.remove()
            except Exception:
                pass
            self._cbar = None
        self.map_canvas.draw_idle()

    def draw_map(self, x, y, z, i0=None, scatter=True, trigs=None, partial=None,
                 drop_partial=False):
        """Draw the position map, coloured by ``z``.

        ``drop_partial`` leaves out the points whose position record is
        incomplete. They carry a correct intensity at a position that can be
        the better part of a step off, which a scatter shows as one slightly
        misplaced dot but tricontourf smears across the triangles around it.
        """
        ax = self.map_canvas.ax
        ax.clear()
        self._marker_artists = []   # dropped by ax.clear(); re-drawn below
        if self._cbar is not None:
            try:
                self._cbar.remove()
            except Exception:
                pass
            self._cbar = None
        xi, yi, zi, pi = _align_and_normalize(x, y, z, i0, trigs, partial)
        xi, yi, zi, pi = _drop_partial_points(xi, yi, zi, pi, drop_partial)
        if xi.size == 0:
            self.map_canvas.draw_idle()
            return
        if scatter:
            sc = ax.scatter(xi, yi, c=zi, s=8)
        else:
            sc = ax.tricontourf(xi, yi, zi, levels=50)
        _mark_partial(ax, xi, yi, pi)
        # "auto", not "equal": a flyscan range is routinely far from square --
        # scan 244 is 10216 x 141, i.e. 72:1 -- and equal *data* units draw
        # that as a sliver a few pixels tall whatever shape the box is.  The
        # box is what gets squared, by _SquareStart; letting the data fill it
        # costs true proportions and buys a map you can actually read.
        ax.set_aspect("auto")
        self.apply_square(ax)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        self._cbar = self.map_canvas.figure.colorbar(sc, ax=ax)
        self._draw_frame_marker()


# ---------------------------------------------------------------------------
# Vortex tab
# ---------------------------------------------------------------------------

class VortexTab(_SquareStart, QtWidgets.QWidget):
    process_requested = QtCore.Signal()
    redraw_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview = None
        self._span_patch = None
        self._cbar = None
        self._reset_view_next = True

        self.e_start = QtWidgets.QSpinBox(); self.e_start.setMaximum(1_000_000)
        self.e_stop = QtWidgets.QSpinBox(); self.e_stop.setMaximum(1_000_000)
        self.e_start.setValue(DEFAULT_VORTEX_ROI[0])
        self.e_stop.setValue(DEFAULT_VORTEX_ROI[1])
        for s in (self.e_start, self.e_stop):
            s.valueChanged.connect(self._update_overlay)

        self.process_btn = QtWidgets.QPushButton("Process")
        self.process_btn.clicked.connect(self.process_requested)

        form = QtWidgets.QFormLayout()
        form.addRow("e_start (channel)", self.e_start)
        form.addRow("e_stop (channel)", self.e_stop)
        form.addRow(self.process_btn)

        form_widget = QtWidgets.QWidget()
        form_widget.setLayout(form)

        self.geometry_panel = _ScanGeometryPanel()
        self.partial_panel = _PartialGroupsPanel()
        self.partial_panel.drop_toggled.connect(
            lambda _: self.redraw_requested.emit())
        left = QtWidgets.QWidget()
        left.setMaximumWidth(285)
        left_v = QtWidgets.QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.addWidget(form_widget)
        left_v.addWidget(self.geometry_panel)
        left_v.addWidget(self.partial_panel, 1)

        # Preview display control (y-axis scale).
        self.scale_combo = QtWidgets.QComboBox()
        self.scale_combo.addItems(["Linear", "Log"])     # Linear is the default
        self.scale_combo.currentIndexChanged.connect(self._render_preview)

        ctrl = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(ctrl); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QtWidgets.QLabel("Y scale:")); h.addWidget(self.scale_combo)
        h.addStretch(1)

        self.preview_canvas = _Canvas()
        self.map_canvas = _Canvas()

        right = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        right.addWidget(_make_preview_panel(self.preview_canvas, ctrl, self))
        right.addWidget(_make_map_panel(self.map_canvas, self))
        right.setSizes([1, 1])
        self._init_square(right)

        outer = QtWidgets.QHBoxLayout(self)
        outer.addWidget(left)
        outer.addWidget(right, 1)

    def get_roi(self):
        return (self.e_start.value(), self.e_stop.value())

    def set_partial_report(self, records, n_groups=0, dropped=0):
        self.partial_panel.set_report(records, n_groups, dropped)

    def drop_incomplete(self):
        """Whether incomplete-position points should be left off the map."""
        return self.partial_panel.drop_chk.isChecked()

    def set_scan_geometry(self, geo):
        self.geometry_panel.set_geometry(geo)

    def set_preview(self, spectrum):
        """Cache the spectrum, reset spinbox bounds, render with current scale."""
        self._preview = spectrum
        self._reset_view_next = True
        if spectrum is not None:
            nch = spectrum.size
            self.e_start.setMaximum(nch)
            self.e_stop.setMaximum(nch)
        self._render_preview()

    def _render_preview(self):
        """Draw the spectrum using the current Y-scale control.

        Preserves the pan/zoom view across scale toggles; only resets it on a
        fresh ``set_preview``.
        """
        ax = self.preview_canvas.ax
        preserve = (not self._reset_view_next) and ax.has_data() and self._preview is not None
        if preserve:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.clear()
        self._span_patch = None
        spectrum = self._preview
        if spectrum is None:
            ax.set_title("(no Vortex data for this scan)")
            self._reset_view_next = False
            self.preview_canvas.draw_idle()
            return
        ax.plot(spectrum, lw=0.8)
        ax.set_xlabel("channel")
        ax.set_ylabel("counts (sum over elements)")
        ax.set_title("Vortex spectrum, frame 0")
        self.apply_square(ax)
        ax.set_yscale("log" if self.scale_combo.currentText() == "Log" else "linear")
        if preserve:
            ax.set_xlim(xlim)
            # Only restore ylim if it is positive on a log axis — otherwise
            # matplotlib warns and ignores it. Let autoscale pick a new ylim.
            if ax.get_yscale() != "log" or ylim[0] > 0:
                ax.set_ylim(ylim)
        self._reset_view_next = False
        self._update_overlay()

    def _update_overlay(self):
        if self._preview is None:
            return
        ax = self.preview_canvas.ax
        if self._span_patch is not None:
            try:
                self._span_patch.remove()
            except Exception:
                pass
        e0, e1 = self.get_roi()
        self._span_patch = ax.axvspan(e0, e1, alpha=0.25, color="red")
        self.preview_canvas.draw_idle()

    def clear_map(self):
        ax = self.map_canvas.ax
        ax.clear()
        if self._cbar is not None:
            try:
                self._cbar.remove()
            except Exception:
                pass
            self._cbar = None
        self.map_canvas.draw_idle()

    def draw_map(self, x, y, z, i0=None, scatter=True, trigs=None, partial=None,
                 drop_partial=False):
        """Draw the position map, coloured by ``z``.

        ``drop_partial`` leaves out the points whose position record is
        incomplete. They carry a correct intensity at a position that can be
        the better part of a step off, which a scatter shows as one slightly
        misplaced dot but tricontourf smears across the triangles around it.
        """
        ax = self.map_canvas.ax
        ax.clear()
        if self._cbar is not None:
            try:
                self._cbar.remove()
            except Exception:
                pass
            self._cbar = None
        xi, yi, zi, pi = _align_and_normalize(x, y, z, i0, trigs, partial)
        xi, yi, zi, pi = _drop_partial_points(xi, yi, zi, pi, drop_partial)
        if xi.size == 0:
            self.map_canvas.draw_idle()
            return
        if scatter:
            sc = ax.scatter(xi, yi, c=zi, s=8)
        else:
            sc = ax.tricontourf(xi, yi, zi, levels=50)
        _mark_partial(ax, xi, yi, pi)
        # "auto", not "equal": a flyscan range is routinely far from square --
        # scan 244 is 10216 x 141, i.e. 72:1 -- and equal *data* units draw
        # that as a sliver a few pixels tall whatever shape the box is.  The
        # box is what gets squared, by _SquareStart; letting the data fill it
        # costs true proportions and buys a map you can actually read.
        ax.set_aspect("auto")
        self.apply_square(ax)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        self._cbar = self.map_canvas.figure.colorbar(sc, ax=ax)
        self.map_canvas.draw_idle()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, initial_folder=None):
        super().__init__()
        self.setWindowTitle("Flyscan viewer")
        self.resize(1300, 850)

        # Per-scan caches.
        self._folder = initial_folder or ""
        self._scan = None
        self._xs = None
        self._ys = None
        self._i0s = None
        self._trigs = None      # trigger value of each position group
        self._partial = None    # groups that only saw part of an exposure
        self._groups = None     # full PositionGroups, for the partial report
        self._eiger_z = None
        self._vortex_z = None
        self._worker = None
        # The naming convention (6-digit vs. unpadded) can differ between
        # streams, so we cache the matching format per stream on load.
        self._fmt_eiger = FNAME_FORMAT
        self._fmt_vortex = FNAME_FORMAT

        # ---- Top control bar ------------------------------------------------
        self.folder_label = QtWidgets.QLabel(self._folder or "(no folder)")
        self.folder_label.setMinimumWidth(220)
        self.folder_label.setStyleSheet("QLabel { color: #444; }")
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)

        self.scan_spin = QtWidgets.QSpinBox()
        self.scan_spin.setMaximum(999_999)
        self.scan_spin.setValue(238)

        load_btn = QtWidgets.QPushButton("Load")
        load_btn.clicked.connect(self._on_load)

        self.norm_chk = QtWidgets.QCheckBox("Normalize by I0")
        self.norm_chk.setEnabled(False)
        self.norm_chk.stateChanged.connect(self._redraw_current_map)

        self.style_combo = QtWidgets.QComboBox()
        self.style_combo.addItems(["Scatter", "Tricontourf"])
        self.style_combo.currentIndexChanged.connect(self._redraw_current_map)


        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Folder:"))
        top.addWidget(self.folder_label, 1)
        top.addWidget(browse_btn)
        top.addSpacing(20)
        top.addWidget(QtWidgets.QLabel("Scan #:"))
        top.addWidget(self.scan_spin)
        top.addWidget(load_btn)
        top.addSpacing(20)
        top.addWidget(self.norm_chk)
        top.addWidget(QtWidgets.QLabel("Style:"))
        top.addWidget(self.style_combo)

        top_widget = QtWidgets.QWidget()
        top_widget.setLayout(top)

        # ---- Tabs -----------------------------------------------------------
        self.tabs = QtWidgets.QTabWidget()
        self.eiger_tab = EigerTab()
        self.vortex_tab = VortexTab()
        self.tabs.addTab(self.eiger_tab, "Eiger")
        self.tabs.addTab(self.vortex_tab, "Vortex")
        self.eiger_tab.process_requested.connect(self._process_eiger)
        self.vortex_tab.process_requested.connect(self._process_vortex)
        self.tabs.currentChanged.connect(self._redraw_current_map)
        self.eiger_tab.redraw_requested.connect(self._redraw_current_map)
        self.vortex_tab.redraw_requested.connect(self._redraw_current_map)

        # ---- Central layout -------------------------------------------------
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.addWidget(top_widget)
        v.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.status = self.statusBar()
        self.status.showMessage("Ready")

    # ------------------------------------------------------------------ slots
    def _browse_folder(self):
        start = self._folder or os.getcwd()
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose sample folder", start
        )
        if path:
            self._folder = path
            self.folder_label.setText(path)

    def _on_load(self):
        if not self._folder:
            self.status.showMessage("Pick a sample folder first.")
            return
        scan = self.scan_spin.value()

        # Drop the previous scan's side panels up front, so a load that fails
        # below never leaves another scan's geometry or flags on screen.
        self._groups = self._trigs = self._partial = None
        for tab in (self.eiger_tab, self.vortex_tab):
            tab.set_scan_geometry(None)
            tab.set_partial_report([])

        pos_path, pos_fmt = _resolve_h5(self._folder, "pos_stream", scan)
        if pos_path is None:
            self.status.showMessage(
                f"pos_stream missing for scan {scan} in {self._folder}"
            )
            return

        try:
            groups = reduce_position_stream(
                scan, self._folder, fname_format=pos_fmt,
            )
        except Exception as e:
            self.status.showMessage(f"Failed to load position stream: {e!r}")
            return

        self._scan = scan
        i0s, xs, ys = groups.i0s, groups.xs, groups.ys
        self._xs, self._ys, self._i0s = xs, ys, i0s
        self._trigs, self._partial = groups.trigs, groups.partial
        self._groups = groups
        self._refresh_partial_report()

        # Beam/detector geometry, read from frame 0 of the Eiger file and the
        # scan's master file. Never fatal — a missing field just shows as "—".
        try:
            geo = read_scan_geometry(self._folder, scan, fname_format=pos_fmt)
        except Exception as e:
            geo = None
            self.status.showMessage(f"Scan geometry unavailable: {e!r}")
        self.eiger_tab.set_scan_geometry(geo)
        self.vortex_tab.set_scan_geometry(geo)

        usable = _is_i0_usable(i0s)
        self.norm_chk.setEnabled(usable)
        if not usable:
            self.norm_chk.setChecked(False)

        # Detector previews — each is independent. Cache the matching
        # filename format per stream so the workers pass the right one;
        # only overwrite the cache when resolution succeeds.
        frame = None
        try:
            eiger_path, fmt = _resolve_h5(self._folder, "eiger", scan)
            if eiger_path is not None:
                self._fmt_eiger = fmt
                frame = _read_eiger_frame(self._folder, scan)
        except Exception as e:
            self.status.showMessage(f"Eiger preview failed: {e!r}")
        self.eiger_tab.set_preview(frame)
        self.eiger_tab.clear_map()
        self._eiger_z = None
        self.tabs.setTabEnabled(0, frame is not None)

        spec = None
        try:
            vortex_path, fmt = _resolve_h5(self._folder, "vortex", scan)
            if vortex_path is not None:
                self._fmt_vortex = fmt
                spec = _read_vortex_spectrum(self._folder, scan)
        except Exception as e:
            self.status.showMessage(f"Vortex preview failed: {e!r}")
        self.vortex_tab.set_preview(spec)
        self.vortex_tab.clear_map()
        self._vortex_z = None
        self.tabs.setTabEnabled(1, spec is not None)

        self.status.showMessage(
            f"Loaded scan {scan}: {xs.size} points · "
            f"Eiger {'OK' if frame is not None else 'missing'} · "
            f"Vortex {'OK' if spec is not None else 'missing'} · "
            f"I0 {'usable' if usable else 'absent'}"
        )

    # ------------------------------------------------------------ processing
    def _start_worker(self, func, kwargs, on_done):
        self._worker = ProcessWorker(func, (self._scan, self._folder), kwargs)
        self._worker.finished_ok.connect(on_done)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_failed(self, msg):
        self.status.showMessage(f"Processing failed: {msg}")
        self.eiger_tab.process_btn.setEnabled(True)
        self.vortex_tab.process_btn.setEnabled(True)

    def _process_eiger(self):
        if self._scan is None:
            self.status.showMessage("Load a scan first.")
            return
        roi = self.eiger_tab.get_roi()
        self.eiger_tab.process_btn.setEnabled(False)
        self.status.showMessage(f"Processing Eiger ROI {roi}…")
        self._start_worker(
            process_images,
            dict(roi=roi, batch=PROCESS_BATCH, fname_format=self._fmt_eiger),
            self._on_eiger_done,
        )

    def _on_eiger_done(self, sums):
        self._eiger_z = sums
        self._refresh_partial_report()
        self.eiger_tab.process_btn.setEnabled(True)
        scatter = self.style_combo.currentText() == "Scatter"
        i0 = self._i0s if self.norm_chk.isChecked() else None
        self.eiger_tab.draw_map(self._xs, self._ys, sums, i0, scatter,
                                self._trigs, self._partial,
                                self.eiger_tab.drop_incomplete())
        self.status.showMessage(f"Eiger processed: {sums.size} points.")

    def _process_vortex(self):
        if self._scan is None:
            self.status.showMessage("Load a scan first.")
            return
        roi = self.vortex_tab.get_roi()
        self.vortex_tab.process_btn.setEnabled(False)
        self.status.showMessage(f"Processing Vortex window {roi}…")
        self._start_worker(
            process_vortex,
            dict(roi=roi, batch=PROCESS_BATCH, fname_format=self._fmt_vortex),
            self._on_vortex_done,
        )

    def _on_vortex_done(self, sums):
        self._vortex_z = sums
        self._refresh_partial_report()
        self.vortex_tab.process_btn.setEnabled(True)
        scatter = self.style_combo.currentText() == "Scatter"
        i0 = self._i0s if self.norm_chk.isChecked() else None
        self.vortex_tab.draw_map(self._xs, self._ys, sums, i0, scatter,
                                 self._trigs, self._partial,
                                 self.vortex_tab.drop_incomplete())
        self.status.showMessage(f"Vortex processed: {sums.size} points.")

    def _refresh_partial_report(self):
        """Re-list the partial groups; the frame column needs the frame count,
        which is only known once a detector stream has been processed."""
        if self._groups is None:
            return
        n_groups = int(self._groups.trigs.size)
        dropped = int(np.sum(self._groups.coverage - self._groups.counts))
        for tab, z in ((self.eiger_tab, self._eiger_z),
                       (self.vortex_tab, self._vortex_z)):
            n_frames = 0 if z is None else int(np.size(z))
            tab.set_partial_report(
                describe_partial_groups(self._groups, n_frames),
                n_groups, dropped,
            )

    def _redraw_current_map(self):
        if self._xs is None:
            return
        scatter = self.style_combo.currentText() == "Scatter"
        i0 = self._i0s if self.norm_chk.isChecked() else None
        idx = self.tabs.currentIndex()
        if idx == 0 and self._eiger_z is not None:
            self.eiger_tab.draw_map(self._xs, self._ys, self._eiger_z, i0, scatter,
                                    self._trigs, self._partial,
                                    self.eiger_tab.drop_incomplete())
        elif idx == 1 and self._vortex_z is not None:
            self.vortex_tab.draw_map(self._xs, self._ys, self._vortex_z, i0, scatter,
                                     self._trigs, self._partial,
                                     self.vortex_tab.drop_incomplete())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Flyscan viewer")
    parser.add_argument("--folder", default=None,
                        help="Sample folder (containing pos_stream/, eiger/, vortex/)")
    parser.add_argument("--scan", type=int, default=None,
                        help="Initial scan number")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(initial_folder=args.folder or os.getcwd())
    if args.scan is not None:
        win.scan_spin.setValue(args.scan)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
