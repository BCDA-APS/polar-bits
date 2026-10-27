"""The HKL tab's combo boxes must not change under a stray mouse or key.

Picking a mode, a sample or a diffractometer on that tab writes instrument
state into the live session, so Qt's defaults are too eager: a wheel over the
closed box steps the value, and so do the arrow keys while it holds focus.
Scrolling the controls column with the pointer over the Mode box used to
switch the solver mode.  The boxes are now ``_ClickOnlyComboBox`` wired to
``activated``, so only a click in the popup can change them.

``qtpy`` is in the ``gui`` extra only, so these skip where it is not
installed.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def hkl_tab(qt_app):
    """An HKL tab whose Mode box is filled with two modes to choose from."""
    from id4_common.gui.tabs.hkl import HklTab

    tab = HklTab()
    tab._mode_combo.addItems(["bissector", "psi_constant"])
    tab._mode_combo.setCurrentIndex(0)
    qt_app.processEvents()
    return tab, qt_app


def _combos(tab):
    return (tab._mode_combo, tab._sample_combo, tab._device_combo)


def test_the_boxes_take_focus_only_from_a_click(hkl_tab):
    """A box the wheel cannot focus is a box the wheel cannot step."""
    from qtpy.QtCore import Qt

    tab, _app = hkl_tab

    for combo in _combos(tab):
        assert combo.focusPolicy() == Qt.ClickFocus


def test_the_wheel_does_not_change_the_mode(hkl_tab):
    """What the bug looked like: scrolling the column switched the mode."""
    from qtpy.QtCore import QPoint
    from qtpy.QtCore import QPointF
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QWheelEvent
    from qtpy.QtWidgets import QApplication

    tab, _app = hkl_tab
    combo = tab._mode_combo
    centre = QPointF(combo.rect().center())

    try:
        event = QWheelEvent(
            centre,
            combo.mapToGlobal(combo.rect().center()),
            QPoint(0, 0),
            QPoint(0, -120),  # one notch away from the user
            Qt.NoButton,
            Qt.NoModifier,
            Qt.NoScrollPhase,
            False,
        )
    except TypeError:  # pragma: no cover - binding without this signature
        pytest.skip("QWheelEvent signature differs in this Qt binding")

    QApplication.sendEvent(combo, event)

    assert combo.currentIndex() == 0
    assert combo.currentText() == "bissector"
    # Left unaccepted, so the scroll area underneath gets it instead.
    assert not event.isAccepted()


def test_the_arrow_keys_do_not_change_a_closed_box(hkl_tab):
    """Stepping with the popup shut is the keyboard version of the same bug."""
    from qtpy.QtCore import QEvent
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QKeyEvent
    from qtpy.QtWidgets import QApplication

    tab, _app = hkl_tab
    combo = tab._mode_combo

    for key in (Qt.Key_Down, Qt.Key_End, Qt.Key_PageDown):
        event = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
        QApplication.sendEvent(combo, event)

    assert combo.currentIndex() == 0


def test_filling_the_box_does_not_write_the_mode_back(hkl_tab, monkeypatch):
    """``activated`` fires for a click, never for a programmatic index.

    The old wiring was ``currentIndexChanged``, which fires either way; a
    refresh that re-selected the current mode could push it at the kernel.
    """
    tab, app = hkl_tab
    sent = []
    monkeypatch.setattr(tab, "_act", lambda code: sent.append(code))
    tab._state = {"mode": "bissector"}

    tab._mode_combo.setCurrentIndex(1)
    app.processEvents()

    assert sent == []
    assert tab._mode_combo.currentText() == "psi_constant"
