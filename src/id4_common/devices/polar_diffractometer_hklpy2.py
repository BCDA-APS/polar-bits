"""
Polar diffractometer
"""

import math
from pathlib import Path

from hklpy2 import diffractometer_class_factory
from numpy import arcsin
from numpy import pi
from numpy import sin
from numpy import tan
from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import FormattedComponent
from ophyd import Kind
from ophyd import PseudoPositioner
from ophyd import PseudoSingle
from ophyd import Signal
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument
from scipy.constants import Planck
from scipy.constants import speed_of_light

from ..utils.analyzer_utils import calcdhkl
from ..utils.analyzer_utils import check_structure_factor
from .huber_filter import HuberFilter
from .jj_slits import SlitDevice

# Constants
WAVELENGTH_CONSTANT = 12.39
PTTH_MIN_DEGREES = 79
PTTH_MAX_DEGREES = 101
PTH_MIN_DEGREES = 39
PTH_MAX_DEGREES = 51
ANALYZER_LIST_PATH = Path(__file__).parent / "analyzerlist.dat"


class UBMatrixSignal(Signal):
    """
    In-memory ophyd Signal that wraps the UB matrix on the parent diffractometer.

    Reads/writes parent.sample.UB and fires ophyd subscribers on put(), so
    other components can subscribe to UB matrix changes via .subscribe().
    """

    def __init__(self, pv_name, *, parent=None, name=None, **kwargs):
        """Initialize, ignoring the PV name (Component-required, unused here)."""
        super().__init__(name=name, parent=parent, **kwargs)

    def get(self, **kwargs):
        """Return the parent diffractometer's current UB matrix."""
        self._readback = self.parent.sample.UB
        return self._readback

    def put(self, value, *, timestamp=None, force=False, **kwargs):
        """Write the UB matrix back to the parent and notify subscribers."""
        self.parent.sample.UB = value
        super().put(value, timestamp=timestamp, force=force, **kwargs)


class AnalyzerDevice(PseudoPositioner):
    """
    Crystal polarization analyzer with pseudo-energy axis and crystal setup.
    """

    energy = Component(PseudoSingle, limits=(2.6, 34))
    th = Component(EpicsMotor, "pmth", labels=("motor",))
    tth_trans = Component(EpicsMotor, "m25", labels=("motor",))

    _real = ["th", "tth_trans"]

    # Analyzer motors
    th_motor = Component(EpicsMotor, "m24", labels=("motor",))
    tth = Component(EpicsMotor, "pm2th", labels=("motor",))
    eta = Component(EpicsMotor, "m23", labels=("motor",))
    chi = Component(EpicsMotor, "m26", labels=("motor",))

    d_spacing = Component(Signal, value=1e4, kind="config")
    crystal = Component(Signal, value="None", kind="config")
    tth_detector_distance = Component(
        EpicsSignal, "TWTH:Drive.C", kind="config"
    )
    tracking = Component(Signal, value=False, kind="config")

    def move_single(self, pseudo, position, **kwargs):
        """Guard move_single to require analyzer setup before moving energy."""
        if self.d_spacing.get() == 1e4:
            raise RuntimeError(
                "The analyzer has not been setup, please run the .setup() "
                "function before moving the energy"
            )
        return super().move_single(pseudo, position, **kwargs)

    # These assume that the analyzer is part of the diffractometer.
    @property
    def beamline_wavelength(self):
        """
        Return the current beamline wavelength from the parent diffractometer
        beam object.
        """
        return self.parent.beam.wavelength.get()

    @property
    def beamline_energy(self):
        """
        Return the current beamline energy in keV from the parent diffractometer
        beam object.
        """
        return self.parent.beam.energy.get()

    def convert_energy_to_theta(self, energy):
        """
        Convert photon energy (keV) to Bragg angle (degrees) using the crystal
        d-spacing.
        """
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = speed_of_light * Planck * 6.241509e15 * 1e10 / energy
        theta = arcsin(lamb / 2 / self.d_spacing.get()) * 180.0 / pi
        return theta

    def convert_energy_to_tth_trans(self, energy):
        """
        Convert photon energy (keV) to the two-theta translation stage position
        (mm).
        """
        # lambda in angstroms, theta in degrees, energy in keV
        th = self.convert_energy_to_theta(energy)
        tth = 2 * th
        tth_trans = self.tth_detector_distance.get() * tan(
            (tth - 45 - th) * pi / 180.0
        )
        return tth_trans

    def convert_theta_to_energy(self, theta):
        """
        Convert Bragg angle (degrees) to photon energy (keV) using the crystal
        d-spacing.
        """
        # lambda in angstroms, theta in degrees, energy in keV
        lamb = 2 * self.d_spacing.get() * sin(theta * pi / 180)
        energy = speed_of_light * Planck * 6.241509e15 * 1e10 / lamb
        return energy

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Run a forward (pseudo -> real) calculation"""
        return self.RealPosition(
            th=self.convert_energy_to_theta(pseudo_pos.energy),
            tth_trans=self.convert_energy_to_tth_trans(pseudo_pos.energy),
        )

    @real_position_argument
    def inverse(self, real_pos):
        """Run an inverse (real -> pseudo) calculation"""
        # Changing y does not change the energy.
        return self.PseudoPosition(
            energy=self.convert_theta_to_energy(real_pos.th)
        )

    def set_energy(self, energy):
        """
        Calibrate the Bragg-angle motor to match the given photon energy (keV).
        """
        # energy in keV, theta in degrees.
        theta = self.convert_energy_to_theta(energy)
        self.th_motor.set_current_position(theta)

    def calc(self, acal="No"):
        """
        Print analyzer Bragg angles for the current crystal at the current
        beamline energy.
        """
        d_ana = self.d_spacing.get()
        if d_ana == 1e4:
            self.setup()
            d_ana = self.d_spacing.get()
        wavelength = self.beamline_wavelength
        energy = self.beamline_energy
        cryst = self.crystal.get()
        th_angle = math.degrees(math.asin(wavelength / (2 * d_ana)))
        tth_angle = 2 * th_angle
        print(
            f"[ath, atth] = [{th_angle:.2f}, {tth_angle:.2f}] for {cryst} "
            f"analyzer at {energy:.2f} keV"
        )
        if acal == "No":
            acal = input(f"Calibrate ath position (y/n/r)? [{acal}]: ") or acal
        if acal in ["Yes", "yes", "Y", "y"]:
            print(f"Calibrating ath to {th_angle:.2f}")
            self.set_energy(energy)
        elif acal == "r":
            print("Releasing calibration for ath!")
            self.th_motor.user_offset.put(45)

    def setup(
        self, analyzer_energy=None, analyzer_list_path=ANALYZER_LIST_PATH
    ):
        """
        List compatible analyzer crystals and interactively configure d-spacing
        and crystal.
        """
        if not analyzer_energy:
            energy = self.beamline_energy
            wavelength = self.beamline_wavelength
        else:
            energy = analyzer_energy
            wavelength = WAVELENGTH_CONSTANT / energy
        ptthmin = math.radians(PTTH_MIN_DEGREES)
        ptthmax = math.radians(PTTH_MAX_DEGREES)

        d_dict = {}
        print(
            f"{'#':>2}{'Crystal':>8}{'Refl.':>11}{'Range (keV)':>15}"
            f"{'d_hkl':>10}{'2th (deg)':>11}"
        )
        with open(analyzer_list_path, "r") as f:
            for num, line in enumerate(f):
                split = line.split()
                if "##REFERENCES" in line:
                    break
                (
                    analyzer,
                    hh,
                    kk,
                    ll,
                    a,
                    b,
                    c,
                    alpha,
                    beta,
                    gamma,
                    symmetry,
                    spacegroupnumber,
                    special,
                ) = split[:13]
                hh, kk, ll = map(int, [hh, kk, ll])
                a, b, c = map(float, [a, b, c])
                alpha, beta, gamma = map(
                    lambda x: math.radians(float(x)), [alpha, beta, gamma]
                )
                spacegroupnumber = int(spacegroupnumber)

                for i in range(
                    1, 100
                ):  # Arbitrary limit to prevent infinite loop
                    hhh, kkk, lll = hh * i, kk * i, ll * i
                    dhkl = calcdhkl(
                        hhh, kkk, lll, alpha, beta, gamma, symmetry, a, b, c
                    )
                    if check_structure_factor(
                        hhh, kkk, lll, spacegroupnumber, special
                    ):
                        ana_emax = WAVELENGTH_CONSTANT / (
                            2 * dhkl * math.sin(ptthmin / 2)
                        )
                        ana_emin = WAVELENGTH_CONSTANT / (
                            2 * dhkl * math.sin(ptthmax / 2)
                        )

                        if ana_emin <= energy <= ana_emax:
                            tt_angle = 2 * math.degrees(
                                math.asin(wavelength / (2 * dhkl))
                            )
                            print(
                                f"{num:>2} {analyzer:<9} {hhh:>2}{kkk:>3}"
                                f"{lll:>3}  [{ana_emin:5.2f},{ana_emax:5.2f}]"
                                f"{dhkl:10.3f}{tt_angle:11.2f}"
                            )
                            d_dict[num] = [
                                analyzer,
                                hhh,
                                kkk,
                                lll,
                                dhkl,
                                tt_angle,
                            ]
                            break
                        elif ana_emin > energy:
                            break
        ttdiff = max(abs(ptthmax - 90), abs(ptthmin - 90))
        d_best = {}
        for key, value in d_dict.items():
            if abs(value[5] - 90) < ttdiff:
                ttdiff = abs(value[5] - 90)
                d_best = [key, value]
        if analyzer_energy:
            print(
                f"Best analyzer to use at {energy}: {d_best[1][0]}_"
                f"{d_best[1][1]}{d_best[1][2]}{d_best[1][3]}"
            )
        else:
            anum = (
                input(f"Choice of polarization analyzer [{d_best[0]}]: ")
                or d_best[0]
            )
            anum = int(anum) if isinstance(anum, str) else anum
            if anum in d_dict:
                ana = d_dict[anum]
                cryst = f"{ana[0]}_{ana[1]}{ana[2]}{ana[3]}"
            else:
                ana = d_best[1:][0]
                cryst = f"{ana[0]}_{ana[1]}{ana[2]}{ana[3]}"
                print(f"Choice not possible, using {cryst}")

            d_ana = ana[4]
            self.d_spacing.put(d_ana)
            self.crystal.put(cryst)


class DiffractometerMixin(Device):
    """
    Mixin adding table, area-detector, filter, slit, and analyzer components to
    a diffractometer.
    """

    # Subscribable signal wrapping sample.UB for UB-matrix sync
    _ub_sync = Component(UBMatrixSignal, "", kind="omitted")

    # Table vertical/horizontal
    tablex = Component(EpicsMotor, "m3", labels=("motor",))
    tabley = Component(EpicsMotor, "m1", labels=("motor",))

    # Area detector motors
    pad_rail = Component(EpicsMotor, "m21", labels=("motor",))
    point_rail = Component(EpicsMotor, "m22", labels=("motor",))

    # # Guard slit
    # guardslt  = ...

    # Filters
    filter = Component(HuberFilter, "atten:", labels=("filter",))

    # Detector JJ slit
    detslt = Component(
        SlitDevice,
        "",
        motorsDict={"top": "m31", "bot": "m32", "out": "m34", "inb": "m33"},
        slitnum=2,
        labels=("slit",),
    )

    # Analyzer
    ana = Component(AnalyzerDevice, "", labels=("track_energy",))

    @property
    def hints(self):
        """Return only explicitly-hinted sub-components to avoid busy plotting.

        ``Kind`` is a bitfield: ``Kind.hinted`` (0b101) shares the
        ``Kind.normal`` bit (0b001). ``_get_components_of_kind(Kind.hinted)``
        therefore yields *both* normal and hinted components. The mask
        ``(~Kind.normal & Kind.hinted)`` isolates the "hinted-only" bit so
        only components explicitly tagged ``Kind.hinted`` contribute fields.
        """
        fields = []
        for _, component in self._get_components_of_kind(Kind.hinted):
            if (~Kind.normal & Kind.hinted) & component.kind:
                c_hints = component.hints
                fields.extend(c_hints.get("fields", []))
        return {"fields": fields}

    def default_settings(self):
        """
        Apply default settings for the diffractometer mixin (no-op; subclasses
        override).
        """
        pass
        # self._update_calc_energy()


mono_kwargs = {
    "class": "hklpy2.incident.EpicsMonochromatorRO",
    "prefix": "4idVDCM:",
    "source_type": "Simulated read-only EPICS Monochromator",
    "pv_energy": "BraggERdbkAO",  # the energy readback PV
    "energy_units": "keV",
    "pv_wavelength": "BraggLambdaRdbkAO",  # the wavelength readback PV
    "wavelength_units": "angstrom",
    "wavelength_deadband": 0.000_150,
    "kind": "config",
}


CradleDiffractometerBase = diffractometer_class_factory(
    solver="hkl_soleil",
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=dict(
        tau="m73", mu="m4", gamma="m19", delta="m20", chi="m37", phi="m38"
    ),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=mono_kwargs.copy(),
)

# Changes the positioners kind to config or normal. This will prevent busy
# plotting.
for pos in CradleDiffractometerBase._real + CradleDiffractometerBase._pseudo:
    getattr(CradleDiffractometerBase, pos).kind = Kind.config | Kind.normal


class CradleDiffractometer(CradleDiffractometerBase, DiffractometerMixin):
    """hklpy2 APS-POLAR cradle diffractometer with sample XYZ translation."""

    x = Component(EpicsMotor, "m40", labels=("motor",))
    y = Component(EpicsMotor, "m41", labels=("motor",))
    z = Component(EpicsMotor, "m42", labels=("motor",))


HPDiffractometerBase = diffractometer_class_factory(
    solver="hkl_soleil",
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=dict(
        tau="m73", mu="m4", gamma="m19", delta="m20", chi="m5", phi="m6"
    ),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=mono_kwargs.copy(),
)

# Changes the positioners kind to config or normal. This will prevent busy
# plotting.
for pos in CradleDiffractometerBase._real + CradleDiffractometerBase._pseudo:
    getattr(CradleDiffractometerBase, pos).kind = Kind.config | Kind.normal


class HPDiffractometer(HPDiffractometerBase, DiffractometerMixin):
    """
    hklpy2 APS-POLAR HP-press diffractometer with base, nano, and tilt motors.
    """

    chi = Component(EpicsMotor, "m5", labels=("motor",))
    phi = Component(EpicsMotor, "m6", labels=("motor",))

    basex = Component(EpicsMotor, "m7", labels=("motor",))
    basey = Component(EpicsMotor, "SMBaseY", labels=("motor",))
    basez = Component(EpicsMotor, "SMBaseZ", labels=("motor",))
    basey_motor = Component(EpicsMotor, "m9", labels=("motor",))
    basez_motor = Component(EpicsMotor, "m8", labels=("motor",))

    sample_tilt = Component(EpicsMotor, "m11", labels=("motor",))

    x = Component(EpicsMotor, "m12", labels=("motor",))
    y = Component(EpicsMotor, "m14", labels=("motor",))
    z = Component(EpicsMotor, "m13", labels=("motor",))

    nanox = FormattedComponent(
        EpicsMotor, "4idgSoftX:jena:m1", labels=("motor",)
    )
    nanoy = FormattedComponent(
        EpicsMotor, "4idgSoftX:jena:m2", labels=("motor",)
    )
    nanoz = FormattedComponent(
        EpicsMotor, "4idgSoftX:jena:m3", labels=("motor",)
    )


CradleDiffractometerPSI = diffractometer_class_factory(
    solver="hkl_soleil",
    solver_kwargs={"engine": "psi"},
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=dict(
        tau="m73", mu="m4", gamma="m19", delta="m20", chi="m37", phi="m38"
    ),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=mono_kwargs.copy(),
)


HPDiffractometerPSI = diffractometer_class_factory(
    solver="hkl_soleil",
    solver_kwargs={"engine": "psi"},
    geometry="APS POLAR",
    motor_labels=["motor"],
    reals=dict(
        tau="m73", mu="m4", gamma="m19", delta="m20", chi="m5", phi="m6"
    ),
    _real="tau mu chi phi gamma delta".split(),
    beam_kwargs=mono_kwargs.copy(),
)
