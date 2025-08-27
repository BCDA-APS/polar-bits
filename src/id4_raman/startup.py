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

from apsbits.core.instrument_init import make_devices
from apsbits.core.instrument_init import oregistry
from apsbits.core.instrument_init import instrument  # noqa: F401
from apsbits.utils.aps_functions import aps_dm_setup  # TODO: is this correct?
from apsbits.utils.config_loaders import get_config
from apsbits.utils.config_loaders import load_config
from apsbits.utils.config_loaders import load_config_yaml
from apsbits.utils.config_loaders import update_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from IPython import get_ipython

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

# Get the path to the instrument package
instrument_path = Path(__file__).parent

# Load configuration to be used by the instrument.

# First the general iconfig
iconfig_path = instrument_path.parent / "id4_common" / "configs" / "iconfig.yml"
load_config(iconfig_path)

# Load extras for this station and update the config
extras = load_config_yaml(instrument_path / "configs" / "iconfig_extras.yml")
update_config(extras)

# Get the configuration
iconfig = get_config()

logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# Discard oregistry items loaded above.
oregistry.clear()

# Configure the session with callbacks, devices, and plans.
aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

from id4_common.utils.local_magics import LocalMagics  # noqa: E402
get_ipython().register_magics(LocalMagics)

# Initialize core bluesky components
from id4_common.utils.run_engine import (  # noqa: F401, E402
    RE,
    sd,
    bec,
    cat as full_cat,  # This is the whole beamline catalog, below we narrow it.
    peaks
)

# Import optional components based on configuration
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    # from .callbacks.nexus_data_file_writer import nxwriter_init
    # nxwriter = nxwriter_init(RE)
    from id4_common.callbacks.nexus_data_file_writer import (  # noqa: F401
        nxwriter
    )

if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from id4_common.callbacks.spec_data_file_writer import (  # noqa: F401
        init_specwriter_with_RE,
        newSpecFile,
        spec_comment,
        specwriter
    )

    init_specwriter_with_RE(RE)
    # Remove specwritter preprocessor --> the extra stream tried to trigger
    # devices that are disconnected.
    _ = RE.preprocessors.pop()

from id4_common.callbacks.dichro_stream import (  # noqa: F401, E402
    dichro, plot_dichro_settings, dichro_bec
)

# These imports must come after the above setup.
if running_in_queueserver():
    # To make all the standard plans available in QS, import by '*', otherwise
    # import plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403, F401
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    # from apstools.plans import *  # noqa: F401, F403
    # from apstools.utils import *  # noqa: F401, F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

    from id4_common.suspenders.shutters_suspenders import (  # noqa: F401
        shutter_suspenders,
    )
    from id4_common.suspenders.suspender_utils import (  # noqa: F401
        suspender_restart,
        suspender_stop,
        suspender_change_sleep
    )

    from id4_common.utils.wax import wm, wax, wa_new  # noqa: F401
    from id4_common.utils.counters_class import counters  # noqa: F401
    from id4_common.utils.pr_setup import pr_setup  # noqa: F401
    from id4_common.utils.attenuator_utils import atten  # noqa: F401
    from id4_common.utils.dm_utils import *  # noqa: F401, F403
    from id4_common.utils.experiment_utils import *  # noqa: F401, F403
    from id4_common.utils.hkl_utils import *  # noqa: F401, F403

    # TODO: DM, hklpy, experiment_utils seems to be changing the
    # logging level. I don't know why.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    from id4_common.utils.polartools_hklpy_imports import *  # noqa: F401, F403
    from id4_common.utils.oregistry_auxiliar import get_devices  # noqa: F401
    from id4_common.utils.load_vortex import load_vortex  # noqa: F401
    from id4_common.utils.device_loader import (  # noqa: F401
        load_yaml_devices,
        find_loadable_devices,
        load_device,
        remove_device,
        connect_device,
        reload_all_devices,
    )

    from id4_common.plans import *  # noqa: F401, F403

logger.info("Loading 4-ID-B devices, this can take a few minutes.")
RE(make_devices(clear=True, file="devices.yml"))  # Create the devices.
stations = ["4idb"]
for device in oregistry.findall(stations):
    connect_device(device, raise_error=False)

counters.plotselect(11, 0)

for sus in shutter_suspenders.values():
    RE.install_suspender(sus)

# Use a subset of the catalog - just for this station
# This helps sorting up if there is a mix up of the scan_ids when using
# two stations at the same time.
cat = db_query(  # noqa: F405
    full_cat,
    dict(instrument_name=f'polar-{iconfig["STATION"]}')
)

# TODO: REMOVE THIS AFTER UPSTREAM FIX
_ = RE.preprocessors.pop()
