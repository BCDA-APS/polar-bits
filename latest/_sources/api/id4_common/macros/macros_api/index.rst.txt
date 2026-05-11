id4_common.macros.macros_api
============================

.. py:module:: id4_common.macros.macros_api

.. autoapi-nested-parse::

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



