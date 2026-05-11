"""Bind 4-ID-G HP diffractometer motor shortcuts into the interactive session.

Resolves ``huber_hp`` from ``oregistry`` at import time and assigns
each named sub-device to ``__main__`` under the same short name.
Importing this module is the side-effect: ``import
id4_common.macros.shortcuts_4idg_hp`` makes ``h``, ``k``, ``l``,
``nanox``, ``sample_tilt``, ``xeryon``, ... directly usable in the
IPython session.
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
    "basex",
    "basey",
    "basez",
    "basey_motor",
    "basez_motor",
    "sample_tilt",
    "x",
    "y",
    "z",
    "nanox",
    "nanoy",
    "nanoz",
    "xeryon",
):
    dev = getattr(_diff, item)
    logger.info(f"{dev.name} --> {item}")
    setattr(namespace, item, dev)
