id4_common.devices.polar_diffractometer_hklpy2
==============================================

.. py:module:: id4_common.devices.polar_diffractometer_hklpy2

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


   .. py:method:: calc()


   .. py:method:: setup(analyzer_energy=None, analyzer_list_path=ANALYZER_LIST_PATH)


.. py:class:: DiffractometerMixin(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Base class for device objects

   This class provides attribute access to one or more Signals, which can be
   a mixture of read-only and writable. All must share the same base_name.

   :param prefix: The PV prefix for all components of the device
   :type prefix: str, optional
   :param name: The name of the device (as will be reported via read()`
   :type name: str, keyword only
   :param kind: (or equivalent integer), optional
                Default is ``Kind.normal``. See :class:`~ophydobj.Kind` for options.
   :type kind: a member of the :class:`~ophydobj.Kind` :class:`~enum.IntEnum`
   :param read_attrs: DEPRECATED: the components to include in a normal reading
                      (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: DEPRECATED: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None, optional
   :param connection_timeout: Timeout for connection of all underlying signals.

                              The default value DEFAULT_CONNECTION_TIMEOUT means, "Fall back to
                              class-wide default." See Device.set_defaults to
                              configure class defaults.

                              Explicitly passing None means, "Wait forever."
   :type connection_timeout: float or None, optional

   .. attribute:: lazy_wait_for_connection

      When instantiating a lazy signal upon first access, wait for it to
      connect before returning control to the user.  See also the context
      manager helpers: ``wait_for_lazy_connection`` and
      ``do_not_wait_for_lazy_connection``.

      :type: bool

   .. attribute:: Subscriptions



   .. attribute:: -------------



   .. attribute:: SUB_ACQ_DONE

      A one-time subscription indicating the requested trigger-based
      acquisition has completed.


   .. py:attribute:: tablex


   .. py:attribute:: tabley


   .. py:attribute:: pad_rail


   .. py:attribute:: point_rail


   .. py:attribute:: filter


   .. py:attribute:: detslt


   .. py:attribute:: ana


   .. py:method:: default_settings()


.. py:data:: mono_kwargs

.. py:data:: CradleDiffractometerBase

.. py:class:: CradleDiffractometer(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`CradleDiffractometerBase`, :py:obj:`DiffractometerMixin`


   Base class for device objects

   This class provides attribute access to one or more Signals, which can be
   a mixture of read-only and writable. All must share the same base_name.

   :param prefix: The PV prefix for all components of the device
   :type prefix: str, optional
   :param name: The name of the device (as will be reported via read()`
   :type name: str, keyword only
   :param kind: (or equivalent integer), optional
                Default is ``Kind.normal``. See :class:`~ophydobj.Kind` for options.
   :type kind: a member of the :class:`~ophydobj.Kind` :class:`~enum.IntEnum`
   :param read_attrs: DEPRECATED: the components to include in a normal reading
                      (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: DEPRECATED: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None, optional
   :param connection_timeout: Timeout for connection of all underlying signals.

                              The default value DEFAULT_CONNECTION_TIMEOUT means, "Fall back to
                              class-wide default." See Device.set_defaults to
                              configure class defaults.

                              Explicitly passing None means, "Wait forever."
   :type connection_timeout: float or None, optional

   .. attribute:: lazy_wait_for_connection

      When instantiating a lazy signal upon first access, wait for it to
      connect before returning control to the user.  See also the context
      manager helpers: ``wait_for_lazy_connection`` and
      ``do_not_wait_for_lazy_connection``.

      :type: bool

   .. attribute:: Subscriptions



   .. attribute:: -------------



   .. attribute:: SUB_ACQ_DONE

      A one-time subscription indicating the requested trigger-based
      acquisition has completed.


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z


.. py:data:: HPDiffractometerBase

.. py:class:: HPDiffractometer(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`CradleDiffractometerBase`, :py:obj:`DiffractometerMixin`


   Base class for device objects

   This class provides attribute access to one or more Signals, which can be
   a mixture of read-only and writable. All must share the same base_name.

   :param prefix: The PV prefix for all components of the device
   :type prefix: str, optional
   :param name: The name of the device (as will be reported via read()`
   :type name: str, keyword only
   :param kind: (or equivalent integer), optional
                Default is ``Kind.normal``. See :class:`~ophydobj.Kind` for options.
   :type kind: a member of the :class:`~ophydobj.Kind` :class:`~enum.IntEnum`
   :param read_attrs: DEPRECATED: the components to include in a normal reading
                      (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: DEPRECATED: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None, optional
   :param connection_timeout: Timeout for connection of all underlying signals.

                              The default value DEFAULT_CONNECTION_TIMEOUT means, "Fall back to
                              class-wide default." See Device.set_defaults to
                              configure class defaults.

                              Explicitly passing None means, "Wait forever."
   :type connection_timeout: float or None, optional

   .. attribute:: lazy_wait_for_connection

      When instantiating a lazy signal upon first access, wait for it to
      connect before returning control to the user.  See also the context
      manager helpers: ``wait_for_lazy_connection`` and
      ``do_not_wait_for_lazy_connection``.

      :type: bool

   .. attribute:: Subscriptions



   .. attribute:: -------------



   .. attribute:: SUB_ACQ_DONE

      A one-time subscription indicating the requested trigger-based
      acquisition has completed.


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


.. py:data:: CradleDiffractometerPSI

.. py:data:: HPDiffractometerPSI

