"""Live scan plot, fed by documents streamed from the kernel.

Every plottable detector field in the run gets a curve and a check box, so a
scan with several detectors can be filtered down to the interesting ones.  The
fields hinted by the run -- which is what ``counters`` controls -- are ticked
by default, matching what BestEffortCallback draws inline in the console.

The selectors sit in a panel down the right-hand side of the canvas: a **Plot**
column of check boxes and a **Mon** column of radio buttons.  Picking a monitor
divides every curve by that field point by point, which is how a detector is
normalised against I0 -- the usual way to take the incident-flux drift of a
scan out of the data.

Data is retained **raw** for all fields regardless of tick state, so enabling a
curve part-way through a scan shows its full history, and changing the monitor
recomputes every curve from the values already recorded rather than only
affecting points from there on.

Under the plot is the **peak row**: ``cen``/``com``/``max``/``min``/``fwhm`` for
one chosen curve, a dotted vertical marker on the plot for each of the four that
has a position, and a button that moves the scanned axis onto each.  The
statistics come from
:func:`~id4_common.utils.peak_statistics.peak_statistics` fed the *plotted* arrays,
so a monitor selection is inherited for free -- what the markers show and the
buttons move to is the peak of the curve on screen, not of the raw detector.
"""

import logging

import numpy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import (
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup
from qtpy.QtWidgets import QCheckBox
from qtpy.QtWidgets import QComboBox
from qtpy.QtWidgets import QGridLayout
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QRadioButton
from qtpy.QtWidgets import QScrollArea
from qtpy.QtWidgets import QSizePolicy
from qtpy.QtWidgets import QVBoxLayout
from qtpy.QtWidgets import QWidget

from ...utils.peak_statistics import peak_statistics
from .base import BaseTab
from .base import value_label

logger = logging.getLogger(__name__)

#: Stream that BEC plots from.
PRIMARY = "primary"

#: Flyscans are plotted by the Flyscan plot tab, out of their own HDF5 files.
#: They write no ``primary`` stream at all -- only ``baseline`` -- so letting
#: one through here resets the axes and then leaves them empty, throwing away
#: the scan the user was looking at in exchange for nothing.
#:
#: Matched on the plan name only: ``flyscan``, ``flyscan_snake``, ``flyscan_1d``
#: (``plans/flyscans.py``, ``plans/flyscan_demo.py``).  ``master_file_path``
#: looks like a flyscan marker and is not -- *every* POLAR scan carries it,
#: ``lup`` and ``rel_grid_scan`` included, because the NeXus writer records a
#: master file for all of them.  Testing for it ignored every scan there was.
FLYSCAN_PREFIX = "flyscan"

#: The reduced stream a dichro scan writes alongside ``primary``: XAS and XMCD
#: at one point per polarization pair, which is what the measurement is for.
#: Its two positioners are the scanned axes -- positioner1 the slow one,
#: positioner2 the fast one, confirmed against scan 995 where their ranges
#: match ``huber_hp_nanoy`` and ``huber_hp_nanox`` exactly.
DICHRO_STREAM = "dichro_monitor"
DICHRO_SLOW = "dichro_positioner1"
DICHRO_FAST = "dichro_positioner2"
DICHRO_XAS = "dichro_xas"
DICHRO_XMCD = "dichro_xmcd"

#: Colours for the 1D dichro pair, matching their axis labels.
DICHRO_COLOURS = {DICHRO_XAS: "#1f77b4", DICHRO_XMCD: "#d62728"}


def is_flyscan(doc):
    """Whether *doc* is the start document of a flyscan."""
    return (doc.get("plan_name") or "").startswith(FLYSCAN_PREFIX)


#: Width of the selector panel.  Detector fields have long names
#: (``eiger_stats1_total``), so the panel scrolls rather than pushing the
#: canvas out of the way.
SELECTOR_WIDTH = 260

#: Reuses the Scan tab's helper -- its reply is broadcast to every tab, so
#: asking for it here costs no extra round-trip.
OPTIONS_KEY = "scan_options"
OPTIONS_EXPR = "_gui_scan_options()"

#: The four peak statistics that have a position on the x axis, in the order
#: they are shown, each with the colour of its marker line.  The same colour is
#: used for the statistic's name in the peak row and for its "Go to" button,
#: which is how a line on the plot is identified -- deliberately *not* through
#: the matplotlib legend, which belongs to the curves.  These are picked away
#: from the default curve cycle, and the markers are dotted where curves are
#: solid, so a marker still reads as a marker if a curve lands on the same hue.
MARKER_STYLES = (
    ("cen", "#d62728"),
    ("com", "#1f9e5a"),
    ("max", "#7b3fb5"),
    ("min", "#c77f00"),
)

#: What each statistic means, for the buttons and the toggle.
MARKER_TOOLTIPS = {
    "cen": "Midpoint of the two half-maximum crossings — what BEC prints as cen.",
    "com": "Centre of mass: the intensity-weighted mean position.",
    "max": "Position of the largest plotted value.",
    "min": "Position of the smallest plotted value.",
}


class _Toolbar(NavigationToolbar):
    """NavigationToolbar whose cursor readout stays on one line.

    Over an image -- which is what a grid scan draws -- matplotlib appends the
    value under the cursor to the position with a *newline*, and gives the
    readout label a size policy that ignores its own height.  The two lines are
    then drawn into a strip sized for one: measured here, 41 px of text in a
    32 px label, so both lines come out clipped.

    Flattening the break puts the whole reading on one line, which fits the
    space that already exists -- 21 px tall, and 319 px wide (391 px worst
    case) in a 784 px label -- so nothing has to shrink to be readable.  The
    vertical policy is relaxed too, so the label asks for the height it needs
    rather than accepting whatever it is given.
    """

    #: What the newline between position and value becomes.
    _JOIN = "   "

    def __init__(self, canvas, parent=None):
        """Build the toolbar, then stop its readout being squashed."""
        super().__init__(canvas, parent)
        label = getattr(self, "locLabel", None)
        if label is not None:
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

    def set_message(self, s):
        """Show *s* with any line break flattened into a separator."""
        super().set_message(s.replace("\n", self._JOIN))


def _format(value):
    """Format a position for display *and* for the generated command.

    ``%.10g`` because the two must be the same string: a button that says
    ``1.0234`` and then moves to ``1.0234000000000002`` is a button you cannot
    trust.  Ten significant digits keeps hkl pseudo-axis precision while
    dropping the float noise that ``repr`` would show.
    """
    return f"{float(value):.10g}"


class ScanPlotTab(BaseTab):
    """Plot the running scan, point by point, one curve per detector field."""

    title = "Live plot"

    #: The canvas should fill the pane, not scroll inside it.
    scrollable = False

    #: Worth watching while setting up the next scan in another tab.
    detachable = True

    def __init__(self, parent=None):
        """Build an empty canvas, toolbar and (initially empty) selector panel."""
        super().__init__(parent)

        # Before the widgets: _build_peak_row creates the checkbox whose
        # signal reads this.
        self._derivative = False
        # Right-hand axis carrying the undifferentiated curves for reference.
        self._ref_axes = None
        # Right-hand axis carrying XMCD, when the dichro stream is shown.
        self._dichro_axes = None

        self._figure = Figure(tight_layout=True)
        self._axes = self._figure.add_subplot(111)
        self._canvas = FigureCanvas(self._figure)

        self._status = QLabel("Waiting for a scan…")

        layout = QVBoxLayout(self)
        layout.addWidget(_Toolbar(self._canvas, self))
        middle = QHBoxLayout()
        middle.addWidget(self._canvas, 1)
        middle.addWidget(self._build_selector_panel(), 0)
        layout.addLayout(middle, 1)
        layout.addWidget(self._build_peak_row())
        layout.addWidget(self._build_stream_row())
        layout.addWidget(self._status)

        self._monitor_group = None
        self._axis_fields = {}
        self._kernel_idle = False
        self._scan_running = False
        self._reset_state()
        self._clear_selectors()
        self._draw_placeholder()
        self._update_peak()

    def _build_peak_row(self):
        """Peak statistics for one curve, the marker toggle and the four buttons."""
        self._peak_combo = QComboBox()
        self._peak_combo.setToolTip("Which curve to find the peak of.")
        # Real channel names are long ("eiger_stats1_total", "Ion Chamber
        # 2"); at the width Qt picks from the empty combo they all elide to the
        # same few characters, so there is no telling which curve is selected.
        self._peak_combo.setMinimumWidth(150)
        self._peak_combo.currentTextChanged.connect(
            lambda _text: self._update_peak()
        )

        self._peak_values = value_label("")

        self._markers_box = QCheckBox("Markers")
        self._markers_box.setChecked(True)
        self._markers_box.setToolTip(
            "Draw a dotted vertical line on the plot at each statistic, in the "
            "colour its name is printed in."
        )
        self._markers_box.toggled.connect(lambda _state: self._update_peak())

        self._derivative_box = QCheckBox("Derivative")
        self._derivative_box.setToolTip(
            "Plot d/dx of every curve against the scanned axis, and report the "
            "statistics of that instead.\n"
            "On a knife edge or a slit scan the derivative is the beam "
            "profile, so its fwhm is the beam size."
        )
        self._derivative_box.toggled.connect(self._set_derivative)

        # Two lines, not one.  The five statistics at full precision plus four
        # buttons do not fit across the default 1100 px window, and a QHBoxLayout
        # does not wrap -- it clips the label instead, which silently ate "min"
        # and "fwhm".  Splitting gives the numbers the whole width and costs one
        # row of the canvas.
        values_row = QHBoxLayout()
        values_row.setContentsMargins(0, 0, 0, 0)
        self._peak_label = QLabel("Peak of")
        values_row.addWidget(self._peak_label)
        values_row.addWidget(self._peak_combo)
        values_row.addWidget(self._peak_values, 1)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.addWidget(self._markers_box)
        buttons_row.addWidget(self._derivative_box)
        buttons_row.addSpacing(12)

        # One button per statistic, coloured to match its marker so the button,
        # the name in the peak row and the line on the plot are one thing.
        self._peak_buttons = {}
        for name, colour in MARKER_STYLES:
            button = QPushButton(f"Go to {name}")
            button.setStyleSheet(f"color: {colour};")
            button.clicked.connect(
                lambda _checked=False, n=name: self._go_to(n)
            )
            self._peak_buttons[name] = button
            buttons_row.addWidget(button)
        buttons_row.addStretch(1)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        column.addLayout(values_row)
        column.addLayout(buttons_row)

        self._peak_row = QWidget()
        self._peak_row.setLayout(column)
        return self._peak_row

    def _build_stream_row(self):
        """Stream picker, shown only for a run that writes a dichro stream."""
        self._stream_combo = QComboBox()
        self._stream_combo.addItems([PRIMARY, DICHRO_STREAM])
        self._stream_combo.setToolTip(
            "Which stream to plot.  A dichro scan writes its reduced XAS and "
            "XMCD to dichro_monitor, one point per polarization pair; the "
            "detectors themselves are in primary."
        )
        self._stream_combo.currentTextChanged.connect(self._set_stream)

        self._dichro_field = QComboBox()
        self._dichro_field.addItems([DICHRO_XMCD, DICHRO_XAS])
        self._dichro_field.setToolTip("Which dichro channel to map.")
        self._dichro_field.currentTextChanged.connect(
            lambda _t: self._repaint_stream()
        )

        self._stream_row = QWidget()
        row = QHBoxLayout(self._stream_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel("Stream"))
        row.addWidget(self._stream_combo)
        row.addWidget(self._dichro_field)
        row.addStretch(1)
        self._stream_row.hide()
        return self._stream_row

    def _build_selector_panel(self):
        """The Plot / Mon columns, down the right-hand side of the canvas."""
        self._selector_grid = QGridLayout()
        self._selector_grid.setHorizontalSpacing(10)
        self._selector_grid.setVerticalSpacing(2)
        # Divisor radio first, field name second.  The names are long
        # ("eiger_stats1_total", "pr2_th_user_setpoint") and the panel has a
        # fixed width, so with the name column first the radios were pushed off
        # the right-hand edge and could only be reached by scrolling sideways.
        # Narrow column pinned, the name column takes what is left.
        self._selector_grid.setColumnStretch(0, 0)
        self._selector_grid.setColumnStretch(1, 1)

        holder = QWidget()
        inner = QVBoxLayout(holder)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addLayout(self._selector_grid)
        inner.addStretch(1)

        self._selector_area = QScrollArea()
        self._selector_area.setWidget(holder)
        self._selector_area.setWidgetResizable(True)
        self._selector_area.setFixedWidth(SELECTOR_WIDTH)
        return self._selector_area

    # -- state ------------------------------------------------------------

    def _reset_state(self):
        self._descriptor_uid = None
        self._x_field = None
        self._x_data = []
        # field -> {"y": raw values, "line": Line2D|None, "box": QCheckBox,
        #           "radio": QRadioButton}
        self._series = {}
        self._monitor = None
        self._start_time = None
        self._use_elapsed_time = False
        # 2D (mesh) state, used when the run is a grid scan.
        self._grid = None  # {"slow","fast","shape","extents"}
        self._grid_field = None
        self._grid_data = None
        self._grid_cells = []
        # Scan id on the axes now, so a skipped flyscan can say what is still
        # being shown.  Not cleared by _reset_state's caller for a flyscan --
        # that path returns before any reset.
        self._scan_id = None
        # True while a flyscan is running and being ignored.
        self._ignoring = False
        # The dichro_monitor stream, when the run writes one.
        self._dichro_uid = None
        self._dichro_columns = {}
        self._stream = PRIMARY
        # Title text, kept so switching stream can put it back.
        self._title_text = ""
        if getattr(self, "_stream_row", None) is not None:
            self._stream_row.hide()
            blocked = self._stream_combo.blockSignals(True)
            self._stream_combo.setCurrentText(PRIMARY)
            self._stream_combo.blockSignals(blocked)
        self._image = None
        self._colorbar = None
        # Peak statistics of the field named in the peak combo, or None.
        self._peak_stats = None
        # statistic -> the axvline drawn for it.  Emptied here rather than
        # removed: _on_start clears the axes straight afterwards, which takes
        # the artists with it.
        self._marker_lines = {}

    def _clear_selectors(self):
        while self._selector_grid.count():
            item = self._selector_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # setParent(None) as well as deleteLater(): the deferred delete
                # is not processed until the event loop gets round to it, and
                # until then the old row is still a child of the panel and
                # paints on top of the new one at its former position.
                widget.setParent(None)
                widget.deleteLater()
        # A fresh exclusive group each run; the old one dies with its buttons.
        self._monitor_group = QButtonGroup(self)
        self._monitor_group.setExclusive(True)

        plot_header = QLabel("Plot")
        plot_header.setToolTip("Tick a channel to draw it as a curve.")
        monitor_header = QLabel("÷ by")
        monitor_header.setToolTip(
            "Pick one channel to divide every plotted curve by, point by "
            "point -- normalising against I0, typically.  One at a time, "
            "hence radio buttons rather than tick boxes."
        )
        for column, header in enumerate((monitor_header, plot_header)):
            header.setStyleSheet("font-weight: bold;")
            self._selector_grid.addWidget(header, 0, column)

        # "no monitor" is a real member of the group, so choosing it is how the
        # division is switched off again.
        self._no_monitor = QRadioButton()
        self._no_monitor.setChecked(True)
        self._no_monitor.setToolTip(
            "Divide by nothing: plot the channels as they were counted."
        )
        self._monitor_group.addButton(self._no_monitor)
        self._no_monitor.toggled.connect(
            lambda checked: self._set_monitor(None) if checked else None
        )
        label = QLabel("none (raw)")
        label.setToolTip(
            "Divide by nothing: plot the channels as they were counted."
        )
        label.setStyleSheet("font-style: italic;")
        self._selector_grid.addWidget(self._no_monitor, 1, 0, Qt.AlignCenter)
        self._selector_grid.addWidget(label, 1, 1)

    # -- document handling ------------------------------------------------

    def on_document(self, name, doc):
        """Consume one Bluesky document."""
        handler = getattr(self, f"_on_{name}", None)
        if handler is None:
            return
        try:
            handler(doc)
        except Exception:  # noqa: BLE001 - a bad document must not kill the tab
            logger.exception("Failed to handle %r document.", name)

    def _on_start(self, doc):
        if is_flyscan(doc):
            # Leave everything as it is: the previous scan stays on screen, and
            # the status line says why it has stopped moving.
            self._ignoring = True
            shown = (
                f" — still showing scan {self._scan_id}"
                if self._scan_id is not None
                else ""
            )
            self._status.setText(
                f"Flyscan {doc.get('scan_id', '?')} running; it is plotted in "
                f"the Flyscan plot tab{shown}."
            )
            return
        self._ignoring = False
        # Fresh axes per run.  The colourbar has to go before the state that
        # holds it is cleared, or it is orphaned -- it lives in its own axes,
        # so self._axes.clear() does not take it away.
        self._discard_colorbar()
        # Same reasoning as the colourbar: a twin axis is its own axes, so
        # self._axes.clear() would leave it behind -- the derivative's
        # reference axis, and the dichro stream's XMCD axis, which otherwise
        # kept the previous scan's curve drawn over the new one.
        self._drop_reference_axes()
        self._drop_dichro_axes()
        self._reset_state()
        self._clear_selectors()
        self._start_time = doc.get("time")
        # After _reset_state, which clears it.
        self._scan_id = doc.get("scan_id")

        hints = doc.get("hints") or {}
        dimensions = hints.get("dimensions") or []
        self._grid = self._grid_geometry(doc, hints, dimensions)

        if dimensions:
            fields, stream = dimensions[0]
            if stream == PRIMARY and fields:
                self._x_field = fields[0]
        if self._x_field in (None, "time"):
            # count() and friends have no scanned motor.
            self._x_field = "time"
            self._use_elapsed_time = True

        self._axes.clear()
        scan_id = doc.get("scan_id", "?")
        plan = doc.get("plan_name", "scan")
        self._title_text = f"#{scan_id}  {plan}"
        self._axes.set_title(self._title_text)
        if self._grid:
            # Match BestEffortCallback's LiveGrid: the inner (fast) axis runs
            # horizontally, the outer (slow) axis vertically.
            self._axes.set_xlabel(self._grid["fast"])
            self._axes.set_ylabel(self._grid["slow"])
        else:
            self._axes.set_xlabel(
                "time (s)" if self._use_elapsed_time else self._x_field
            )
            self._axes.grid(True, alpha=0.3)
        self._canvas.draw_idle()
        self._status.setText(f"Scan #{scan_id} ({plan}) running…")
        self._scan_running = True
        self._update_peak()

    @staticmethod
    def _grid_geometry(doc, hints, dimensions):
        """Return mesh geometry for a rectilinear grid scan, else None.

        ``grid_scan``/``rel_grid_scan`` set ``hints["gridding"]`` and carry
        ``shape``/``extents``; ``dimensions`` is ordered outer(slow) first.
        """
        if hints.get("gridding") != "rectilinear" or len(dimensions) < 2:
            return None
        shape = doc.get("shape")
        extents = doc.get("extents")
        if not shape or not extents or len(shape) < 2 or len(extents) < 2:
            return None
        try:
            slow = dimensions[0][0][0]
            fast = dimensions[1][0][0]
        except (IndexError, TypeError):
            return None
        return {
            "slow": slow,
            "fast": fast,
            "shape": (int(shape[0]), int(shape[1])),
            "extents": (list(extents[0]), list(extents[1])),
            # Set by _anchor_grid once the first readback arrives.
            "anchored": False,
        }

    def _on_descriptor(self, doc):
        if doc.get("name") == DICHRO_STREAM:
            # Remember it and offer the picker; the primary view stays up
            # until the user asks for the other stream.
            self._dichro_uid = doc.get("uid")
            self._dichro_columns = {
                key: [] for key in (doc.get("data_keys") or {})
            }
            self._stream_row.show()
            return
        if doc.get("name") != PRIMARY:
            return
        self._descriptor_uid = doc.get("uid")
        if self._series:
            return
        hinted, plottable = self._candidate_fields(doc)
        for field in plottable:
            self._add_series(field, checked=field in hinted)
        if not plottable:
            self._status.setText("No numeric detector field to plot.")
        if self._grid:
            # An image can show one channel at a time, so the check boxes act
            # as a selector here rather than as independent curves.
            self._select_grid_field(
                next((f for f in plottable if f in hinted), None)
                or (plottable[0] if plottable else None)
            )
        self._update_peak()

    def _candidate_fields(self, descriptor):
        """Return (hinted fields, all plottable fields) for this descriptor.

        Hinted fields are what ``counters``/``select_plot`` marked, i.e. the
        user's own choice, so they are the ones ticked by default.
        """
        data_keys = descriptor.get("data_keys") or {}
        hints = descriptor.get("hints") or {}

        # The scanned axes themselves are never a y (or colour) channel.  For a
        # mesh that means both of them, not just the one on the x axis.
        axis_fields = {self._x_field}
        if self._grid:
            axis_fields |= {self._grid["slow"], self._grid["fast"]}

        hinted = []
        for obj_hints in hints.values():
            for field in obj_hints.get("fields", []):
                if field not in axis_fields and field in data_keys:
                    hinted.append(field)

        plottable = []
        for field, spec in data_keys.items():
            if field in axis_fields:
                continue
            # Scalars only: images and arrays have a non-empty shape.
            if spec.get("dtype") == "number" and not spec.get("shape"):
                plottable.append(field)

        # Keep hinted fields first and in hint order, then the rest.
        ordered = hinted + [f for f in sorted(plottable) if f not in hinted]
        return hinted, ordered

    def _add_series(self, field, checked):
        box = QCheckBox(field)
        box.setChecked(checked)
        box.setToolTip(field)
        box.toggled.connect(lambda state, f=field: self._on_toggle(f, state))

        radio = QRadioButton()
        radio.setToolTip(f"Divide the plotted curves by {field}.")
        self._monitor_group.addButton(radio)
        radio.toggled.connect(
            lambda checked, f=field: self._set_monitor(f) if checked else None
        )

        row = self._selector_grid.rowCount()
        self._selector_grid.addWidget(radio, row, 0, Qt.AlignCenter)
        self._selector_grid.addWidget(box, row, 1)
        self._series[field] = {
            "y": [],
            "line": None,
            "box": box,
            "radio": radio,
            # The undifferentiated curve on the twin axis, when shown.
            "ref": None,
        }

    # -- normalisation ------------------------------------------------------

    def _values(self, series):
        """Return the plotted values: raw, normalised, and/or differentiated.

        Every curve and every peak statistic goes through here, so taking the
        derivative at this one point is what makes the peak row describe the
        derivative too -- which is the whole point of the option: ``fwhm`` of
        the derivative of a knife edge is the beam size.
        """
        return self._differentiate(self._normalised(series))

    def _normalised(self, series):
        """The values before differentiation: raw, or over the monitor."""
        if self._monitor is None:
            return series["y"]
        monitor = self._series.get(self._monitor)
        if monitor is None:
            return series["y"]
        out = []
        # strict=False: both lists are appended once per event so they match,
        # and a truncated curve beats an exception mid-scan if they ever do not.
        for value, divisor in zip(series["y"], monitor["y"], strict=False):
            try:
                out.append(value / divisor)
            except (TypeError, ZeroDivisionError):
                # A dropped key or a monitor reading of zero: leave a gap
                # rather than a spike or an exception mid-scan.
                out.append(float("nan"))
        return out

    def _differentiate(self, values):
        """d(values)/dx against the scanned axis, when the option is on.

        ``numpy.gradient`` because it copes with the uneven point spacing a
        ``lup`` on a slow axis can produce and returns one value per point, so
        the derivative stays aligned with ``_x_data`` and every caller here
        keeps working unchanged.

        A step in x of zero would divide by zero, so those points are dropped
        to NaN -- ``peak_statistics`` already discards non-finite pairs, and a
        gap reads better than an infinite spike.
        """
        if not self._derivative or self._grid:
            return values
        x = numpy.asarray(self._x_data, dtype=float)
        y = numpy.asarray(values, dtype=float)
        size = min(x.size, y.size)
        # Two points are the minimum numpy.gradient will accept.
        if size < 2:
            return [float("nan")] * len(values)
        x, y = x[:size], y[:size]
        with numpy.errstate(divide="ignore", invalid="ignore"):
            slope = numpy.gradient(y, x)
        slope[~numpy.isfinite(slope)] = numpy.nan
        return list(slope) + [float("nan")] * (len(values) - size)

    def _label_base(self, field):
        """The curve's name before differentiation, ratio included."""
        return f"{field} / {self._monitor}" if self._monitor else field

    def _label(self, field):
        """The curve/colourbar label, which says so when it is a ratio."""
        base = self._label_base(field)
        return f"d({base})/dx" if self._derivative and not self._grid else base

    def _shown(self, series):
        """Whether a field is drawn.  The monitor itself never is -- it would
        be a flat line of ones."""
        return series["box"].isChecked() and series["box"].isEnabled()

    def _set_monitor(self, field):
        """Normalise every curve by *field*, or stop normalising when None."""
        if field == self._monitor:
            return
        self._monitor = field
        for name, series in self._series.items():
            series["box"].setEnabled(name != field)

        if self._grid:
            if self._grid_field == field:
                # The image cannot show the monitor divided by itself.
                self._select_grid_field(
                    next((n for n in self._series if n != field), None)
                )
            self._rebuild_grid()
            self._update_status()
            self._update_peak()
            return

        for name, series in self._series.items():
            line = series["line"]
            if line is None:
                continue
            line.set_data(self._x_data, self._values(series))
            line.set_label(self._label(name))
            line.set_visible(self._shown(series))
        self._sync_references()
        self._rescale()
        self._update_status()
        self._update_peak()

    def _set_derivative(self, enabled):
        """Switch every curve between the signal and its derivative.

        The raw points are kept either way -- as with the monitor selection,
        this recomputes the curves already recorded rather than only affecting
        points from here on, so it can be ticked mid-scan or after one.
        """
        enabled = bool(enabled)
        if enabled == self._derivative:
            return
        self._derivative = enabled
        # A mesh has no single axis to differentiate along; the option is
        # ignored there (``_differentiate`` returns the values untouched) and
        # the image is left as it is.
        if self._grid:
            return
        for name, series in self._series.items():
            line = series["line"]
            if line is None:
                continue
            line.set_data(self._x_data, self._values(series))
            line.set_label(self._label(name))
        self._sync_references()
        self._rescale()
        self._update_status()
        self._update_peak()

    def _on_toggle(self, field, checked):
        series = self._series.get(field)
        if series is None:
            return
        if self._grid:
            if checked:
                self._select_grid_field(field)
            return
        if checked and series["line"] is None:
            self._create_line(field, series)
        elif series["line"] is not None:
            series["line"].set_visible(self._shown(series))
        self._sync_references()
        self._rescale()
        self._update_status()
        self._update_peak()

    # -- 2D (mesh) rendering ----------------------------------------------

    def _select_grid_field(self, field):
        """Show *field* as the image, unticking the others."""
        if field is None:
            return
        for name, series in self._series.items():
            box = series["box"]
            blocked = box.blockSignals(True)
            box.setChecked(name == field)
            box.blockSignals(blocked)
        if field != self._grid_field:
            self._grid_field = field
            # Rebuild from the points already recorded, so switching channel
            # mid-scan redraws the whole mesh rather than starting it over.
            self._rebuild_grid()

    def _rebuild_grid(self):
        """Recompute the mesh from every point seen so far."""
        if self._grid is None or self._grid_field is None:
            return
        rows, columns = self._grid["shape"]
        self._grid_data = numpy.full((rows, columns), numpy.nan)
        series = self._series.get(self._grid_field)
        if series is not None:
            cells = zip(self._grid_cells, self._values(series), strict=False)
            for cell, value in cells:
                if cell is not None:
                    self._grid_data[cell] = value
        self._redraw_grid()

    def _anchor_grid(self, data):
        """Move the declared extents onto the actual readbacks, once.

        ``rel_grid_scan`` records its extents as the *offsets* it was handed --
        ``((-10, 10), (-10, 10))`` -- while the motors read absolute positions
        around wherever they happened to start.  Mapping readbacks into those
        relative extents clamps nearly every point onto one corner, so a whole
        20x20 mesh arrives as a couple of pixels.

        The *span* is right either way; only the origin is missing.  A grid
        scan takes its first point at the start corner, so the offset is that
        point minus the declared start.  For an absolute ``grid_scan`` the
        offset comes out at zero and nothing moves.
        """
        if self._grid is None or self._grid["anchored"]:
            return
        slow = data.get(self._grid["slow"])
        fast = data.get(self._grid["fast"])
        if slow is None or fast is None:
            return
        (slow0, slow1), (fast0, fast1) = self._grid["extents"]
        shift_slow = float(slow) - slow0
        shift_fast = float(fast) - fast0
        self._grid["extents"] = (
            [slow0 + shift_slow, slow1 + shift_slow],
            [fast0 + shift_fast, fast1 + shift_fast],
        )
        self._grid["anchored"] = True
        # The image is created with the extents as they were; a relative scan
        # would otherwise keep the axes labelled -10..10.
        if self._image is not None:
            (s0, s1), (f0, f1) = self._grid["extents"]
            self._image.set_extent([f0, f1, s0, s1])

    def _grid_indices(self, data):
        """Map a point's motor positions to (row, column) in the mesh.

        Derived from the readback values and the run's declared extents rather
        than from the event order, so snaked scans and out-of-order points land
        correctly without having to model the trajectory.
        """
        rows, columns = self._grid["shape"]
        (slow0, slow1), (fast0, fast1) = self._grid["extents"]
        slow = data.get(self._grid["slow"])
        fast = data.get(self._grid["fast"])
        if slow is None or fast is None:
            return None

        def _index(value, low, high, count):
            if count <= 1 or high == low:
                return 0
            position = (float(value) - low) / (high - low) * (count - 1)
            return max(0, min(count - 1, int(round(position))))

        return _index(slow, slow0, slow1, rows), _index(
            fast, fast0, fast1, columns
        )

    def _accumulate_grid(self, cell):
        """Fill in the one cell this event landed in."""
        if self._grid_field is None or cell is None:
            return
        series = self._series.get(self._grid_field)
        if series is None or not series["y"]:
            return
        if self._grid_data is None:
            rows, columns = self._grid["shape"]
            self._grid_data = numpy.full((rows, columns), numpy.nan)
        self._grid_data[cell] = self._values(series)[-1]
        self._redraw_grid()

    def _discard_colorbar(self):
        if getattr(self, "_colorbar", None) is None:
            return
        try:
            self._colorbar.remove()
        except Exception:  # noqa: BLE001 - already gone with the axes
            logger.debug("Colorbar removal failed.", exc_info=True)
        self._colorbar = None

    def _redraw_grid(self):
        if self._grid is None or self._grid_data is None:
            return
        finite = numpy.isfinite(self._grid_data)
        if self._image is None and not finite.any():
            # imshow on an all-NaN array has nothing to autoscale to; wait for
            # the first real point.
            return
        (slow0, slow1), (fast0, fast1) = self._grid["extents"]
        if self._image is None:
            self._image = self._axes.imshow(
                self._grid_data,
                origin="lower",
                aspect="auto",
                interpolation="nearest",
                extent=[fast0, fast1, slow0, slow1],
            )
            self._colorbar = self._figure.colorbar(self._image, ax=self._axes)
        else:
            self._image.set_data(self._grid_data)
        if finite.any():
            self._image.set_clim(
                float(numpy.nanmin(self._grid_data)),
                float(numpy.nanmax(self._grid_data)),
            )
        if self._colorbar is not None:
            self._colorbar.set_label(self._label(self._grid_field))
        self._canvas.draw_idle()

    def _reference_axes(self):
        """The right-hand axis the reference curves live on, made on demand.

        A twin rather than the same axis because the signal and its derivative
        have different units and, on a knife edge, wildly different magnitudes
        -- drawn together on one scale the smaller of the two is a flat line.
        """
        if self._ref_axes is None:
            self._ref_axes = self._axes.twinx()
            self._ref_axes.set_zorder(self._axes.get_zorder() - 1)
            # Otherwise the twin's opaque background hides the derivative.
            self._axes.patch.set_visible(False)
        return self._ref_axes

    def _drop_reference_axes(self):
        """Remove the twin axis and every reference curve on it."""
        for series in self._series.values():
            series["ref"] = None
        if self._ref_axes is not None:
            try:
                self._ref_axes.remove()
            except Exception:  # noqa: BLE001 - already gone with the axes
                logger.debug("Reference axis removal failed.", exc_info=True)
            self._ref_axes = None
        self._axes.patch.set_visible(True)

    def _sync_reference(self, field, series):
        """Draw, update or drop one field's reference curve."""
        wanted = (
            self._derivative
            and not self._grid
            and series["line"] is not None
            and self._shown(series)
        )
        line = series.get("ref")
        if not wanted:
            if line is not None:
                line.remove()
                series["ref"] = None
            return
        values = self._normalised(series)
        label = f"{self._label_base(field)} (signal)"
        if line is None:
            # Dashed, thin and faded, in its curve's own colour: context for
            # the derivative rather than something competing with it.
            (line,) = self._reference_axes().plot(
                self._x_data,
                values,
                linestyle="--",
                linewidth=1.0,
                alpha=0.45,
                color=series["line"].get_color(),
                label=label,
            )
            series["ref"] = line
        else:
            line.set_data(self._x_data, values)
            line.set_label(label)

    def _sync_references(self):
        """Bring every reference curve into line with the current state."""
        for field, series in self._series.items():
            self._sync_reference(field, series)
        if self._ref_axes is None:
            return
        if not any(s.get("ref") for s in self._series.values()):
            self._drop_reference_axes()
        else:
            self._ref_axes.relim(visible_only=True)
            self._ref_axes.autoscale_view()
            self._ref_axes.set_ylabel("signal")

    def _create_line(self, field, series):
        (line,) = self._axes.plot(
            self._x_data,
            self._values(series),
            marker="o",
            markersize=3,
            label=self._label(field),
        )
        series["line"] = line
        # Colour the check box to match its curve.
        series["box"].setStyleSheet(f"color: {line.get_color()};")

    def _on_event(self, doc):
        if self._dichro_uid and doc.get("descriptor") == self._dichro_uid:
            data = doc.get("data") or {}
            for field, values in self._dichro_columns.items():
                value = data.get(field)
                values.append(
                    value if isinstance(value, (int, float)) else float("nan")
                )
            if self._stream == DICHRO_STREAM:
                self._draw_dichro()
            return
        if doc.get("descriptor") != self._descriptor_uid:
            return
        data = doc.get("data") or {}

        if self._grid:
            self._x_data.append(doc.get("seq_num", len(self._x_data) + 1))
            for field, series in self._series.items():
                value = data.get(field)
                series["y"].append(
                    value if isinstance(value, (int, float)) else float("nan")
                )
            self._anchor_grid(data)
            cell = self._grid_indices(data)
            self._grid_cells.append(cell)
            self._accumulate_grid(cell)
            self._update_status()
            return

        if self._use_elapsed_time:
            x = doc.get("time", 0.0) - (
                self._start_time or doc.get("time", 0.0)
            )
        elif self._x_field in data:
            x = data[self._x_field]
        else:
            return

        self._x_data.append(x)
        for field, series in self._series.items():
            value = data.get(field)
            # Keep the arrays the same length even if a key is missing.
            series["y"].append(
                value if isinstance(value, (int, float)) else float("nan")
            )
        # The monitor's own point has to be in before any ratio is computed,
        # hence the second pass.
        for field, series in self._series.items():
            if self._shown(series):
                if series["line"] is None:
                    self._create_line(field, series)
                else:
                    series["line"].set_data(self._x_data, self._values(series))
        self._sync_references()

        self._rescale()
        self._update_status()

    def _set_stream(self, name):
        """Switch the canvas between the primary and dichro streams."""
        if name == self._stream:
            return
        self._stream = name
        self._repaint_stream()

    def _repaint_stream(self):
        """Redraw whichever stream is selected, from what has arrived so far."""
        self._discard_colorbar()
        self._drop_reference_axes()
        self._drop_dichro_axes()
        self._axes.clear()
        self._image = None
        for series in self._series.values():
            # The artists died with the axes; _redraw_primary makes new ones.
            series["line"] = None
            series["ref"] = None
        self._axes.set_title(self._title_text)
        self._dichro_field.setVisible(
            self._stream == DICHRO_STREAM and bool(self._grid)
        )
        if self._stream == DICHRO_STREAM:
            self._draw_dichro()
        else:
            self._redraw_primary()
        # Both ways: it is what decides whether the peak row belongs on screen,
        # and the row describes the primary channels only.
        self._update_peak()

    def _redraw_primary(self):
        """Put the primary stream back on the axes after a stream switch."""
        if self._grid:
            self._axes.set_xlabel(self._grid["fast"])
            self._axes.set_ylabel(self._grid["slow"])
            self._redraw_grid()
        else:
            for field, series in self._series.items():
                if self._shown(series):
                    self._create_line(field, series)
            self._sync_references()
            self._rescale()
        self._canvas.draw_idle()

    def _drop_dichro_axes(self):
        """Remove the right-hand XMCD axis, if one is up."""
        if self._dichro_axes is None:
            return
        try:
            self._dichro_axes.remove()
        except Exception:  # noqa: BLE001 - already gone with the axes
            logger.debug("Dichro axis removal failed.", exc_info=True)
        self._dichro_axes = None
        self._axes.patch.set_visible(True)

    def _draw_dichro(self):
        """Draw the dichro stream: a map on a mesh, two curves otherwise."""
        columns = self._dichro_columns
        slow = columns.get(DICHRO_SLOW) or []
        fast = columns.get(DICHRO_FAST) or []
        if not slow:
            self._status.setText("Waiting for dichro points…")
            return
        # Tear down what the previous pass left behind.  A twin axis and a
        # colourbar are each their own axes, so ``self._axes.clear()`` does not
        # take them away -- and this runs once per dichro point during a live
        # scan, so they pile up: an extra right-hand scale and an extra stale
        # trace for every point that arrives.
        self._discard_colorbar()
        self._drop_dichro_axes()
        self._image = None
        self._axes.clear()
        self._axes.set_title(self._title_text)
        if self._grid and any(v == v for v in fast):
            self._draw_dichro_map(slow, fast)
        else:
            self._draw_dichro_curves(slow, columns)
        self._canvas.draw_idle()
        self._update_status()

    def _draw_dichro_map(self, slow, fast):
        """Map one dichro channel over the mesh.

        The geometry comes from the run's declared shape and the anchored
        extents, never from the points in hand: a scan can be interrupted
        part-way -- 995 was -- and min/max of a partial mesh would put every
        point in the wrong cell.
        """
        field = self._dichro_field.currentText()
        values = self._dichro_columns.get(field) or []
        rows, columns_n = self._grid["shape"]
        grid = numpy.full((rows, columns_n), numpy.nan)
        for index in range(min(len(slow), len(fast), len(values))):
            point = {
                self._grid["slow"]: slow[index],
                self._grid["fast"]: fast[index],
            }
            self._anchor_grid(point)
            cell = self._grid_indices(point)
            if cell is not None:
                grid[cell] = values[index]

        (slow0, slow1), (fast0, fast1) = self._grid["extents"]
        self._image = self._axes.imshow(
            grid,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[fast0, fast1, slow0, slow1],
        )
        finite = numpy.isfinite(grid)
        if finite.any():
            self._image.set_clim(
                float(numpy.nanmin(grid)),
                float(numpy.nanmax(grid)),
            )
        self._colorbar = self._figure.colorbar(self._image, ax=self._axes)
        self._colorbar.set_label(field)
        self._axes.set_xlabel(self._grid["fast"])
        self._axes.set_ylabel(self._grid["slow"])

    def _draw_dichro_curves(self, slow, columns):
        """XAS on the left axis and XMCD on the right, against positioner1.

        Two axes because the pair differ by about two orders of magnitude; on
        one scale XMCD is a flat line along the bottom.
        """
        self._axes.set_xlabel(DICHRO_SLOW)
        handles = []
        xas = columns.get(DICHRO_XAS) or []
        if xas:
            count = min(len(slow), len(xas))
            (line,) = self._axes.plot(
                slow[:count],
                xas[:count],
                marker="o",
                markersize=3,
                color=DICHRO_COLOURS[DICHRO_XAS],
                label=DICHRO_XAS,
            )
            handles.append(line)
            self._axes.set_ylabel(DICHRO_XAS)
        xmcd = columns.get(DICHRO_XMCD) or []
        if xmcd:
            count = min(len(slow), len(xmcd))
            self._dichro_axes = self._axes.twinx()
            (line,) = self._dichro_axes.plot(
                slow[:count],
                xmcd[:count],
                marker="o",
                markersize=3,
                color=DICHRO_COLOURS[DICHRO_XMCD],
                label=DICHRO_XMCD,
            )
            handles.append(line)
            self._dichro_axes.set_ylabel(DICHRO_XMCD)
        if len(handles) > 1:
            self._axes.legend(
                handles,
                [h.get_label() for h in handles],
                fontsize="small",
                loc="best",
            )

    def _update_status(self):
        if self._stream == DICHRO_STREAM:
            points = len(self._dichro_columns.get(DICHRO_SLOW) or [])
            self._status.setText(f"{DICHRO_STREAM} — {points} points.")
            return
        normalised = f", normalised by {self._monitor}" if self._monitor else ""
        if self._grid:
            rows, columns = self._grid["shape"]
            self._status.setText(
                f"{len(self._x_data)} of {rows * columns} points — "
                f"{self._grid_field} vs {self._grid['fast']} / "
                f"{self._grid['slow']}{normalised}"
            )
            return
        shown = sum(1 for s in self._series.values() if self._shown(s))
        self._status.setText(
            f"{len(self._x_data)} points — {shown} of {len(self._series)} "
            f"curves shown{normalised}"
        )

    def _rescale(self):
        # visible_only so hidden curves do not stretch the axes.
        self._axes.relim(visible_only=True)
        self._axes.autoscale_view()
        visible = [
            s["line"]
            for s in self._series.values()
            if s["line"] is not None and self._shown(s)
        ]
        # The reference curves live on the twin axis, so its handles have to be
        # gathered explicitly or they appear on the plot with nothing naming
        # them -- a legend owned by one axis knows only its own lines.
        refs = [s["ref"] for s in self._series.values() if s.get("ref")]
        handles = visible + refs
        if len(handles) > 1:
            self._axes.legend(
                handles,
                [h.get_label() for h in handles],
                fontsize="small",
                loc="best",
            )
        elif self._axes.get_legend() is not None:
            self._axes.get_legend().remove()
        if len(visible) == 1:
            self._axes.set_ylabel(visible[0].get_label())
        else:
            self._axes.set_ylabel("")
        self._canvas.draw_idle()

    def _on_stop(self, doc):
        if self._ignoring:
            # The flyscan we skipped has finished; the next ordinary scan is
            # free to take the axes again.
            self._ignoring = False
            return
        # The curves are deliberately left on the axes after the scan.
        reason = doc.get("exit_status", "completed")
        self._status.setText(f"Scan {reason} — {len(self._x_data)} points.")
        self._canvas.draw_idle()
        self._scan_running = False
        self._update_peak()

    # -- peak statistics, markers and the move buttons ---------------------

    def _peak_field(self):
        """Which curve the peak row describes: the combo's choice, if drawn."""
        shown = [name for name, s in self._series.items() if self._shown(s)]
        current = self._peak_combo.currentText()
        if current not in shown:
            current = shown[0] if shown else ""
        # Repopulate only when the list really changed, or the combo fights the
        # user by resetting the choice on every event.
        combo = self._peak_combo
        existing = [combo.itemText(i) for i in range(combo.count())]
        if existing != shown:
            blocked = self._peak_combo.blockSignals(True)
            self._peak_combo.clear()
            self._peak_combo.addItems(shown)
            self._peak_combo.blockSignals(blocked)
        if current:
            blocked = self._peak_combo.blockSignals(True)
            self._peak_combo.setCurrentText(current)
            self._peak_combo.blockSignals(blocked)
        return current or None

    def _peak_axis(self):
        """Dotted path of the scanned axis, or None if it cannot be resolved.

        The documents name the axis by its *hinted field* (``huber_euler_h``); the
        command has to name it by a path that is valid Python in the session
        (``huber_euler.h``).  ``_gui_scan_options()`` supplies the map.
        """
        if not self._x_field or self._use_elapsed_time:
            return None
        return self._axis_fields.get(self._x_field)

    @staticmethod
    def _stat_position(stats, name):
        """x of a statistic, or None.  ``max``/``min`` are ``(x, y)`` pairs."""
        value = (stats or {}).get(name)
        if value is None:
            return None
        return value[0] if name in ("max", "min") else value

    def _update_peak(self):
        """Recompute the peak row and markers, and set the buttons' state."""
        self._peak_stats = None

        # A mesh has two axes and no single peak; count() has no axis at all;
        # and the statistics are computed from ``_series``, which holds the
        # *primary* channels -- reporting them while the dichro stream is on
        # screen would describe a curve that is not being shown.
        if (
            self._grid
            or self._use_elapsed_time
            or not self._series
            or self._stream != PRIMARY
        ):
            self._peak_row.setVisible(False)
            self._draw_markers({})
            return
        self._peak_row.setVisible(True)

        field = self._peak_field()
        if field is None:
            self._show_peak("No curve selected.", {})
            self._draw_markers({})
            return

        series = self._series[field]
        stats = peak_statistics(self._x_data, self._values(series))
        self._peak_stats = stats

        positions = {
            name: self._stat_position(stats, name)
            for name, _colour in MARKER_STYLES
        }
        # The statistic's name carries its marker's colour, so the peak row is
        # the key to the plot.  Rich text collapses runs of spaces, hence the
        # explicit gaps.
        parts = [
            f'<span style="color:{colour}; font-weight:bold">{name}</span> '
            + (_format(positions[name]) if positions[name] is not None else "—")
            for name, colour in MARKER_STYLES
        ]
        parts.append(
            f"fwhm {_format(stats['fwhm'])}"
            if stats["fwhm"] is not None
            else "fwhm —"
        )
        self._show_peak("&nbsp;&nbsp;&nbsp;".join(parts), positions)
        self._draw_markers(positions)

    def _show_peak(self, text, positions):
        """Fill in the peak row, disabling each button that cannot act."""
        self._peak_values.setText(text)
        axis = self._peak_axis()

        if self._scan_running:
            reason = "Wait for the scan to finish."
        elif not self._kernel_idle:
            reason = "The kernel is busy."
        elif axis is None:
            reason = (
                f"Cannot work out which device reports '{self._x_field}'."
                if self._x_field
                else "No scanned axis."
            )
        else:
            reason = None

        for name, _colour in MARKER_STYLES:
            button = self._peak_buttons[name]
            position = positions.get(name)
            button.setEnabled(reason is None and position is not None)
            # The value is *not* repeated on the button: four of them, each with
            # a ten-significant-digit position, overran the row and clipped the
            # labels.  The peak row prints the number a couple of centimetres to
            # the left in this button's own colour, and the tooltip carries the
            # exact command, so nothing is lost by keeping the button short.
            if reason is not None:
                button.setToolTip(reason)
            elif position is None:
                button.setToolTip(f"This curve has no {name}.")
            else:
                button.setToolTip(
                    f"{MARKER_TOOLTIPS[name]}\nRE(mv({axis}, {_format(position)}))"
                )

    def _draw_markers(self, positions):
        """One dotted vertical line per statistic, or none if the box is off.

        Called from ``_update_peak`` only, which is not run per event, so the
        markers settle once the scan ends rather than jittering through it.
        """
        wanted = self._markers_box.isChecked()
        for name, colour in MARKER_STYLES:
            position = positions.get(name)
            line = self._marker_lines.get(name)
            if not wanted or position is None:
                if line is not None:
                    self._remove_marker(name)
                continue
            if line is None:
                # "_nolegend_": the legend is the curves' -- a marker is named
                # by the colour of its statistic in the peak row instead.
                self._marker_lines[name] = self._axes.axvline(
                    position,
                    color=colour,
                    linestyle=":",
                    linewidth=1.5,
                    label="_nolegend_",
                )
            else:
                line.set_xdata([position, position])
        self._canvas.draw_idle()

    def _remove_marker(self, name):
        line = self._marker_lines.pop(name, None)
        if line is None:
            return
        try:
            line.remove()
        except (ValueError, NotImplementedError):
            # Already gone with an axes.clear(); nothing left to do.
            pass

    def _go_to(self, statistic):
        """Move the scanned axis onto *statistic* of the displayed curve."""
        axis = self._peak_axis()
        value = self._stat_position(self._peak_stats, statistic)
        if axis is None or value is None:
            return
        # An explicit literal rather than RE(cen()): it is exactly the number
        # on the button, it needs no catalog round-trip, and it reads back in
        # the session history as an ordinary move.
        self.run_in_console(f"RE(mv({axis}, {_format(value)}))")

    # -- kernel exchange ----------------------------------------------------

    def refresh(self):
        """Re-read the axis list, which is how a hinted field becomes a path."""
        self.request({OPTIONS_KEY: OPTIONS_EXPR})

    def on_kernel_values(self, values):
        """Pick up the hinted-field to dotted-path map."""
        options = values.get(OPTIONS_KEY)
        if not isinstance(options, dict):
            return
        fields = options.get("axis_fields")
        if isinstance(fields, dict):
            self._axis_fields = fields
            self._update_peak()

    # -- misc -------------------------------------------------------------

    def _draw_placeholder(self):
        self._axes.set_xticks([])
        self._axes.set_yticks([])
        self._axes.text(
            0.5,
            0.5,
            "The next scan will be plotted here.",
            ha="center",
            va="center",
            transform=self._axes.transAxes,
            alpha=0.5,
        )
        self._canvas.draw_idle()

    def on_kernel_state(self, state):
        """Note when the kernel is gone, so a stalled plot is explicable."""
        self._kernel_idle = state == "idle"
        if state == "idle" and not self._axis_fields:
            self.refresh()
        if state == "dead":
            self._status.setText("Kernel is not running.")
        self._update_peak()
