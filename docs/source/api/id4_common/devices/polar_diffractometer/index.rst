id4_common.devices.polar_diffractometer
=======================================

.. py:module:: id4_common.devices.polar_diffractometer

.. autoapi-nested-parse::

   Polar diffractometer







Module Contents
---------------

.. py:data:: WAVELENGTH_CONSTANT
   :value: 12.39


.. py:data:: PTTH_MIN_DEGREES
   :value: 79


.. py:data:: PTTH_MAX_DEGREES
   :value: 101


.. py:data:: PTH_MIN_DEGREES
   :value: 39


.. py:data:: PTH_MAX_DEGREES
   :value: 51


.. py:data:: ANALYZER_LIST_PATH

.. py:class:: AnalyzerDevice(prefix='', *, concurrent=True, read_attrs=None, configuration_attrs=None, name, egu='', auto_target=True, **kwargs)

   Bases: :py:obj:`ophyd.PseudoPositioner`


   A pseudo positioner which can be comprised of multiple positioners

   :param prefix: The PV prefix for all components of the device
   :type prefix: str
   :param concurrent: If set, all real motors will be moved concurrently. If not, they will
                      be moved in order of how they were defined initially
   :type concurrent: bool, optional
   :param read_attrs: the components to include in a normal reading (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param name: The name of the device
   :type name: str, optional
   :param egu: The user-defined engineering units for the whole PseudoPositioner
   :type egu: str, optional
   :param auto_target: Automatically set the target position of PseudoSingle devices when
                       moving to a single PseudoPosition
   :type auto_target: bool, optional
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None
   :param settle_time: The amount of time to wait after moves to report status completion
   :type settle_time: float, optional
   :param timeout: The default timeout to use for motion requests, in seconds.
   :type timeout: float, optional


   .. py:attribute:: energy


   .. py:attribute:: th


   .. py:attribute:: tth_trans


   .. py:attribute:: th_motor


   .. py:attribute:: tth


   .. py:attribute:: eta


   .. py:attribute:: chi


   .. py:attribute:: d_spacing


   .. py:attribute:: crystal


   .. py:attribute:: tth_detector_distance


   .. py:attribute:: tracking


   .. py:method:: move_single(pseudo, position, **kwargs)

      Move one PseudoSingle axis to a position

      All other positioners will use their current setpoint/target value, if
      available. Failing that, their current readback value will be used (see
      ``PseudoSingle.sync`` and ``PseudoSingle.target``).

      :param pseudo: PseudoSingle positioner to move
      :type pseudo: PseudoSingle
      :param position: Position only for the PseudoSingle
      :type position: float
      :param kwargs: Passed onto move
      :type kwargs: dict



   .. py:property:: beamline_wavelength


   .. py:property:: beamline_energy


   .. py:method:: convert_energy_to_theta(energy)


   .. py:method:: convert_energy_to_tth_trans(energy)


   .. py:method:: convert_theta_to_energy(theta)


   .. py:method:: forward(pseudo_pos)

      Run a forward (pseudo -> real) calculation



   .. py:method:: inverse(real_pos)

      Run an inverse (real -> pseudo) calculation



   .. py:method:: set_energy(energy)


   .. py:method:: calc(acal='No')


   .. py:method:: setup(analyzer_energy=None, analyzer_list_path=ANALYZER_LIST_PATH)


.. py:class:: SixCircleDiffractometer

   Bases: :py:obj:`hkl.geometries.ApsPolar`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   HKL engine.


   .. py:attribute:: h


   .. py:attribute:: k


   .. py:attribute:: l


   .. py:attribute:: tau


   .. py:attribute:: mu


   .. py:attribute:: gamma


   .. py:attribute:: delta


   .. py:attribute:: tablex


   .. py:attribute:: tabley


   .. py:attribute:: pad_rail


   .. py:attribute:: point_rail


   .. py:attribute:: filter


   .. py:attribute:: detslt


   .. py:attribute:: ana


   .. py:attribute:: energy


   .. py:attribute:: energy_update_calc_flag


   .. py:attribute:: energy_offset


   .. py:property:: hints


   .. py:method:: default_settings()


.. py:class:: CradleDiffractometer

   Bases: :py:obj:`SixCircleDiffractometer`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   HKL engine.


   .. py:attribute:: chi


   .. py:attribute:: phi


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z


.. py:class:: HPDiffractometer

   Bases: :py:obj:`SixCircleDiffractometer`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   HKL engine.


   .. py:attribute:: chi


   .. py:attribute:: phi


   .. py:attribute:: basex


   .. py:attribute:: basey


   .. py:attribute:: basez


   .. py:attribute:: basey_motor


   .. py:attribute:: basez_motor


   .. py:attribute:: sample_tilt


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z


   .. py:attribute:: nanox


   .. py:attribute:: nanoy


   .. py:attribute:: nanoz


.. py:class:: PolarPSI

   Bases: :py:obj:`hkl.geometries.ApsPolar`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   Psi engine.


   .. py:attribute:: psi


   .. py:attribute:: tau


   .. py:attribute:: mu


   .. py:attribute:: gamma


   .. py:attribute:: delta


.. py:class:: CradlePSI

   Bases: :py:obj:`PolarPSI`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   Psi engine.


   .. py:attribute:: chi


   .. py:attribute:: phi


.. py:class:: HPPSI

   Bases: :py:obj:`PolarPSI`


   ApsPolar: Huber diffractometer in 6-circle horizontal geometry with energy.

   Psi engine.


   .. py:attribute:: chi


   .. py:attribute:: phi
