"""
Auxilary HKL functions.

.. autosummary::
    ~change_diffractometer
    ~newsample
    ~sampleList
    ~sampleChange
    ~sampleRemove
    ~list_reflections
    ~list_orienting
    ~or_swap
    ~setor0
    ~setor1
    ~set_orienting
    ~del_reflection
    ~or0
    ~or1
    ~compute_UB
    ~setmode
    ~ca
    ~wh
    ~ubr
    ~br
    ~uan
    ~setlat
    ~setaz
    ~freeze
    ~freeze_general
    ~show_constraints
    ~reset_constraints
    ~set_constraints
    ~analyzer_configuration
    ~analyzer_set
    ~analyzer_get
    ~update_lattice
    ~write_config
    ~read_config
    ~restore_diffractometer_from_scan
    ~set_detector
    ~theta0


Provide a simplified UI for hklpy2 diffractometer users.

The user must define a diffractometer instance, then
register that instance here calling `set_diffractometer(instance)`.
"""

import asyncio
import logging
import math
import pathlib

import yaml

try:
    from apsbits.core.instrument_init import oregistry
    from bluesky import RunEngine
    from bluesky import RunEngineInterrupted
    from bluesky.plan_stubs import mv
    from bluesky.utils import ProgressBarManager
    from epics import caget
    from epics import caput
    from hklpy2 import ConfigurationRunWrapper
    from hklpy2.run_utils import get_run_orientation
    from hklpy2.user import add_sample
    from hklpy2.user import cahkl
    from hklpy2.user import get_diffractometer
    from hklpy2.user import set_diffractometer as hklpy2_set_diffract

    from .run_engine import RE as polar_RE
    from .run_engine import cat
except ModuleNotFoundError:
    print("gi module is not installed, the hkl_utils functions will not work!")

__all__ = """
    change_diffractometer
    newsample
    sampleList
    sampleChange
    sampleRemove
    list_reflections
    list_orienting
    or_swap
    setor0
    setor1
    set_orienting
    del_reflection
    or0
    or1
    compute_UB
    setmode
    ca
    wh
    ubr
    br
    uan
    setlat
    setaz
    freeze
    freeze_general
    show_constraints
    reset_constraints
    set_constraints
    analyzer_configuration
    analyzer_set
    analyzer_get
    update_lattice
    write_config
    read_config
    restore_diffractometer_from_scan
    set_detector
    theta0
    geometries
    set_diffractometer
""".split()

polar_config = pathlib.Path("polar-config.json")

RE = RunEngine({}, loop=asyncio.new_event_loop())
pbar_manager = ProgressBarManager()

logging.getLogger("hklpy2").setLevel(logging.WARNING)
# Levels: DEBUG, INFO, WARNING (default), ERROR, CRITICAL


class Geometries:
    """Register the diffractometer geometries."""

    configuration_wrapper = None

    def __init__(
        self, huber_euler_nm, huber_euler_psi_nm, huber_hp_nm, huber_hp_psi_nm
    ):
        self._huber_euler = huber_euler_nm
        self._huber_euler_psi = huber_euler_psi_nm
        self._huber_hp = huber_hp_nm
        self._huber_hp_psi = huber_hp_psi_nm

    @property
    def huber_euler(self):
        return oregistry.find(self._huber_euler)

    @huber_euler.setter
    def huber_euler(self, value):
        self._huber_euler = value

    @property
    def huber_euler_psi(self):
        return oregistry.find(self._huber_euler_psi)

    @huber_euler_psi.setter
    def huber_euler_psi(self, value):
        self._huber_euler_psi = value

    @property
    def huber_hp(self):
        return oregistry.find(self._huber_hp)

    @huber_hp.setter
    def huber_hp(self, value):
        self._huber_hp = value

    @property
    def huber_hp_psi(self):
        return oregistry.find(self._huber_hp_psi)

    @huber_hp_psi.setter
    def huber_hp_psi(self, value):
        self._huber_hp_psi = value


geometries = Geometries(
    "huber_euler", "huber_euler_psi", "huber_hp", "huber_hp_psi"
)

_DIFFRACTOMETER_NAMES = ["huber_euler", "huber_hp"]


def set_diffractometer(diffractometer):
    """
    Wraps the `hklpy2.user.set_diffractometer` and adds the diffractometer
    configuration wrapper to the RunEngine preprocessors.

    Parameters
    ----------
    diffractometer : str or DiffractometerBase, optional
        Name or device instance to activate.
    """

    hklpy2_set_diffract(diffractometer)

    try:
        polar_RE.preprocessors.remove(geometries.configuration_wrapper)
    except ValueError:
        pass

    geometries.configuration_wrapper = ConfigurationRunWrapper(diffractometer)
    polar_RE.preprocessors.append(geometries.configuration_wrapper.wrapper)


def change_diffractometer(diffractometer=None):
    """
    Select and initialize the active diffractometer (huber_euler or huber_hp).

    1. Selects the diffractometer (interactive prompt or argument).
    2. Applies the appropriate axis constraints.
    3. Creates aliases for all real diffractometer axes in the calling
       namespace (mu, gamma, delta, chi, phi, tau) and the reciprocal-space
       pseudo axes (h, k, l).

    Parameters
    ----------
    diffractometer : str or DiffractometerBase, optional
        Name or device instance to activate. If not provided, prompts
        interactively with the current diffractometer as the default.
    """
    current = get_diffractometer()
    current_name = current.name if current is not None else "none"

    if diffractometer is not None:
        answer = (
            diffractometer
            if isinstance(diffractometer, str)
            else diffractometer.name
        )
    else:
        choices_str = "/".join(_DIFFRACTOMETER_NAMES)
        answer = input(
            f"Diffractometer ({choices_str}) [{current_name}]? "
        ).strip()
        if not answer:
            answer = current_name

    if answer not in _DIFFRACTOMETER_NAMES:
        print(
            f"Unknown diffractometer '{answer}'. Choose from: {'/'.join(_DIFFRACTOMETER_NAMES)}"
        )
        return

    new_geom = oregistry.find(answer)
    set_diffractometer(new_geom)
    print(f"Active diffractometer: {new_geom.name}")

    if new_geom.name == "huber_euler":
        set_constraints(-1, 1, 0, 90, -20, 200, -180, 180, -2, 140, -5, 50)
    elif new_geom.name == "huber_hp":
        set_constraints(-1, 1, 0, 90, 80, 100, -7, 7, -2, 140, -5, 50)

    aliases = {
        axis: getattr(new_geom, axis) for axis in new_geom.real_axis_names
    }
    aliases.update(
        {
            "h": new_geom.h,
            "k": new_geom.k,
            "l": new_geom.l,
            "ath": new_geom.ana.th,
            "atth": new_geom.ana.tth,
            "eta": new_geom.ana.eta,
            "achi": new_geom.ana.chi,
        }
    )
    if new_geom.name == "huber_euler":
        aliases.update(
            {
                "cryox": new_geom.x,
                "cryoy": new_geom.y,
                "cryoz": new_geom.z,
            }
        )
    elif new_geom.name == "huber_hp":
        aliases.update(
            {
                "xeryon": new_geom.xeryon,
                "x": new_geom.x,
                "y": new_geom.y,
                "z": new_geom.z,
                "nanox": new_geom.nanox,
                "nanoy": new_geom.nanoy,
                "nanoz": new_geom.nanoz,
                "basex": new_geom.basex,
                "basey": new_geom.basey,
                "basez": new_geom.basez,
            }
        )
    try:
        ip = get_ipython()  # — available in IPython/Bluesky sessions
        ip.push(aliases)
    except NameError:
        globals().update(aliases)
    print(f"Aliases created: {', '.join(aliases)}")


def newsample():
    """
    Interactively add a new sample with lattice constants.

    Prompts the user for:
      - sample name
      - lattice constants (a, b, c, alpha, beta, gamma)

    Uses defaults if the user just presses Enter.
    """
    _geom_ = get_diffractometer()
    # Ask for sample name
    name = input("Sample name? ").strip()
    if not name:
        print("Sample name cannot be empty.")
        return

    # Default values
    defaults = {
        "a": 5.0,
        "b": 5.0,
        "c": 5.0,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
    }

    def ask(name, default):
        val = input(f"{name} ({default})? ") or default
        try:
            return float(val)
        except ValueError:
            print(f"Invalid {name}, keeping {default}")
            return default

    # Collect lattice parameters
    a = ask("a", defaults["a"])
    b = ask("b", defaults["b"])
    c = ask("c", defaults["c"])
    alpha = ask("alpha", defaults["alpha"])
    beta = ask("beta", defaults["beta"])
    gamma = ask("gamma", defaults["gamma"])

    # Call your existing function
    add_sample(name, a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)

    print(
        f"Added sample '{name}' with lattice constants: "
        f"a={a}, b={b}, c={c}, alpha={alpha}, beta={beta}, gamma={gamma}"
    )

    if len(_geom_.real_positioners) == 6:
        motors = _geom_.real_positioners._fields
        ref1_hkl = (0, 0, 2)
        ref1_pos = dict(gamma=40, mu=20, chi=90, phi=0, delta=0, tau=0)
        _geom_.add_reflection(ref1_hkl, [ref1_pos[m] for m in motors])
        ref2_hkl = (2, 0, 0)
        ref2_pos = dict(gamma=40, mu=20, chi=0, phi=0, delta=0, tau=0)
        _geom_.add_reflection(ref2_hkl, [ref2_pos[m] for m in motors])
        list_reflections()
        # Use the primitive direction of ref2 as the azimuthal reference
        from functools import reduce
        from math import gcd

        g = reduce(gcd, (abs(x) for x in ref2_hkl if x != 0))
        az_hkl = tuple(x // g for x in ref2_hkl)
        setaz(*az_hkl)
        compute_UB()


def sampleList():
    """List all samples currently defined in hklpy2; specify  current one."""
    _geom_ = get_diffractometer()
    samples = _geom_.samples
    print("")
    for nm, sample in samples.items():
        #        orienting_refl = samples[x].reflections
        print(f"Sample = {nm}")
        print("Lattice:", end=" ")
        #        print(*samples[x].lattice._fields, sep=", ", end=" = ")
        print(sample.lattice)
        print(
            "======================================================================"
        )
    print("\nCurrent sample: " + _geom_.sample.name)


def sampleChange(sample_key=None):
    """
    Change selected sample in hklpy2.

    Parameters
    ----------
    sample_key : string, optional
        Name of the sample as set in hklpy. If None it will ask for which
        sample.
    """
    _geom_ = get_diffractometer()
    if sample_key is None:
        d = _geom_.samples.keys()
        print("Sample keys:", list(d))
        sample_key = (
            input("\nEnter sample key [{}]: ".format(_geom_.sample.name))
            or _geom_.sample.name
        )
    try:
        _geom_.sample = sample_key  # define the current sample
        print("\nCurrent sample: " + _geom_.sample.name)
        # to be done: check if orienting reflections exist
    #        compute_UB()

    except KeyError:
        print("Not a valid sample key")


def sampleRemove(sample_key=None):
    """
    Remove selected sample in hklpy.

    Parameters
    ----------
    sample_key : string, optional
        Name of the sample as set in hklpy. If None it will ask for which
        sample.
    """
    _geom_ = get_diffractometer()
    if sample_key is None:
        d = _geom_.samples.keys()
        print("Sample keys:", list(d))
        sample_key = input(
            "\nEnter sample key to remove [{}]: ".format(_geom_.sample.name)
        )
        if sample_key == _geom_.sample.name:
            print("The current sample cannot be removed.")
            sample_key = " "
    try:
        _geom_.samples.pop(sample_key)  # remove the sample
        print("\n[{}] sample is removed.".format(sample_key))

    except KeyError:
        print("Not a valid sample key")


def list_reflections(all_samples=False):
    """
    Lists all reflections defined in hklpy for six-circle geometry.

    Parameters
    ----------
    all_samples : bool, optional
        If True, list reflections for all samples.
        If False, only the current sample. Defaults to False.
    """
    _geom_ = get_diffractometer()
    samples = _geom_.samples.values() if all_samples else [_geom_.sample]

    for sample in samples:
        print(f"Sample: {sample.name}")

        orienting_refl = sample.reflections.order  # orientation reflection keys

        # column widths
        refl_width = 8
        pseudo_width = 9  # for h, k, l
        real_width = 10  # for motor positions

        # Header
        if len(_geom_.real_positioners) == 6:
            real_headers = ["Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"]
        else:
            real_headers = list(_geom_.real_positioners._fields)
        header = (
            f"\n{'#':>{refl_width}}"
            + "".join(
                f"{m:>{pseudo_width}}"
                for m in _geom_.pseudo_positioners._fields
            ).upper()
            + "".join(f"{k:>{real_width}}" for k in real_headers)
            + "   orienting"
        )
        print(header)

        # Rows
        for key, ref in sample.reflections.items():
            h, k, l = list(ref.pseudos.values())
            if len(_geom_.real_positioners) == 6:
                reals = ref.reals
                pos_vals = [
                    reals["gamma"],
                    reals["mu"],
                    reals["chi"],
                    reals["phi"],
                    reals["delta"],
                    reals["tau"],
                ]
            else:
                pos_vals = list(ref.reals.values())

            tag = ""
            if orienting_refl and key == orienting_refl[0]:
                tag = "first"
            elif len(orienting_refl) > 1 and key == orienting_refl[1]:
                tag = "second"

            row = (
                f"{key:>{refl_width}}"
                f"{h:{pseudo_width}.3f}{k:{pseudo_width}.3f}{l:{pseudo_width}.3f}"
                + "".join(f"{v:{real_width}.3f}" for v in pos_vals)
                + (f"   {tag}" if tag else "")
            )
            print(row)

        if len(samples) > 1 and all_samples:
            print("=" * 107)


def or_swap():
    """Swaps the two orientation reflections in hklpy."""
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    sample.reflections.swap()
    list_reflections()
    compute_UB()


def compute_UB():
    """
    Calculates the UB matrix. v

    This fixes one issue with the hklpy calc_UB in that using wh() right after
    will not work, it needs to run one calculation first.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = get_diffractometer()
    _geom_for_psi_ = oregistry.find(_geom_.name + "_psi")

    sample = _geom_.sample
    print("Computing UB...")
    sample.core.calc_UB(
        sample.reflections.order[0], sample.reflections.order[1]
    )
    Sync_UB_Matrix(_geom_, _geom_for_psi_)
    first_ref = sample.reflections[sample.reflections.order[0]]
    h, k, l = list(first_ref.pseudos.values())
    _geom_.forward(h, k, l)
    # TODO: prefer to not use caput to a specific PV, hard to maintain, verify,
    # etc...
    caput(
        "4idgSoftX:Bluesky:UB_matrix",
        [
            sample.UB[0][0],
            sample.UB[0][1],
            sample.UB[0][2],
            sample.UB[1][0],
            sample.UB[1][1],
            sample.UB[1][2],
            sample.UB[2][0],
            sample.UB[2][1],
            sample.UB[2][2]
        ]
    )
    eiger_x = caget("4idEiger:ROI1:MinX") + caget("4idEiger:ROI1:SizeX")/2
    eiger_y = caget("4idEiger:ROI1:MinY") + caget("4idEiger:ROI1:SizeY")/2
    caput("4idgSoftX:Eiger:Center", [eiger_x,eiger_y])

# TODO: Do we really need this? Could put the UB matrix as part of the
# diffractometer, then sync with a callback.
class Sync_UB_Matrix:
    """
    Keep the UB matrix of target in sync with source via an ophyd subscription.

    Subscribes to source._ub_sync (an ArrayAttributeSignal pointing at
    core.sample.UB) so that whenever the signal is updated the callback
    copies the new matrix to the target and syncs simulated motor positions.
    Call cleanup() to remove the subscription when no longer needed.
    """

    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.source._ub_sync.subscribe(self.sync_callback)
        # Trigger an immediate copy using the current value
        self.sync_callback(value=self.source._ub_sync.get())

    def cleanup(self):
        """Remove the UB-sync subscription."""
        self.source._ub_sync.clear_sub(self.sync_callback)

    def sync_callback(self, value=None, **kwargs):
        if value is None:
            return
        print(f"Copy UB from {self.source.name} to {self.target.name}")
        self.target.sample.UB = value

        # Sync real motor positions if target has simulated motors
        for axis_name in self.source.real_axis_names:
            ptarget = getattr(self.target, axis_name, None)
            if ptarget is not None and hasattr(ptarget, "move"):
                psource = getattr(self.source, axis_name)
                ptarget.move(psource.position)

        # Sync the azimuthal reference reflection (h2, k2, l2) extras of
        # the psi constant mode. Read from source.core.all_extras so it
        # works regardless of source's current mode, then push to target
        # by temporarily switching to a psi-capable mode if needed.
        src_extras = self.source.core.all_extras
        h2k2l2 = {
            k: src_extras[k] for k in ("h2", "k2", "l2") if k in src_extras
        }
        if len(h2k2l2) == 3:
            psi_modes = [
                m for m in self.target.core.modes if "psi" in m.lower()
            ]
            if psi_modes:
                saved_mode = self.target.core.mode
                if "psi" not in saved_mode.lower():
                    self.target.core.mode = psi_modes[0]
                try:
                    current_extras = self.target.core.extras
                    merged = {**h2k2l2}
                    if "psi" in current_extras:
                        merged["psi"] = current_extras.get("psi", 0.0)
                    self.target.core.extras = merged
                finally:
                    self.target.core.mode = saved_mode


def setor0():
    """
    Sets the primary orientation in hklpy2.

    Parameters
    ----------
    diffractometer real motors : float, optional
        Values of motor positions for current reflection. It will ask
        for it.
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. It will ask
        for it.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order
    motors = _geom_.real_positioners._fields
    ordered_reals = (
        ("gamma", "mu", "chi", "phi", "delta", "tau")
        if len(_geom_.real_positioners) == 6
        else motors
    )
    if len(orienting_refl) > 0:
        for key, ref in sample.reflections.items():
            if key == orienting_refl[0]:
                pos = {k: ref.reals[k] for k in ordered_reals}
                old_h, old_k, old_l = list(ref.pseudos.values())
    else:
        pos = {k: 0 for k in ordered_reals}
        old_h = 0
        old_k = 0
        old_l = 0

    print("Enter primary-reflection angles:")
    inputs = {}
    for m in ordered_reals:
        temppos = input("{} = [{:6.2f}]: ".format(m, pos[m])) or pos[m]
        inputs[m] = float(temppos)
    or0pos = [inputs[m] for m in motors]
    h = input("H = [{}]: ".format(old_h)) or old_h
    k = input("K = [{}]: ".format(old_k)) or old_k
    l = input("L = [{}]: ".format(old_l)) or old_l

    try:
        _geom_.add_reflection(
            (float(h), float(k), float(l)),
            or0pos,
        )
    except Exception as e:
        print(f"Error adding reflection: {e}")

    if len(orienting_refl) > 1:
        sample.reflections.order.pop(0)
        # sample.reflections.order.pop(-1)
    sample.reflections.order.insert(0, list(sample.reflections.keys())[-1])

    if len(orienting_refl) > 2:
        compute_UB()


def setor1():
    """
    Sets the primary orientation in hklpy2.

    Parameters
    ----------
    diffractometer real motors : float, optional
        Values of motor positions for current reflection. It will ask
        for it.
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. It will ask
        for it.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order
    motors = _geom_.real_positioners._fields
    ordered_reals = (
        ("gamma", "mu", "chi", "phi", "delta", "tau")
        if len(_geom_.real_positioners) == 6
        else motors
    )
    if len(orienting_refl) > 1:
        for key, ref in sample.reflections.items():
            if key == orienting_refl[1]:
                pos = {k: ref.reals[k] for k in ordered_reals}
                old_h, old_k, old_l = list(ref.pseudos.values())
    else:
        pos = {k: 0 for k in ordered_reals}
        old_h = 0
        old_k = 0
        old_l = 0

    print("Enter secondary-reflection angles:")
    inputs = {}
    for m in ordered_reals:
        temppos = input("{} = [{:6.2f}]: ".format(m, pos[m])) or pos[m]
        inputs[m] = float(temppos)
    or0pos = [inputs[m] for m in motors]
    h = input("H = [{}]: ".format(old_h)) or old_h
    k = input("K = [{}]: ".format(old_k)) or old_k
    l = input("L = [{}]: ".format(old_l)) or old_l

    try:
        _geom_.add_reflection((float(h), float(k), float(l)), or0pos)
    except Exception as e:
        print(f"Error adding reflection: {e}")

    if len(orienting_refl) > 1:
        sample.reflections.order.pop(1)
        # sample.reflections.order.pop(-1)
    sample.reflections.order.insert(1, list(sample.reflections.keys())[-1])

    if len(orienting_refl) > 1:
        compute_UB()


def or0(h=None, k=None, l=None):
    """
    Sets the primary orientation in hklpy2 using the current motor positions.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order
    if not h and not k and not l:
        if len(orienting_refl) > 0:
            for key, ref in sample.reflections.items():
                if key == orienting_refl[0]:
                    hr, kr, lr = list(ref.pseudos.values())
        else:
            hr = 2
            kr = 0
            lr = 0
        h = (input("H ({})? ".format(hr)) if not h else h) or hr
        k = (input("K ({})? ".format(kr)) if not k else k) or kr
        l = (input("L ({})? ".format(lr)) if not l else l) or lr
    _geom_.add_reflection((float(h), float(k), float(l)), _geom_.real_position)

    if len(orienting_refl) > 1:
        sample.reflections.order.pop(0)
        # sample.reflections.order.pop(-1)
        sample.reflections.order.insert(0, list(sample.reflections.keys())[-1])

    if len(orienting_refl) > 2:
        compute_UB()


def or1(h=None, k=None, l=None):
    """
    Sets the secondary orientation in hklpy2 using the current motor positions.

    Parameters
    ----------
    h, k, l : float, optional
        Values of H, K, L positions for current reflection. If None, it will ask
        for it.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order
    if not h and not k and not l:
        if len(orienting_refl) > 1:
            for key, ref in sample.reflections.items():
                if key == orienting_refl[1]:
                    hr, kr, lr = list(ref.pseudos.values())
        else:
            hr = 0
            kr = 2
            lr = 0
        h = (input("H ({})? ".format(hr)) if not h else h) or hr
        k = (input("K ({})? ".format(kr)) if not k else k) or kr
        l = (input("L ({})? ".format(lr)) if not l else l) or lr
    _geom_.add_reflection((float(h), float(k), float(l)), _geom_.real_position)

    if len(orienting_refl) > 2:
        sample.reflections.order.pop(1)
        # sample.reflections.order.pop(-1)
        sample.reflections.order.insert(1, list(sample.reflections.keys())[-1])

    if len(orienting_refl) > 1:
        compute_UB()


def set_orienting():
    """
    Change the primary and secondary orienting reflections
    to existing reflections in the reflection list (hklpy2).

    WARNING: Works only with six-circle geometry (fix in progress).
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order

    # Column widths for alignment
    idx_width = 3
    pseudo_width = 9
    real_width = 10

    # Print header
    ordered_reals = ("gamma", "mu", "chi", "phi", "delta", "tau")
    real_headers = (
        ["Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"]
        if len(_geom_.real_positioners) == 6
        else list(_geom_.real_positioners._fields)
    )
    header = (
        f"\n{'#':>{idx_width}}"
        + "".join(
            f"{m:>{pseudo_width}}" for m in _geom_.pseudo_positioners._fields
        ).upper()
        + "".join(f"{k:>{real_width}}" for k in real_headers)
        + "   orienting"
    )
    print(header)

    # Find current orienting reflection indices (defaults: 0,1)
    or0_old, or1_old = 0, 1
    if len(orienting_refl) > 0:
        or0_old = list(sample.reflections.keys()).index(orienting_refl[0])
    if len(orienting_refl) > 1:
        or1_old = list(sample.reflections.keys()).index(orienting_refl[1])

    # Print reflection list
    for i, (key, ref) in enumerate(sample.reflections.items()):
        h, k, l = list(ref.pseudos.values())
        pos = (
            [ref.reals[k] for k in ordered_reals]
            if len(_geom_.real_positioners) == 6
            else list(ref.reals.values())
        )

        tag = ""
        if len(orienting_refl) > 0 and key == orienting_refl[0]:
            tag = "first"
        elif len(orienting_refl) > 1 and key == orienting_refl[1]:
            tag = "second"

        row = (
            f"{i:>{idx_width}}"
            f"{h:{pseudo_width}.3f}{k:{pseudo_width}.3f}{l:{pseudo_width}.3f}"
            + "".join(f"{v:{real_width}.3f}" for v in pos)
            + (f"   {tag}" if tag else "")
        )
        print(row)

    # Prompt user for orienting reflections
    try:
        or0 = int(input(f"\nFirst orienting ({or0_old})? ") or or0_old)
        or1 = int(input(f"Second orienting ({or1_old})? ") or or1_old)
    except ValueError:
        print("Invalid input, keeping old orienting reflections.")
        or0, or1 = or0_old, or1_old

    keys = list(sample.reflections.keys())

    # Safely update orienting reflections
    if 0 <= or0 < len(keys):
        sample.reflections.order[0:1] = [keys[or0]]
    if 0 <= or1 < len(keys):
        if len(sample.reflections.order) > 1:
            sample.reflections.order[1:2] = [keys[or1]]
        else:
            sample.reflections.order.append(keys[or1])

    # Recompute UB matrix
    compute_UB()


def del_reflection():
    """
    Delete a reflection from the current sample's reflection list.

    - Displays reflections like set_orienting()
    - User inputs index number of reflection to delete
    - Orienting reflections (first/second) cannot be deleted
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order

    # Column widths for alignment
    idx_width = 3
    pseudo_width = 9
    real_width = 10

    # Print header
    ordered_reals = ("gamma", "mu", "chi", "phi", "delta", "tau")
    real_headers = (
        ["Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"]
        if len(_geom_.real_positioners) == 6
        else list(_geom_.real_positioners._fields)
    )
    header = (
        f"\n{'#':>{idx_width}}"
        + "".join(
            f"{m:>{pseudo_width}}" for m in _geom_.pseudo_positioners._fields
        ).upper()
        + "".join(f"{k:>{real_width}}" for k in real_headers)
        + "   orienting"
    )
    print(header)

    # Print reflection list
    keys = list(sample.reflections.keys())
    for i, (key, ref) in enumerate(sample.reflections.items()):
        h, k, l = list(ref.pseudos.values())
        pos = (
            [ref.reals[k] for k in ordered_reals]
            if len(_geom_.real_positioners) == 6
            else list(ref.reals.values())
        )

        tag = ""
        if len(orienting_refl) > 0 and key == orienting_refl[0]:
            tag = "first"
        elif len(orienting_refl) > 1 and key == orienting_refl[1]:
            tag = "second"

        row = (
            f"{i:>{idx_width}}"
            f"{h:{pseudo_width}.3f}{k:{pseudo_width}.3f}{l:{pseudo_width}.3f}"
            + "".join(f"{v:{real_width}.3f}" for v in pos)
            + (f"   {tag}" if tag else "")
        )
        print(row)

    # Prompt for index to delete
    try:
        idx = int(input("\nEnter reflection number to delete: "))
    except ValueError:
        print("Invalid input. Aborting delete.")
        return

    # Safety checks
    if idx < 0 or idx >= len(keys):
        print("Invalid index. Aborting delete.")
        return
    if keys[idx] in orienting_refl[:2]:
        print(
            "Cannot delete orienting reflections (first/second). Aborting delete."
        )
        return

    # Delete reflection
    ref_key = keys[idx]
    del sample.reflections[ref_key]
    print(f"Deleted reflection '{ref_key}'.")


def list_orienting():
    """
    List the first and second orienting reflections only
    from the current sample's reflection list.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    orienting_refl = sample.reflections.order

    if len(orienting_refl) < 2:
        print("Not enough orienting reflections defined.")
        return

    # Column widths for alignment
    idx_width = 3
    pseudo_width = 9
    real_width = 10

    # Print header
    custom_positioners = ("gamma", "mu", "chi", "phi", "delta", "tau")
    header = (
        f"\n{'#':>{idx_width}}"
        + "".join(
            f"{m:>{pseudo_width}}" for m in _geom_.pseudo_positioners._fields
        ).upper()
        + "".join(f"{k.capitalize():>{real_width}}" for k in custom_positioners)
        + "   orienting"
    )
    print(header)

    # Print only orienting reflections
    keys = list(sample.reflections.keys())
    for tag, key in zip(["first", "second"], orienting_refl[:2], strict=False):
        if key not in sample.reflections:
            continue
        idx = keys.index(key)
        ref = sample.reflections[key]
        h, k, l = list(ref.pseudos.values())
        pos = [ref.reals[k] for k in custom_positioners]

        row = (
            f"{idx:>{idx_width}}"
            f"{h:{pseudo_width}.3f}{k:{pseudo_width}.3f}{l:{pseudo_width}.3f}"
            + "".join(f"{v:{real_width}.3f}" for v in pos)
            + f"   {tag}"
        )
        print(row)


def setmode(mode=None):
    """
    Set the mode of the currently selected diffractometer.

    Parameters
    ----------
    mode : string, optional
        Mode to be selected. If None, it will ask.
    """
    _geom_ = get_diffractometer()
    current_mode = _geom_.core.mode
    for index, item in enumerate(_geom_.core.modes):
        print("{:2d}. {}".format(index + 1, item))
        if current_mode == item:
            current_index = index
    if mode:
        _geom_.core.mode = _geom_.core.modes[int(mode) - 1]
        print("\nSet mode to {}".format(mode))
    else:
        mode = input("\nMode ({})? ".format(current_index + 1)) or (
            current_index + 1
        )
        _geom_.core.mode = _geom_.core.modes[int(mode) - 1]

    # Freeze the appropriate detector angle at 0 based on mode geometry.
    # Local axis names are derived from the solver→local axis name mapping
    # (E6C solver: 'gamma' = horizontal detector, 'delta' = vertical detector).
    selected_mode = _geom_.core.mode
    if "vertical" in selected_mode:
        solver_det = "gamma"  # horizontal detector angle frozen at 0
    elif "horizontal" in selected_mode:
        solver_det = "delta"  # vertical detector angle frozen at 0
    else:
        solver_det = None

    if solver_det is not None:
        solver_reals = _geom_.core.solver_real_axis_names
        local_reals = list(_geom_.real_positioners._fields)
        solver_to_local = dict(zip(solver_reals, local_reals, strict=False))
        det_angle = solver_to_local.get(solver_det)
        if det_angle is not None:
            _geom_.core.presets = {det_angle: 0}
            print(f"Preset {det_angle}=0 for mode '{selected_mode}'")
        else:
            _geom_.core.presets = {}
    else:
        _geom_.core.presets = {}


def freeze(*args):
    """
    Set preset values for the constant axes of the current mode.

    - For psi constant modes: freezes psi. Uses args[0] if given, otherwise
      computes the current psi from the psi-engine counterpart diffractometer.
    - For '4-circles constant phi/mu/chi horizontal': freezes that axis.
      Uses args[0] if given, otherwise uses the current motor position.
    - For other modes: prompts interactively for each constant axis,
      showing the current preset as the default.
    Updates ``_geom_.core.presets`` or ``_geom_.core.extras`` as appropriate.
    """
    _geom_ = get_diffractometer()
    current_mode = _geom_.core.mode

    if current_mode in (
        "psi constant",
        "psi constant vertical",
        "psi constant horizontal",
    ):
        _geom_for_psi_ = oregistry.find(_geom_.name + "_psi")
        if len(args) == 0:
            psi = _geom_for_psi_.inverse(0).psi
        elif len(args) == 1:
            psi = args[0]
        else:
            raise ValueError(
                "either no argument or a psi value needs to be provided."
            )
        _geom_.core.extras = {"psi": psi}
        print(f"Psi = {psi}")
        return

    _single_axis_modes = {
        "4-circles constant phi horizontal": "phi",
        "4-circles constant mu horizontal": "mu",
        "4-circles constant chi horizontal": "chi",
    }
    if current_mode in _single_axis_modes:
        axis = _single_axis_modes[current_mode]
        if len(args) == 0:
            value = getattr(_geom_.real_positioners, axis).position
        elif len(args) == 1:
            value = args[0]
        else:
            raise ValueError(
                f"either no argument or a {axis} value needs to be provided."
            )
        _geom_.core.presets = {**_geom_.core.presets, axis: value}
        print(f"{axis.capitalize()} = {value}")
        return

    constant_axes = _geom_.core.constant_axis_names

    if not constant_axes:
        print(f"Mode '{current_mode}' has no constant (frozen) axes.")
        return

    print(f"Mode: {current_mode}")
    current_presets = _geom_.core.presets
    new_presets = {}

    for axis in constant_axes:
        current_val = current_presets.get(axis, 0.0)
        raw = input(f"  {axis} ({current_val})? ") or current_val
        try:
            new_presets[axis] = float(raw)
        except ValueError:
            print(f"  Invalid value for '{axis}', keeping {current_val}")
            new_presets[axis] = float(current_val)

    _geom_.core.presets = new_presets
    print("Frozen angles:")
    for axis, val in new_presets.items():
        print(f"  {axis} = {val}")


def freeze_general():
    """
    Interactively set preset values for the constant axes of the current mode.

    For each angle held constant in the current mode, prompts for a value
    (showing the current preset as default). Updates ``_geom_.core.presets``.
    """
    _geom_ = get_diffractometer()
    current_mode = _geom_.core.mode
    constant_axes = _geom_.core.constant_axis_names

    if not constant_axes:
        print(f"Mode '{current_mode}' has no constant (frozen) axes.")
        return

    print(f"Mode: {current_mode}")
    current_presets = _geom_.core.presets
    new_presets = {}
    for axis in constant_axes:
        current_val = current_presets.get(axis, 0.0)
        raw = input(f"  {axis} ({current_val})? ") or current_val
        try:
            new_presets[axis] = float(raw)
        except ValueError:
            print(f"  Invalid value for '{axis}', keeping {current_val}")
            new_presets[axis] = float(current_val)

    _geom_.core.presets = new_presets
    print("Frozen angles:")
    for axis, val in new_presets.items():
        print(f"  {axis} = {val}")


def ca(h, k, l):
    """
    Calculate the motors position of a reflection.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.
    """
    _geom_ = get_diffractometer()
    pos = cahkl(h, k, l)
    if "No solutions" in pos:
        print(pos)
    else:
        # print(pos)
        print("\n   Calculated Positions:")
        print(
            "\n   H K L = {:5f}, {:5f}, {:5f}".format(
                h,
                k,
                l,
            )
        )
        print(
            f"\n   Lambda (Energy) = {_geom_.beam.wavelength.get():6.4f} \u212b"
            f" ({_geom_.beam.energy.get():6.4f}) keV"
        )
        if len(_geom_.real_positioners) == 6:
            pos_dict = dict(
                zip(_geom_.real_positioners._fields, pos, strict=False)
            )
            print(
                "\n{:>9}{:>9}{:>9}{:>9}{:>9}{:>9}".format(
                    "Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"
                )
            )
            print(
                "{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}{:>9.3f}".format(
                    pos_dict["gamma"],
                    pos_dict["mu"],
                    pos_dict["chi"],
                    pos_dict["phi"],
                    pos_dict["delta"],
                    pos_dict["tau"],
                )
            )
        else:
            print(
                f"\n{''.join(f'{k:>10}' for k in _geom_.real_positioners._fields)}"
                f"\n{''.join(f'{v:>10.3f}' for v in pos)}"
            )


def _wh():
    """
    Retrieve information on the current reciprocal space position.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.
    """
    _geom_ = get_diffractometer()
    _geom_for_psi_ = oregistry.find(_geom_.name + "_psi")
    _geom_for_psi_.sample.UB = _geom_.sample.UB
    print(
        f"\n   {' '.join(_geom_.pseudo_positioners._fields).upper()}"
        f" = {', '.join([f'{v.position:5f}' for v in _geom_.pseudo_positioners])}"
    )

    # Snapshot the current (h, k, l) into uppercase H/K/L globals so the
    # user can reuse them at the prompt (e.g. `mv(diff.h, H+0.01, ...)`).
    hkl_globals = {
        "H": _geom_.h.position,
        "K": _geom_.k.position,
        "L": _geom_.l.position,
    }
    try:
        ip = get_ipython()  # — available in IPython / Bluesky sessions
        ip.push(hkl_globals)
    except NameError:
        globals().update(hkl_globals)
    print(
        f"\n   Lambda (Energy) = {_geom_.beam.wavelength.get():6.4f} \u212b"
        f" ({_geom_.beam.energy.get():6.4f}) keV"
    )
    _rp_ = _geom_.real_positioners
    if len(_rp_) == 6:
        print(
            "\n{:>10}{:>10}{:>10}{:>10}{:>10}{:>10}".format(
                "Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"
            )
        )
        print(
            "{:>10.3f}{:>10.3f}{:>10.3f}{:>10.3f}{:>10.3f}{:>10.3f}".format(
                _rp_.gamma.position,
                _rp_.mu.position,
                _rp_.chi.position,
                _rp_.phi.position,
                _rp_.delta.position,
                _rp_.tau.position,
            )
        )
    else:
        print(
            f"\n{''.join(f'{k:>10}' for k in _rp_._fields)}"
            f"\n{''.join(f'{v.position:>10.3f}' for v in _rp_)}"
        )
    print(
        "\n   PSI = {:5.4f} ".format(
            _geom_for_psi_.inverse(0).psi,
        )
    )
    _h2, _k2, _l2 = _geom_for_psi_.core.extras.values()
    print(
        "   PSI reference vector = {:3.3f} {:3.3f} {:3.3f}".format(
            _h2,
            _k2,
            _l2,
        )
    )


def _ensure_idle():
    if RE.state != "idle":
        print("The RunEngine invoked by magics cannot be resumed.")
        print("Aborting...")
        RE.abort()


def ubr(h, k, l):
    """
    Move the motors to a reciprocal space point.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.

    Returns
    -------
    """
    _geom_ = get_diffractometer()
    plan = mv(_geom_.h, float(h), _geom_.k, float(k), _geom_.l, float(l))
    RE.waiting_hook = pbar_manager
    try:
        RE(plan)
    except RunEngineInterrupted:
        ...
    RE.waiting_hook = None
    _ensure_idle()
    return None


def br(h, k, l):
    """
    Move the motors to a reciprocal space point.

    Parameters
    ----------
    h, k, l : float
        H, K, and L values.

    Returns
    -------
    Generator for the bluesky Run Engine.

    Example
    -------
    RE(br(2, 2, 0))
    """
    _geom_ = get_diffractometer()
    yield from mv(_geom_.h, float(h), _geom_.k, float(k), _geom_.l, float(l))


def uan(*args):
    """
    Moves the delta and eta motors.

    WARNING: This function will only work with six circles. This will be fixed
    in future releases.

    Parameters
    ----------
    delta, eta: float, optional??
        Delta and eta motor angles to be moved to.

    Returns
    -------
    """
    _geom_ = get_diffractometer()
    if len(args) != 2:
        tth, th = args
        raise ValueError("Usage: uan(gamma,mu))")
    else:
        tth, th = args
        if len(_geom_.real_position) == 6:
            print("Moving to (gamma,mu)=({},{})".format(tth, th))
            plan = mv(_geom_.gamma, tth, _geom_.mu, th)
        elif len(_geom_.real_position) == 4:
            print("Moving to (tth,th)=({},{})".format(tth, th))
            plan = mv(_geom_.tth, tth, _geom_.th, th)
    RE.waiting_hook = pbar_manager
    try:
        RE(plan)
    except RunEngineInterrupted:
        ...
    RE.waiting_hook = None
    _ensure_idle()
    return None


def setlat(*args):
    """
    Set the lattice constants for the current sample.

    Parameters
    ----------
    a, b, c, alpha, beta, gamma : float, optional
        Lattice constants.
        - If all 6 are provided as arguments, they are used directly.
        - If none are provided, the user will be prompted interactively.

    Notes
    -----
    If two orienting reflections are defined, UB will be recomputed automatically.
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample

    # Current lattice values
    param_names = sample.lattice.system_parameter_names(0)
    current_values = [getattr(sample.lattice, p) for p in param_names]

    # Case 1: direct arguments
    if len(args) == 6:
        new_values = args

    # Case 2: interactive input
    elif len(args) == 0:
        new_values = []
        for name, current in zip(param_names, current_values, strict=False):
            try:
                val = input(f"Lattice {name} ({current})? ") or current
                new_values.append(float(val))
            except ValueError:
                print(f"Invalid input for {name}, keeping old value {current}.")
                new_values.append(current)

    else:
        raise ValueError(
            "Provide either 0 or 6 arguments: a, b, c, alpha, beta, gamma."
        )

    # Apply new lattice parameters
    for name, val in zip(param_names, new_values, strict=False):
        setattr(sample.lattice, name, float(val))

    # Recompute UB if orienting reflections exist
    if len(sample.reflections.order) > 1:
        compute_UB()
        #print("Computing UB...")
        #sample.core.calc_UB(
        #    sample.reflections.order[0], sample.reflections.order[1]
        #)
        #_geom_.forward(1, 0, 0)

    # Final confirmation
    print("\nUpdated lattice parameters:")
    for name in param_names:
        print(f"  {name} = {getattr(sample.lattice, name):.4f}")


def setaz(*args):
    """
    Set the azimuthal reference reflection (h2, k2, l2).

    Always updates the psi counterpart of the active diffractometer (which uses the psi engine).
    If the main diffractometer is currently in a psi constant mode,
    its h2/k2/l2 extras are also updated while preserving the psi value.
    Works regardless of the current mode.

    Parameters
    ----------
    h2, k2, l2 : int or float, optional
        Miller indices of the azimuthal reference reflection.
        If not provided, the user will be prompted interactively.
    """
    _geom_ = get_diffractometer()
    _geom_for_psi_ = oregistry.find(_geom_.name + "_psi")

    # Current reference values from the psi diffractometer
    _h2, _k2, _l2 = list(_geom_for_psi_.core.extras.values())

    # Parse input
    if len(args) == 3:
        h2, k2, l2 = args
    elif len(args) == 0:

        def ask(name, current):
            val = input(f"{name} = ({current})? ") or current
            try:
                return float(val)
            except ValueError:
                print(f"Invalid {name}, keeping {current}")
                return float(current)

        h2 = ask("H", _h2)
        k2 = ask("K", _k2)
        l2 = ask("L", _l2)
    else:
        raise ValueError(
            "Either no arguments or exactly 3 arguments (h, k, l) must be provided."
        )

    extras = {"h2": h2, "k2": k2, "l2": l2}

    # Always set on the psi diffractometer
    _geom_for_psi_.core.extras = extras

    # Always store h2/k2/l2 on the main diffractometer by temporarily
    # switching to psi constant horizontal (the only mode that accepts these
    # extras), preserving any existing psi value, then restoring the mode.
    psi_modes = (
        "psi constant",
        "psi constant vertical",
        "psi constant horizontal",
    )
    current_psi = (
        _geom_.core.extras.get("psi", 0.0)
        if _geom_.core.mode in psi_modes
        else 0.0
    )
    _saved_mode = _geom_.core.mode
    _geom_.core.mode = "psi constant horizontal"
    _geom_.core.extras = {**extras, "psi": current_psi}
    _geom_.core.mode = _saved_mode

    psi = _geom_for_psi_.inverse(0).psi
    print(f"Reference vector = {h2} {k2} {l2} with Psi = {psi:3.2f}")


def show_constraints():
    """
    Show constraints (low, high) and cut point for each real axis.
    """
    _geom_ = get_diffractometer()
    axes = _geom_.real_axis_names
    for axis in axes:
        c = _geom_.core.constraints[axis]
        print(
            "{:>10} - [{:>6}, {:>6}] cut={:>6}".format(
                axis, c.low_limit, c.high_limit, c.cut_point
            )
        )


def reset_constraints():
    """
    Reset all constraints
    """
    _geom_ = get_diffractometer()
    _geom_.core.reset_constraints()
    print("New constraints:")
    show_constraints()


def set_constraints(*args):
    """
    Change constraint values (low/high limits and optional cut point).

    Call patterns
    -------------
    - ``set_constraints()``: prompt interactively for every axis.
    - ``set_constraints(axis)``: prompt interactively for one axis.
    - ``set_constraints(axis, low, high)``: set limits only.
    - ``set_constraints(axis, low, high, cut)``: set limits and cut point.
    - ``set_constraints(low1, high1, ..., low6, high6)``: 12 args, set
      limits for all axes (cut points unchanged).
    - ``set_constraints(low1, high1, cut1, ..., low6, high6, cut6)``: 18
      args, set limits and cut points for all axes.

    Interactive input may supply 2 numbers (low, high) or 3 numbers
    (low, high, cut), separated by spaces or commas. Press Enter to keep
    the current values.
    """
    _geom_ = get_diffractometer()
    axes = _geom_.real_axis_names

    def _apply(axis, tokens):
        """Set limits (and optionally cut) on `axis` from a 2- or 3-token list."""
        c = _geom_.core.constraints[axis]
        c.limits = tokens[0], tokens[1]
        if len(tokens) >= 3:
            c.cut_point = float(tokens[2])

    if len(args) == 18:
        for n, axis in enumerate(axes):
            _apply(axis, args[3 * n : 3 * n + 3])

    elif len(args) == 12:
        for n, axis in enumerate(axes):
            _apply(axis, args[2 * n : 2 * n + 2])

    elif len(args) == 4:
        axis, low, high, cut = args
        _apply(axis, (low, high, cut))

    elif len(args) == 3:
        axis, low, high = args
        _apply(axis, (low, high))

    elif len(args) == 1:
        axis = args[0]
        c = _geom_.core.constraints[axis]
        low, high, cut = c.low_limit, c.high_limit, c.cut_point
        value = (
            input(
                "{} constraints low, high, cut = "
                "[{:3.3f}, {:3.3f}, {:3.3f}]: ".format(axis, low, high, cut)
            )
        ) or [low, high, cut]
        if isinstance(value, str):
            value = value.replace(",", " ").split()
        _apply(axis, value)

    elif len(args) == 0:
        for axis in axes:
            c = _geom_.core.constraints[axis]
            low, high, cut = c.low_limit, c.high_limit, c.cut_point
            value = (
                input(
                    "{:>10} - [{:>6}, {:>6}] cut={:>6}: ".format(
                        axis, low, high, cut
                    )
                )
            ) or [low, high, cut]
            if isinstance(value, str):
                value = value.replace(",", " ").split()
            _apply(axis, value)

    print("New constraints:")
    show_constraints()


def analyzer_configuration(energy=None, d_spacing=None, crystal=None):
    """
    Configure analyzer
        - Select analyzer crystal and determine d-spacing

    Parameters
    ----------

    """
    _geom_ = get_diffractometer()
    d_ana = _geom_.ana.d_spacing.get()
    crystal_current = _geom_.ana.crystal.get()

    if d_ana != 1e4 or d_spacing:
        print(f"Current analyzer: {crystal_current} with d_spacing = {d_ana}")
        print(f"change to: {crystal} with d_spacing = {d_spacing}")
        _geom_.ana.d_spacing.put(d_spacing)
        if crystal:
            _geom_.ana.crystal.put(crystal)
    else:
        _geom_.ana.setup(energy)


def analyzer_set():
    """
    Set analyzer

    Parameters
    ----------

    """
    _geom_ = get_diffractometer()
    _geom_.ana.calc()


def analyzer_get():
    """
    Get current analyzer

    Parameters
    ----------

    """
    _geom_ = get_diffractometer()
    d_ana = _geom_.ana.d_spacing.get()
    crystal = _geom_.ana.crystal.get()

    if d_ana != 1e4:
        print(f"Current analyzer: {crystal} with d_spacing = {d_ana}")
    else:
        print("Aanalyzer not selected yet. Run analyzer_configuration() first!")

def update_lattice(lattice_constant=None):
    """
    Update lattice constants.

    Parameters
    ----------
    lattice_constant: string, optional
        a, b or c or auto (default)
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample
    a = sample.lattice.a
    b = sample.lattice.b
    c = sample.lattice.c
    alpha = sample.lattice.alpha
    beta = sample.lattice.beta
    gamma = sample.lattice.gamma
    hh = _geom_.h.position
    kk = _geom_.k.position
    ll = _geom_.l.position

    if round(hh) == 0 and round(kk) == 0:
        lattice_auto = "c"
    elif round(hh) == 0 and round(ll) == 0:
        lattice_auto = "b"
    elif round(kk) == 0 and round(ll) == 0:
        lattice_auto = "a"
    else:
        lattice_auto = None
    if not lattice_constant:
        lattice_constant = (
            input("Lattice parameter (a, b, or c or [auto])? ") or lattice_auto
        )
    else:
        print("Specify lattice parameter 'a', 'b' or 'c' or none")
    if lattice_constant == "a" and abs(round(hh)) > 0:
        a = a / hh * round(hh)
    elif lattice_constant == "b" and abs(round(kk)) > 0:
        b = b / kk * round(kk)
    elif lattice_constant == "c" and abs(round(ll)) > 0:
        c = c / ll * round(ll)
    else:
        if lattice_constant:
            print(
                f"Updating lattice parameter {lattice_constant} not possible. "
            )
        else:
            print(
                "Auto calc not possible. Specify lattice parameter to refine."
            )

        return
    print("Refining lattice parameter {}".format(lattice_constant))
    sample.lattice.a = float(a)
    sample.lattice.b = float(b)
    sample.lattice.c = float(c)
    sample.lattice.alpha = float(alpha)
    sample.lattice.beta = float(beta)
    sample.lattice.gamma = float(gamma)
    if len(sample.reflections.order) > 1:
        compute_UB()
        #print("Computing UB...")
        #sample.core.calc_UB(
        #    sample.reflections.order[0],
        #    sample.reflections.order[1],
        #)
        #_geom_.forward(1, 0, 0)
    print(
        "\n   H K L = {:5.4f} {:5.4f} {:5.4f}".format(
            _geom_.h.position,
            _geom_.k.position,
            _geom_.l.position,
        )
    )
    print(
        "   a, b, c, alpha, beta, gamma = {:5.4f} {:5.4f} {:5.4f} {:5.4f} {:5.4f} {:5.4f}".format(
            sample.lattice.a,
            sample.lattice.b,
            sample.lattice.c,
            sample.lattice.alpha,
            sample.lattice.beta,
            sample.lattice.gamma,
        )
    )


def write_config(filename="default", overwrite=False):
    """
    Write diffractometer configuration to file in current directory.

    Parameters
    ----------
    method : string, optional
        Only "File" is currently supported.
    overwrite : bool, optional
        If False, asks for confirmation before overwriting an existing file.
    """
    _geom_ = get_diffractometer()
    file = pathlib.Path(f"{filename}_polar_config.yml")
    if file.exists() and not overwrite:
        answer = input(f"File '{file}' already exists. Overwrite? ([y]/n): ")
        if answer.strip().lower() == "n":
            print("Configuration file not written.")
            return
    _geom_.export(str(file), comment="4-ID-G POLAR beamline")
    print(f"Configuration written to '{file}'.")


def _prompt_clear_mode(config, source="file"):
    """
    List user-defined samples and ask whether to overwrite or append.

    Parameters
    ----------
    config : dict
        Configuration mapping (expects an optional ``"samples"`` key).
    source : str
        Noun used in the "samples in this ..." message (e.g. ``"file"`` or
        ``"configuration"``).

    Returns
    -------
    bool or None
        ``True`` to overwrite, ``False`` to append, or ``None`` if the user
        cancelled (caller should abort without loading).
    """
    file_samples = [k for k in config.get("samples", {}) if k != "sample"]
    if file_samples:
        print(f"\nSamples in this {source}:")
        for s in file_samples:
            print(f"  {s}")
    else:
        print("\nNo user-defined samples found in this file.")

    mode = (
        input(
            "\nOverwrite current configuration or append? "
            "([o]verwrite/[a]ppend): "
        )
        .strip()
        .lower()
    )
    if mode == "a":
        return False
    elif mode == "o":
        return True
    print("Configuration not loaded.")
    return None


def read_config():
    """
    Read diffractometer configuration from file in current directory.

    Lists all files matching *_polar_config.yml, prompts the user to select
    one, and loads it. Defaults to default_polar_config.yml if it exists.
    """
    _geom_ = get_diffractometer()
    files = sorted(pathlib.Path(".").glob("*_polar_config.yml"))
    if not files:
        print("No *_polar_config.yml files found in current directory.")
        return

    default_file = pathlib.Path("default_polar_config.yml")
    default_idx = next((i for i, f in enumerate(files) if f == default_file), 0)

    print("\nAvailable configuration files:")
    for i, f in enumerate(files):
        marker = " (default)" if f == default_file else ""
        print(f"  {i}: {f}{marker}")

    answer = input(f"\nSelect file to load [{default_idx}]: ").strip()
    try:
        idx = int(answer) if answer else default_idx
        file = files[idx]
    except (ValueError, IndexError):
        print("Invalid selection. Configuration not loaded.")
        return

    with open(file) as f:
        config = yaml.safe_load(f)

    clear = _prompt_clear_mode(config, source="file")
    if clear is None:
        return

    print(f"Loading '{file}'...")
    # hklpy2 changed restore() defaults: on hardware-backed diffractometers
    # `restore_samples` / `restore_extras` default to False. Pass them
    # explicitly so the YAML's samples and azimuthal-reference extras are
    # actually applied. Wavelength and mode are intentionally left at the
    # current values to avoid silently retargeting motors.
    _geom_.restore(
        str(file),
        clear=clear,
        restore_samples=True,
        restore_extras=True,
        restore_constraints=True,
    )

    # Touch the psi-mode geometry so a missing entry surfaces here rather
    # than later inside compute_UB() / a scan plan.
    _ = oregistry.find(_geom_.name + "_psi")
    compute_UB()


def restore_diffractometer_from_scan(
    scan_id, diffractometer=None, clear=None
):
    """
    Restore diffractometer orientation from a previous scan.

    Parameters
    ----------
    scan_id : int or string
        Scan ID to restore orientation from.
    diffractometer : diffractometer object, optional
        Diffractometer to restore. Defaults to the current diffractometer.
    clear : bool or None
        Option to clear any previous diffractometer setup or append it. User
        will be asked if None.
    """

    info = get_run_orientation(cat[scan_id])

    if diffractometer is None:
        diffractometer = get_diffractometer()

    name = diffractometer.name
    labels = list(info.keys())

    if not labels:
        uid = cat[scan_id].metadata["start"]["uid"]
        raise ValueError(
            f"The scan #{scan_id} ({uid = }) does not have any hklpy2 "
            "configuration saved."
        )

    if name not in labels:
        uid = cat[scan_id].metadata["start"]["uid"]

        print(f"{name} was not found in the scan #{scan_id} ({uid = }).")

        print("Available options are: ")
        for label in labels:
            print(label)

        name = input(f"Enter diffractometer name ({labels[0]}): ") or labels[0]
        if name not in labels:
            raise ValueError(
                f"'{name}' is not in scan #{scan_id}. "
                f"Available: {', '.join(labels)}."
            )

    config = info[name]

    if clear is None:
        clear = _prompt_clear_mode(config, source="configuration")
        if clear is None:
            return

    diffractometer.restore(
        config,
        clear=clear,
        restore_samples=True,
        restore_extras=True,
        restore_constraints=True,
    )

    # Mirror read_config(): surface a missing psi-mode geometry here and
    # recompute the UB from the restored reflections rather than trusting the
    # stored matrix.
    _ = oregistry.find(diffractometer.name + "_psi")
    compute_UB()


def set_detector():
    """
    Interactively select detector on Huber detectorarm to be used.
    Detectors are mounted 25 degrees apart from each other in delta

    Prompts the user for:
      - Detector: (E)iger or (P)oint Detector/Analyzer

    Uses defaults if the user just presses Enter.
    """
    offset = caget("4idgSoft:m20.OFF")
    if offset == 25:
        dets = "Eiger"
    elif offset == 0:
        dets = "Point detector/Analyzer"
    else:
        dets = "undefined"
    det = input(f"(E)iger or (P)oint Detector/Analyzer [{dets}]: ") or dets
    if det in ("Point detector/Analyzer", "Point detector", "point detector", "p", "P"):
        caput("4idgSoft:m20.OFF", 0)
        print("Current detector: Point detector/Aanalyzer")
    elif det in ("Eiger", "eiger", "e", "E"):
        caput("4idgSoft:m20.OFF", 25)
        print("Current detector: Eiger")
    else:
        print("Select Eiger or Point Detector")
        print(f"Current detector: {dets}")


class whClass:
    """
    _wh function used without parenthesis
    """

    def __repr__(self):
        print("")
        try:
            _wh()
        except Exception:
            pass
        return ""


wh = whClass()


def theta0():
    """
    Calculate 2-theta zero-offset and lattice parameter ``a0`` for a cubic sample.

    Reads the current wavelength from the diffractometer beam object,
    displays the saved reflection list, asks the user to choose two
    reflections by index, then computes the zero-shift and ``a0`` from
    those two reflections (Brueckel 1994).

    Assumes horizontal scattering geometry (``gamma = 2*theta``,
    ``delta = 0``).
    """
    _geom_ = get_diffractometer()
    sample = _geom_.sample

    wavelength = _geom_.beam.wavelength.get()
    energy = _geom_.beam.energy.get()
    print(f"\n   Lambda = {wavelength:.4f} Å  ({energy:.4f} keV)")
    print("   CALCULATES ZERO-SHIFT AND A0 FOR CUBIC SYSTEMS\n")

    orienting_refl = sample.reflections.order
    idx_width = 3
    pseudo_width = 9
    real_width = 10

    if len(_geom_.real_positioners) == 6:
        real_headers = ["Gamma", "Mu", "Chi", "Phi", "Delta", "Tau"]
    else:
        real_headers = list(_geom_.real_positioners._fields)

    header = (
        f"\n{'#':>{idx_width}}"
        + "".join(
            f"{m:>{pseudo_width}}" for m in _geom_.pseudo_positioners._fields
        ).upper()
        + "".join(f"{k:>{real_width}}" for k in real_headers)
        + "   orienting"
    )
    print(header)

    keys = list(sample.reflections.keys())
    for i, (key, ref) in enumerate(sample.reflections.items()):
        h, k, l = list(ref.pseudos.values())  # noqa: E741
        if len(_geom_.real_positioners) == 6:
            reals = ref.reals
            pos_vals = [
                reals["gamma"],
                reals["mu"],
                reals["chi"],
                reals["phi"],
                reals["delta"],
                reals["tau"],
            ]
        else:
            pos_vals = list(ref.reals.values())

        tag = ""
        if orienting_refl and key == orienting_refl[0]:
            tag = "first"
        elif len(orienting_refl) > 1 and key == orienting_refl[1]:
            tag = "second"

        row = (
            f"{i:>{idx_width}}"
            f"{h:{pseudo_width}.3f}{k:{pseudo_width}.3f}"
            f"{l:{pseudo_width}.3f}"
            + "".join(f"{v:{real_width}.3f}" for v in pos_vals)
            + (f"   {tag}" if tag else "")
        )
        print(row)

    i1_old, i2_old = 0, 1
    if len(orienting_refl) > 0:
        i1_old = keys.index(orienting_refl[0])
    if len(orienting_refl) > 1:
        i2_old = keys.index(orienting_refl[1])

    try:
        i1 = int(input(f"\nFirst reflection ({i1_old})? ") or i1_old)
        i2 = int(input(f"Second reflection ({i2_old})? ") or i2_old)
    except ValueError:
        print("Invalid input. Aborting.")
        return

    if not (0 <= i1 < len(keys) and 0 <= i2 < len(keys)):
        print("Index out of range. Aborting.")
        return
    if i1 == i2:
        print("Both reflections are the same. Aborting.")
        return

    ref1 = sample.reflections[keys[i1]]
    ref2 = sample.reflections[keys[i2]]

    xh1, xk1, xl1 = list(ref1.pseudos.values())
    xh2, xk2, xl2 = list(ref2.pseudos.values())

    if len(_geom_.real_positioners) == 6:
        zt1 = ref1.reals["gamma"]
        zt2 = ref2.reals["gamma"]
    else:
        pos1 = list(ref1.reals.values())
        pos2 = list(ref2.reals.values())
        zt1 = pos1[0]
        zt2 = pos2[0]

    xla = wavelength

    PI180 = math.pi / 180
    xt1 = zt1 / 2.0
    xt2 = zt2 / 2.0
    xb1 = xh1**2 + xk1**2 + xl1**2
    xb2 = xh2**2 + xk2**2 + xl2**2
    xb = math.sqrt(xb2 / xb1)
    xttttz = xb * math.sin(xt1 * PI180) - math.sin(xt2 * PI180)
    xttttN = xb * math.cos(xt1 * PI180) - math.cos(xt2 * PI180)
    xtet0 = math.atan(xttttz / xttttN) / PI180
    xlah = xla / 2.0
    a01 = xlah * math.sqrt(xb1) / math.sin(PI180 * (xt1 - xtet0))
    a02 = xlah * math.sqrt(xb2) / math.sin(PI180 * (xt2 - xtet0))
    zt1_corr = zt1 - 2 * xtet0
    zt2_corr = zt2 - 2 * xtet0

    print(f"\n   2*THETA ZERO-SHIFT      = {2 * xtet0:10.4f} deg")
    print(f"   A0 (from refl {i1}, {i2})  = {a01:10.5f}  {a02:10.5f} Å")
    print(
        f"   CORRECTED 2*THETA       = {zt1_corr:10.4f}  "
        f"{zt2_corr:10.4f} deg"
    )
