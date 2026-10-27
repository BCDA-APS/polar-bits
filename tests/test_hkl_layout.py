"""The HKL tab's controls have to grow with the window, not stay frozen.

The tab is a horizontal splitter (controls in a scroller, 3D model beside it)
over a one-line status label.  A horizontal ``QSplitter`` is only *Preferred*
vertically, so with no stretch factor it stopped at its size hint and the
label below -- ``Preferred`` as well, and so equally entitled to the space --
absorbed every pixel the window gained.  Dragging the window taller grew the
blank gap around the status line while the controls kept their height and
their scroll bar kept its length.

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
    """An HKL tab shown inside a resizable holder, as a tab page is."""
    from id4_common.gui.tabs.hkl import HklTab
    from qtpy.QtWidgets import QVBoxLayout
    from qtpy.QtWidgets import QWidget

    tab = HklTab()
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(tab)
    holder.resize(1100, 500)
    holder.show()
    qt_app.processEvents()
    # Kept on the fixture so the holder outlives the test; a parentless
    # QWidget going out of scope takes the tab down with it.
    return tab, holder, qt_app


def _grow(hkl_tab, height):
    tab, holder, app = hkl_tab
    holder.resize(1100, height)
    app.processEvents()
    return tab


def test_the_controls_grow_with_the_window(hkl_tab):
    """The splitter takes the new height, well past its own size hint."""
    from qtpy.QtWidgets import QSplitter

    tab, _holder, _app = hkl_tab
    split = tab.findChild(QSplitter)

    _grow(hkl_tab, 700)
    short = split.height()
    _grow(hkl_tab, 1200)
    tall = split.height()

    # 500 px more window; the splitter is the only thing that should take it.
    assert tall - short > 400
    assert tall > split.sizeHint().height()


def test_the_scroll_bar_lengthens_as_the_tab_grows(hkl_tab):
    """What the bug looked like: a scroll bar that never changed length.

    The page step *is* the slider's length -- how much of the content the
    viewport shows -- so a viewport that grows has to lengthen it.
    """
    from qtpy.QtWidgets import QScrollArea

    tab, _holder, _app = hkl_tab
    area = tab.findChild(QScrollArea)

    _grow(hkl_tab, 700)
    short = area.verticalScrollBar().pageStep()
    _grow(hkl_tab, 1200)
    tall = area.verticalScrollBar().pageStep()

    assert tall - short > 400


def test_the_status_label_keeps_its_own_height(hkl_tab):
    """It is one line of text, and it is where the slack used to go."""
    tab, _holder, _app = hkl_tab

    _grow(hkl_tab, 1200)

    # Room for a wrapped second line, nowhere near the hundreds of pixels it
    # ballooned to.
    assert tab._status.height() < 3 * tab._status.sizeHint().height()
