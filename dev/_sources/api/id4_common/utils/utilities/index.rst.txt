id4_common.utils.utilities
==========================

.. py:module:: id4_common.utils.utilities

.. autoapi-nested-parse::

   Utility functions.

   .. autosummary::
       ~plotselect
       ~set_counting_time
       ~list_functions







Module Contents
---------------

.. py:data:: utils
   :value: None


.. py:data:: path

.. py:function:: plotselect(dets=None, mon=None)

   Selects detectors and monitor plotted during scan.
   Delegates to counters.plotselect().


.. py:function:: set_counting_time(time=None, monitor=False)

   Sets counting time / monitor counts:
       time <  200: counting time in seconds
       time >= 200: monitor counts


.. py:function:: list_functions(select=None)

   List available functions

   select: string, optional
       None: all packages
       "absorption": functions related to absorption experiments
       "diffraction": functions related to diffraction experiments
       "hklpy": functions related to reciprocal space


