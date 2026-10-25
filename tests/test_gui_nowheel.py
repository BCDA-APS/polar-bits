"""The mouse wheel must never change a value anywhere in the GUI.

Qt steps a spin box, combo box, slider or tab bar that merely sits under the
pointer.  The controls in this GUI write instrument state and live in tall
scroll areas the operator scrolls with that same wheel, so a scroll aimed at
the column was quietly re-tuning whatever it passed over.
:func:`id4_common.gui.nowheel.install_wheel_guard` puts one event filter on
the application to stop it -- without stopping the scroll itself.

``qtpy`` is in the ``gui`` extra only, so these skip where it is not
installed.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def guarded_app(monkeypatch):
    """A headless QApplication with the wheel guard installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    from qtpy.QtWidgets import QApplication

    from id4_common.gui.nowheel import install_wheel_guard

    app = QApplication.instance() or QApplication([])
    install_wheel_guard(app)
    return app


@pytest.fixture
def scrolled(guarded_app):
    """A tall column of value widgets inside a short scroll area.

    The shape the bug lived in: more controls than fit, so the operator
    scrolls, and the pointer passes over every one of them on the way.
    """
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QComboBox
    from qtpy.QtWidgets import QDoubleSpinBox
    from qtpy.QtWidgets import QScrollArea
    from qtpy.QtWidgets import QSlider
    from qtpy.QtWidgets import QSpinBox
    from qtpy.QtWidgets import QVBoxLayout
    from qtpy.QtWidgets import QWidget

    column = QWidget()
    layout = QVBoxLayout(column)
    widgets = {}

    widgets["double"] = QDoubleSpinBox()
    widgets["double"].setRange(-10.0, 10.0)
    widgets["double"].setValue(1.5)
    widgets["int"] = QSpinBox()
    widgets["int"].setRange(0, 100)
    widgets["int"].setValue(7)
    widgets["combo"] = QComboBox()
    widgets["combo"].addItems(["first", "second", "third"])
    widgets["combo"].setCurrentIndex(1)
    widgets["slider"] = QSlider(Qt.Horizontal)
    widgets["slider"].setRange(0, 100)
    widgets["slider"].setValue(50)

    for widget in widgets.values():
        layout.addWidget(widget)
    # Enough filler to make the column taller than the viewport.
    for _ in range(40):
        layout.addWidget(QSpinBox())

    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(column)
    area.resize(300, 120)
    area.show()
    guarded_app.processEvents()
    return area, widgets, guarded_app


def _wheel_at(widget, notches=-1):
    """Send one wheel event to ``widget``; return it for accept checks."""
    from qtpy.QtCore import QPoint
    from qtpy.QtCore import QPointF
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QWheelEvent
    from qtpy.QtWidgets import QApplication

    centre = widget.rect().center()
    try:
        event = QWheelEvent(
            QPointF(centre),
            widget.mapToGlobal(centre),
            QPoint(0, 0),
            QPoint(0, 120 * notches),
            Qt.NoButton,
            Qt.NoModifier,
            Qt.NoScrollPhase,
            False,
        )
    except TypeError:  # pragma: no cover - binding without this signature
        pytest.skip("QWheelEvent signature differs in this Qt binding")
    QApplication.sendEvent(widget, event)
    return event


def test_the_wheel_changes_no_value(scrolled):
    """Spin boxes, combo boxes and sliders all hold still under the wheel."""
    _area, widgets, app = scrolled

    for widget in widgets.values():
        _wheel_at(widget)
        _wheel_at(widget, notches=+1)
    app.processEvents()

    assert widgets["double"].value() == pytest.approx(1.5)
    assert widgets["int"].value() == 7
    assert widgets["combo"].currentIndex() == 1
    assert widgets["combo"].currentText() == "second"
    assert widgets["slider"].value() == 50


def test_the_scroll_area_still_scrolls(scrolled):
    """The wheel is redirected, not swallowed -- the column must still move.

    Eating the event outright would trade one annoyance for a worse one: a
    column that refuses to scroll wherever a control sits under the mouse.
    """
    area, widgets, app = scrolled
    bar = area.verticalScrollBar()
    assert bar.maximum() > 0, "the column has to overflow for this to mean it"
    start = bar.value()

    for _ in range(3):
        _wheel_at(widgets["double"])
    app.processEvents()

    assert bar.value() > start


def test_a_scroll_bar_is_left_alone(scrolled):
    """A scroll bar is a slider whose whole job is to answer the wheel."""
    area, _widgets, app = scrolled
    bar = area.verticalScrollBar()
    start = bar.value()

    for _ in range(3):
        _wheel_at(bar)
    app.processEvents()

    assert bar.value() > start


def test_installing_twice_adds_one_filter(guarded_app):
    """A second install returns the guard already in place."""
    from id4_common.gui.nowheel import install_wheel_guard

    first = install_wheel_guard(guarded_app)
    second = install_wheel_guard(guarded_app)

    assert first is second
