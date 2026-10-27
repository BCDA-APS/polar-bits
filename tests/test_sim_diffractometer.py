"""Simulated POLAR diffractometers.

``hkl_soleil`` needs libhkl (through ``gi``), which has no macOS build and is
not in the CI environment, so these tests skip there and only run on a Linux
host with ``hkl`` installed.
"""

import math

import numpy
import pytest

try:
    from id4_common.devices import sim_diffractometer
except (ImportError, ValueError) as exc:  # gi missing or Hkl typelib missing
    pytest.skip(f"hkl_soleil is not available: {exc}", allow_module_level=True)

from ophyd import SoftPositioner

#: hc in keV*angstrom
HC = 12.398_419_843_320_026


class _Registry:
    """Stand-in for ``oregistry`` holding the devices of one test."""

    def __init__(self, *devices):
        self._devices = {d.name: d for d in devices}

    def find(self, name, allow_none=False):
        return self._devices.get(name)


@pytest.fixture
def sim():
    """A simulated diffractometer."""
    return sim_diffractometer.SimDiffractometer("", name="sim_euler")


@pytest.fixture
def sim_psi(sim, monkeypatch):
    """The psi partner of ``sim``, mirroring its motors."""
    psi = sim_diffractometer.SimDiffractometerPSI("", name="sim_euler_psi")
    monkeypatch.setattr(sim_diffractometer, "oregistry", _Registry(sim, psi))
    psi._post_connect_setup()
    return psi


def test_is_simulator(sim):
    """Every real axis is soft, so hklpy2 classifies it as a simulator."""
    assert sim.is_simulator
    assert sim.real_axis_names == "tau mu chi phi gamma delta".split()
    for axis in sim.real_axis_names:
        assert isinstance(getattr(sim, axis), SoftPositioner)


def test_energy_is_user_defined(sim):
    """Energy is a soft signal coupled to the wavelength."""
    assert sim.beam.energy.get() == pytest.approx(10.0)
    sim.beam.energy.put(8.9)
    assert sim.beam.wavelength.get() == pytest.approx(HC / 8.9, rel=1e-6)


def test_analyzer_follows_simulated_energy(sim):
    """The analyzer is soft, untracked, and uses the simulated beam."""
    ana = sim.ana
    assert "track_energy" not in ana._ophyd_labels_
    assert ana.tth_detector_distance.get() == 1000.0

    sim.beam.energy.put(8.9)
    assert ana.beamline_energy == pytest.approx(8.9)

    ana.d_spacing.put(1.0)
    ana.energy.move(8.0)
    theta = math.degrees(math.asin(HC / 8.0 / 2 / 1.0))
    assert ana.th.position == pytest.approx(theta, rel=1e-4)
    assert ana.energy.position == pytest.approx(8.0, rel=1e-4)


def test_analyzer_set_energy_redefines_positions(sim):
    """Calibration sets the soft positions instead of EPICS offsets."""
    ana = sim.ana
    ana.d_spacing.put(1.0)
    ana.set_energy(9.0)
    assert ana.th.position == pytest.approx(ana.convert_energy_to_theta(9.0))
    assert ana.tth_trans.position == pytest.approx(
        ana.convert_energy_to_tth_trans(9.0)
    )
    ana.release_calibration()
    ana.ath_reset_offset()


def test_psi_partner_mirrors_motors_and_wavelength(sim, sim_psi):
    """The psi device follows its partner's soft motors and wavelength."""
    sim.delta.move(30.0)
    sim.chi.move(12.5)
    assert sim_psi.delta.position == pytest.approx(30.0)
    assert sim_psi.chi.position == pytest.approx(12.5)

    sim.beam.energy.put(7.5)
    assert sim_psi.beam.wavelength.get() == pytest.approx(HC / 7.5, rel=1e-6)


def test_psi_mirror_does_not_duplicate_on_reconnect(sim, sim_psi):
    """Calling the connection hook again replaces the subscriptions."""
    n_subs = len(sim_psi._mirror_subs)
    sim_psi._post_connect_setup()
    assert len(sim_psi._mirror_subs) == n_subs


@pytest.fixture
def real(monkeypatch, sim):
    """A second simulator standing in for the real diffractometer."""
    real = sim_diffractometer.SimDiffractometer("", name="huber_euler")
    sim.real_diffractometer = "huber_euler"
    monkeypatch.setattr(sim_diffractometer, "oregistry", _Registry(sim, real))
    return real


def test_sync_needs_a_real_diffractometer(sim):
    """Without a configured or passed device the sync refuses clearly."""
    with pytest.raises(ValueError, match="no real diffractometer"):
        sim.sync_energy()


def test_sync_motors(sim, real):
    """Diffractometer axes, analyzer motors and crystal are copied."""
    real.delta.move(25.0)
    real.mu.move(1.5)
    real.ana.eta.move(3.0)
    real.ana.d_spacing.put(1.5)
    real.ana.crystal.put("Cu_220")
    sim.sync_motors()
    assert sim.delta.position == pytest.approx(25.0)
    assert sim.mu.position == pytest.approx(1.5)
    assert sim.ana.eta.position == pytest.approx(3.0)
    assert sim.ana.d_spacing.get() == 1.5
    assert sim.ana.crystal.get() == "Cu_220"


def test_sync_energy(sim, real):
    """The beam energy is copied."""
    real.beam.energy.put(7.1)
    sim.sync_energy()
    assert sim.beam.energy.get() == pytest.approx(7.1)


def test_sync_setup(sim, real):
    """Samples, reflections, UB and mode are copied; positions are not."""
    real.add_sample("si", 5.431)
    real.add_reflection(
        (0, 0, 4),
        dict(tau=0, mu=0, chi=0, phi=0, gamma=0, delta=69.0),
        name="r004",
    )
    real.core.mode = real.core.modes[-1]
    real.delta.move(10.0)

    sim.sync_setup()
    assert sim.sample.name == "si"
    assert sim.sample.lattice.a == pytest.approx(5.431)
    assert "r004" in sim.sample.reflections
    assert numpy.allclose(sim.sample.UB, real.sample.UB)
    assert sim.core.mode == real.core.mode
    assert sim.delta.position == pytest.approx(0.0)


def test_sync_all(sim, real):
    """sync_all copies setup, energy and motors."""
    real.add_sample("si", 5.431)
    real.beam.energy.put(9.3)
    real.chi.move(4.0)
    sim.sync_all()
    assert sim.sample.name == "si"
    assert sim.beam.energy.get() == pytest.approx(9.3)
    assert sim.chi.position == pytest.approx(4.0)
