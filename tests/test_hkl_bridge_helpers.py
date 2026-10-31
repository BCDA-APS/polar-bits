"""The HKL tab and MCP layer must not change the console's state by accident.

Report item 4.5 (huber_euler wrong positions, 2026-10-31): pressing
Calculate replaced the console's presets and psi, the tab pushed a stale copy
of them back, and Add sample silently replaced a sample of the same name.

The kernel helpers are exercised by ``exec``-ing the very code string the GUI
installs, against a fake diffractometer, so none of this needs libhkl.  The
tab tests skip where ``qtpy`` is absent -- it is in the ``gui`` extra only.
"""

from __future__ import annotations

from collections import namedtuple
from types import SimpleNamespace

import pytest

REALS = ("tau", "mu", "chi", "phi", "gamma", "delta")
PSI_MODE = "psi constant horizontal"
Reals = namedtuple("Reals", REALS)


class FakeCore:
    """Per-mode presets and extras with hklpy2's setter semantics."""

    def __init__(self):
        self.modes = ["4-circles bissecting horizontal", PSI_MODE]
        self.mode = self.modes[0]
        self._constant = {self.modes[0]: ["tau", "delta"], PSI_MODE: ["tau"]}
        self._presets = {m: {} for m in self.modes}
        self._extras = {
            self.modes[0]: {},
            PSI_MODE: {"h2": 0.0, "k2": 0.0, "l2": 1.0, "psi": 0.0},
        }

    @property
    def constant_axis_names(self):
        return list(self._constant[self.mode])

    @property
    def presets(self):
        # Live dict, as hklpy2's getter returns.
        return self._presets[self.mode]

    @presets.setter
    def presets(self, values):
        self._presets[self.mode] = {
            k: v for k, v in values.items() if k in self.constant_axis_names
        }

    @property
    def extras(self):
        return self._extras[self.mode]

    @extras.setter
    def extras(self, values):
        unknown = set(values) - set(self._extras[self.mode])
        if unknown:
            raise ValueError(f"unknown extras {sorted(unknown)}")
        self._extras[self.mode].update(values)


class FakeDiffractometer:
    """Just enough of a diffractometer for the ``_gui_hkl_*`` helpers."""

    def __init__(self, name="huber_euler"):
        self.name = name
        self.core = FakeCore()
        self.real_positioners = SimpleNamespace(_fields=REALS)
        self.pseudo_positioners = SimpleNamespace(_fields=("h", "k", "l"))
        for field in REALS + ("h", "k", "l"):
            setattr(self, field, SimpleNamespace(position=1.0))
        self.beam = SimpleNamespace(
            wavelength=SimpleNamespace(get=lambda: 4.1774),
            energy=SimpleNamespace(get=lambda: 2.968),
        )
        self.fail = False
        self.solved_with = None
        self.added = None

    def forward(self, h, k, l):  # noqa: E741 - the Miller index
        self.solved_with = (dict(self.core.presets), dict(self.core.extras))
        if self.fail:
            raise ValueError("no solution")
        return Reals(*range(len(REALS)))

    def add_sample(self, name, a, **kwargs):
        self.added = (name, a, kwargs)


@pytest.fixture
def kernel(monkeypatch):
    """The installed helpers plus the fake diffractometer they act on."""
    monkeypatch.setenv("ID4_STATION", "id4_g")
    from id4_common.gui.hkl_bridge import hkl_helpers_code

    dev = FakeDiffractometer()
    namespace = {"oregistry": SimpleNamespace(find=lambda name: dev)}
    exec(hkl_helpers_code(), namespace)
    return SimpleNamespace(dev=dev, **namespace)


# --- Calculate is a what-if -------------------------------------------------


def test_calculate_restores_the_console_presets(kernel):
    """The solve uses the tab's presets; the console's are put back."""
    dev = kernel.dev
    dev.core.presets = {"delta": 0.0}  # e.g. what setmode left

    out = kernel._gui_hkl_calc("huber_euler", 1, 1, 0, None, {"tau": 5.0})

    assert dev.solved_with[0] == {"tau": 5.0}
    assert out["presets"] == {"tau": 5.0}
    assert "error" not in out
    assert dev.core.presets == {"delta": 0.0}


def test_calculate_with_nothing_ticked_keeps_the_presets(kernel):
    """The original bug: an empty dict wiped the console's presets."""
    dev = kernel.dev
    dev.core.presets = {"delta": 0.0}

    kernel._gui_hkl_calc("huber_euler", 1, 1, 0, None, {})

    assert dev.solved_with[0] == {}
    assert dev.core.presets == {"delta": 0.0}


def test_calculate_restores_psi(kernel):
    dev = kernel.dev
    dev.core.mode = PSI_MODE
    dev.core.extras = {"psi": 30.0}  # e.g. what freeze(psi) left

    out = kernel._gui_hkl_calc("huber_euler", 1, 1, 0, 90.0, {})

    assert dev.solved_with[1]["psi"] == 90.0
    assert out["psi"] == 90.0
    assert dev.core.extras["psi"] == 30.0


def test_a_failed_solve_still_restores(kernel):
    dev = kernel.dev
    dev.core.mode = PSI_MODE
    dev.core.presets = {"tau": 1.0}
    dev.core.extras = {"psi": 30.0}
    dev.fail = True

    out = kernel._gui_hkl_calc("huber_euler", 1, 1, 0, 90.0, {"tau": 5.0})

    assert out["error"] == "no solution"
    assert dev.core.presets == {"tau": 1.0}
    assert dev.core.extras["psi"] == 30.0


def test_the_mcp_path_leaves_presets_alone(kernel):
    """``request_hkl`` calls without presets: they are never written."""
    dev = kernel.dev
    dev.core.presets = {"delta": 0.0}
    live = dev.core.presets

    out = kernel._gui_hkl_calc("huber_euler", 1, 1, 0)

    assert dev.solved_with[0] == {"delta": 0.0}
    assert "presets" not in out
    assert dev.core.presets is live


# --- the position poll carries the fixed values -----------------------------


def test_position_reports_presets_and_extras(kernel):
    dev = kernel.dev
    dev.core.mode = PSI_MODE
    dev.core.presets = {"tau": 2.0}

    out = kernel._gui_hkl_position("huber_euler")

    assert out["mode"] == PSI_MODE
    assert out["presets"] == {"tau": 2.0}
    assert out["extras"] == {"h2": 0.0, "k2": 0.0, "l2": 1.0, "psi": 0.0}


# --- Add sample does not replace by default ---------------------------------


def test_add_sample_does_not_replace_by_default(kernel):
    """MCP passes seven arguments, so it can never replace a sample."""
    kernel._gui_hkl_add_sample("huber_euler", "s", 4, 4, 4, 90, 90, 90)
    assert kernel.dev.added[2]["replace"] is False


def test_add_sample_replaces_when_asked(kernel):
    kernel._gui_hkl_add_sample(
        "huber_euler", "s", 4, 4, 4, 90, 90, 90, replace=True
    )
    assert kernel.dev.added[2]["replace"] is True


# --- the tab ----------------------------------------------------------------


@pytest.fixture
def hkl_tab(monkeypatch):
    """An HKL tab with a loaded state and its kernel traffic captured."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("ID4_STATION", "id4_g")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    from id4_common.gui.tabs.hkl import HklTab
    from qtpy.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    tab = HklTab()
    tab.sent = []
    tab.console = []
    tab.request = tab.sent.append
    tab.run_in_console = lambda code: tab.console.append(code) or True
    tab._state = {
        "device": tab.device,
        "mode": "4-circles bissecting horizontal",
        "presets": {"delta": 0.0},
        "extras": {},
        "psi_reference": {},
        "pseudo_fields": ["h", "k", "l"],
        "samples": {"default": {}, "mysample": {}},
    }
    tab._app = app
    return tab


def _position(tab, **changes):
    position = {
        key: tab._state[key]
        for key in ("mode", "presets", "extras", "psi_reference")
    }
    position["device"] = tab.device
    position.update(changes)
    return position


def test_tab_rereads_state_when_the_console_changes_presets(hkl_tab):
    from id4_common.gui.hkl_bridge import POSITION_KEY
    from id4_common.gui.hkl_bridge import STATE_KEY

    hkl_tab.on_kernel_values({POSITION_KEY: _position(hkl_tab)})
    assert not any(STATE_KEY in r for r in hkl_tab.sent)

    changed = _position(hkl_tab, presets={"delta": 0.0, "tau": 3.0})
    hkl_tab.on_kernel_values({POSITION_KEY: changed})
    assert any(STATE_KEY in r for r in hkl_tab.sent)


def test_tab_waits_while_its_own_write_is_pending(hkl_tab):
    from id4_common.gui.hkl_bridge import POSITION_KEY
    from id4_common.gui.hkl_bridge import STATE_KEY

    hkl_tab._presets_timer.start()
    changed = _position(hkl_tab, presets={})
    hkl_tab.on_kernel_values({POSITION_KEY: changed})
    hkl_tab._presets_timer.stop()

    assert not any(STATE_KEY in r for r in hkl_tab.sent)


def test_move_drives_the_calculated_angles(hkl_tab, monkeypatch):
    from qtpy.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.Yes
    )
    monkeypatch.setattr(hkl_tab, "_start_progress", lambda: None)
    hkl_tab._apply_calculation(
        {
            "h": 1.0,
            "k": 1.0,
            "l": 0.0,
            "presets": {"delta": 0.0},
            "reals": {"mu": 10.0, "gamma": 20.0},
        }
    )
    # Editing the boxes afterwards must not change what moves.
    hkl_tab._calc_boxes["h"].setValue(2.0)

    hkl_tab._move()

    dev = hkl_tab.device
    assert hkl_tab.console == [
        f"RE(bps.mv({dev}.mu, 10.0, {dev}.gamma, 20.0)); "
        f"{dev}.h.sync(); {dev}.k.sync(); {dev}.l.sync()"
    ]


def test_add_sample_asks_before_replacing(hkl_tab, monkeypatch):
    from id4_common.gui.tabs.hkl import ACTION_KEY
    from qtpy.QtWidgets import QMessageBox

    hkl_tab.poller = object()  # _act needs one to send anything
    asked = []

    def answer(*args, **kwargs):
        asked.append(args)
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", answer)
    hkl_tab._sample_name.setText("mysample")
    hkl_tab._add_sample()
    assert asked
    assert not any(ACTION_KEY in r for r in hkl_tab.sent)

    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.Yes
    )
    hkl_tab._sample_name.setText("mysample")
    hkl_tab._add_sample()
    sent = [r[ACTION_KEY] for r in hkl_tab.sent if ACTION_KEY in r]
    assert sent and sent[-1].endswith("replace=True)")


def test_add_sample_with_a_new_name_does_not_ask(hkl_tab, monkeypatch):
    from id4_common.gui.tabs.hkl import ACTION_KEY
    from qtpy.QtWidgets import QMessageBox

    hkl_tab.poller = object()

    def fail(*args, **kwargs):
        raise AssertionError("should not ask")

    monkeypatch.setattr(QMessageBox, "question", fail)
    hkl_tab._sample_name.setText("brand_new")
    hkl_tab._add_sample()
    sent = [r[ACTION_KEY] for r in hkl_tab.sent if ACTION_KEY in r]
    assert sent and sent[-1].endswith("replace=False)")
