"""The Session tab's console-log controls: directory, prefix, split size.

The log used to be one file at one free-form path.  It is now a series of
``<prefix>_<date>_<NNN>.log`` files: the operator picks the directory and the
prefix, the suffix is added, and a "Split at" spin box sets the size limit.
That spin box sits in a scrolled tab, so the wheel must not step it.

``qtpy`` is in the ``gui`` extra only, so these skip where it is not
installed.  Settings go to an INI file under ``tmp_path``, never to the
user's real QSettings.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def app(monkeypatch):
    """A headless QApplication with the wheel guard installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    from id4_common.gui.nowheel import install_wheel_guard
    from qtpy.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    install_wheel_guard(application)
    return application


@pytest.fixture
def settings(app, tmp_path, monkeypatch):
    """Point the Session tab's QSettings at a throwaway INI file."""
    from id4_common.gui.tabs import status
    from qtpy.QtCore import QSettings

    path = str(tmp_path / "settings.ini")

    def _settings(*_args):
        return QSettings(path, QSettings.IniFormat)

    monkeypatch.setattr(status, "QSettings", _settings)
    return _settings()


@pytest.fixture
def tab(settings, tmp_path):
    """A Session tab with a live transcript, inside a short scroll area."""
    from id4_common.gui.tabs.status import StatusTab
    from id4_common.gui.transcript import ConsoleTranscript
    from qtpy.QtWidgets import QScrollArea

    widget = StatusTab()
    widget.session_cwd = str(tmp_path / "cwd")
    widget.transcript = ConsoleTranscript()
    widget.sync_transcript()
    area = QScrollArea()
    area.setWidget(widget)
    area.resize(300, 120)
    area.show()
    yield widget
    widget.transcript.stop()
    area.close()


def test_an_old_single_file_path_seeds_directory_and_prefix(settings):
    """An upgrade keeps logging where the old version did."""
    from id4_common.gui.tabs.status import LOG_PATH_KEY
    from id4_common.gui.tabs.status import stored_log_target

    settings.setValue(LOG_PATH_KEY, "/data/run7/console.log")

    assert stored_log_target(settings) == ("/data/run7", "console", 10)


def test_nothing_stored_leaves_the_directory_to_the_caller(settings):
    """An empty directory means "follow the working directory"."""
    from id4_common.gui.tabs.status import stored_log_target

    assert stored_log_target(settings) == ("", "console", 10)


def test_the_wheel_does_not_change_the_split_size(tab, app):
    """Scrolling past the spin box scrolls the tab, not the value."""
    from qtpy.QtCore import QPoint
    from qtpy.QtCore import QPointF
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QWheelEvent
    from qtpy.QtWidgets import QApplication

    box = tab._log_max_mb
    before = box.value()
    centre = box.rect().center()
    for notches in (-1, 1):
        try:
            event = QWheelEvent(
                QPointF(centre),
                box.mapToGlobal(centre),
                QPoint(0, 0),
                QPoint(0, 120 * notches),
                Qt.NoButton,
                Qt.NoModifier,
                Qt.NoScrollPhase,
                False,
            )
        except TypeError:  # pragma: no cover - other binding signature
            pytest.skip("QWheelEvent signature differs in this Qt binding")
        QApplication.sendEvent(box, event)
    app.processEvents()

    assert box.value() == before
    assert box.focusPolicy() == Qt.ClickFocus


def test_start_uses_directory_prefix_and_size(tab, settings, tmp_path):
    """Start opens ``<dir>/<prefix>_<date>_001.log`` and remembers it all."""
    from id4_common.gui.tabs.status import stored_log_target

    tab._log_dir_edit.setText(str(tmp_path / "logs"))
    tab._log_prefix_edit.setText("polar")
    tab._log_max_mb.setValue(3)
    tab._toggle_log()

    transcript = tab.transcript
    assert transcript.active
    assert transcript.path.parent == tmp_path / "logs"
    assert transcript.path.name.startswith("polar_")
    assert transcript.path.name.endswith("_001.log")
    assert transcript.max_bytes == 3 * 1024 * 1024
    assert not tab._log_prefix_edit.isEnabled()
    assert stored_log_target(settings) == (str(tmp_path / "logs"), "polar", 3)

    # The size stays editable while logging and applies at once.
    tab._log_max_mb.setValue(5)
    assert transcript.max_bytes == 5 * 1024 * 1024

    tab._toggle_log()
    assert not transcript.active
    assert tab._log_prefix_edit.isEnabled()


def test_the_prefix_cannot_name_another_directory(tab):
    """Path separators are refused; the directory has its own field."""
    from qtpy.QtGui import QValidator

    validator = tab._log_prefix_edit.validator()

    assert validator.validate("run/7", 0)[0] == QValidator.Invalid
    assert validator.validate("run7", 0)[0] == QValidator.Acceptable
