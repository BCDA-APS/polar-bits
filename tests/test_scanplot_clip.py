"""Clipping the colour scale of a 2D map, so a spike stops flattening it.

A ``grid_scan``/``rel_grid_scan`` mesh is drawn with the full range of its
cells, so one wild cell -- the corner where the beam ran off the sample, a
detector glitch -- stretches the scale over a range nothing else occupies and
the rest of the map goes one flat shade.  The "Clip map scale" button leaves
the most extreme cells at each end out of the scale instead.

The pure percentile helpers are tested on their own, then the tab is driven
through both of its map-drawing paths: the primary mesh and the dichro one.

``qtpy`` and ``matplotlib`` are in the ``gui`` extra only, so these skip where
the GUI is not installed.
"""

from __future__ import annotations

import pytest

PRIMARY_UID = "desc-primary"
DICHRO_UID = "desc-dichro"
SHAPE = (3, 3)

#: Nine cells, so a percentile has to bite hard to cut anything at all; 20%
#: takes roughly the extreme cell and a half from each end.
CLIP_PERCENT = 20.0


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    pytest.importorskip("matplotlib", reason="matplotlib is in the gui extra")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _start_doc(gridded=True):
    doc = {
        "uid": "start-1",
        "scan_id": 1,
        "plan_name": "rel_grid_scan" if gridded else "scan",
        "hints": {
            "dimensions": [[["slowm"], "primary"], [["fastm"], "primary"]]
        },
        "motors": ["slowm", "fastm"],
    }
    if gridded:
        doc["shape"] = list(SHAPE)
        doc["extents"] = [[0.0, 2.0], [0.0, 2.0]]
        doc["hints"]["gridding"] = "rectilinear"
    return doc


def _primary_descriptor():
    return {
        "uid": PRIMARY_UID,
        "name": "primary",
        "data_keys": {
            "slowm": {"dtype": "number", "shape": []},
            "fastm": {"dtype": "number", "shape": []},
            "det": {"dtype": "number", "shape": []},
        },
        "hints": {"det_obj": {"fields": ["det"]}},
    }


def _dichro_descriptor():
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM

    return {
        "uid": DICHRO_UID,
        "name": DICHRO_STREAM,
        "data_keys": {
            "dichro_positioner1": {"dtype": "number", "shape": []},
            "dichro_positioner2": {"dtype": "number", "shape": []},
            "dichro_xas": {"dtype": "number", "shape": []},
            "dichro_xmcd": {"dtype": "number", "shape": []},
        },
    }


def _fill_mesh(tab, values, dichro=False):
    """Feed one event per cell of the 3x3 mesh, in row-major order."""
    seq = 0
    for row in range(SHAPE[0]):
        for col in range(SHAPE[1]):
            value = values[seq]
            seq += 1
            if dichro:
                doc = {
                    "descriptor": DICHRO_UID,
                    "seq_num": seq,
                    "time": float(seq),
                    "data": {
                        "dichro_positioner1": float(row),
                        "dichro_positioner2": float(col),
                        "dichro_xas": 100.0 + seq,
                        "dichro_xmcd": value,
                    },
                }
            else:
                doc = {
                    "descriptor": PRIMARY_UID,
                    "seq_num": seq,
                    "time": float(seq),
                    "data": {
                        "slowm": float(row),
                        "fastm": float(col),
                        "det": value,
                    },
                }
            tab.on_document("event", doc)


@pytest.fixture
def grid_tab(qt_app):
    """A plot tab part-way into a plain ``rel_grid_scan``; no events yet."""
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc())
    tab.on_document("descriptor", _primary_descriptor())
    return tab


@pytest.fixture
def dichro_grid_tab(qt_app):
    """The same run, but also writing a ``dichro_monitor`` stream.

    The dichro descriptor puts the tab on that stream by itself; nothing here
    switches it.
    """
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc())
    tab.on_document("descriptor", _primary_descriptor())
    tab.on_document("descriptor", _dichro_descriptor())
    return tab


# -- the percentile helpers, on their own ---------------------------------


def test_clipped_limits_cuts_both_ends_of_a_spiky_map(qt_app):
    """The limits land inside the data, and the arrows say both ends went."""
    import numpy
    from id4_common.gui.tabs.scanplot import clipped_limits

    z = numpy.arange(100, dtype=float).reshape(10, 10)
    z[0, 0] = -1e6
    z[9, 9] = 1e6

    low, high, extend = clipped_limits(z, 5.0)

    assert low > float(z.min())
    assert high < float(z.max())
    assert extend == "both"


def test_clipped_limits_leaves_a_flat_map_alone(qt_app):
    """Both percentiles coincide, and there is no scale left to clip."""
    import numpy
    from id4_common.gui.tabs.scanplot import clipped_limits

    flat = numpy.full((5, 5), 3.0)

    assert clipped_limits(flat, CLIP_PERCENT) == (None, None, "neither")


def test_clipped_limits_needs_three_finite_cells(qt_app):
    """A mesh two points into a scan has nothing to take a percentile of."""
    import numpy
    from id4_common.gui.tabs.scanplot import clipped_limits

    barely = numpy.full((3, 3), numpy.nan)
    barely[0, 0] = 1.0
    barely[0, 1] = 5.0

    assert clipped_limits(barely, CLIP_PERCENT) == (None, None, "neither")


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [
        (2.0, 8.0, "both"),
        (2.0, None, "min"),
        (None, 8.0, "max"),
        (None, None, "neither"),
        (0.0, 9.0, "neither"),
    ],
)
def test_scale_extend_names_the_ends_that_were_cut(qt_app, low, high, expected):
    """The arrows are asked of the data, not carried from the clip."""
    import numpy
    from id4_common.gui.tabs.scanplot import scale_extend

    z = numpy.arange(10, dtype=float)

    assert scale_extend(z, low, high) == expected


def test_centered_limits_puts_zero_in_the_middle_and_only_widens(qt_app):
    """Widening costs the shorter end contrast and buys a readable sign."""
    import numpy
    from id4_common.gui.tabs.scanplot import centered_limits

    z = numpy.array([-0.2, 0.4, 0.9])

    low, high = centered_limits(z, -0.1, 0.8)

    assert low == -high
    assert low <= -0.1
    assert high >= 0.8


# -- the controls on the tab ----------------------------------------------


def test_map_row_follows_whether_the_run_is_a_mesh(qt_app):
    """Nothing to clip on a line scan, so the row stays out of the way."""
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    assert tab._map_row.isVisibleTo(tab) is False

    tab.on_document("start", _start_doc(gridded=True))
    assert tab._map_row.isVisibleTo(tab) is True

    tab.on_document("start", _start_doc(gridded=False))
    assert tab._map_row.isVisibleTo(tab) is False


def test_percentage_box_is_live_only_while_clipping(grid_tab):
    """No amount to set when nothing is being clipped by it."""
    tab = grid_tab
    assert tab._clip_spin.isEnabled() is False

    tab._clip_btn.setChecked(True)
    assert tab._clip_spin.isEnabled() is True

    tab._clip_btn.setChecked(False)
    assert tab._clip_spin.isEnabled() is False


def test_unclipped_primary_mesh_keeps_the_full_range(grid_tab):
    """The button off has to leave the mesh exactly as it was drawn before."""
    tab = grid_tab
    _fill_mesh(tab, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 1000.0])

    assert tab._image.get_clim() == (1.0, 1000.0)
    assert tab._colorbar.extend == "neither"


def test_clipping_pulls_the_primary_mesh_scale_off_the_spike(grid_tab):
    """One cell at 1000 against eight below 10 is what wrecks a scale."""
    tab = grid_tab
    _fill_mesh(tab, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 1000.0])

    tab._clip_spin.setValue(CLIP_PERCENT)
    tab._clip_btn.setChecked(True)

    low, high = tab._image.get_clim()
    assert low > 1.0
    # The spike is out of the scale entirely; the eight real cells get it.
    assert high < 10.0
    assert tab._colorbar.extend == "both"
    assert "colour clipped at 20%" in tab._status.text()


def test_unclipping_puts_the_full_range_back(grid_tab):
    """Toggling off restores both the limits and the bar's arrows."""
    tab = grid_tab
    _fill_mesh(tab, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 1000.0])

    tab._clip_spin.setValue(CLIP_PERCENT)
    tab._clip_btn.setChecked(True)
    tab._clip_btn.setChecked(False)

    assert tab._image.get_clim() == (1.0, 1000.0)
    assert tab._colorbar.extend == "neither"
    assert "clipped" not in tab._status.text()


def test_clipped_xmcd_map_stays_symmetric_about_zero(dichro_grid_tab):
    """Sign is the signal, so white has to stay on zero however hard we clip.

    Clipping a diverging map narrows it and then mirrors it, which is a
    different thing from clipping it to its own two percentiles: those are
    lopsided, and seismic read against a lopsided range stops meaning +/-.
    """
    from id4_common.gui.tabs.scanplot import DICHRO_XMCD

    tab = dichro_grid_tab
    # Lopsided, with one cell two orders of magnitude out.
    _fill_mesh(
        tab,
        [0.9, -0.2, 0.4, -0.1, 0.7, 0.2, -0.05, 0.3, 50.0],
        dichro=True,
    )
    assert tab._dichro_field.currentText() == DICHRO_XMCD
    assert tab._image.get_clim() == (-50.0, 50.0)

    tab._clip_spin.setValue(CLIP_PERCENT)
    tab._clip_btn.setChecked(True)

    low, high = tab._image.get_clim()
    assert low == -high
    # The spike no longer sets the scale.
    assert high < 1.0
    assert tab._image.get_cmap().name == "seismic"


def test_clipped_xas_map_uses_its_own_two_percentiles(dichro_grid_tab):
    """XAS is a count rate with no midpoint, so it is not mirrored."""
    from id4_common.gui.tabs.scanplot import DICHRO_XAS

    tab = dichro_grid_tab
    _fill_mesh(tab, [0.1] * 9, dichro=True)
    tab._dichro_field.setCurrentText(DICHRO_XAS)
    # ``_fill_mesh`` writes XAS as 100 + seq, so 101..109 over nine cells.
    assert tab._image.get_clim() == (101.0, 109.0)

    tab._clip_spin.setValue(CLIP_PERCENT)
    tab._clip_btn.setChecked(True)

    low, high = tab._image.get_clim()
    assert 101.0 < low < high < 109.0
    assert low != -high


def test_a_dichro_run_opens_on_the_dichro_stream(qt_app):
    """The reduced XAS/XMCD is what the scan was run for, so show it."""
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM
    from id4_common.gui.tabs.scanplot import PRIMARY
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc())
    tab.on_document("descriptor", _primary_descriptor())
    assert tab._stream == PRIMARY
    assert tab._stream_row.isVisibleTo(tab) is False

    tab.on_document("descriptor", _dichro_descriptor())

    assert tab._stream == DICHRO_STREAM
    assert tab._stream_combo.currentText() == DICHRO_STREAM
    assert tab._stream_row.isVisibleTo(tab) is True


def test_a_plain_run_stays_on_primary(qt_app):
    """Nothing to switch to, and no picker to offer."""
    from id4_common.gui.tabs.scanplot import PRIMARY
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc())
    tab.on_document("descriptor", _primary_descriptor())
    _fill_mesh(tab, [float(n) for n in range(9)])

    assert tab._stream == PRIMARY
    assert tab._stream_row.isVisibleTo(tab) is False


def test_the_next_run_starts_over_on_primary(dichro_grid_tab):
    """A plain scan after a dichro one must not stay on the empty stream."""
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM
    from id4_common.gui.tabs.scanplot import PRIMARY

    tab = dichro_grid_tab
    assert tab._stream == DICHRO_STREAM

    tab.on_document("start", _start_doc(gridded=False))
    tab.on_document("descriptor", _primary_descriptor())

    assert tab._stream == PRIMARY
    assert tab._stream_row.isVisibleTo(tab) is False


def test_a_later_pick_of_primary_stands(dichro_grid_tab):
    """Switching back is the user's call, and nothing switches them away.

    The auto-switch is driven off the descriptor, which arrives once, so the
    primary events that keep coming all run must not drag the view back.
    """
    from id4_common.gui.tabs.scanplot import PRIMARY

    tab = dichro_grid_tab
    tab._stream_combo.setCurrentText(PRIMARY)

    _fill_mesh(tab, [float(n) for n in range(9)])

    assert tab._stream == PRIMARY


def test_dichro_descriptor_before_the_primary_one(qt_app):
    """Descriptor order is not guaranteed, and the dichro view has to hold.

    Switching on the first descriptor means the primary one lands *after* the
    canvas is already dichro; every primary paint path has to stay out of it.
    """
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc())
    tab.on_document("descriptor", _dichro_descriptor())
    assert tab._stream == DICHRO_STREAM

    tab.on_document("descriptor", _primary_descriptor())
    _fill_mesh(tab, [0.1 * n for n in range(1, 10)], dichro=True)

    assert tab._stream == DICHRO_STREAM
    assert tab._colorbar.ax.get_ylabel() == "dichro_xmcd"


def test_clip_note_stays_off_the_1d_dichro_status(qt_app):
    """A dichro line scan draws curves, and curves have no colour scale."""
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document("start", _start_doc(gridded=False))
    tab.on_document("descriptor", _primary_descriptor())
    tab.on_document("descriptor", _dichro_descriptor())
    tab._clip_btn.setChecked(True)

    for seq in range(1, 4):
        tab.on_document(
            "event",
            {
                "descriptor": DICHRO_UID,
                "seq_num": seq,
                "time": float(seq),
                "data": {
                    "dichro_positioner1": float(seq),
                    "dichro_positioner2": float("nan"),
                    "dichro_xas": 100.0 + seq,
                    "dichro_xmcd": 0.1 * seq,
                },
            },
        )

    assert tab._image is None
    assert "clipped" not in tab._status.text()
