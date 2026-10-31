"""
Simulated polar diffractometer

Geometry-only twins of the POLAR diffractometers. The real axes and the
polarization analyzer motors are ``SoftPositioner`` objects and the beam
energy is a user-defined soft signal, so nothing here talks to EPICS. Set the
energy with ``sim_euler.beam.energy.put(<keV>)``.

To start from the beamline state, copy it from the real diffractometer with
``sync_motors()``, ``sync_energy()``, ``sync_setup()`` (samples, reflections,
UB, constraints, mode) or ``sync_all()``.
"""

import copy
import logging

from apsbits.core.instrument_init import oregistry
from hklpy2 import diffractometer_class_factory
from ophyd import Component
from ophyd import Signal
from ophyd import SoftPositioner

from .hklpy2_workarounds import _ThreadSafeSolverMixin
from .polar_diffractometer import AnalyzerDevice
from .polar_diffractometer import DiffractometerCoreMixin
from .polar_diffractometer import _set_axes_kind

logger = logging.getLogger(__name__)

#: Nominal analyzer two-theta detector distance (mm).
SIM_TTH_DETECTOR_DISTANCE = 1000.0

sim_beam_kwargs = {
    "class": "hklpy2.incident.WavelengthXray",
    "source_type": "Simulated",
    "energy": 10.0,  # keV
    "kind": "config",
}

sim_reals = dict(tau=None, mu=None, gamma=None, delta=None, chi=None, phi=None)


class SimAnalyzerDevice(AnalyzerDevice):
    """
    Polarization analyzer with simulated motors.

    The energy calculations and crystal setup are inherited from
    ``AnalyzerDevice`` and use the parent's simulated beam energy. The
    calibration methods redefine the soft positions instead of writing EPICS
    motor offsets.
    """

    th = Component(SoftPositioner, init_pos=45, labels=("motor",))
    tth_trans = Component(SoftPositioner, init_pos=0, labels=("motor",))

    th_motor = Component(SoftPositioner, init_pos=45, labels=("motor",))
    tth = Component(SoftPositioner, init_pos=90, labels=("motor",))
    eta = Component(SoftPositioner, init_pos=0, labels=("motor",))
    chi = Component(SoftPositioner, init_pos=0, labels=("motor",))

    tth_detector_distance = Component(
        Signal, value=SIM_TTH_DETECTOR_DISTANCE, kind="config"
    )

    def ath_reset_offset(self):
        """No motor offsets to reset in the simulated analyzer."""
        print("Simulated analyzer: no motor offset to reset.")

    def set_energy(self, energy):
        """
        Redefine the Bragg-angle positions to match the given energy (keV).
        """
        theta = self.convert_energy_to_theta(energy)
        self.th._set_position(theta)
        self.th_motor._set_position(theta)
        self.tth_trans._set_position(self.convert_energy_to_tth_trans(energy))

    def release_calibration(self):
        """No calibration offsets to release in the simulated analyzer."""
        print("Simulated analyzer: no calibration offset to release.")


SimDiffractometerBase = diffractometer_class_factory(
    solver="hkl_soleil",
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=sim_reals.copy(),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=sim_beam_kwargs.copy(),
)

_set_axes_kind(SimDiffractometerBase)


# _ThreadSafeSolverMixin is a temporary hklpy2 workaround; drop it from
# the bases when the class is removed.
class SimDiffractometer(
    _ThreadSafeSolverMixin, DiffractometerCoreMixin, SimDiffractometerBase
):
    """
    hklpy2 APS-POLAR diffractometer with simulated motors and analyzer.

    ``real_diffractometer`` names the real diffractometer that the ``sync_*``
    methods copy from (e.g. ``"huber_euler"``).
    """

    # No "track_energy" label: the beamline energy device must not move it.
    ana = Component(SimAnalyzerDevice, "")

    #: Analyzer motors copied by sync_motors.
    _analyzer_axes = ("th", "tth_trans", "th_motor", "tth", "eta", "chi")

    def __init__(self, *args, real_diffractometer=None, **kwargs):
        """Initialize, storing the name of the real diffractometer."""
        super().__init__(*args, **kwargs)
        self.real_diffractometer = real_diffractometer

    def _find_real(self, real_diffractometer=None):
        """Return the real diffractometer to copy from."""
        real = (
            real_diffractometer
            if real_diffractometer is not None
            else self.real_diffractometer
        )
        if real is None:
            raise ValueError(
                f"{self.name} has no real diffractometer to sync from, pass "
                "one (e.g. real_diffractometer='huber_euler')."
            )
        if isinstance(real, str):
            device = oregistry.find(real, allow_none=True)
            if device is None:
                raise ValueError(f"Diffractometer {real!r} is not loaded.")
            return device
        return real

    @staticmethod
    def _copy_positions(source, target, axes, prefix=""):
        """Copy positions of ``axes`` from source to soft target.

        Returns the axes that could not be read from the source.
        """
        skipped = []
        for axis in axes:
            try:
                position = getattr(source, axis).position
            except Exception as exc:
                skipped.append(f"{prefix}{axis} ({exc})")
                continue
            if position is None:
                skipped.append(f"{prefix}{axis} (no position)")
                continue
            getattr(target, axis)._set_position(position)
        return skipped

    def sync_motors(self, real_diffractometer=None):
        """
        Copy the real diffractometer's motor positions into this simulator.

        Copies the six diffractometer axes, the analyzer motors and the
        analyzer crystal setup (``d_spacing``, ``crystal``), so that
        ``ana.energy`` reads as on the real device. Axes that cannot be read
        (e.g. a disconnected IOC) are skipped and reported.

        Parameters
        ----------
        real_diffractometer : str or Diffractometer, optional
            Device to copy from. Defaults to ``self.real_diffractometer``.
        """
        real = self._find_real(real_diffractometer)
        skipped = self._copy_positions(real, self, self.real_axis_names)
        skipped += self._copy_positions(
            real.ana, self.ana, self._analyzer_axes, prefix="ana."
        )
        self.ana.d_spacing.put(real.ana.d_spacing.get())
        self.ana.crystal.put(real.ana.crystal.get())

        print(f"Copied motor positions from {real.name} to {self.name}.")
        if skipped:
            print("Skipped: " + ", ".join(skipped))

    def sync_energy(self, real_diffractometer=None):
        """
        Copy the real beamline energy into this simulator.

        Parameters
        ----------
        real_diffractometer : str or Diffractometer, optional
            Device to copy from. Defaults to ``self.real_diffractometer``.
        """
        real = self._find_real(real_diffractometer)
        self.beam.wavelength.put(real.beam.wavelength.get())
        print(
            f"Copied energy from {real.name} to {self.name}: "
            f"{self.beam.energy.get():.4f} keV."
        )

    def sync_setup(self, real_diffractometer=None):
        """
        Copy the real orientation setup into this simulator.

        Replaces the samples (lattice, reflections, U and UB), the active
        sample, the constraints, the mode, its extras and presets. The psi
        partner (``<name>_psi``) is updated from the real psi partner too,
        when both are loaded. Motor positions and energy are not changed.

        Parameters
        ----------
        real_diffractometer : str or Diffractometer, optional
            Device to copy from. Defaults to ``self.real_diffractometer``.
        """
        real = self._find_real(real_diffractometer)
        _copy_setup(real, self)

        psi = oregistry.find(f"{self.name}_psi", allow_none=True)
        real_psi = oregistry.find(f"{real.name}_psi", allow_none=True)
        if psi is not None and real_psi is not None:
            _copy_setup(real_psi, psi)

        print(
            f"Copied samples, reflections, UB, constraints and mode from "
            f"{real.name} to {self.name} (sample: {self.sample.name})."
        )

    def sync_all(self, real_diffractometer=None):
        """
        Copy the real setup, energy and motor positions into this simulator.

        Parameters
        ----------
        real_diffractometer : str or Diffractometer, optional
            Device to copy from. Defaults to ``self.real_diffractometer``.
        """
        self.sync_setup(real_diffractometer)
        self.sync_energy(real_diffractometer)
        self.sync_motors(real_diffractometer)


def _copy_setup(source, target):
    """Copy the orientation setup of ``source`` into soft ``target``.

    ``source.configuration`` would also read the beam wavelength and the
    auxiliary motors over EPICS, so the target's own configuration is used as
    the template and only the orientation sections are taken from the source.
    """
    core = source.core
    config = target.configuration
    config["samples"] = copy.deepcopy(
        {name: sample._asdict() for name, sample in core._samples.items()}
    )
    config["sample_name"] = core.sample.name
    config["constraints"] = copy.deepcopy(core.constraints._asdict())
    config["axes"]["extra_axes"] = dict(core.all_extras)
    config["presets"] = copy.deepcopy(core._mode_presets)
    target.restore(
        config,
        clear=True,
        restore_constraints=True,
        restore_wavelength=False,
        restore_mode=False,
        restore_samples=True,
        restore_extras=True,
        restore_presets=True,
    )
    target.core.mode = core.mode


SimDiffractometerPSIBase = diffractometer_class_factory(
    solver="hkl_soleil",
    solver_kwargs={"engine": "psi"},
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=sim_reals.copy(),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=sim_beam_kwargs.copy(),
)


# _ThreadSafeSolverMixin is a temporary hklpy2 workaround; drop it from
# the bases when the class is removed.
class SimDiffractometerPSI(_ThreadSafeSolverMixin, SimDiffractometerPSIBase):
    """
    Simulated hklpy2 APS-POLAR diffractometer using the psi engine.

    The real ``*_psi`` devices share motor PVs with their partner. Here the
    partner (same name without ``_psi``) has its own soft motors, so the real
    axes and the wavelength are mirrored from it after connection.
    """

    def __init__(self, *args, **kwargs):
        """Initialize, with no partner subscriptions yet."""
        super().__init__(*args, **kwargs)
        self._mirror_subs = []

    def _post_connect_setup(self):
        """Mirror the partner's real axes and wavelength into this device."""
        self._clear_mirror()
        partner_name = self.name.removesuffix("_psi")
        partner = oregistry.find(partner_name, allow_none=True)
        if partner is None:
            logger.warning(
                "%s: partner %r is not loaded, its motors will not be "
                "mirrored.",
                self.name,
                partner_name,
            )
            return

        for axis in self.real_axis_names:
            source = getattr(partner, axis)
            target = getattr(self, axis)

            def _copy(value=None, _target=target, **kwargs):
                if value is not None:
                    _target._set_position(value)

            _copy(source.position)
            cid = source.subscribe(
                _copy, event_type=source.SUB_READBACK, run=False
            )
            self._mirror_subs.append((source, cid))

        wavelength = partner.beam.wavelength

        def _copy_wavelength(value=None, **kwargs):
            if value is not None:
                self.beam.wavelength.put(value)

        _copy_wavelength(wavelength.get())
        cid = wavelength.subscribe(_copy_wavelength, run=False)
        self._mirror_subs.append((wavelength, cid))

    def _clear_mirror(self):
        """Remove the subscriptions to the partner."""
        for obj, cid in self._mirror_subs:
            obj.unsubscribe(cid)
        self._mirror_subs = []
