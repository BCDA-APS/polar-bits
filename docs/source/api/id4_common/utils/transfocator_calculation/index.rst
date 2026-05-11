id4_common.utils.transfocator_calculation
=========================================

.. py:module:: id4_common.utils.transfocator_calculation

.. autoapi-nested-parse::

   Transfocator functions.

   .. autosummary::
       ~read_delta
       ~transfocator







Module Contents
---------------

.. py:data:: BE_REFR_INDEX_FILE
   :value: '/home/beams/POLAR/polar_instrument/src/instrument/utils/Be_refr_index.dat'


.. py:function:: read_delta(energy=None, path=BE_REFR_INDEX_FILE)

   Return the refractive index delta for beryllium at the given photon energy
   (eV).


.. py:function:: transfocator_calc(distance=None, energy=None, experiment='diffractometer', beamline='polar', verbose=True)

   Calculate the CRL lens configuration for the requested focus distance and
   energy.


.. py:function:: transfocator_calc_old(distance=None, energy=None, experiment='diffractometer', beamline='polar')

   Calculate CRL lens configuration using the legacy (non-verbose) algorithm.


