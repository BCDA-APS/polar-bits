id4_common.devices.phaseplates
==============================

.. py:module:: id4_common.devices.phaseplates

.. autoapi-nested-parse::

   Phase retarders.





Module Contents
---------------

.. py:class:: MicronsSignal(parent_attr, *, parent=None, **kwargs)

   Bases: :py:obj:`ophyd.DerivedSignal`


   A signal that converts the offset from degrees to microns


   .. py:method:: describe()

      Description based on the original signal description



   .. py:method:: inverse(value)

      Compute original signal value -> derived signal value



   .. py:method:: forward(value)

      Compute derived signal value -> original signal value



.. py:class:: PRPzt(PV, *args, drio_prefix='4idaSoft:232DRIO:1:', **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Phase retarder PZT


   .. py:attribute:: remote_setpoint


   .. py:attribute:: remote_readback


   .. py:attribute:: localdc


   .. py:attribute:: center


   .. py:attribute:: offset_degrees


   .. py:attribute:: offset_microns


   .. py:attribute:: servoon


   .. py:attribute:: servooff


   .. py:attribute:: servostatus


   .. py:attribute:: selectDC


   .. py:attribute:: selectAC


   .. py:attribute:: ACstatus


   .. py:attribute:: conversion_factor


.. py:class:: PRDeviceBase(prefix, name, motorsDict, **kwargs)

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


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: d_spacing


   .. py:attribute:: offset_degrees


   .. py:attribute:: motor_switch


   .. py:attribute:: tracking


   .. py:method:: convert_energy_to_theta(energy)


   .. py:method:: convert_theta_to_energy(theta)


   .. py:method:: forward(pseudo_pos)

      Run a forward (pseudo -> real) calculation



   .. py:method:: inverse(real_pos)

      Run an inverse (real -> pseudo) calculation



   .. py:method:: set_energy(energy)


   .. py:method:: default_settings()


.. py:class:: PRDevice(prefix, name, prnum, motorsDict, **kwargs)

   Bases: :py:obj:`PRDeviceBase`


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


   .. py:attribute:: pzt


   .. py:attribute:: select_pr


   .. py:method:: default_settings()
