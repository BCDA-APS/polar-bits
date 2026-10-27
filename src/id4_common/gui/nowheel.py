"""An application-wide guard against values changed by the mouse wheel.

Qt lets the wheel step a spin box, a combo box, a slider or a tab bar that
merely happens to sit under the pointer -- no click, no focus, no warning.
In this GUI many of those widgets write real instrument state (a solver mode,
a motor target, a detector count time), and the controls live in tall scroll
areas that the operator scrolls with that same wheel.  A scroll aimed at the
column was quietly re-tuning whatever it passed over.

So the wheel never changes a value here.  One event filter on the
``QApplication`` catches every wheel event on its way to a value widget and
hands it to the enclosing scroll area instead: the column still scrolls, the
value does not move.  Keyboard and clicks are untouched, and an *open* combo
popup is a separate view widget, so scrolling inside it still works.

The redirect is explicit because Qt will not do it for us.  Qt propagates an
*ignored* wheel event up the parent chain, but only for a spontaneous one --
a re-sent event is delivered to its receiver and stops there -- so the guard
looks the ancestor up itself and sends to that scroll area's viewport, the
widget that actually does the scrolling.

Plot canvases are deliberately not covered: pyqtgraph does its wheel zoom
inside a ``QGraphicsView``, which is none of the guarded types.

Install it once, right after the ``QApplication`` exists and before any
widget is built::

    app = QApplication.instance() or QApplication(sys.argv[:1])
    install_wheel_guard(app)
"""

import logging

from qtpy.QtCore import QEvent
from qtpy.QtCore import QObject
from qtpy.QtWidgets import QAbstractScrollArea
from qtpy.QtWidgets import QAbstractSlider
from qtpy.QtWidgets import QAbstractSpinBox
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QComboBox
from qtpy.QtWidgets import QScrollBar
from qtpy.QtWidgets import QTabBar

logger = logging.getLogger(__name__)

#: Widget types whose value the wheel must not change.  ``QAbstractSpinBox``
#: covers every spin box including the date/time ones, ``QAbstractSlider``
#: every slider and dial -- scroll bars are pulled back out below, since
#: scrolling is the whole point of one.
GUARDED = (QAbstractSpinBox, QComboBox, QAbstractSlider, QTabBar)

#: The attribute the guard parks itself under, so a second install is a
#: no-op rather than a second filter on every event.
_GUARD_ATTR = "_id4_wheel_guard"


def _enclosing_viewport(widget):
    """Return the viewport of the nearest enclosing scroll area, or None."""
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            return parent.viewport()
        parent = parent.parentWidget()
    return None


class WheelGuard(QObject):
    """Event filter that keeps the wheel from changing a widget's value."""

    def eventFilter(self, obj, event):
        """Redirect a wheel event on a guarded widget to its scroll area."""
        if event.type() != QEvent.Wheel:
            return False
        if isinstance(obj, QScrollBar) or not isinstance(obj, GUARDED):
            return False
        viewport = _enclosing_viewport(obj)
        if viewport is not None:
            event.ignore()
            QApplication.sendEvent(viewport, event)
        return True


def install_wheel_guard(app=None):
    """Install the wheel guard on ``app`` (the running one by default).

    Returns the :class:`WheelGuard`, which is kept alive on the application
    object -- a filter that goes out of scope stops filtering.  Calling this
    twice on the same application returns the guard already installed.
    """
    app = app or QApplication.instance()
    if app is None:  # pragma: no cover - no application to guard
        logger.debug("No QApplication; wheel guard not installed.")
        return None
    guard = getattr(app, _GUARD_ATTR, None)
    if guard is None:
        guard = WheelGuard(app)
        app.installEventFilter(guard)
        setattr(app, _GUARD_ATTR, guard)
    return guard
