"""
Utility functions and short convenience wrappers for common session
operations.

.. autosummary::
    ~plotselect
    ~set_counting_time
    ~list_functions
    ~opt
    ~crl_setup
    ~crl_size
    ~piezo_jena_setup
    ~te
    ~spec_off
    ~spec_on
    ~plots_on
    ~plots_off

"""

import pathlib
from datetime import datetime
from inspect import getmembers
from inspect import isfunction

from apsbits.core.instrument_init import oregistry

from id4_common.plans.peak_position import cen
from id4_common.plans.peak_position import maxi
from id4_common.utils import hkl_utils
from id4_common.utils.counters_class import counters

try:
    from hkl import user
    from hkl import util
except ModuleNotFoundError:
    user = util = None


try:
    from polartools import absorption
    from polartools import area_detector_handlers
    from polartools import diffraction
    from polartools import load_data
    from polartools import manage_database
    from polartools import pressure_calibration
    from polartools import process_images
except ModuleNotFoundError:
    load_data = diffraction = absorption = None
    pressure_calibration = process_images = None
    area_detector_handlers = manage_database = None

try:
    from apstools import utils
except ModuleNotFoundError:
    utils = None

__all__ = """
    plotselect
    set_counting_time
    list_functions
    opt
    crl_setup
    crl_size
    piezo_jena_setup
    te
    spec_off
    spec_on
    plots_on
    plots_off
    hkl_utils
    user
    util
    absorption
    area_detector_handlers
    diffraction
    load_data
    manage_database
    pressure_calibration
    process_images
    utils
    path
""".split()

path = pathlib.Path("startup_experiment.py")


def plotselect(dets=None, mon=None):
    """
    Selects detectors and monitor plotted during scan.
    Delegates to counters.plotselect().
    """
    counters.plotselect(dets=dets, mon=mon)


def _select_monitor():
    """Display enumerated channels from scaler1/scaler2 and return chosen channel name."""
    all_options = counters.detectors_plot_options
    scaler_rows = all_options[
        all_options["detectors"].isin(["scalers", "scaler1", "scaler2"])
    ]
    print(scaler_rows[["channels", "detectors"]].to_string())
    current_mon = counters.monitor
    mon_matches = scaler_rows[scaler_rows["channels"] == current_mon].index
    current_idx = (
        int(mon_matches[0]) if len(mon_matches) else int(scaler_rows.index[0])
    )
    idx = input(f"Monitor index [{current_idx}]: ") or current_idx
    return all_options.loc[int(idx), "channels"]


def set_counting_time(time=None, monitor=False):
    """
    Sets counting time / monitor counts:
        time <  200: counting time in seconds
        time >= 200: monitor counts
    """
    scalers = counters._available_scalers

    def _set_time(t):
        counters._mon = "Time"
        for scaler in scalers:
            scaler.preset_monitor.put(t)

    def _set_monitor(mon, counts):
        counters._mon = mon
        counters.monitor_counts = counts

    if time:
        if monitor:
            if monitor != "Time" and time > 199:
                _set_monitor(monitor, time)
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        monitor, time
                    )
                )
            elif monitor == "Time" and time < 200:
                _set_time(time)
                print("New counting time = {}".format(time))
            else:
                raise ValueError("Counting time of {} too high.".format(time))
        else:
            if time < 200:
                _set_time(time)
                print("New counting time: {} s".format(time))
            else:
                _set_monitor(counters.monitor, time)
                print(
                    "Counting against monitor '{}' for {} counts".format(
                        counters.monitor, time
                    )
                )
    else:
        if counters.monitor == "Time":
            current = scalers[0].preset_monitor.get() if scalers else 1
        else:
            current = counters.monitor_counts
        time = input("Counting time/counts [{}]: ".format(current)) or current
        time = float(time)
        if time < 100:
            _set_time(time)
            print("New counting time: {} s".format(time))
        else:
            monitor = _select_monitor()
            _set_monitor(monitor, int(time))
            print(
                "Counting against monitor '{}' for {} counts".format(
                    monitor, int(time)
                )
            )


def list_functions(select=None):
    """
    List available functions

    select: string, optional
        None: all packages
        "absorption": functions related to absorption experiments
        "diffraction": functions related to diffraction experiments
        "hklpy": functions related to reciprocal space
    """
    if select == "absorption":
        packages = [absorption]
    elif select == "diffraction":
        packages = [load_data, diffraction, utils]
    elif select == "hklpy":
        packages = [user, util]
    else:
        packages = [
            hkl_utils,
            load_data,
            diffraction,
            absorption,
            pressure_calibration,
            process_images,
            area_detector_handlers,
            manage_database,
            utils,
            user,
            util,
        ]

    for item in packages:
        function_list = getmembers(item, isfunction)
        print("-" * len(item.__name__))
        print(item.__name__)
        print("-" * len(item.__name__))
        for funct in function_list:
            print(funct[0])


def opt(method="cen"):
    """
    Move positioner of last scan to center of last scan

    usage: RE(opt())
        optional argument: 	method = 'cen' (default)
                                                method = 'max'


    """
    cat = load_data.load_catalog("4id_polar")
    motor = cat[-1].metadata["start"]
    rmotor = ".".join(motor["motors"][0].rsplit("_", 1))
    positioner = oregistry.find(motor["motors"][0])
    time = datetime.now() - datetime.fromtimestamp(motor["time"])

    if time.seconds < 60:
        if method == "cen":
            yield from cen(positioner=positioner, confirm=False)
        elif method == "max":
            yield from maxi(positioner=positioner, confirm=False)

    else:
        inp = input(f"Move {rmotor} to center (Y/[N])? ")
        if inp in ["Y", "y", "yes"]:
            if method == "cen":
                yield from cen(positioner=positioner, confirm=False)
            elif method == "max":
                yield from maxi(positioner=positioner, confirm=False)


def crl_setup(hutch=None):
    """
    Switch the CRL sample-position offset to the active hutch.

    Delegates to :meth:`CRLClass.select_g` / ``select_h``, which
    write to the IOC's ``ZOffsetToggle`` PV.  The per-hutch offset values
    themselves live on the device as ``crl.offset_g`` / ``offset_h`` and
    are not changed here.

    Parameters
    ----------
    hutch : {'g', 'h'}, optional
        Hutch to switch to.  Case-insensitive, accepts ``"G"`` / ``"H"``
        and the longer aliases ``"diffractometer"`` (= G) /
        ``"magnet"`` (= H) for backwards compatibility.  When ``None``
        (default), prompt interactively.
    """
    if hutch is None:
        hutch = input("Hutch (G / H) [G]: ").strip().lower() or "g"
    else:
        hutch = str(hutch).strip().lower()

    crl_dev = oregistry.find("crl")

    if hutch in ("g", "diffractometer") or hutch.startswith("d"):
        crl_dev.select_g()
        label = "G (diffractometer)"
    elif (
        hutch in ("h", "magnet")
        or hutch.startswith("m")
        or hutch.startswith("9")
    ):
        crl_dev.select_h()
        label = "H (magnet)"
    else:
        print(f"Unknown hutch '{hutch}'.  Choose 'G' or 'H'.")
        return

    print(f"CRL sample-position offset set for {label}.")


def crl_size(focal_size):
    """
    Set the CRL focal size.

    Renamed from ``crl`` so the function does not shadow the ``crl``
    device that ``load_device("crl")`` injects into the session
    namespace.

    Parameters
    ----------
    focal_size : float
        Target focal size in microns. If < 5 µm, the device's
        ``minimize_button`` is triggered instead of writing a setpoint.
        Otherwise the value is written to ``crl.beamsize`` (which handles
        the microns -> meters conversion internally).
    """
    focal_size = float(focal_size)
    crl_dev = oregistry.find("crl")
    if focal_size < 5:
        crl_dev.minimize_button.put(1)
    else:
        crl_dev.beamsize.set(focal_size)


def piezo_jena_setup():
    """
    Check and change the modulation-input state of the PiezoJena device.
    This needs to be turned ON to allow analog input from the FPGA used for
    fly scanning, which is trigering the Eiger detector and reading the
    interferometers of the sample position.

    For each axis (x, y, z), reads the current modulation-input state
    (ON / OFF) and prompts for a new value with the current state shown as
    the default. Accepts ``on`` / ``off`` (case-insensitive); pressing
    Enter keeps the current state.
    """
    piezo = oregistry.find("piezo_jena")

    def _label(raw):
        if not raw:
            return "OFF"
        return "ON" if str(raw).strip().split(",")[-1].strip() == "1" else "OFF"

    for axis in ("x", "y", "z"):
        status = piezo.read_status(axis)
        current = _label(status)
        ans = (
            input(f"  {axis} modulation input (ON/OFF) [{current}]? ")
            .strip()
            .lower()
        )

        if not ans:
            new_state = current
        elif ans in ("on", "1"):
            new_state = "ON"
        elif ans in ("off", "0"):
            new_state = "OFF"
        else:
            print(f"  Invalid value '{ans}', keeping {current}")
            new_state = current

        if new_state == current:
            print(f"  {axis}: {current} (unchanged)")
            continue

        if new_state == "ON":
            piezo.modulation_input_on(axis)
        else:
            piezo.modulation_input_off(axis)
        print(f"  {axis}: {current} -> {new_state}")


def te(temperature):
    """
    Set the active temperature controller's setpoint.

    Thin shortcut over the ``tc`` signal installed by
    :func:`id4_common.utils.temperature_setup.temperature_setup`.  Writes
    the setpoint and returns immediately; the controller continues ramping
    toward the target on its own.

    Parameters
    ----------
    temperature : float
        Target temperature setpoint.

    Raises
    ------
    RuntimeError
        ``temperature_setup()`` has not been run, so there is no active
        controller to talk to.
    """
    from .temperature_setup import get_active_label
    from .temperature_setup import get_active_tc

    tc = get_active_tc()
    if tc is None:
        raise RuntimeError(
            "No active temperature controller.  Run "
            "`temperature_setup('<label>')` first (see "
            "id4_common.utils.temperature_setup.TEMPERATURE_CONTROLLERS "
            "for the available labels)."
        )
    tc.setpoint.put(float(temperature))
    print(f"{get_active_label()}: setpoint -> {float(temperature)}")


def _spec_writer_tokens():
    """Return the RE subscription tokens currently bound to specwriter."""
    from id4_common.callbacks.spec_data_file_writer import specwriter
    from id4_common.utils.run_engine import RE

    tokens = []
    for tok, entry in RE.dispatcher.cb_registry.callbacks.items():
        # bluesky has changed the cb_registry value shape across
        # versions: either the bare callable or (callable, kwargs).
        cb = entry[0] if isinstance(entry, tuple) else entry
        if cb is specwriter.receiver:
            tokens.append(tok)
    return tokens


def spec_off():
    """Unsubscribe the SPEC file writer from the RunEngine.

    No-op (returns 0) if the writer is already unsubscribed. Pair with
    :func:`spec_on` to re-enable.
    """
    from id4_common.utils.run_engine import RE

    tokens = _spec_writer_tokens()
    for tok in tokens:
        RE.unsubscribe(tok)
    print(f"SPEC writer: off ({len(tokens)} subscription(s) removed)")
    return len(tokens)


def spec_on():
    """Re-subscribe the SPEC file writer to the RunEngine.

    No-op if the writer is already subscribed (avoids duplicate output).
    """
    from id4_common.callbacks.spec_data_file_writer import specwriter
    from id4_common.utils.run_engine import RE

    if _spec_writer_tokens():
        print("SPEC writer: already on")
        return None
    token = RE.subscribe(specwriter.receiver)
    print("SPEC writer: on")
    return token


def plots_on():
    """Enable BestEffortCallback live plots."""
    from id4_common.utils.run_engine import bec

    bec.enable_plots()
    print("Live plots: on")


def plots_off():
    """Disable BestEffortCallback live plots."""
    from id4_common.utils.run_engine import bec

    bec.disable_plots()
    print("Live plots: off")
    print("Kestrel can be used for plotting (nefarian.xray.aps.anl.gov:4173)")
