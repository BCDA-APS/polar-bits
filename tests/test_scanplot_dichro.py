"""The live plot's handling of a dichro run, which writes two streams at once.

A dichro scan emits ``primary`` and ``dichro_monitor`` interleaved, and the
plot tab shows one of them at a time.  The bug these tests pin down: every
drawing path for the primary stream kept firing while the dichro view was up,
so on a grid scan the canvas flipped between the two maps point by point --
primary event, mesh; dichro event, XMCD map; and round again.

``qtpy`` and ``matplotlib`` are in the ``gui`` extra only, so these skip where
the GUI is not installed.
"""

from __future__ import annotations

import pytest

PRIMARY_UID = "desc-primary"
DICHRO_UID = "desc-dichro"
SHAPE = (3, 3)


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    pytest.importorskip("matplotlib", reason="matplotlib is in the gui extra")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def dichro_grid_tab(qt_app):
    """A plot tab part-way into a dichro ``rel_grid_scan``, start + descriptors.

    No events yet: each test feeds the points it needs.
    """
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM
    from id4_common.gui.tabs.scanplot import ScanPlotTab

    tab = ScanPlotTab()
    tab.on_document(
        "start",
        {
            "uid": "start-1",
            "scan_id": 1,
            "plan_name": "rel_grid_scan",
            "shape": list(SHAPE),
            "extents": [[0.0, 2.0], [0.0, 2.0]],
            "hints": {
                "gridding": "rectilinear",
                "dimensions": [
                    [["slowm"], "primary"],
                    [["fastm"], "primary"],
                ],
            },
            "motors": ["slowm", "fastm"],
        },
    )
    tab.on_document(
        "descriptor",
        {
            "uid": PRIMARY_UID,
            "name": "primary",
            "data_keys": {
                "slowm": {"dtype": "number", "shape": []},
                "fastm": {"dtype": "number", "shape": []},
                "det": {"dtype": "number", "shape": []},
            },
            "hints": {"det_obj": {"fields": ["det"]}},
        },
    )
    tab.on_document(
        "descriptor",
        {
            "uid": DICHRO_UID,
            "name": DICHRO_STREAM,
            "data_keys": {
                "dichro_positioner1": {"dtype": "number", "shape": []},
                "dichro_positioner2": {"dtype": "number", "shape": []},
                "dichro_xas": {"dtype": "number", "shape": []},
                "dichro_xmcd": {"dtype": "number", "shape": []},
            },
        },
    )
    return tab


def _dichro_event(seq, row, col, xmcd):
    return {
        "descriptor": DICHRO_UID,
        "seq_num": seq,
        "time": float(seq),
        "data": {
            "dichro_positioner1": float(row),
            "dichro_positioner2": float(col),
            "dichro_xas": 100.0 + seq,
            "dichro_xmcd": xmcd,
        },
    }


def _primary_event(seq, row, col):
    return {
        "descriptor": PRIMARY_UID,
        "seq_num": seq,
        "time": float(seq),
        "data": {"slowm": float(row), "fastm": float(col), "det": 100.0 + seq},
    }


def _mapped_channel(tab):
    """The channel the colour bar says is on the canvas."""
    return tab._colorbar.ax.get_ylabel() if tab._colorbar else None


def test_primary_events_leave_the_dichro_map_alone(dichro_grid_tab):
    """The canvas must not flip stream as the primary points come in.

    Each polarization pair writes one dichro point and several primary ones;
    before the fix every one of those primary events repainted the mesh over
    the XMCD map, and the next dichro point painted it back.
    """
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM

    tab = dichro_grid_tab
    tab._stream_combo.setCurrentText(DICHRO_STREAM)

    seq = 0
    for row in range(SHAPE[0]):
        for col in range(SHAPE[1]):
            seq += 1
            tab.on_document("event", _dichro_event(seq, row, col, 0.1 * seq))
            assert _mapped_channel(tab) == "dichro_xmcd"
            for _ in range(4):
                tab.on_document("event", _primary_event(seq, row, col))
            # The point of the whole exercise.
            assert _mapped_channel(tab) == "dichro_xmcd"


def test_mesh_keeps_accumulating_behind_the_dichro_view(dichro_grid_tab):
    """Not drawing is not the same as not recording.

    Switching back has to show the whole mesh, including the points that
    arrived while the dichro stream had the canvas.
    """
    import numpy

    from id4_common.gui.tabs.scanplot import DICHRO_STREAM

    tab = dichro_grid_tab
    tab._stream_combo.setCurrentText(DICHRO_STREAM)

    seq = 0
    for row in range(SHAPE[0]):
        for col in range(SHAPE[1]):
            seq += 1
            tab.on_document("event", _dichro_event(seq, row, col, 0.1 * seq))
            tab.on_document("event", _primary_event(seq, row, col))

    assert int(numpy.isfinite(tab._grid_data).sum()) == SHAPE[0] * SHAPE[1]

    tab._stream_combo.setCurrentText("primary")
    assert _mapped_channel(tab) == "det"
    assert len(tab._axes.images) == 1


def test_xmcd_map_is_seismic_and_centred_on_zero(dichro_grid_tab):
    """XMCD is signed, so its colour scale has to put white on zero.

    XAS is a count rate with no meaningful midpoint and keeps the default map
    and the data's own limits.
    """
    from id4_common.gui.tabs.scanplot import DICHRO_STREAM
    from id4_common.gui.tabs.scanplot import DICHRO_XAS
    from id4_common.gui.tabs.scanplot import DICHRO_XMCD

    tab = dichro_grid_tab
    tab._stream_combo.setCurrentText(DICHRO_STREAM)

    # Deliberately lopsided: -0.2 .. 0.9, so an uncentred scale would show.
    values = [0.9, -0.2, 0.4, -0.1, 0.7, 0.2, -0.05, 0.3, 0.6]
    seq = 0
    for row in range(SHAPE[0]):
        for col in range(SHAPE[1]):
            seq += 1
            tab.on_document(
                "event", _dichro_event(seq, row, col, values[seq - 1])
            )

    assert tab._dichro_field.currentText() == DICHRO_XMCD
    assert tab._image.get_cmap().name == "seismic"
    # Mirrored about zero on the larger excursion, not clamped to the data.
    assert tab._image.get_clim() == (-0.9, 0.9)

    tab._dichro_field.setCurrentText(DICHRO_XAS)
    assert tab._image.get_cmap().name != "seismic"
    # ``_dichro_event`` writes XAS as 100 + seq, so 101..109 over nine points.
    assert tab._image.get_clim() == (101.0, 109.0)
