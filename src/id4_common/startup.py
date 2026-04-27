"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

import logging
from pathlib import Path

from apsbits.utils.config_loaders import get_config
from apsbits.utils.config_loaders import load_config

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

# Get the path to the instrument package
instrument_path = Path(__file__).parent

# Load configuration to be used by the instrument.
iconfig_path = instrument_path / "configs" / "iconfig.yml"
load_config(iconfig_path)

iconfig = get_config()  # noqa: F841

logger.info("Starting Instrument with iconfig: %s", iconfig_path)

from ._common_startup import *  # noqa: F401, F403, E402

_load_devices = input("\n==> Do you want to load all devices? [Y/n]: ") or "y"

try:
    if _load_devices.lower() in ["y", "yes"]:
        logger.info("Loading all devices, this can take a few minutes.")

        make_devices(clear=True, file="devices.yml", device_manager=instrument)  # noqa: F405
        stations = ["core", "4idb", "4idg", "4idh"]
        for device in oregistry.findall(stations):  # noqa: F405
            connect_device(device, raise_error=False)  # noqa: F405

        counters.plotselect(11, 0)  # noqa: F405

        # Diffractometer
        select_diffractometer(get_huber_euler())  # noqa: F405
        select_engine_for_psi(get_huber_euler_psi())  # noqa: F405
    else:
        logger.info(
            "No device has been loaded. Please see the reload_all_devices, "
            "load_device, and find_loadable_devices functions for options to "
            "load devices."
        )
except AttributeError:
    logger.info(
        "No device has been loaded. Please see the reload_all_devices, "
        "load_device, and find_loadable_devices functions for options to "
        "load devices."
    )

for sus in shutter_suspenders.values():  # noqa: F405
    RE.install_suspender(sus)  # noqa: F405
