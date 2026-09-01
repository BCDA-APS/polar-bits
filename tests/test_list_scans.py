"""Tests for id4_common.plans.list_scans (issue #77)."""

from __future__ import annotations

import pathlib
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest

PLANS_DIR = pathlib.Path(__file__).resolve().parent.parent / (
    "src/id4_common/plans"
)


def _fresh_plans_package():
    """Install a bare ``id4_common.plans`` package in ``sys.modules``.

    Lets a single plan module be imported from disk without running the
    package ``__init__`` (which pulls in every other plan).  Same trick as
    the ``fresh_module`` fixture in ``test_peak_position.py``.
    """
    for name in list(sys.modules):
        if name.startswith("id4_common.plans"):
            del sys.modules[name]
    pkg = types.ModuleType("id4_common.plans")
    pkg.__path__ = [str(PLANS_DIR)]
    sys.modules["id4_common.plans"] = pkg
    return pkg


# ---------------------------------------------------------------------------
# _args_contains — the numpy-array regression (real _local_scan_utils)
# ---------------------------------------------------------------------------


class _Dev:
    """Stand-in for an ophyd device.

    A plain object, deliberately not a ``MagicMock``: mocks are iterable,
    which makes numpy treat them as length-0 sequences and changes the
    comparison error.  Real ophyd devices are not iterable and inherit
    ``object.__eq__``, which is what these tests are about.
    """

    def __init__(self, name):
        self.name = name


@pytest.fixture
def scan_utils():
    """Load the real ``_local_scan_utils`` with its heavy deps stubbed."""
    _fresh_plans_package()

    # Module-level: HDF1_NAME_FORMAT = Path(iconfig["AREA_DETECTOR"][...])
    from apsbits.utils.config_loaders import get_config

    get_config().setdefault(
        "AREA_DETECTOR", {"HDF5_FILE_TEMPLATE": "%s/%s_%4.4d"}
    )

    hklpy2 = types.ModuleType("hklpy2")
    user = types.ModuleType("hklpy2.user")
    user.get_diffractometer = MagicMock(return_value=None)
    hklpy2.user = user
    sys.modules.setdefault("hklpy2", hklpy2)
    sys.modules.setdefault("hklpy2.user", user)

    # conftest's dichro_stream stub only carries `dichro`; pr_setup wants
    # more, and _local_scan_utils only tolerates a *missing* pr_setup.
    dichro_mod = sys.modules["id4_common.callbacks.dichro_stream"]
    for _name in ("dichro_bec", "plot_dichro_settings"):
        if not hasattr(dichro_mod, _name):
            setattr(dichro_mod, _name, MagicMock(name=_name))

    for name, attr, value in (
        ("id4_common.utils.counters_class", "counters", MagicMock()),
        ("id4_common.utils.experiment_utils", "experiment", MagicMock()),
        ("id4_common.utils.pr_setup", "pr_setup", MagicMock()),
    ):
        mod = sys.modules.get(name) or types.ModuleType(name)
        setattr(mod, attr, value)
        sys.modules[name] = mod

    import id4_common.plans._local_scan_utils as lsu

    return lsu


def test_args_contains_finds_the_device(scan_utils):
    """A device present in args is found; one that isn't, isn't."""
    motor = _Dev("motor")
    other = _Dev("other")
    args = (motor, [1, 2, 3])

    assert scan_utils._args_contains(args, motor) is True
    assert scan_utils._args_contains(args, other) is False


def test_args_contains_survives_numpy_position_lists(scan_utils):
    """Array-valued args must not raise (issue #77).

    ``list_scan`` puts whole position lists into ``args``.  The previous
    ``device in args`` test broadcast against a numpy array and blew up
    with "truth value of an array ... is ambiguous"; this asserts both
    that the old form really does raise and that the new one doesn't.
    """
    motor = _Dev("motor")
    absent = _Dev("absent")
    args = (motor, np.linspace(0, 1, 11))

    # The bug being guarded against.
    with pytest.raises(ValueError, match="ambiguous"):
        absent in args  # noqa: B015

    assert scan_utils._args_contains(args, absent) is False
    assert scan_utils._args_contains(args, motor) is True


def test_args_contains_uses_identity_not_equality(scan_utils):
    """Two equal-but-distinct objects must not be conflated."""

    class Equalish:
        def __eq__(self, other):
            return True

        __hash__ = None

    a, b = Equalish(), Equalish()
    assert scan_utils._args_contains((a, [1, 2]), b) is False
    assert scan_utils._args_contains((a, [1, 2]), a) is True


# ---------------------------------------------------------------------------
# list_scans — argument parsing
# ---------------------------------------------------------------------------


@pytest.fixture
def list_scans():
    """Load ``list_scans`` with the scan-machinery modules stubbed out."""
    _fresh_plans_package()

    recorded: dict = {"decorators": {}}

    def _passthrough(name):
        def factory(*args, **kwargs):
            recorded["decorators"][name] = (args, kwargs)

            def decorator(func):
                return func

            return decorator

        return factory

    prep = types.ModuleType("id4_common.plans.local_preprocessors")
    for _name in (
        "configure_counts_decorator",
        "extra_devices_decorator",
        "stage_4idg_softglue_decorator",
        "stage_dichro_decorator",
        "stage_magnet911_decorator",
    ):
        setattr(prep, _name, _passthrough(_name))
    sys.modules["id4_common.plans.local_preprocessors"] = prep

    utils = types.ModuleType("id4_common.plans._local_scan_utils")

    def _collect_extras(args):
        recorded["extras_args"] = args
        return []
        yield  # pragma: no cover - keeps this a generator

    utils._collect_extras = _collect_extras
    utils._build_scan_md = lambda *a, **k: {"hints": {"detectors": []}}
    utils._check_magnet911 = lambda args: False
    utils._configure_dichro = lambda dichro: None
    utils._configure_fixq = lambda fixq: None
    utils._default_per_step = lambda *a: None
    utils._hkl_motors = lambda fixq: []
    utils._setup_detectors = lambda time: []
    utils._setup_file_io = lambda dets: ("master.hdf", {}, {})
    utils.flag = types.SimpleNamespace(vortex_sgz=False)

    def _reset_real_motors_decorator(motors):
        def decorator(func):
            return func

        return decorator

    utils.reset_real_motors_decorator = _reset_real_motors_decorator
    sys.modules["id4_common.plans._local_scan_utils"] = utils

    import id4_common.plans.list_scans as mod

    mod._recorded = recorded
    return mod


def test_split_rejects_even_arg_count(list_scans):
    """``motor, list`` without a trailing time is rejected."""
    motor = MagicMock(name="motor")
    with pytest.raises(ValueError, match="multiple of 2 plus 1"):
        list_scans._split_list_scan_args((motor, [1, 2, 3]))


def test_split_rejects_mismatched_list_lengths(list_scans):
    """Every position list must have the same length."""
    m1, m2 = MagicMock(name="m1"), MagicMock(name="m2")
    m1.name, m2.name = "m1", "m2"
    with pytest.raises(ValueError, match="same length"):
        list_scans._split_list_scan_args((m1, [1, 2, 3], m2, [4, 5], 0.5))


def test_split_rejects_scalar_positions(list_scans):
    """A scalar where a list belongs gets a clear message."""
    motor = MagicMock(name="motor")
    motor.name = "motor"
    with pytest.raises(ValueError, match="sized iterable"):
        list_scans._split_list_scan_args((motor, 1.0, 0.5))


def test_split_returns_motors_args_and_time(list_scans):
    """Motors are the even-indexed args; time is peeled off the end."""
    m1, m2 = MagicMock(name="m1"), MagicMock(name="m2")
    scan_args, motors, time = list_scans._split_list_scan_args(
        (m1, [1, 2, 3], m2, [4, 5, 6], 0.25)
    )

    assert motors == [m1, m2]
    assert time == 0.25
    assert scan_args == (m1, [1, 2, 3], m2, [4, 5, 6])


def test_split_accepts_numpy_position_lists(list_scans):
    """numpy arrays are valid position lists (issue #77)."""
    motor = MagicMock(name="motor")
    positions = np.linspace(-1, 1, 7)
    scan_args, motors, time = list_scans._split_list_scan_args(
        (motor, positions, 0.5)
    )

    assert motors == [motor]
    assert time == 0.5
    assert scan_args[1] is positions


def test_split_accepts_a_single_point(list_scans):
    """A one-entry list is a legal (if degenerate) scan."""
    motor = MagicMock(name="motor")
    scan_args, motors, time = list_scans._split_list_scan_args(
        (motor, [42.0], 1.0)
    )
    assert motors == [motor]
    assert scan_args == (motor, [42.0])


# ---------------------------------------------------------------------------
# list_scans — what reaches bluesky
# ---------------------------------------------------------------------------


def _drive(plan):
    """Run a plan generator to completion with a no-op RunEngine."""
    try:
        msg = plan.send(None)
        while True:
            msg = plan.send(None)
            del msg
    except StopIteration:
        return


def test_list_scan_forwards_positions_to_bluesky(list_scans, monkeypatch):
    """The trailing time is stripped before the args reach bluesky."""
    seen: dict = {}

    def fake_bp_list_scan(detectors, *args, per_step=None, md=None):
        seen["detectors"] = detectors
        seen["args"] = args
        seen["md"] = md
        return
        yield  # pragma: no cover - keeps this a generator

    monkeypatch.setattr(list_scans, "bp_list_scan", fake_bp_list_scan)

    motor = MagicMock(name="motor")
    positions = [0.0, 0.5, 1.0]
    _drive(list_scans.list_scan(motor, positions, 0.5, detectors=[]))

    assert seen["args"] == (motor, positions)
    assert seen["md"]["hints"]["scan_type"] == "list_scan"


def test_list_scan_tolerates_numpy_positions_end_to_end(
    list_scans, monkeypatch
):
    """A numpy position list drives the whole plan without raising."""
    seen: dict = {}

    def fake_bp_list_scan(detectors, *args, per_step=None, md=None):
        seen["args"] = args
        return
        yield  # pragma: no cover - keeps this a generator

    monkeypatch.setattr(list_scans, "bp_list_scan", fake_bp_list_scan)

    motor = MagicMock(name="motor")
    positions = np.linspace(0, 1, 5)
    _drive(list_scans.list_scan(motor, positions, 0.5, detectors=[]))

    assert seen["args"][1] is positions


def test_rel_list_scan_sets_its_plan_name(list_scans, monkeypatch):
    """``rel_list_scan`` labels the run so SPEC/analysis can tell them apart."""
    seen: dict = {}

    def fake_bp_list_scan(detectors, *args, per_step=None, md=None):
        seen["md"] = md
        return
        yield  # pragma: no cover - keeps this a generator

    monkeypatch.setattr(list_scans, "bp_list_scan", fake_bp_list_scan)
    # The relative wrappers need real motors; bypass them for this check.
    monkeypatch.setattr(
        list_scans, "reset_positions_decorator", lambda motors: lambda f: f
    )
    monkeypatch.setattr(
        list_scans, "relative_set_decorator", lambda motors: lambda f: f
    )

    motor = MagicMock(name="motor")
    _drive(list_scans.rel_list_scan(motor, [-1, 0, 1], 0.5, detectors=[]))

    assert seen["md"]["plan_name"] == "rel_list_scan"
