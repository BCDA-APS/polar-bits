id4_common.plans.local_scans
============================

.. py:module:: id4_common.plans.local_scans

.. autoapi-nested-parse::

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
