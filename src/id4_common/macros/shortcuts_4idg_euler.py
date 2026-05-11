"""Bind 4-ID-G Euler diffractometer motor shortcuts into the interactive session.

Resolves the diffractometer from ``oregistry`` at import time and
assigns each named sub-device to ``__main__`` under the same short
name. Importing this module is the side-effect: ``import
id4_common.macros.shortcuts_4idg_euler`` makes ``h``, ``k``, ``l``,
``gamma``, ``delta``, ... directly usable in the IPython session.
"""

import sys
from logging import getLogger

from apsbits.core.instrument_init import oregistry

logger = getLogger(__name__)
_diff = oregistry.find("huber_hp")
MAIN_NAMESPACE = "__main__"
namespace = sys.modules[MAIN_NAMESPACE]

logger.info("Adding devices shortcuts to the main namespace:")
for item in (
    "h",
    "k",
    "l",
    "tau",
    "mu",
    "gamma",
    "delta",
    "chi",
    "phi",
    "x",
    "y",
    "z",
):
    dev = getattr(_diff, item)
    logger.info(f"{dev.name} --> {item}")
    setattr(namespace, item, dev)
