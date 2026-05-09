"""Tests for id4_common.utils.temperature_setup."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_device(dotted_paths):
    """Build a mock device that resolves each dotted attribute path.

    Each leaf is a unique MagicMock so the test can identify which path
    `temperature_setup` ended up resolving.
    """
    device = SimpleNamespace()
    for path in dotted_paths:
        parts = path.split(".")
        cursor = device
        for part in parts[:-1]:
            if not hasattr(cursor, part):
                setattr(cursor, part, SimpleNamespace())
            cursor = getattr(cursor, part)
        leaf = MagicMock(name=path)
        setattr(cursor, parts[-1], leaf)
    return device


@pytest.fixture
def fresh_module(monkeypatch):
    """Reload temperature_setup with clean module-level state and a stub sd.

    Patches:
    - sd (the SupplementalData instance) with a stub that has a list-typed
      ``baseline`` so the baseline-membership branches are exercised.
    - oregistry.find with a callable controlled by the test.
    - sys.modules["__main__"] with an isolated SimpleNamespace so we can
      assert what gets injected without polluting the real __main__.
    """
    # Force a fresh import so the module-level _active_label is None.
    sys.modules.pop("id4_common.utils.temperature_setup", None)

    # Stub sd.baseline as a real list before the import.
    fake_sd = MagicMock()
    fake_sd.baseline = []
    sys.modules["id4_common.utils.run_engine"].sd = fake_sd

    # Isolated __main__.
    fake_main = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    import id4_common.utils.temperature_setup as ts_mod

    return ts_mod, fake_sd, fake_main


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seed_dict_paths_resolve_against_a_mock_device(fresh_module):
    """Every path in TEMPERATURE_CONTROLLERS resolves through _resolve_path."""
    ts_mod, _, _ = fresh_module

    # Group entries by device so we mirror the real registry shape.
    by_device = {}
    for label, (device, sp, rb) in ts_mod.TEMPERATURE_CONTROLLERS.items():
        by_device.setdefault(device, set()).update([sp, rb])

    for device_name, paths in by_device.items():
        device = _build_device(paths)
        for path in paths:
            resolved = ts_mod._resolve_path(device, path)
            assert isinstance(resolved, MagicMock), (
                f"path {device_name}.{path} did not resolve to a leaf"
            )


def test_unknown_label_raises_keyerror(fresh_module):
    ts_mod, _, _ = fresh_module
    with pytest.raises(KeyError, match="bogus-label"):
        ts_mod.temperature_setup("bogus-label")


def test_missing_device_raises_lookuperror(fresh_module, monkeypatch):
    ts_mod, _, _ = fresh_module
    # oregistry.find returns None -> we should raise LookupError.
    fake_registry = MagicMock()
    fake_registry.find.return_value = None
    monkeypatch.setattr(ts_mod, "oregistry", fake_registry)

    with pytest.raises(LookupError, match="not in oregistry"):
        ts_mod.temperature_setup("g-336-loop1")


def test_setup_injects_tc_ts_and_label(fresh_module, monkeypatch):
    ts_mod, fake_sd, fake_main = fresh_module
    label = "g-336-loop1"
    _, sp_path, rb_path = ts_mod.TEMPERATURE_CONTROLLERS[label]
    device = _build_device([sp_path, rb_path])

    fake_registry = MagicMock()
    fake_registry.find.return_value = device
    monkeypatch.setattr(ts_mod, "oregistry", fake_registry)

    ts_mod.temperature_setup(label)

    expected_tc = ts_mod._resolve_path(device, sp_path)
    expected_ts = ts_mod._resolve_path(device, rb_path)

    assert fake_main.tc is expected_tc
    assert fake_main.ts is expected_ts
    assert fake_main.TEMPERATURE_CONTROLLER == label
    assert ts_mod.get_active_label() == label
    assert ts_mod.get_active_tc() is expected_tc
    assert ts_mod.get_active_ts() is expected_ts
    assert expected_ts in fake_sd.baseline
    assert fake_sd.baseline.count(expected_ts) == 1


def test_resetup_swaps_baseline(fresh_module, monkeypatch):
    """Re-running with a different label removes the previous ts from baseline."""
    ts_mod, fake_sd, _ = fresh_module

    label_a = "g-336-loop1"
    label_b = "g-340-loop1"
    _, sp_a, rb_a = ts_mod.TEMPERATURE_CONTROLLERS[label_a]
    _, sp_b, rb_b = ts_mod.TEMPERATURE_CONTROLLERS[label_b]

    devices = {
        "temp_336_4idg": _build_device([sp_a, rb_a]),
        "temp_340_4idg": _build_device([sp_b, rb_b]),
    }
    fake_registry = MagicMock()
    fake_registry.find.side_effect = lambda name, **kw: devices[name]
    monkeypatch.setattr(ts_mod, "oregistry", fake_registry)

    ts_mod.temperature_setup(label_a)
    ts_a = ts_mod.get_active_ts()
    ts_mod.temperature_setup(label_b)
    ts_b = ts_mod.get_active_ts()

    assert ts_a not in fake_sd.baseline
    assert ts_b in fake_sd.baseline
    assert len(fake_sd.baseline) == 1


def test_add_to_baseline_false_skips_membership(fresh_module, monkeypatch):
    ts_mod, fake_sd, _ = fresh_module
    label = "h-9T-vti-a"
    _, sp_path, rb_path = ts_mod.TEMPERATURE_CONTROLLERS[label]
    device = _build_device([sp_path, rb_path])

    fake_registry = MagicMock()
    fake_registry.find.return_value = device
    monkeypatch.setattr(ts_mod, "oregistry", fake_registry)

    ts_mod.temperature_setup(label, add_to_baseline=False)
    assert fake_sd.baseline == []
    assert ts_mod.get_active_label() == label
