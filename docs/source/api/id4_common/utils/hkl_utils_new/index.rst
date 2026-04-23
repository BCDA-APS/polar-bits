id4_common.utils.hkl_utils_new
==============================

.. py:module:: id4_common.utils.hkl_utils_new

.. autoapi-nested-parse::

   Auxilary HKL functions.

   .. autosummary::
       ~newsample
       ~sampleChange
       ~sampleRemove
       ~_sampleList
       ~list_reflections
       ~or_swap
       ~setor0
       ~setor1
       ~set_orienting
       ~del_reflection
       ~list_orienting
       ~or0
       ~or1
       ~compute_UB
       ~calc_UB
       ~setmode
       ~ca
       ~ubr
       ~br
       ~uan
       ~an
       ~_wh
       ~setlat
       ~setaz
       ~freeze_psi
       ~wh









Module Contents
---------------

.. py:data:: RE

.. py:data:: pbar_manager

.. py:class:: Geometries(huber_euler, huber_euler_psi, huber_hp, huber_hp_psi)

   Register the diffractometer geometries.


   .. py:property:: huber_euler


   .. py:property:: huber_euler_psi


   .. py:property:: huber_hp


   .. py:property:: huber_hp_psi


.. py:data:: geometries

.. py:function:: newsample()

   Interactively add a new sample with lattice constants.

   Prompts the user for:
     - sample name
     - lattice constants (a, b, c, alpha, beta, gamma)

   Uses defaults if the user just presses Enter.


.. py:function:: list_reflections(all_samples=False)

   Lists all reflections defined in hklpy for six-circle geometry.

   :param all_samples: If True, list reflections for all samples.
                       If False, only the current sample. Defaults to False.
   :type all_samples: bool, optional


.. py:function:: sampleChange(sample_key=None)

   Change selected sample in hklpy2.

   :param sample_key: Name of the sample as set in hklpy. If None it will ask for which
                      sample.
   :type sample_key: string, optional


.. py:function:: sampleRemove(sample_key=None)

   Remove selected sample in hklpy.

   :param sample_key: Name of the sample as set in hklpy. If None it will ask for which
                      sample.
   :type sample_key: string, optional


.. py:function:: or_swap()

   Swaps the two orientation reflections in hklpy.


.. py:function:: calc_UB(r1, r2, wavelength=None, output=False)

   Compute the UB matrix with two reflections.

   :param r1: Orienting reflections from hklpy.
   :type r1: hklpy reflections
   :param r2: Orienting reflections from hklpy.
   :type r2: hklpy reflections
   :param wavelength: This is not used...
   :type wavelength: float, optional
   :param output: Toggle to decide whether to print the UB matrix.
   :type output: boolean


.. py:function:: compute_UB()

   Calculates the UB matrix.

   This fixes one issue with the hklpy calc_UB in that using wh() right after
   will not work, it needs to run one calculation first.

   :param h: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type h: float, optional
   :param k: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type k: float, optional
   :param l: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type l: float, optional


.. py:function:: setor0()

   Sets the primary orientation in hklpy2.

   :param diffractometer real motors: Values of motor positions for current reflection. It will ask
                                      for it.
   :type diffractometer real motors: float, optional
   :param h: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type h: float, optional
   :param k: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type k: float, optional
   :param l: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type l: float, optional


.. py:function:: setor1()

   Sets the primary orientation in hklpy2.

   :param diffractometer real motors: Values of motor positions for current reflection. It will ask
                                      for it.
   :type diffractometer real motors: float, optional
   :param h: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type h: float, optional
   :param k: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type k: float, optional
   :param l: Values of H, K, L positions for current reflection. It will ask
             for it.
   :type l: float, optional


.. py:function:: or0(h=None, k=None, l=None)

   Sets the primary orientation in hklpy2 using the current motor positions.

   :param h: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type h: float, optional
   :param k: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type k: float, optional
   :param l: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type l: float, optional


.. py:function:: or1(h=None, k=None, l=None)

   Sets the secondary orientation in hklpy2 using the current motor positions.

   :param h: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type h: float, optional
   :param k: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type k: float, optional
   :param l: Values of H, K, L positions for current reflection. If None, it will ask
             for it.
   :type l: float, optional


.. py:function:: set_orienting()

   Change the primary and secondary orienting reflections
   to existing reflections in the reflection list (hklpy2).

   WARNING: Works only with six-circle geometry (fix in progress).


.. py:function:: del_reflection()

   Delete a reflection from the current sample's reflection list.

   - Displays reflections like set_orienting()
   - User inputs index number of reflection to delete
   - Orienting reflections (first/second) cannot be deleted


.. py:function:: list_orienting()

   List the first and second orienting reflections only
   from the current sample's reflection list.


.. py:function:: setmode(mode=None)

   Set the mode of the currently selected diffractometer.

   WARNING: This function will only work with six circles. This will be fixed
   in future releases.

   :param mode: Mode to be selected. If None, it will ask.
   :type mode: string, optional


.. py:function:: ca(h, k, l)

   Calculate the motors position of a reflection.

   :param h: H, K, and L values.
   :type h: float
   :param k: H, K, and L values.
   :type k: float
   :param l: H, K, and L values.
   :type l: float


.. py:function:: ubr(h, k, l)

   Move the motors to a reciprocal space point.

   :param h: H, K, and L values.
   :type h: float
   :param k: H, K, and L values.
   :type k: float
   :param l: H, K, and L values.
   :type l: float


.. py:function:: br(h, k, l)

   Move the motors to a reciprocal space point.

   :param h: H, K, and L values.
   :type h: float
   :param k: H, K, and L values.
   :type k: float
   :param l: H, K, and L values.
   :type l: float

   :rtype: Generator for the bluesky Run Engine.


.. py:function:: uan(*args)

   Moves the delta and eta motors.

   WARNING: This function will only work with six circles. This will be fixed
   in future releases.

   :param delta: Delta and eta motor angles to be moved to.
   :type delta: float, optional??
   :param eta: Delta and eta motor angles to be moved to.
   :type eta: float, optional??


.. py:function:: an(delta=None, eta=None)

   Moves the delta and theta motors.

   WARNING: This function will only work with six circles. This will be fixed
   in future releases.

   :param delta: Delta and th motor angles to be moved to.
   :type delta: float, optional??
   :param th: Delta and th motor angles to be moved to.
   :type th: float, optional??

   :rtype: Generator for the bluesky Run Engine.


.. py:function:: setlat(*args)

   Set the lattice constants for the current sample.

   :param a: Lattice constants.
             - If all 6 are provided as arguments, they are used directly.
             - If none are provided, the user will be prompted interactively.
   :type a: float, optional
   :param b: Lattice constants.
             - If all 6 are provided as arguments, they are used directly.
             - If none are provided, the user will be prompted interactively.
   :type b: float, optional
   :param c: Lattice constants.
             - If all 6 are provided as arguments, they are used directly.
             - If none are provided, the user will be prompted interactively.
   :type c: float, optional
   :param alpha: Lattice constants.
                 - If all 6 are provided as arguments, they are used directly.
                 - If none are provided, the user will be prompted interactively.
   :type alpha: float, optional
   :param beta: Lattice constants.
                - If all 6 are provided as arguments, they are used directly.
                - If none are provided, the user will be prompted interactively.
   :type beta: float, optional
   :param gamma: Lattice constants.
                 - If all 6 are provided as arguments, they are used directly.
                 - If none are provided, the user will be prompted interactively.
   :type gamma: float, optional

   .. rubric:: Notes

   If two orienting reflections are defined, UB will be recomputed automatically.


.. py:function:: setaz(*args)

   Set the azimuthal reference reflection (h2, k2, l2).

   Works differently depending on geometry:
     - 4-circle: uses 'psi_constant'
     - 6-circle: uses 'psi_constant_vertical' and 'psi_constant_horizontal'

   :param h2: Miller indices of the azimuthal reference reflection.
              - If provided, these are used directly.
              - If not provided, the user will be prompted interactively.
   :type h2: int or float, optional
   :param k2: Miller indices of the azimuthal reference reflection.
              - If provided, these are used directly.
              - If not provided, the user will be prompted interactively.
   :type k2: int or float, optional
   :param l2: Miller indices of the azimuthal reference reflection.
              - If provided, these are used directly.
              - If not provided, the user will be prompted interactively.
   :type l2: int or float, optional


.. py:function:: freeze_psi(*args)

