"""Bind 4-ID-H 9-Tesla magnet motor shortcuts into the interactive session.

Resolves ``magnet911`` from ``oregistry`` at import time, walks each
``device.subattr`` dotted path, and assigns the resulting object to
``__main__`` under the requested short name. Importing this module is
the side-effect: ``import id4_common.macros.shortcuts_4idh_9T`` makes
``field``, ``tabx``, ``sy``, ... directly usable in the IPython
session.
"""

import sys
from logging import getLogger

from apsbits.core.instrument_init import oregistry

logger = getLogger(__name__)
_mag = oregistry.find("magnet911")
MAIN_NAMESPACE = "__main__"
namespace = sys.modules[MAIN_NAMESPACE]

logger.info("Adding devices shortcuts to the main namespace:")
for path, label in {
    "ps.field": "field",
    "tab.x": "tabx",
    "tab.y": "taby",
    "tab.z": "tabz",
    "tab.sx": "tabsx",
    "tab.sz": "tabsz",
    "tab.srot": "tabrot",
    "samp.y": "sy",
    "samp.th": "sth",
}.items():
    dev = _mag
    for part in path.split("."):
        dev = getattr(dev, part)
    logger.info(f"{dev.name} --> {label}")
    setattr(namespace, label, dev)
