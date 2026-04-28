"""
Common startup logic shared by all POLAR beamline startups.

Import this module AFTER loading the instrument config via load_config /
update_config.  The config singleton must be populated before this module
is first imported because several objects here are built at import time
(instrument, RE, bec, …).

Usage in an instrument startup::

    load_config(...)
    update_config(extras)
    from id4_common._common_startup import *  # noqa: F401, F403
    # then do station-specific device loading
"""

import logging

from apsbits.core.instrument_init import init_instrument
from apsbits.utils.config_loaders import get_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from IPython import get_ipython

from id4_common.utils.aps_functions import aps_dm_setup
from id4_common.utils.make_devices import make_devices  # noqa: F401

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

iconfig = get_config()

instrument, oregistry = init_instrument("guarneri")
oregistry.clear()

aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

register_bluesky_magics()

from id4_common.utils.local_magics import LocalMagics  # noqa: E402

get_ipython().register_magics(LocalMagics)

from id4_common.utils.run_engine import RE  # noqa: E402
from id4_common.utils.run_engine import bec  # noqa: F401, E402
from id4_common.utils.run_engine import cat as cat_full  # noqa: F401, E402
from id4_common.utils.run_engine import cat_legacy  # noqa: F401, E402
from id4_common.utils.run_engine import peaks  # noqa: F401, E402
from id4_common.utils.run_engine import sd  # noqa: F401, E402

if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from id4_common.callbacks.nexus_data_file_writer import (
        nxwriter,  # noqa: F401
    )

if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from id4_common.callbacks.spec_data_file_writer import (
        init_specwriter_with_RE,
    )
    from id4_common.callbacks.spec_data_file_writer import (
        newSpecFile,  # noqa: F401
    )
    from id4_common.callbacks.spec_data_file_writer import (
        spec_comment,  # noqa: F401
    )
    from id4_common.callbacks.spec_data_file_writer import (
        specwriter,  # noqa: F401
    )

    init_specwriter_with_RE(RE)
    # Remove specwriter preprocessor — the extra stream tried to trigger
    # devices that are disconnected.
    _ = RE.preprocessors.pop()

from id4_common.callbacks.dichro_stream import dichro  # noqa: F401, E402
from id4_common.callbacks.dichro_stream import dichro_bec  # noqa: F401, E402
from id4_common.callbacks.dichro_stream import (  # noqa: F401, E402
    plot_dichro_settings,
)

if running_in_queueserver():
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403
else:
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

    from id4_common.suspenders.shutters_suspenders import shutter_suspenders
    from id4_common.suspenders.suspender_utils import (  # noqa: F401
        suspender_change_sleep,
    )
    from id4_common.suspenders.suspender_utils import (
        suspender_restart,  # noqa: F401
    )
    from id4_common.suspenders.suspender_utils import (
        suspender_stop,  # noqa: F401
    )
    from id4_common.utils.attenuator_utils import atten  # noqa: F401
    from id4_common.utils.counters_class import counters  # noqa: F401
    from id4_common.utils.dm_utils import *  # noqa: F403
    from id4_common.utils.experiment_utils import *  # noqa: F403
    from id4_common.utils.hkl_utils import *  # noqa: F403
    from id4_common.utils.pr_setup import pr_setup  # noqa: F401
    from id4_common.utils.shorts import opt  # noqa: F401
    from id4_common.utils.undulator_setup import undulator_setup  # noqa: F401
    from id4_common.utils.wax import wa_new  # noqa: F401
    from id4_common.utils.wax import wax  # noqa: F401
    from id4_common.utils.wax import wm  # noqa: F401

    # TODO: DM, hklpy, experiment_utils seems to be changing the
    # logging level. I don't know why.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    from id4_common.plans import *  # noqa: F403
    from id4_common.utils.device_loader import connect_device  # noqa: F401
    from id4_common.utils.device_loader import (
        find_loadable_devices,  # noqa: F401
    )
    from id4_common.utils.device_loader import load_device  # noqa: F401
    from id4_common.utils.device_loader import load_yaml_devices  # noqa: F401
    from id4_common.utils.device_loader import reload_all_devices  # noqa: F401
    from id4_common.utils.device_loader import remove_device  # noqa: F401
    from id4_common.utils.load_vortex import load_vortex  # noqa: F401
    from id4_common.utils.oregistry_auxiliar import get_devices  # noqa: F401
    from id4_common.utils.polartools_hklpy_imports import *  # noqa: F403

# Use only the A shutter suspender, but the B shutter is still there.
RE.install_suspender(shutter_suspenders["a_shutter"])
