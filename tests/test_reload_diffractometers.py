"""A device reload must not leave the session on stale diffractometers.

Report item 4.6 (huber_euler wrong positions, 2026-10-31):
``reload_all_devices()`` runs ``make_devices(clear=True)``, which builds new
diffractometer objects with hklpy2's default sample.  hklpy2's selection, the
plans, the console aliases and the shortcut macros kept the old objects,
while the GUI and the ``<name>_psi`` lookups got the new ones.

Fakes stand in for the devices and the registry, so none of this needs libhkl
or EPICS.
"""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


class FakeRegistry:
    """``oregistry.find`` over a plain dict."""

    def __init__(self, devices):
        self.devices = dict(devices)

    def find(self, name, allow_none=False):
        if name in self.devices:
            return self.devices[name]
        if allow_none:
            return None
        raise KeyError(name)


class FakeDevice:
    """A diffractometer stand-in whose ``destroy()`` is logged."""

    #: Shared call log, set by the ``hkl_utils`` fixture.
    log = None
    #: Make ``copy_setup`` / ``destroy`` raise.
    broken = False
    busy = False

    def __init__(self, name):
        self.name = name

    def destroy(self):
        if self.busy:
            raise RuntimeError("busy")
        FakeDevice.log.append(("destroy", self))


def _device(name):
    return FakeDevice(name)


@pytest.fixture
def hkl_utils(hkl_utils_module, monkeypatch):
    """hkl_utils with the registry, selection and copy faked, calls logged."""
    from id4_common.utils import diffractometer_setup

    module = hkl_utils_module

    calls = []
    monkeypatch.setattr(
        module,
        "change_diffractometer",
        lambda name: calls.append(("select", name)),
    )

    def fake_copy(source, target):
        if getattr(source, "broken", False):
            raise RuntimeError("IOC down")
        calls.append(("copy", source, target))

    monkeypatch.setattr(diffractometer_setup, "copy_setup", fake_copy)
    monkeypatch.setattr(importlib, "reload", lambda m: calls.append(m))
    monkeypatch.setattr(FakeDevice, "log", calls)
    module.fake_sd = SimpleNamespace(baseline=[], monitors=[])
    monkeypatch.setattr(module, "sd", module.fake_sd)
    module.calls = calls
    return module


def _reload(hkl_utils, monkeypatch, old, new, active):
    """Snapshot ``old``, swap the registry to ``new``, then restore."""
    monkeypatch.setattr(hkl_utils, "oregistry", FakeRegistry(old))
    snapshot = hkl_utils.snapshot_diffractometers()
    monkeypatch.setattr(hkl_utils, "oregistry", FakeRegistry(new))
    monkeypatch.setattr(hkl_utils, "get_diffractometer", lambda: active)
    hkl_utils.restore_diffractometers(snapshot)
    return snapshot


def test_snapshot_takes_only_registered_diffractometers(hkl_utils, monkeypatch):
    euler, psi, other = (
        _device("huber_euler"),
        _device("huber_euler_psi"),
        _device("gslt"),
    )
    monkeypatch.setattr(
        hkl_utils,
        "oregistry",
        FakeRegistry({d.name: d for d in (euler, psi, other)}),
    )
    assert hkl_utils.snapshot_diffractometers() == {
        "huber_euler": euler,
        "huber_euler_psi": psi,
    }


def test_reselects_then_carries_the_orientation(hkl_utils, monkeypatch):
    old = {n: _device(n) for n in ("huber_euler", "huber_euler_psi")}
    new = {n: _device(n) for n in ("huber_euler", "huber_euler_psi")}

    _reload(hkl_utils, monkeypatch, old, new, active=old["huber_euler"])

    # Selecting first: change_diffractometer resets the constraints, which
    # the copy then brings back.  Each old object goes only once copied.
    assert hkl_utils.calls == [
        ("select", "huber_euler"),
        ("copy", old["huber_euler"], new["huber_euler"]),
        ("destroy", old["huber_euler"]),
        ("copy", old["huber_euler_psi"], new["huber_euler_psi"]),
        ("destroy", old["huber_euler_psi"]),
    ]


def test_a_failed_copy_is_reported_and_the_rest_continue(
    hkl_utils, monkeypatch, capsys
):
    old = {n: _device(n) for n in ("huber_euler", "huber_hp")}
    old["huber_euler"].broken = True
    new = {n: _device(n) for n in ("huber_euler", "huber_hp")}

    _reload(hkl_utils, monkeypatch, old, new, active=None)

    # The failed one keeps its old object: the only copy of its orientation.
    assert hkl_utils.calls == [
        ("copy", old["huber_hp"], new["huber_hp"]),
        ("destroy", old["huber_hp"]),
    ]
    out = capsys.readouterr().out
    assert "Could not carry huber_euler's orientation" in out
    assert "IOC down" in out


def test_an_active_device_that_was_not_reloaded_is_not_reselected(
    hkl_utils, monkeypatch, capsys
):
    old = {"huber_euler": _device("huber_euler")}

    _reload(hkl_utils, monkeypatch, old, {}, active=old["huber_euler"])

    assert hkl_utils.calls == []
    assert "no longer loaded" in capsys.readouterr().out


def test_loaded_shortcut_macros_are_reimported(hkl_utils, monkeypatch):
    macro = types.ModuleType("id4_common.macros.shortcuts_fake")
    unrelated = types.ModuleType("id4_common.macros.not_a_shortcut")
    monkeypatch.setitem(sys.modules, macro.__name__, macro)
    monkeypatch.setitem(sys.modules, unrelated.__name__, unrelated)

    _reload(hkl_utils, monkeypatch, {}, {}, active=None)

    assert macro in hkl_utils.calls
    assert unrelated not in hkl_utils.calls


def test_the_old_object_leaves_the_baseline_and_monitors(
    hkl_utils, monkeypatch
):
    """A destroyed device left in the baseline would break every run."""
    old = {"huber_euler": _device("huber_euler")}
    new = {"huber_euler": _device("huber_euler")}
    # The new one failed to connect, so connect_device never swapped them.
    hkl_utils.fake_sd.baseline[:] = [old["huber_euler"], "other"]
    hkl_utils.fake_sd.monitors[:] = [old["huber_euler"]]

    _reload(hkl_utils, monkeypatch, old, new, active=None)

    assert hkl_utils.fake_sd.baseline == ["other"]
    assert hkl_utils.fake_sd.monitors == []


def test_the_new_object_stays_in_the_baseline(hkl_utils, monkeypatch):
    old = {"huber_euler": _device("huber_euler")}
    new = {"huber_euler": _device("huber_euler")}
    hkl_utils.fake_sd.baseline[:] = [new["huber_euler"]]

    _reload(hkl_utils, monkeypatch, old, new, active=None)

    assert hkl_utils.fake_sd.baseline == [new["huber_euler"]]


def test_a_failed_destroy_is_reported_and_the_rest_continue(
    hkl_utils, monkeypatch, capsys
):
    old = {n: _device(n) for n in ("huber_euler", "huber_hp")}
    old["huber_euler"].busy = True
    new = {n: _device(n) for n in ("huber_euler", "huber_hp")}

    _reload(hkl_utils, monkeypatch, old, new, active=None)

    assert ("destroy", old["huber_hp"]) in hkl_utils.calls
    assert "Could not release the old huber_euler (busy)" in (
        capsys.readouterr().out
    )


def test_set_diffractometer_keeps_one_configuration_wrapper(
    hkl_utils, monkeypatch
):
    """The old wrapper used to stay, pointing at the previous device."""

    class FakeWrapper:
        def __init__(self, device):
            self.device = device

        def wrapper(self, plan):
            return plan

    def other(plan):
        return plan

    preprocessors = [other]
    monkeypatch.setattr(hkl_utils, "hklpy2_set_diffract", lambda d: None)
    monkeypatch.setattr(hkl_utils, "ConfigurationRunWrapper", FakeWrapper)
    monkeypatch.setattr(
        hkl_utils, "polar_RE", SimpleNamespace(preprocessors=preprocessors)
    )
    monkeypatch.setattr(hkl_utils.geometries, "configuration_wrapper", None)

    first, second = _device("huber_euler"), _device("huber_hp")
    hkl_utils.set_diffractometer(first)
    hkl_utils.set_diffractometer(second)

    assert len(preprocessors) == 2
    assert preprocessors[0] is other
    assert preprocessors[1].__self__.device is second


def test_copy_setup_takes_orientation_but_not_wavelength():
    """``copy_setup`` builds on the target's config and restores it all."""
    from id4_common.utils.diffractometer_setup import copy_setup

    sample = SimpleNamespace(name="s1", _asdict=lambda: {"lattice": "x"})
    source = SimpleNamespace(
        core=SimpleNamespace(
            _samples={"s1": sample},
            sample=sample,
            constraints=SimpleNamespace(_asdict=lambda: {"mu": "limits"}),
            all_extras={"h2": 0.0, "k2": 0.0, "l2": 1.0},
            _mode_presets={"bissector": {"tau": 0.0}},
            mode="psi constant horizontal",
        )
    )
    restored = {}
    target = SimpleNamespace(
        configuration={"axes": {}, "beam": "target's own"},
        core=SimpleNamespace(mode="bissector"),
        restore=lambda config, **kwargs: restored.update(
            config=config, kwargs=kwargs
        ),
    )

    copy_setup(source, target)

    config = restored["config"]
    assert config["samples"] == {"s1": {"lattice": "x"}}
    assert config["sample_name"] == "s1"
    assert config["constraints"] == {"mu": "limits"}
    assert config["axes"]["extra_axes"] == {"h2": 0.0, "k2": 0.0, "l2": 1.0}
    assert config["presets"] == {"bissector": {"tau": 0.0}}
    assert config["beam"] == "target's own"
    assert restored["kwargs"]["restore_wavelength"] is False
    assert restored["kwargs"]["restore_samples"] is True
    assert restored["kwargs"]["restore_extras"] is True
    assert target.core.mode == "psi constant horizontal"
