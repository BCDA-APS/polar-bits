"""The "÷ by" channel survives a change of scan.

Picking a channel to divide by is a choice the user makes once per session,
not once per run, so the scan viewer remembers it.  A run that has the channel
gets it back; a run without it starts on "none (raw)", and the choice returns
on the next run that has the channel.  Choosing "none (raw)" is itself a
choice, and is remembered the same way.

``qtpy`` and ``matplotlib`` are in the ``gui`` extra only, so these skip where
the GUI is not installed.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    pytest.importorskip("matplotlib", reason="matplotlib is in the gui extra")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _start_doc(scan_id, gridded=False):
    doc = {
        "uid": f"start-{scan_id}",
        "scan_id": scan_id,
        "plan_name": "rel_grid_scan" if gridded else "scan",
        "hints": {
            "dimensions": [[["slowm"], "primary"], [["fastm"], "primary"]]
            if gridded
            else [[["slowm"], "primary"]]
        },
        "motors": ["slowm", "fastm"] if gridded else ["slowm"],
    }
    if gridded:
        doc["shape"] = [2, 2]
        doc["extents"] = [[0.0, 1.0], [0.0, 1.0]]
        doc["hints"]["gridding"] = "rectilinear"
    return doc


def _descriptor(uid, fields, gridded=False):
    data_keys = {"slowm": {"dtype": "number", "shape": []}}
    if gridded:
        data_keys["fastm"] = {"dtype": "number", "shape": []}
    for field in fields:
        data_keys[field] = {"dtype": "number", "shape": []}
    return {
        "uid": uid,
        "name": "primary",
        "data_keys": data_keys,
        "hints": {"det_obj": {"fields": list(fields)}},
    }


def _run(tab, scan_id, fields, gridded=False):
    """Start a run and hand the tab its primary descriptor."""
    tab.on_document("start", _start_doc(scan_id, gridded=gridded))
    tab.on_document(
        "descriptor", _descriptor(f"desc-{scan_id}", fields, gridded=gridded)
    )


def _radio_checked(tab, field):
    return tab._series[field]["radio"].isChecked()


@pytest.fixture
def tab(qt_app):
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    return ScanPlotTab()


def test_monitor_is_kept_when_the_next_scan_has_the_channel(tab):
    """The Norm choice carries over to the next scan."""
    _run(tab, 1, ["I0", "det"])
    tab._series["I0"]["radio"].setChecked(True)

    _run(tab, 2, ["I0", "det"])

    assert tab._monitor == "I0"
    assert _radio_checked(tab, "I0")
    assert tab._series["I0"]["box"].isEnabled() is False


def test_monitor_waits_out_a_scan_without_the_channel(tab):
    """A scan lacking the channel is plotted raw, and the choice comes back."""
    _run(tab, 1, ["I0", "det"])
    tab._series["I0"]["radio"].setChecked(True)

    _run(tab, 2, ["det"])
    assert tab._monitor is None
    assert tab._no_monitor.isChecked()

    _run(tab, 3, ["I0", "det"])
    assert tab._monitor == "I0"
    assert _radio_checked(tab, "I0")


def test_choosing_none_raw_is_remembered_too(tab):
    """Switching normalisation off is a choice the next scan respects."""
    _run(tab, 1, ["I0", "det"])
    tab._series["I0"]["radio"].setChecked(True)
    tab._no_monitor.setChecked(True)

    _run(tab, 2, ["I0", "det"])

    assert tab._monitor is None
    assert tab._no_monitor.isChecked()


def test_a_fresh_session_starts_on_none_raw(tab):
    """Nothing picked yet, so nothing to carry over."""
    _run(tab, 1, ["I0", "det"])

    assert tab._monitor is None
    assert tab._no_monitor.isChecked()


def test_a_mesh_never_plots_the_monitor_as_its_image(tab):
    """The image cannot show the channel divided by itself."""
    _run(tab, 1, ["I0", "det"], gridded=True)
    tab._series["I0"]["radio"].setChecked(True)

    _run(tab, 2, ["I0", "det"], gridded=True)

    assert tab._monitor == "I0"
    assert tab._grid_field == "det"
