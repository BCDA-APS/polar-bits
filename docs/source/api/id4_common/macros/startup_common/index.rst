id4_common.macros.startup_common
================================

.. py:module:: id4_common.macros.startup_common

.. autoapi-nested-parse::

   One-line session-restart helper.

   Importing this module runs the canonical post-restart sequence:
   ``experiment_resume()`` (auto-discovers the experiment snapshot from
   the cwd or the most recent run in the catalog) followed by
   ``restore_session_state()`` (re-applies every auto-saved setup knob —
   PR setup, energy tracking, undulator offsets, counters, qxscan
   params). The per-knob status dict is printed so the user can see what
   was applied / skipped / failed.





Module Contents
---------------

.. py:data:: status
