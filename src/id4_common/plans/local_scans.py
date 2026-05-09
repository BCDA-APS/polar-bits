"""
Backward-compatibility shim for the polar-bits scan plans.

The scan implementations were split out per-category in May 2026 (issue
#56) so each module stays small and focused:

- :mod:`id4_common.plans.base_scans`  — ``count``, ``ascan``, ``lup``,
  ``qxscan``
- :mod:`id4_common.plans.move_plans`  — ``mv``, ``mvr``, ``abs_set``
- :mod:`id4_common.plans.grid_scans`  — ``grid_scan``, ``rel_grid_scan``
- :mod:`id4_common.plans.hkl_scans`   — ``th2th``, ``hklscan``, ``hscan``,
  ``kscan``, ``lscan``, ``psiscan``

This shim re-exports every public symbol so existing
``from id4_common.plans.local_scans import ...`` callers keep working.
New code should import from the focused modules directly.
"""

__all__ = [
    "lup",
    "ascan",
    "mv",
    "mvr",
    "grid_scan",
    "rel_grid_scan",
    "qxscan",
    "count",
    "abs_set",
    "psiscan",
    "hklscan",
    "hscan",
    "kscan",
    "lscan",
    "th2th",
]

from .base_scans import ascan  # noqa: F401
from .base_scans import count  # noqa: F401
from .base_scans import lup  # noqa: F401
from .base_scans import qxscan  # noqa: F401
from .grid_scans import grid_scan  # noqa: F401
from .grid_scans import rel_grid_scan  # noqa: F401
from .hkl_scans import hklscan  # noqa: F401
from .hkl_scans import hscan  # noqa: F401
from .hkl_scans import kscan  # noqa: F401
from .hkl_scans import lscan  # noqa: F401
from .hkl_scans import psiscan  # noqa: F401
from .hkl_scans import th2th  # noqa: F401
from .move_plans import abs_set  # noqa: F401
from .move_plans import mv  # noqa: F401
from .move_plans import mvr  # noqa: F401
