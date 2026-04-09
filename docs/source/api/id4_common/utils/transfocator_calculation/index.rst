id4_common.utils.transfocator_calculation
=========================================

.. py:module:: id4_common.utils.transfocator_calculation

.. autoapi-nested-parse::

   Transfocator functions.

   .. autosummary::
       ~read_delta
       ~transfocator



Attributes
----------

.. autoapisummary::

   id4_common.utils.transfocator_calculation.BE_REFR_INDEX_FILE


Functions
---------

.. autoapisummary::

   id4_common.utils.transfocator_calculation.read_delta
   id4_common.utils.transfocator_calculation.transfocator_calc
   id4_common.utils.transfocator_calculation.transfocator_calc_old


Module Contents
---------------

.. py:data:: BE_REFR_INDEX_FILE
   :value: '/home/beams/POLAR/polar_instrument/src/instrument/utils/Be_refr_index.dat'


.. py:function:: read_delta(energy=None, path=BE_REFR_INDEX_FILE)

.. py:function:: transfocator_calc(distance=None, energy=None, experiment='diffractometer', beamline='polar', verbose=True)

.. py:function:: transfocator_calc_old(distance=None, energy=None, experiment='diffractometer', beamline='polar')

