"""
Utility functions.

.. autosummary::
    ~plotselect
    ~set_counting_time
    ~list_functions

"""

from inspect import getmembers, isfunction
import fileinput
import pathlib
import sys

from id4_common.utils.run_engine import RE
from id4_common.utils import hkl_utils_hklpy2
from id4_common.utils.counters_class import counters

try:
    from hkl import user, util
except ModuleNotFoundError:
    user = util = None


try:
    from polartools import (
        load_data,
        diffraction,
        absorption,
        pressure_calibration,
        process_images,
        area_detector_handlers,
        manage_database,
    )
except ModuleNotFoundError:
    load_data = diffraction = absorption = None
    pressure_calibration = process_images = None
    area_detector_handlers = manage_database = None

try:
    from apstools import utils
except ModuleNotFoundError:
    utils = None

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
    current_idx = int(mon_matches[0]) if len(mon_matches) else int(scaler_rows.index[0])
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
                print("Counting against monitor '{}' for {} counts".format(monitor, time))
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
                print("Counting against monitor '{}' for {} counts".format(
                    counters.monitor, time
                ))
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
            print("Counting against monitor '{}' for {} counts".format(monitor, int(time)))



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
            hkl_utils_hklpy2,
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
