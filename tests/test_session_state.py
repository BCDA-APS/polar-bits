"""Tests for id4_common.utils.session_state (auto-saved RE.md knobs)."""

from __future__ import annotations

import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_module(monkeypatch):
    """Reload session_state with a stub RE.md (plain dict) and stub
    oregistry.

    Returns ``(module, fake_oregistry, RE_md)`` so tests can populate the
    registry, drive the save/restore helpers, and inspect what landed in
    ``RE.md["session_state"]``.
    """
    sys.modules.pop("id4_common.utils.session_state", None)

    # Stub RE.md as a real dict so PersistentDict semantics aren't needed.
    re_md = {}
    fake_re = MagicMock(name="RE")
    fake_re.md = re_md
    sys.modules["id4_common.utils.run_engine"].RE = fake_re

    # Stub oregistry; tests fill in `_devices` to control find().
    devices: dict = {}

    def _find(name, allow_none=False, **_):
        dev = devices.get(name)
        if dev is None and not allow_none:
            raise LookupError(name)
        return dev

    fake_oregistry = MagicMock()
    fake_oregistry.find.side_effect = _find
    monkeypatch.setattr(
        sys.modules["apsbits.core.instrument_init"],
        "oregistry",
        fake_oregistry,
    )

    import id4_common.utils.session_state as ss

    monkeypatch.setattr(ss, "oregistry", fake_oregistry)

    return ss, devices, re_md


def _stub_undulators(
    devices, *, ds_offset=0.0, ds_db=0.002, us_offset=0.0, us_db=0.002
):
    """Plant an `undulators` device with us/ds energy_offset + deadband."""
    dev = SimpleNamespace()
    for side, off, db in (("us", us_offset, us_db), ("ds", ds_offset, ds_db)):
        side_dev = SimpleNamespace()
        side_dev.energy_offset = MagicMock()
        side_dev.energy_offset.get.return_value = off
        side_dev.energy_deadband = MagicMock()
        side_dev.energy_deadband.get.return_value = db
        setattr(dev, side, side_dev)
    devices["undulators"] = dev
    return dev


def _stub_energy(devices, *, tracked_names=()):
    """Plant an `energy` device with trackable_devices reflecting flags."""
    trackables = []
    for name in ("undulators_us", "undulators_ds", "pr2"):
        td = SimpleNamespace(name=name, tracking=MagicMock())
        td.tracking.get.return_value = name in tracked_names
        trackables.append(td)
    energy = MagicMock()
    energy.trackable_devices = trackables
    devices["energy"] = energy
    return energy


def _stub_qxscan(devices, *, params=None):
    qx = MagicMock()
    qx._make_params_dict.return_value = params or {"edge": {"Estart": -10}}
    devices["qxscan_setup"] = qx
    return qx


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def test_save_undulator_writes_offsets_and_deadbands(fresh_module):
    ss, devices, re_md = fresh_module
    _stub_undulators(
        devices, ds_offset=-0.072, ds_db=0.002, us_offset=0.0, us_db=0.001
    )

    ss._save_undulator()

    snap = re_md["session_state"]["undulators"]
    assert snap == {
        "us": {"energy_offset": 0.0, "energy_deadband": 0.001},
        "ds": {"energy_offset": -0.072, "energy_deadband": 0.002},
    }
    assert "saved_at" in re_md["session_state"]


def test_save_undulator_skips_when_device_missing(fresh_module):
    ss, _, re_md = fresh_module
    ss._save_undulator()
    assert re_md == {}


def test_save_energy_tracking_lists_active_names(fresh_module):
    ss, devices, re_md = fresh_module
    _stub_energy(devices, tracked_names=("undulators_ds", "pr2"))

    ss._save_energy_tracking()

    assert re_md["session_state"]["energy_tracking"] == {
        "devices": ["undulators_ds", "pr2"],
    }


def test_save_pr_setup_serialises_names_only(fresh_module, monkeypatch):
    ss, _, re_md = fresh_module

    fake_pr = ModuleType("id4_common.utils.pr_setup")
    fake_pr.pr_setup = SimpleNamespace(
        positioner=SimpleNamespace(name="pr2_pzt_localdc"),
        offset=SimpleNamespace(name="pr2_pzt_offset_microns"),
        oscillate_pzt=True,
    )
    monkeypatch.setitem(sys.modules, "id4_common.utils.pr_setup", fake_pr)

    ss._save_pr_setup()

    assert re_md["session_state"]["pr_setup"] == {
        "positioner": "pr2_pzt_localdc",
        "offset": "pr2_pzt_offset_microns",
        "oscillate_pzt": True,
    }


def test_save_counters_records_dev_channel_pairs(fresh_module, monkeypatch):
    ss, _, re_md = fresh_module

    fake_c = ModuleType("id4_common.utils.counters_class")
    fake_c.counters = SimpleNamespace(
        _selected_dets=[("scaler1", "Mn"), ("scaler1", "Fe")],
        _selected_mon=("scaler1", "I0"),
        _selected_extra_read=[],
    )
    monkeypatch.setitem(sys.modules, "id4_common.utils.counters_class", fake_c)

    ss._save_counters()

    assert re_md["session_state"]["counters"] == {
        "detectors": [["scaler1", "Mn"], ["scaler1", "Fe"]],
        "monitor": ["scaler1", "I0"],
        "extra_read": [],
    }


def test_save_qxscan_with_source_uses_pointer(fresh_module):
    ss, devices, re_md = fresh_module
    _stub_qxscan(devices)

    ss._save_qxscan(source="tb.json")

    assert re_md["session_state"]["qxscan"] == {"source": "tb.json"}


def test_save_qxscan_without_source_inlines_params(fresh_module):
    ss, devices, re_md = fresh_module
    _stub_qxscan(devices, params={"edge": {"Estart": -5}})

    ss._save_qxscan()

    assert re_md["session_state"]["qxscan"] == {
        "params": {"edge": {"Estart": -5}}
    }


# ---------------------------------------------------------------------------
# Public save / restore
# ---------------------------------------------------------------------------


def test_save_session_state_calls_every_helper(fresh_module, monkeypatch):
    ss, devices, re_md = fresh_module
    _stub_undulators(devices)
    _stub_energy(devices, tracked_names=("pr2",))
    _stub_qxscan(devices)

    fake_pr = ModuleType("id4_common.utils.pr_setup")
    fake_pr.pr_setup = SimpleNamespace(
        positioner=None,
        offset=None,
        oscillate_pzt=True,
    )
    monkeypatch.setitem(sys.modules, "id4_common.utils.pr_setup", fake_pr)

    fake_c = ModuleType("id4_common.utils.counters_class")
    fake_c.counters = SimpleNamespace(
        _selected_dets=[],
        _selected_mon=("scaler1", "Time"),
        _selected_extra_read=[],
    )
    monkeypatch.setitem(sys.modules, "id4_common.utils.counters_class", fake_c)

    snap = ss.save_session_state()
    assert "undulators" in snap
    assert "energy_tracking" in snap
    assert "pr_setup" in snap
    assert "counters" in snap
    assert "qxscan" in snap


def test_restore_no_snapshot_returns_skipped(fresh_module):
    ss, _, _ = fresh_module
    status = ss.restore_session_state()
    assert status == {"session_state": "skipped: no snapshot in RE.md"}


def test_restore_undulator_calls_put(fresh_module):
    ss, devices, _ = fresh_module
    dev = _stub_undulators(devices)

    status = ss._restore_undulator(
        {"ds": {"energy_offset": -0.072, "energy_deadband": 0.002}}
    )

    assert status == "applied"
    dev.ds.energy_offset.put.assert_called_once_with(-0.072)
    dev.ds.energy_deadband.put.assert_called_once_with(0.002)


def test_restore_undulator_missing_device(fresh_module):
    ss, _, _ = fresh_module
    status = ss._restore_undulator({"ds": {"energy_offset": 0.0}})
    assert status.startswith("skipped:")


def test_restore_energy_tracking_invokes_setup(fresh_module):
    ss, devices, _ = fresh_module
    energy = _stub_energy(devices, tracked_names=())

    status = ss._restore_energy_tracking({"devices": ["pr2"]})

    assert status == "applied"
    energy.tracking_setup.assert_called_once_with(["pr2"])


def test_restore_pr_setup_resolves_devices(fresh_module, monkeypatch):
    ss, devices, _ = fresh_module
    devices["pr2_pzt_localdc"] = SimpleNamespace(name="pr2_pzt_localdc")
    devices["pr2_pzt_offset_microns"] = SimpleNamespace(
        name="pr2_pzt_offset_microns"
    )

    fake_pr_singleton = SimpleNamespace(
        positioner=None,
        offset=None,
        oscillate_pzt=False,
    )
    fake_pr = ModuleType("id4_common.utils.pr_setup")
    fake_pr.pr_setup = fake_pr_singleton
    monkeypatch.setitem(sys.modules, "id4_common.utils.pr_setup", fake_pr)

    status = ss._restore_pr_setup(
        {
            "positioner": "pr2_pzt_localdc",
            "offset": "pr2_pzt_offset_microns",
            "oscillate_pzt": True,
        }
    )
    assert status == "applied"
    assert fake_pr_singleton.positioner is devices["pr2_pzt_localdc"]
    assert fake_pr_singleton.offset is devices["pr2_pzt_offset_microns"]
    assert fake_pr_singleton.oscillate_pzt is True


def test_restore_pr_setup_skips_when_positioner_unknown(
    fresh_module, monkeypatch
):
    ss, _, _ = fresh_module

    fake_pr = ModuleType("id4_common.utils.pr_setup")
    fake_pr.pr_setup = SimpleNamespace(
        positioner=None,
        offset=None,
        oscillate_pzt=False,
    )
    monkeypatch.setitem(sys.modules, "id4_common.utils.pr_setup", fake_pr)

    status = ss._restore_pr_setup(
        {
            "positioner": "missing_pzt",
            "offset": None,
            "oscillate_pzt": True,
        }
    )
    assert "skipped" in status
    assert "missing_pzt" in status


def test_restore_qxscan_via_source(fresh_module):
    ss, devices, _ = fresh_module
    qx = _stub_qxscan(devices)

    status = ss._restore_qxscan({"source": "tb.json"})
    assert status.startswith("applied")
    qx.load_params_json.assert_called_once_with("tb.json")


def test_restore_qxscan_via_inline_params(fresh_module):
    ss, devices, _ = fresh_module
    qx = _stub_qxscan(devices)

    status = ss._restore_qxscan({"params": {"edge": {"Estart": -5}}})
    assert status.startswith("applied")
    qx._read_params_dict.assert_called_once_with({"edge": {"Estart": -5}})


def test_restore_qxscan_missing_source_and_params(fresh_module):
    ss, devices, _ = fresh_module
    _stub_qxscan(devices)

    status = ss._restore_qxscan({})
    assert "skipped" in status


def test_restore_qxscan_failed_load_reports(fresh_module):
    ss, devices, _ = fresh_module
    qx = _stub_qxscan(devices)
    qx.load_params_json.side_effect = FileNotFoundError("no.json")

    status = ss._restore_qxscan({"source": "no.json"})
    assert status.startswith("failed:")
    assert "FileNotFoundError" in status


def test_restore_session_state_with_explicit_state_skips_re_md(fresh_module):
    ss, devices, re_md = fresh_module
    re_md["session_state"] = {"qxscan": {"source": "wrong.json"}}
    qx = _stub_qxscan(devices)

    status = ss.restore_session_state(
        state={"qxscan": {"source": "right.json"}}
    )

    assert status["qxscan"].startswith("applied")
    qx.load_params_json.assert_called_once_with("right.json")
