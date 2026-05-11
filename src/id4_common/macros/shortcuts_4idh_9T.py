from apsbits.core.instrument_init import oregistry  # noqa: F401
from logging import getLogger
import sys

logger = getLogger(__name__)
_mag = oregistry.find("magnet911")
MAIN_NAMESPACE = "__main__"
namespace = sys.modules[MAIN_NAMESPACE]

logger.info("Adding devices shortcuts to the main namespace:")
for item, label in {
    "ps.field": "field",
    "tab.x": "tabx",
    "tab.y": "taby",
    "tab.z": "tabz",
    "tab.sx": "tabsx",
    "tab.sz": "tabsz",
    "tab.srot": "tabrot",
    "samp.y": "sy",
    "samp.th": "sth",
}:
    dev = getattr(_mag, item)
    logger.info(f"{dev.name} --> {item}")
    setattr(namespace, item, dev)
