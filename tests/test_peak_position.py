"""Tests for id4_common.plans.peak_position (issue #59)."""

from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pytest


# Stub the bluesky.plan_stubs.null import if bluesky isn't installed.  The
# real null() returns a single Msg("null"); for unit tests it's enough that
# it's an iterable/generator.
def _ensure_bluesky_stub():
    try:
        import bluesky.plan_stubs  # noqa: F401
    except ImportError:
        import types

        bluesky = types.ModuleType("bluesky")
        plan_stubs = types.ModuleType("bluesky.plan_stubs")

        def null():
            yield None

        plan_stubs.null = null
        bluesky.plan_stubs = plan_stubs
        sys.modules["bluesky"] = bluesky
        sys.modules["bluesky.plan_stubs"] = plan_stubs


_ensure_bluesky_stub()


# ---------------------------------------------------------------------------
# Synthetic data builders
# ---------------------------------------------------------------------------


def _gauss(x, mu, sigma, amp=1.0):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def _make_1d_run(motor_name, x, det_name, y, plan_name="ascan", scan_id=42):
    """Build a mock catalog run with a primary stream that returns x, y."""
    table = SimpleNamespace()
    setattr(table, motor_name, SimpleNamespace(values=np.asarray(x)))
    setattr(table, det_name, SimpleNamespace(values=np.asarray(y)))
    # `run.primary.read()` is called as a method; patch with a Mock returning
    # something that supports attribute access ``table[<key>].values``.
    primary = MagicMock()
    primary.read.return_value = _DictTable(
        {motor_name: np.asarray(x), det_name: np.asarray(y)}
    )
    run = SimpleNamespace(
        metadata={
            "start": {
                "scan_id": scan_id,
                "plan_name": plan_name,
                "motors": [motor_name],
                "hints": {"detectors": [det_name]},
            },
            "stop": {"time": datetime.now().timestamp()},
        },
        primary=primary,
    )
    return run


def _make_2d_grid_run(
    m1_name,
    m2_name,
    m1_vals,
    m2_vals,
    det_name,
    img,
    scan_id=43,
    plan_name="grid_scan",
):
    """Mock a grid_scan run.  ``img`` has shape (len(m1_vals), len(m2_vals))."""
    flat_m1 = np.repeat(m1_vals, len(m2_vals))
    flat_m2 = np.tile(m2_vals, len(m1_vals))
    flat_det = img.reshape(-1)
    primary = MagicMock()
    primary.read.return_value = _DictTable(
        {m1_name: flat_m1, m2_name: flat_m2, det_name: flat_det}
    )
    run = SimpleNamespace(
        metadata={
            "start": {
                "scan_id": scan_id,
                "plan_name": plan_name,
                "motors": [m1_name, m2_name],
                "shape": [len(m1_vals), len(m2_vals)],
                "hints": {"detectors": [det_name]},
            },
            "stop": {"time": datetime.now().timestamp()},
        },
        primary=primary,
    )
    return run


class _DictTable:
    """Minimal stand-in for the xarray Dataset returned by run.primary.read()."""

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return SimpleNamespace(values=np.asarray(self._data[key]))

    def __contains__(self, key):
        return key in self._data


@pytest.fixture
def fresh_module(monkeypatch):
    """Load id4_common.plans.peak_position in isolation (skip the heavy
    package ``__init__.py``) with stubbed ``cat`` / ``mv``.

    Pre-stubs ``id4_common.plans`` and ``id4_common.plans.move_plans`` in
    ``sys.modules`` so ``import id4_common.plans.peak_position`` uses
    ``peak_position.py`` from disk without re-running the package
    ``__init__`` (which pulls in dichro_stream, _local_scan_utils, etc.).
    """
    import pathlib
    import types

    sys.modules.pop("id4_common.plans.peak_position", None)
    sys.modules.pop("id4_common.plans", None)
    sys.modules.pop("id4_common.plans.move_plans", None)

    plans_dir = pathlib.Path(__file__).resolve().parent.parent / (
        "src/id4_common/plans"
    )
    plans_pkg = types.ModuleType("id4_common.plans")
    plans_pkg.__path__ = [str(plans_dir)]
    sys.modules["id4_common.plans"] = plans_pkg

    move_calls: list[tuple] = []

    def fake_mv(*args, **kwargs):
        move_calls.append((args, kwargs))
        if False:  # pragma: no cover - keep as generator
            yield None
        return None

    move_plans_stub = types.ModuleType("id4_common.plans.move_plans")
    move_plans_stub.mv = fake_mv
    sys.modules["id4_common.plans.move_plans"] = move_plans_stub

    fake_cat = {}

    def _set_run(scan_id, run):
        fake_cat[scan_id] = run
        fake_cat[-1] = run

    sys.modules["id4_common.utils.run_engine"].cat = fake_cat

    import id4_common.plans.peak_position as ppm

    return ppm, _set_run, move_calls


# ---------------------------------------------------------------------------
# Helpers — diagnostic
# ---------------------------------------------------------------------------


def test_1d_gaussian_stats(fresh_module):
    ppm, set_run, _ = fresh_module
    x = np.linspace(0, 10, 401)
    y = _gauss(x, mu=5.0, sigma=1.0)
    set_run(-1, _make_1d_run("m1", x, "det1", y))

    result = ppm.peak_pos(-1)

    assert result["shape"] == (401,)
    assert result["axes"] == ["m1"]
    assert abs(result["com"]["det1"] - 5.0) < 0.05
    assert abs(result["cen"]["det1"] - 5.0) < 0.05
    x_max, y_max = result["max"]["det1"]
    assert abs(x_max - 5.0) < 0.05
    assert abs(y_max - 1.0) < 1e-3
    expected_fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0))  # 2.355 for sigma=1
    assert abs(result["fwhm"]["det1"] - expected_fwhm) < 0.1


def test_1d_asymmetric_cen_differs_from_com(fresh_module):
    """An asymmetric peak: cen (FWHM midpoint) ≠ com (centroid)."""
    ppm, set_run, _ = fresh_module
    x = np.linspace(0, 10, 401)
    # Sum of two Gaussians, off-centre, to get an asymmetric profile.
    y = _gauss(x, mu=4.0, sigma=0.4, amp=1.0) + _gauss(
        x, mu=4.5, sigma=2.0, amp=0.5
    )
    set_run(-1, _make_1d_run("m1", x, "det1", y))

    result = ppm.peak_pos(-1)
    assert result["com"]["det1"] != pytest.approx(
        result["cen"]["det1"], abs=0.05
    )


def test_2d_gaussian_stats(fresh_module):
    ppm, set_run, _ = fresh_module
    m1 = np.linspace(-5, 5, 50)
    m2 = np.linspace(-5, 5, 60)
    xx, yy = np.meshgrid(m1, m2, indexing="ij")
    img = _gauss(xx, 1.5, 1.0) * _gauss(yy, -2.0, 1.0)
    set_run(-1, _make_2d_grid_run("m1", "m2", m1, m2, "det1", img))

    result = ppm.peak_pos(-1)

    assert result["shape"] == (50, 60)
    assert result["axes"] == ["m1", "m2"]
    com_m1, com_m2 = result["com"]["det1"]
    assert abs(com_m1 - 1.5) < 0.3
    assert abs(com_m2 - (-2.0)) < 0.3
    max_m1, max_m2, max_h = result["max"]["det1"]
    assert abs(max_m1 - 1.5) < 0.3
    assert abs(max_m2 - (-2.0)) < 0.3
    assert abs(max_h - 1.0) < 0.05
    fw_m1, fw_m2 = result["fwhm"]["det1"]
    expected = 2.0 * np.sqrt(2.0 * np.log(2.0))
    assert abs(fw_m1 - expected) < 0.2
    assert abs(fw_m2 - expected) < 0.2


def test_grid_shape_helper(fresh_module):
    ppm, _, _ = fresh_module
    m1 = np.array([0.0, 1.0, 2.0])
    m2 = np.array([10.0, 20.0, 30.0, 40.0])
    table = _DictTable(
        {
            "m1": np.repeat(m1, 4),
            "m2": np.tile(m2, 3),
            "det1": np.zeros(12),
        }
    )
    motors, shape = ppm._grid_shape({"motors": ["m1", "m2"]}, table)
    assert motors == ["m1", "m2"]
    assert shape == (3, 4)


def test_grid_shape_prefers_start_shape_when_motors_are_constant(fresh_module):
    """Step below motor resolution -> readbacks all equal; trust start['shape']."""
    ppm, _, _ = fresh_module
    table = _DictTable(
        {
            "m1": np.full(9, -0.5501),
            "m2": np.full(9, 0.2471),
            "det1": np.zeros(9),
        }
    )
    motors, shape = ppm._grid_shape(
        {"motors": ["m1", "m2"], "shape": [3, 3]}, table
    )
    assert motors == ["m1", "m2"]
    assert shape == (3, 3)


def test_grid_shape_falls_back_when_start_shape_inconsistent(fresh_module):
    """If start['shape'] doesn't match the table length, fall back to unique."""
    ppm, _, _ = fresh_module
    m1 = np.array([0.0, 1.0, 2.0])
    m2 = np.array([10.0, 20.0, 30.0, 40.0])
    table = _DictTable(
        {
            "m1": np.repeat(m1, 4),
            "m2": np.tile(m2, 3),
            "det1": np.zeros(12),
        }
    )
    motors, shape = ppm._grid_shape(
        {"motors": ["m1", "m2"], "shape": [99, 99]}, table
    )
    assert shape == (3, 4)


def test_grid_shape_handles_noisy_readbacks_with_start_shape(fresh_module):
    """Encoder noise -> more unique readbacks than grid points; trust start."""
    ppm, _, _ = fresh_module
    # 3x3 grid where every readback has small encoder noise — np.unique would
    # report (5, 4) instead of (3, 3) and silently corrupt the result.
    table = _DictTable(
        {
            "m1": np.array(
                [
                    -0.5511,
                    -0.5511,
                    -0.5512,
                    -0.5511,
                    -0.5511,
                    -0.5510,
                    -0.5491,
                    -0.5490,
                    -0.5491,
                ]
            ),
            "m2": np.array(
                [
                    0.2463,
                    0.2470,
                    0.2480,
                    0.2462,
                    0.2470,
                    0.2480,
                    0.2462,
                    0.2470,
                    0.2480,
                ]
            ),
            "det1": np.zeros(9),
        }
    )
    _, shape = ppm._grid_shape({"motors": ["m1", "m2"], "shape": [3, 3]}, table)
    assert shape == (3, 3)


def test_grid_axes_averages_through_encoder_noise(fresh_module):
    """Mean-of-grid must collapse noisy readbacks to one value per grid point."""
    ppm, _, _ = fresh_module
    table = _DictTable(
        {
            "m1": np.array(
                [
                    -0.5511,
                    -0.5511,
                    -0.5512,
                    -0.5511,
                    -0.5511,
                    -0.5510,
                    -0.5491,
                    -0.5490,
                    -0.5491,
                ]
            ),
            "m2": np.array(
                [
                    0.2463,
                    0.2470,
                    0.2480,
                    0.2462,
                    0.2470,
                    0.2480,
                    0.2462,
                    0.2470,
                    0.2480,
                ]
            ),
        }
    )
    axes = ppm._grid_axes(["m1", "m2"], (3, 3), {}, table)
    assert len(axes) == 2
    assert axes[0].shape == (3,)
    assert axes[1].shape == (3,)
    # Three distinct outer (m1) blocks averaged: ~-0.5511, -0.5511, -0.5491
    np.testing.assert_allclose(
        axes[0], [-0.55113, -0.55110, -0.54907], atol=1e-4
    )
    # Three distinct inner (m2) columns averaged: ~0.2462, 0.2470, 0.2480
    np.testing.assert_allclose(axes[1], [0.24623, 0.24703, 0.24803], atol=1e-4)


def test_grid_axes_rejects_snake_axes(fresh_module):
    """snake_axes=True would mix forward/reverse traversals; raise instead."""
    ppm, _, _ = fresh_module
    table = _DictTable(
        {"m1": np.zeros(9), "m2": np.zeros(9)},
    )
    with pytest.raises(NotImplementedError, match="snake_axes"):
        ppm._grid_axes(["m1", "m2"], (3, 3), {"snake_axes": True}, table)


def test_grid_shape_raises_when_inference_inconsistent(fresh_module):
    """No start['shape'] AND noisy readbacks -> explicit error, not wrong data."""
    ppm, _, _ = fresh_module
    table = _DictTable(
        {
            "m1": np.linspace(0, 1, 9),  # 9 unique
            "m2": np.linspace(0, 1, 9),  # 9 unique
            "det1": np.zeros(9),
        }
    )
    with pytest.raises(ValueError, match="Cannot infer grid shape"):
        ppm._grid_shape({"motors": ["m1", "m2"]}, table)


def test_pix_to_motor_helper(fresh_module):
    ppm, _, _ = fresh_module
    m1 = np.array([0.0, 1.0, 2.0])
    m2 = np.array([10.0, 20.0, 30.0, 40.0])
    # idx (1.5, 0.0) -> (0.5*1+0.5*2, 10) = (1.5, 10)
    out = ppm._pix_to_motor((1.5, 0.0), [m1, m2])
    assert out == pytest.approx((1.5, 10.0))


# ---------------------------------------------------------------------------
# Move plans — single-axis 1D
# ---------------------------------------------------------------------------


def test_cen_1d_emits_single_mv(fresh_module, monkeypatch):
    ppm, set_run, calls = fresh_module
    x = np.linspace(0, 10, 401)
    y = _gauss(x, mu=5.0, sigma=1.0)
    set_run(-1, _make_1d_run("m1", x, "det1", y))

    fake_motor = MagicMock(name="m1")
    fake_motor.name = "m1"
    fake_motor.position = 0.0
    monkeypatch.setattr(
        ppm, "oregistry", MagicMock(find=lambda n, **k: fake_motor)
    )

    list(ppm.cen(positioner=fake_motor, confirm=False))

    assert len(calls) == 1
    args, _kw = calls[0]
    assert args[0] is fake_motor
    assert abs(args[1] - 5.0) < 0.05


# ---------------------------------------------------------------------------
# Move plans — 2D grid
# ---------------------------------------------------------------------------


def test_cen_grid_default_moves_both_motors(fresh_module, monkeypatch):
    ppm, set_run, calls = fresh_module
    m1 = np.linspace(-5, 5, 50)
    m2 = np.linspace(-5, 5, 60)
    xx, yy = np.meshgrid(m1, m2, indexing="ij")
    img = _gauss(xx, 1.5, 1.0) * _gauss(yy, -2.0, 1.0)
    set_run(-1, _make_2d_grid_run("m1", "m2", m1, m2, "det1", img))

    motors_db = {}
    for nm in ("m1", "m2"):
        m = MagicMock(name=nm)
        m.name = nm
        m.position = 0.0
        motors_db[nm] = m
    monkeypatch.setattr(
        ppm, "oregistry", MagicMock(find=lambda n, **k: motors_db[n])
    )

    list(ppm.cen(confirm=False))

    assert len(calls) == 1
    args, _kw = calls[0]
    # Expect mv(m1_dev, v1, m2_dev, v2) — 4 positional args.
    assert len(args) == 4
    assert args[0] is motors_db["m1"]
    assert args[2] is motors_db["m2"]
    # FWHM-region centroid should land near the true peak (1.5, -2.0).
    assert abs(args[1] - 1.5) < 0.3
    assert abs(args[3] - (-2.0)) < 0.3


def test_cen_grid_with_single_positioner_projects_to_1d(
    fresh_module, monkeypatch
):
    ppm, set_run, calls = fresh_module
    m1 = np.linspace(-5, 5, 50)
    m2 = np.linspace(-5, 5, 60)
    xx, yy = np.meshgrid(m1, m2, indexing="ij")
    img = _gauss(xx, 1.5, 1.0) * _gauss(yy, -2.0, 1.0)
    set_run(-1, _make_2d_grid_run("m1", "m2", m1, m2, "det1", img))

    fake_m1 = MagicMock(name="m1")
    fake_m1.name = "m1"
    fake_m1.position = 0.0
    monkeypatch.setattr(
        ppm, "oregistry", MagicMock(find=lambda n, **k: fake_m1)
    )

    list(ppm.cen(positioner=fake_m1, confirm=False))

    assert len(calls) == 1
    args, _kw = calls[0]
    assert args[0] is fake_m1
    assert len(args) == 2  # single (motor, value) pair
    assert abs(args[1] - 1.5) < 0.3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_psiscan_is_rejected(fresh_module):
    ppm, set_run, calls = fresh_module
    x = np.linspace(0, 1, 5)
    y = np.zeros(5)
    run = _make_1d_run("m1", x, "det1", y, plan_name="psiscan")
    set_run(-1, run)

    list(ppm.cen(confirm=False))
    assert calls == []


def test_old_scan_prompt(fresh_module, monkeypatch):
    """When confirm=True and the scan stop is > 5 min ago, prompt before moving."""
    ppm, set_run, calls = fresh_module
    x = np.linspace(0, 10, 401)
    y = _gauss(x, mu=5.0, sigma=1.0)
    run = _make_1d_run("m1", x, "det1", y)
    # Backdate stop to 1 hour ago.
    run.metadata["stop"]["time"] = datetime.now().timestamp() - 3600
    set_run(-1, run)

    fake_motor = MagicMock(name="m1")
    fake_motor.name = "m1"
    fake_motor.position = 0.0
    monkeypatch.setattr(
        ppm, "oregistry", MagicMock(find=lambda n, **k: fake_motor)
    )

    # User answers N -> no motion.
    with patch("builtins.input", return_value="N"):
        list(ppm.cen(positioner=fake_motor, confirm=True))
    assert calls == []

    # User answers Y -> motion happens.
    with patch("builtins.input", return_value="Y"):
        list(ppm.cen(positioner=fake_motor, confirm=True))
    assert len(calls) == 1
