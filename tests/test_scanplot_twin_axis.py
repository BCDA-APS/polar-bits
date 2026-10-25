"""The live plot giving the second of two curves its own y scale.

Two detectors in one scan are routinely orders of magnitude apart, so with
exactly two curves ticked the second is drawn against a right-hand axis.
Three or more, or the derivative option, and everything shares the left one.

``qtpy`` and ``matplotlib`` are in the ``gui`` extra only, so these skip where
the GUI is not installed.
"""

from __future__ import annotations

import pytest

DESC_UID = "desc-primary"
FIELDS = ("det_a", "det_b", "det_c")


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    pytest.importorskip("matplotlib", reason="matplotlib is in the gui extra")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(qt_app):
    """A plot tab part-way into a 1-D scan over three detector fields."""
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document(
        "start",
        {
            "uid": "start-1",
            "scan_id": 1,
            "plan_name": "scan",
            "hints": {"dimensions": [[["motor"], "primary"]]},
            "motors": ["motor"],
        },
    )
    tab.on_document(
        "descriptor",
        {
            "uid": DESC_UID,
            "name": "primary",
            "data_keys": {
                "motor": {"dtype": "number", "shape": []},
                **{f: {"dtype": "number", "shape": []} for f in FIELDS},
            },
            "hints": {"d": {"fields": list(FIELDS)}},
        },
    )
    for i in range(4):
        tab.on_document(
            "event",
            {
                "descriptor": DESC_UID,
                "seq_num": i + 1,
                "time": float(i),
                "data": {
                    "motor": float(i),
                    "det_a": float(i),
                    # Four orders of magnitude apart: the case the split is
                    # for.
                    "det_b": float(i) * 1e4,
                    "det_c": float(i) * 2,
                },
            },
        )
    return tab


def _show(tab, *fields):
    """Tick exactly *fields* and nothing else."""
    for name, series in tab._series.items():
        series["box"].setChecked(name in fields)


def _axes_of(tab, field):
    """The axes *field*'s curve is drawn on, or None if it has no curve."""
    line = tab._series[field]["line"]
    return None if line is None else line.axes


def test_two_curves_split_across_both_axes(tab):
    """The second ticked curve lands on a right-hand twin of the first's."""
    _show(tab, "det_a", "det_b")

    assert tab._right_field == "det_b"
    assert tab._right_axes is not None
    assert _axes_of(tab, "det_a") is tab._axes
    assert _axes_of(tab, "det_b") is tab._right_axes
    # Each axis names its own curve, so there is nothing for a legend to say.
    assert tab._axes.get_ylabel() == "det_a"
    assert tab._right_axes.get_ylabel() == "det_b"
    assert tab._axes.get_legend() is None


def test_each_axis_scales_to_its_own_curve(tab):
    """The point of the split: neither curve is flattened by the other."""
    _show(tab, "det_a", "det_b")

    assert tab._axes.get_ylim()[1] < 100  # det_a tops out at 3
    assert tab._right_axes.get_ylim()[1] > 1e4 * 0.9


def test_third_curve_collapses_back_to_one_scale(tab):
    """Three curves have no obvious pairing, so they share the left axis."""
    _show(tab, *FIELDS)

    assert tab._right_field is None
    assert tab._right_axes is None
    assert all(_axes_of(tab, f) is tab._axes for f in FIELDS)
    assert tab._axes.get_legend() is not None


def test_untick_back_to_two_splits_again(tab):
    """The split follows the tick boxes both ways."""
    _show(tab, *FIELDS)
    _show(tab, "det_a", "det_c")

    assert tab._right_field == "det_c"
    assert _axes_of(tab, "det_c") is tab._right_axes


def test_colour_survives_the_move_between_axes(tab):
    """A twin starts matplotlib's colour cycle afresh; the curves must not."""
    _show(tab, "det_a", "det_b")
    colours = {
        f: tab._series[f]["line"].get_color() for f in ("det_a", "det_b")
    }

    assert colours["det_a"] != colours["det_b"]

    _show(tab, *FIELDS)
    _show(tab, "det_a", "det_b")

    for field, colour in colours.items():
        assert tab._series[field]["line"].get_color() == colour


def test_derivative_keeps_the_right_axis_for_its_references(tab):
    """With the derivative on, the right-hand side is the reference curves'."""
    _show(tab, "det_a", "det_b")
    tab._set_derivative(True)

    assert tab._right_field is None
    assert tab._right_axes is None
    assert _axes_of(tab, "det_b") is tab._axes
    # The reference curves took the right-hand side instead.
    assert tab._ref_axes is not None

    tab._set_derivative(False)
    assert tab._right_field == "det_b"


def test_later_points_keep_the_split(tab):
    """A point arriving after the split does not undo it."""
    _show(tab, "det_a", "det_b")
    tab.on_document(
        "event",
        {
            "descriptor": DESC_UID,
            "seq_num": 5,
            "time": 4.0,
            "data": {
                "motor": 4.0,
                "det_a": 4.0,
                "det_b": 4e4,
                "det_c": 8.0,
            },
        },
    )

    assert tab._right_field == "det_b"
    assert _axes_of(tab, "det_b") is tab._right_axes
    assert len(tab._series["det_b"]["line"].get_xdata()) == 5
