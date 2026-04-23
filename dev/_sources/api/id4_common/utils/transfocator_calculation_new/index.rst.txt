id4_common.utils.transfocator_calculation_new
=============================================

.. py:module:: id4_common.utils.transfocator_calculation_new

.. autoapi-nested-parse::

   Transfocator functions.

   .. autosummary::
       ~read_delta
       ~transfocator







Module Contents
---------------

.. py:data:: BE_REFR_INDEX_FILE
   :value: '/home/beams/POLAR/polar_instrument/src/instrument/utils/Be_refr_index.dat'


.. py:data:: LENS_SETTINGS
   :value: '/home/beams/POLAR/polar_instrument/src/instrument/utils/transfocator_settings.csv'


.. py:function:: read_delta(energy, path=BE_REFR_INDEX_FILE)

   Return the refractive index delta for beryllium at the given energy (eV).


.. py:function:: transfocator_calculation(energy, optimize_position: float = None, experiment: str = 'diffractometer', reference_distance: float = 2591, distance_only: bool = False, selected_lenses: list = None, verbose: bool = True)

   Calculate the transfocator position and lenses set.

   :param energy: Beamline energy in keV.
   :type energy: float
   :param optimize_position: CRL motor Z position that will be used to optimize the lenses for
                             the calculation, in mm.
   :type optimize_position: float
   :param experiment: Name of the experimental configuration to focus.
   :type experiment: "diffractometer" or "magnet"
   :param reference_distance: Distance between CRL and sample when the CRL Z motor is at zero.
                              This will normally not
                              change. In mm.
   :type reference_distance: float
   :param distance_only: If True it will only calculate the optimal distance, and won't try
                         to switch lenses.
   :type distance_only: bool
   :param selected_lenses: If distance_only == True, then this is the lenses you want to use
                           for the calculation.
   :type selected_lenses: iterable
   :param verbose: Toggle to print information.
   :type verbose: bool


