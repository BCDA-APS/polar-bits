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

from apsbits.utils.config_loaders import load_config
from apsbits.utils.config_loaders import load_config_yaml
from apsbits.utils.config_loaders import update_config

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

instrument_path = Path(__file__).parent

iconfig_path = instrument_path.parent / "id4_common" / "configs" / "iconfig.yml"
load_config(iconfig_path)
update_config(
    load_config_yaml(instrument_path / "configs" / "iconfig_extras.yml")
)

logger.info("Starting Instrument with iconfig: %s", iconfig_path)

from id4_common._common_startup import *  # noqa: F401, F403, E402

logger.info("Loading 4-ID-H devices, this can take a few minutes.")
make_devices(clear=True, file="devices.yml", device_manager=instrument)  # noqa: F405
for device in oregistry.findall(["core", "4idh"]):  # noqa: F405
    connect_device(device, raise_error=False)  # noqa: F405

counters.plotselect(11, 0)  # noqa: F405

for sus in shutter_suspenders.values():  # noqa: F405
    RE.install_suspender(sus)  # noqa: F405
