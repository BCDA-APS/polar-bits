"""The temporary hklpy2 solver workaround (``_ThreadSafeSolverMixin``).

TEMPORARY: these tests cover a stopgap for hklpy2 problems. Delete this file
together with ``id4_common/devices/hklpy2_workarounds.py`` once hklpy2 is
fixed (see the "Temporary hklpy2 workarounds" section of CLAUDE.md).

Uses hklpy2's pure-Python ``th_tth`` solver, so no libhkl is needed.
"""

import math
import threading

import pytest
from hklpy2 import diffractometer_class_factory
from hklpy2.utils import _SolverDirty
from id4_common.devices.hklpy2_workarounds import _ThreadSafeSolverMixin

ThTthBase = diffractometer_class_factory(solver="th_tth", geometry="TH TTH Q")


class ThTthDiffractometer(_ThreadSafeSolverMixin, ThTthBase):
    """Minimal diffractometer carrying the workaround."""


@pytest.fixture
def diffractometer():
    """A th_tth diffractometer with a clean solver."""
    dev = ThTthDiffractometer("", name="thtth")
    dev.core.update_solver()
    assert dev.core._solver_dirty == _SolverDirty(0)
    return dev


def test_wavelength_change_flags_only_wavelength(diffractometer):
    """A wavelength change no longer forces a full sample re-push."""
    diffractometer.beam.wavelength.put(1.5)
    assert diffractometer.core._solver_dirty == _SolverDirty.WAVELENGTH


def test_wavelength_change_reaches_solver(diffractometer):
    """The next calculation uses the new wavelength."""
    diffractometer.beam.wavelength.put(1.5)
    pos = diffractometer.inverse((10, 20))
    assert diffractometer.core.solver.wavelength == pytest.approx(1.5)
    assert pos.q == pytest.approx(
        4 * math.pi * math.sin(math.radians(10)) / 1.5
    )
    assert diffractometer.core._solver_dirty == _SolverDirty(0)


def test_request_solver_update_true_still_flags_all(diffractometer):
    """The boolean form keeps hklpy2's back-compat meaning."""
    diffractometer.core.request_solver_update(True)
    assert diffractometer.core._solver_dirty == _SolverDirty.ALL


def test_forward_inverse_round_trip(diffractometer):
    """Nested locked calls (forward -> update_solver) do not deadlock."""
    diffractometer.core.request_solver_update(True)
    reals = diffractometer.forward(1.0)
    pos = diffractometer.inverse((reals.th, reals.tth))
    assert pos.q == pytest.approx(1.0)


@pytest.mark.parametrize("name", _ThreadSafeSolverMixin._solver_methods)
def test_core_methods_are_wrapped(diffractometer, name):
    """Every listed Core method goes through the lock."""
    assert hasattr(getattr(diffractometer.core, name), "__wrapped__")


def test_solver_calls_are_serialized(diffractometer):
    """A solver call from another thread waits for the lock holder."""
    done = threading.Event()

    def _inverse():
        diffractometer.core.inverse((10, 20))
        done.set()

    with diffractometer._solver_lock:
        worker = threading.Thread(target=_inverse, daemon=True)
        worker.start()
        assert not done.wait(0.2)
    worker.join(timeout=5)
    assert done.is_set()
