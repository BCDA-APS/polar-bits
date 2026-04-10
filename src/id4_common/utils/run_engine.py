"""
Setup the Bluesky RunEngine, provides ``RE`` and ``sd``.
========================================================

.. autosummary::
    ~RE
    ~sd
    ~bec
    ~peaks
"""

from apsbits.core.run_engine_init import init_RE
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.utils.config_loaders import get_config
from apsbits.core.catalog_init import init_catalog
# from tiled.client import from_profile

iconfig = get_config()
cat = init_catalog(iconfig)
cat_legacy = None
# TODO: This is a placeholder for when we switch to tiled.
# cat_legacy = from_profile(iconfig.get("TILED_PROFILE_NAME"))[
#     iconfig.get("DATABROKER_CATALOG")
# ]
bec, peaks = init_bec_peaks(iconfig)
bec.disable_baseline()
bec.enable_plots()
RE, sd = init_RE(iconfig, subscribers=[bec, cat])
