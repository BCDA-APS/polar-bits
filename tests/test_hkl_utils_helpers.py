"""hkl_utils helpers must not move motors, hide errors, or hide a stale solver.

Report item 4.8 (huber_euler wrong positions, 2026-10-31):

- ``compute_UB`` used ``Sync_UB_Matrix``, which moved the psi partner's
  real axes -- the same EPICS motors as the diffractometer's -- to their
  current positions on every call;
- ``wh`` swallowed every exception;
- ``wh`` and ``ca`` only ever showed the beamline wavelength, never the one
  the solver was using, which is what made the incident invisible.

Fakes stand in for the diffractometers, so none of this needs libhkl.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

PSI_MODE = "psi constant horizontal"
OTHER_MODE = "4-circles bissecting horizontal"


class FakeLattice(SimpleNamespace):
    """Six lattice constants."""


class FakePsiCore:
    """Per-mode extras, as hklpy2's Core keeps them."""

    def __init__(self):
        self.modes = [OTHER_MODE, PSI_MODE]
        self.mode = OTHER_MODE
        self._extras = {
            OTHER_MODE: {},
            PSI_MODE: {"h2": 0.0, "k2": 0.0, "l2": 1.0, "psi": 25.0},
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


class NoMoveAxis:
    """A real axis that must not be commanded."""

    position = 10.0

    def move(self, *args, **kwargs):
        raise AssertionError("a real motor was commanded to move")


def _lattice(a):
    return FakeLattice(a=a, b=a, c=a, alpha=90.0, beta=90.0, gamma=90.0)


def _diffractometer(name, a, ub, core):
    device = SimpleNamespace(
        name=name,
        sample=SimpleNamespace(lattice=_lattice(a), UB=ub),
        core=core,
        real_axis_names=["mu", "gamma"],
    )
    device.mu = NoMoveAxis()
    device.gamma = NoMoveAxis()
    return device


# --- compute_UB's psi copy --------------------------------------------------


def test_sync_psi_copies_without_moving(hkl_utils_module, capsys):
    source = _diffractometer(
        "huber_euler",
        3.91,
        [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]],
        SimpleNamespace(all_extras={"h2": 1.0, "k2": 1.0, "l2": 0.0}),
    )
    target = _diffractometer(
        "huber_euler_psi", 1.0, [[0, 0, 0]] * 3, FakePsiCore()
    )

    hkl_utils_module._sync_psi(source, target)

    assert target.sample.lattice.a == 3.91
    assert target.sample.UB == source.sample.UB
    # The reference lands in the psi mode; the target's own psi is kept.
    assert target.core._extras[PSI_MODE] == {
        "h2": 1.0,
        "k2": 1.0,
        "l2": 0.0,
        "psi": 25.0,
    }
    assert target.core.mode == OTHER_MODE
    assert "Copy UB from huber_euler to huber_euler_psi" in (
        capsys.readouterr().out
    )


def test_sync_psi_without_a_reference_copies_only_the_sample(
    hkl_utils_module,
):
    source = _diffractometer(
        "huber_euler", 3.91, [[2.0] * 3] * 3, SimpleNamespace(all_extras={})
    )
    target = _diffractometer(
        "huber_euler_psi", 1.0, [[0.0] * 3] * 3, FakePsiCore()
    )

    hkl_utils_module._sync_psi(source, target)

    assert target.sample.UB == source.sample.UB
    assert target.core._extras[PSI_MODE]["l2"] == 1.0


def test_the_ub_sync_signal_is_gone():
    """Nothing uses it any more; it would only collect dead subscriptions."""
    pytest.importorskip("gi", reason="polar_diffractometer needs libhkl")
    from id4_common.devices import polar_diffractometer

    assert not hasattr(polar_diffractometer, "UBMatrixSignal")
    assert "_ub_sync" not in (
        polar_diffractometer.DiffractometerCoreMixin.component_names
    )


# --- wh shows its errors ----------------------------------------------------


def test_wh_prints_the_traceback(hkl_utils_module, monkeypatch, capsys):
    def broken():
        raise RuntimeError("solver exploded")

    monkeypatch.setattr(hkl_utils_module, "_wh", broken)

    assert repr(hkl_utils_module.wh) == ""
    assert "RuntimeError: solver exploded" in capsys.readouterr().err


# --- the solver's wavelength ------------------------------------------------


class FakeCore:
    """The bits of hklpy2's Core that ca() and the staleness check use."""

    def __init__(self, solver_wavelength, solutions=()):
        self.solver = SimpleNamespace(wavelength=solver_wavelength)
        self.solutions = list(solutions)
        self.log = []

    def update_solver(self, wavelength=None):
        self.log.append(("update_solver", wavelength))

    def forward(self, pseudos, wavelength=None):
        self.log.append(("forward", wavelength))
        return self.solutions


def _beamline(solver_wavelength, beam_wavelength=4.1774, deadband=1.24e-5):
    return SimpleNamespace(
        name="huber_euler",
        core=FakeCore(solver_wavelength),
        beam=SimpleNamespace(
            wavelength=SimpleNamespace(get=lambda: beam_wavelength),
            energy=SimpleNamespace(get=lambda: 12.398 / beam_wavelength),
            wavelength_deadband=SimpleNamespace(get=lambda: deadband),
        ),
    )


def test_stale_solver_wavelength_tolerates_the_deadband(hkl_utils_module):
    check = hkl_utils_module._stale_solver_wavelength
    assert check(_beamline(4.1774 + 2.0e-5)) is None
    assert check(_beamline(2.2140)) == 2.2140


def test_ca_reports_a_stale_solver_before_resetting_it(
    hkl_utils_module, monkeypatch, capsys
):
    device = _beamline(2.2140)  # the logbook: 5.6 keV in the solver
    monkeypatch.setattr(hkl_utils_module, "get_diffractometer", lambda: device)

    hkl_utils_module.ca(1, 1, 0)

    out = capsys.readouterr().out
    assert "WARNING: the hkl solver was at 2.2140" in out
    assert "No solutions" in out
    # Flushed before the check, then reset to the beamline in the finally.
    assert device.core.log == [
        ("update_solver", None),
        ("forward", 4.1774),
        ("update_solver", 4.1774),
    ]


def test_ca_is_quiet_when_the_solver_is_in_sync(
    hkl_utils_module, monkeypatch, capsys
):
    device = _beamline(4.1774)
    monkeypatch.setattr(hkl_utils_module, "get_diffractometer", lambda: device)

    hkl_utils_module.ca(1, 1, 0)

    assert "WARNING" not in capsys.readouterr().out
