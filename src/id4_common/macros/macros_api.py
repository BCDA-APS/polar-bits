"""
Single-import surface for user macro files (issue #18).

::

    from id4_common.macros.macros_api import *

Re-exports every public scan plan, every move plan, the peak-finding
plans, and the session-level singletons (counters, oregistry, peaks,
atten).  The list is **curated and stable across internal package
reorgs** — macro files keep working when we move things around inside
``id4_common``.

Bluesky stubs (``abs_set``, ``rd``, ``sleep``, ``trigger_and_read``,
``move_per_step``, ``null``, …) are not re-exported here on purpose —
import them explicitly from ``bluesky.plan_stubs`` so the bluesky
surface stays visible in user macros.

Pattern to copy:

::

    from id4_common.macros.macros_api import *
    from bluesky.plan_stubs import abs_set, rd, sleep

    energy = oregistry.find("energy")
    magnet = oregistry.find("magnet911")

    def align_xy(start=-0.015, end=0.015):
        yield from lup(magnet.tab.x, start, end, 60, 0.2)
        yield from cen(magnet.tab.x)
        yield from lup(magnet.tab.y, start, end, 60, 0.2)
        yield from cen(magnet.tab.y)
"""

from apsbits.core.instrument_init import oregistry  # noqa: F401

# Polar-bits scan plans (post-#56 split; aliased from the focused modules
# so user macros never need to know which file each plan lives in).
from ..plans.base_scans import ascan  # noqa: F401
from ..plans.base_scans import count  # noqa: F401
from ..plans.base_scans import lup  # noqa: F401
from ..plans.base_scans import qxscan  # noqa: F401
from ..plans.grid_scans import grid_scan  # noqa: F401
from ..plans.grid_scans import rel_grid_scan  # noqa: F401
from ..plans.hkl_scans import hklscan  # noqa: F401
from ..plans.hkl_scans import hscan  # noqa: F401
from ..plans.hkl_scans import kscan  # noqa: F401
from ..plans.hkl_scans import lscan  # noqa: F401
from ..plans.hkl_scans import psiscan  # noqa: F401
from ..plans.hkl_scans import th2th  # noqa: F401
from ..plans.move_plans import mv  # noqa: F401
from ..plans.move_plans import mvr  # noqa: F401

# Peak-finding plans (the new findpeaks-style cen/com/maxi/mini from #59
# plus the BEC-driven cen2/maxi2/mini2 fallbacks).
from ..plans.center_maximum import cen2  # noqa: F401
from ..plans.center_maximum import maxi2  # noqa: F401
from ..plans.center_maximum import mini2  # noqa: F401
from ..plans.peak_position import cen  # noqa: F401
from ..plans.peak_position import com  # noqa: F401
from ..plans.peak_position import maxi  # noqa: F401
from ..plans.peak_position import mini  # noqa: F401
from ..plans.peak_position import peak  # noqa: F401
from ..plans.peak_position import peak_pos  # noqa: F401
from ..plans.peak_position import pmax  # noqa: F401
from ..plans.peak_position import pmin  # noqa: F401

# Session-level singletons.
from ..utils.attenuator_utils import atten  # noqa: F401
from ..utils.counters_class import counters  # noqa: F401
from ..utils.run_engine import peaks  # noqa: F401

__all__ = [
    # devices
    "oregistry",
    # scan plans
    "ascan",
    "count",
    "lup",
    "qxscan",
    "mv",
    "mvr",
    "grid_scan",
    "rel_grid_scan",
    "hklscan",
    "hscan",
    "kscan",
    "lscan",
    "psiscan",
    "th2th",
    # peak finding (new + legacy)
    "cen",
    "com",
    "maxi",
    "mini",
    "peak",
    "peak_pos",
    "pmax",
    "pmin",
    "cen2",
    "maxi2",
    "mini2",
    # session singletons
    "atten",
    "counters",
    "peaks",
]
