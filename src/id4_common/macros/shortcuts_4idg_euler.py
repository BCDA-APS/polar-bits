from apsbits.core.instrument_init import oregistry  # noqa: F401
from logging import getLogger
import sys

logger = getLogger(__name__)
_diff = oregistry.find("huber_hp")
MAIN_NAMESPACE = "__main__"
namespace = sys.modules[MAIN_NAMESPACE]

logger.info("Adding devices shortcuts to the main namespace:")
for item in (
    'h',
    'k',
    'l',
    'tau',
    'mu',
    'gamma',
    'delta',
    'chi',
    'phi',
    'x',
    'y',
    'z'
):
    dev = getattr(_diff, item)
    logger.info(f"{dev.name} --> {item}")
    setattr(namespace, item, dev)
