id4_common.utils.utilities
==========================

.. py:module:: id4_common.utils.utilities

.. autoapi-nested-parse::

   Utility functions.

   .. autosummary::
       ~setaz
       ~freeze
       ~show_constraints
       ~reset_constraints
       ~set_constraints
       ~change_diffractometer
       ~plotselect
       ~set_counting_time
       ~set_experiment
       ~list_functions







Module Contents
---------------

.. py:data:: path

.. py:function:: setaz(*args)

   Set azimuth in constant Psi geometry


.. py:function:: freeze(*args)

   Freeze angle to value in constant mu, omega, phi, chi and psi modes


.. py:function:: change_diffractometer(*args)

.. py:function:: plotselect(detector=None)

   Selects scalers plotted during scan


.. py:function:: set_counting_time(time=None, monitor=False)

   Sets counting time / monitor counts:
       time <  200: counting time in seconds
       time >= 200: monitor counts

   Needs to be adapted to other detectors than scalers


.. py:function:: set_experiment(name=None, proposal_id=None, sample=None)

   Set experiment parameters.

   :param name:
   :type name: string, optional
   :param proposal_id:
   :type proposal_id: integer, optional
   :param sample:
   :type sample: string, optional


.. py:function:: list_functions(select=None)

   List available functions

   select: string, optional
       None: all packages
       "absorption": functions related to absorption experiments
       "diffraction": functions related to diffraction experiments
       "hklpy": functions related to reciprocal space
