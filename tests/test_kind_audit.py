"""Offline tests for signals hidden by sub-Device kinds (#72, #100).

A ``normal`` signal inside a ``config`` sub-Device reaches neither
``read()`` nor ``read_configuration()``, so it is never saved. These tests
use ophyd fake devices, no IOC needed.
"""

import importlib
import re

import pytest
from id4_common.utils.kind_audit import _reached_signals
from id4_common.utils.kind_audit import find_unrecorded_signals
from ophyd import Component
from ophyd import Device
from ophyd import Kind
from ophyd import Signal
from ophyd.sim import make_fake_device


class _Leaf(Device):
    """Positioner-like sub-Device with one normal and one config signal."""

    readback = Component(Signal, kind="hinted")
    tolerance = Component(Signal, kind="config")


class _Parent(Device):
    """Parent with one sub-Device of each kind."""

    as_normal = Component(_Leaf)
    as_config = Component(_Leaf, kind="config")
    as_omitted = Component(_Leaf, kind="omitted")


def test_config_parent_hides_normal_signal():
    """Only the readback under the config sub-Device is reported."""
    dev = _Parent(name="dev")
    assert find_unrecorded_signals(dev) == ["dev_as_config_readback"]


def test_audit_matches_ophyd_read():
    """The kind walk agrees with what ophyd actually reads."""
    dev = _Parent(name="dev")
    recorded = set(dev.read()) | set(dev.read_configuration())
    walked = {
        sig.name
        for kind in (Kind.normal, Kind.config)
        for sig in _reached_signals(dev, kind)
    }
    assert walked == recorded


# ---------------------------------------------------------------------------
# polar-bits devices
# ---------------------------------------------------------------------------


def _no_setup(dev):
    """Nothing to run after instantiation."""


def _default_settings(dev):
    """Apply the kinds set when the device is loaded, as device_loader does."""
    if hasattr(dev, "default_settings"):
        dev.default_settings()


def _quadem_setup(dev):
    """Apply load-time and post-connect kinds."""
    dev.default_settings()
    dev._post_connect_setup()


def _mono_feedback_setup(dev):
    """Select station B, as the station subscription would."""
    dev._kind_setup("b")


def _vortex_setup(rois):
    """Apply load-time kinds, then select ``rois`` for reading."""

    def setup(dev):
        dev.default_settings()
        dev.read_rois = rois

    return setup


# Deselected ROIs keep only their configuration (name, bounds) on purpose.
_DESELECTED_XSPRESS_ROI = r"_stats\d_roi([2-9]|\d\d+)_\w+_value$"
_DESELECTED_DANTE_ROI = r"_rois_roi([1-9]\d*)_count$"

# module, class, kwargs, setup, allowed (regex of signals dropped on purpose)
DEVICES = [
    ("magnet_911", "Magnet911", {}, _no_setup, None),
    ("aps_undulator", "PolarUndulatorPair", {}, _default_settings, None),
    ("mono_feedback", "MonoFeedback", {}, _mono_feedback_setup, None),
    (
        "monochromator",
        "MonoDevice",
        {"pzt_thf2_pv": "pzt1", "pzt_chi2_pv": "pzt2"},
        _no_setup,
        None,
    ),
    ("mirror_toroidal", "ToroidalMirror", {}, _no_setup, None),
    ("filters_device", "APSFilter", {}, _no_setup, None),
    ("filters_device_avs", "APSFilter", {}, _no_setup, None),
    ("crl_device", "CRLClass", {}, _no_setup, None),
    ("polarimeter", "PolAnalyzer", {}, _no_setup, None),
    # The QuadEM stats plugins stay config on purpose (see
    # StatsPluginQuadEM); the top-level *_mean/*_fast signals carry the data.
    ("quadems", "TetrAMMRO", {}, _quadem_setup, r"_(current\d|sum_all)_"),
    ("quadems", "SydorEMRO", {}, _quadem_setup, r"_(current\d|sum_all)_"),
    # Legacy XMAP: per-point spectra and DXP statistics are not recorded.
    ("vortex_xmap", "VortexXMAP", {}, _default_settings, r"_(mca|dxp)\d_"),
    (
        "vortex_xspress3_me4",
        "VortexXspress34",
        {},
        _vortex_setup([1]),
        _DESELECTED_XSPRESS_ROI,
    ),
    (
        "vortex_xspress3_me7",
        "VortexXspress37",
        {},
        _vortex_setup([1]),
        _DESELECTED_XSPRESS_ROI,
    ),
    (
        "vortex_dante_me4",
        "VortexDante4",
        {},
        _vortex_setup([0]),
        _DESELECTED_DANTE_ROI,
    ),
    (
        "vortex_dante_me1",
        "VortexDante1",
        {},
        _vortex_setup([0]),
        _DESELECTED_DANTE_ROI,
    ),
    ("ad_lambda", "LambdaDetector", {"ioc_files_root": "/a"}, _no_setup, None),
    ("ad_eiger1M", "Eiger1MDetector", {}, _no_setup, None),
    ("ad_vimba", "VimbaDetector", {}, _no_setup, None),
    (
        "ad_lightfield",
        "LightFieldDetector",
        {"ioc_files_root": "/a"},
        _no_setup,
        None,
    ),
]


def _make(module, cls, kwargs, setup):
    """Instantiate a fake device and apply its runtime kinds."""
    pytest.importorskip("apstools.devices")
    mod = importlib.import_module(f"id4_common.devices.{module}")
    dev = make_fake_device(getattr(mod, cls))("x:", name="dev", **kwargs)
    setup(dev)
    return dev


@pytest.mark.parametrize(
    "module, cls, kwargs, setup, allowed",
    DEVICES,
    ids=[f"{m}.{c}" for m, c, *_ in DEVICES],
)
def test_no_hidden_signals(module, cls, kwargs, setup, allowed):
    """No normal signal is hidden by a config parent."""
    dev = _make(module, cls, kwargs, setup)
    lost = find_unrecorded_signals(dev)
    if allowed:
        lost = [name for name in lost if not re.search(allowed, name)]
    assert lost == []


def _config_names(dev):
    """Names of the signals ``read_configuration()`` reaches."""
    return {sig.name for sig in _reached_signals(dev, Kind.config)}


def test_ad_roi_bounds_in_configuration():
    """AD ROI plugin bounds land in the configuration (#72)."""
    dev = _make(
        "ad_lambda", "LambdaDetector", {"ioc_files_root": "/a"}, _no_setup
    )
    config = _config_names(dev)
    for name in ("min_xyz_min_x", "min_xyz_min_y", "size_x", "size_y"):
        assert f"dev_roi1_{name}" in config


def test_xspress_deselected_roi_bounds_in_configuration():
    """Deselected Xspress3 ROIs keep their bounds in the configuration."""
    dev = _make(
        "vortex_xspress3_me4", "VortexXspress34", {}, _vortex_setup([1])
    )
    config = _config_names(dev)
    for roi in (1, 2):
        assert f"dev_stats1_roi{roi}_roi_startx" in config
        assert f"dev_stats1_roi{roi}_roi_name" in config


def test_dante_roi_bounds_in_configuration():
    """Dante per-channel ROI bounds land in the configuration (#72)."""
    dev = _make("vortex_dante_me4", "VortexDante4", {}, _vortex_setup([0]))
    config = _config_names(dev)
    for roi in (0, 1):
        assert f"dev_mcas_mca1_rois_roi{roi}_lo_chan" in config
        assert f"dev_mcas_mca1_rois_roi{roi}_hi_chan" in config


def test_diffractometer_records_wavelength():
    """The beam wavelength/energy are read, not hidden by the beam kind."""
    try:
        mod = importlib.import_module("id4_common.devices.sim_diffractometer")
    except ImportError as exc:  # hkl (Linux-only) missing
        pytest.skip(f"sim diffractometer unavailable: {exc}")
    dev = mod.SimDiffractometer("", name="dev")
    read = {sig.name for sig in _reached_signals(dev, Kind.normal)}
    assert {"dev_beam_wavelength", "dev_beam_energy"} <= read
