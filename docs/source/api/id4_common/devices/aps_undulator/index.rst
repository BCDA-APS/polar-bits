id4_common.devices.aps_undulator
================================

.. py:module:: id4_common.devices.aps_undulator

.. autoapi-nested-parse::

   Undulator support





Module Contents
---------------

.. py:class:: PolarUndulatorPositioner(prefix='', *, limits=None, name=None, read_attrs=None, configuration_attrs=None, parent=None, egu='', **kwargs)

   Bases: :py:obj:`apstools.devices.aps_undulator.UndulatorPositioner`


   A positioner for any of the gap control parameters.

   Communicates with the parent (presumably the undulator device) to
   start and stop the device.

   .. autosummary::

       ~setpoint
       ~readback
       ~actuate
       ~stop_signal
       ~done
       ~done_value


   .. py:method:: set(new_position: Any, *, timeout: float = None, moved_cb: Callable = None, wait: bool = False) -> ophyd.status.StatusBase

      Set a value and return a Status object


      :param new_position: The input here is whatever the device requires (this
                           should be over-ridden by the implementation.  For example
                           a motor would take a float, a shutter the strings {'Open',
                           'Close'}, and a goineometer (h, k, l) tuples
      :type new_position: object
      :param timeout: Maximum time to wait for the motion. If None, the default timeout
                      for this positioner is used.
      :type timeout: float, optional
      :param moved_cb: Deprecated

                       Call this callback when movement has finished. This callback
                       must accept one keyword argument: 'obj' which will be set to
                       this positioner instance.
      :type moved_cb: callable, optional
      :param wait: Deprecated

                   If the method should block until the Status object reports
                   it is done.

                   Defaults to False
      :type wait: bool, optional

      :returns: **status** -- Status object to indicate when the motion / set is done.
      :rtype: StatusBase



.. py:class:: PolarUndulator(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`apstools.devices.STI_Undulator`


   APS Planar Undulator built by STI Optronics.

   .. index::
       Ophyd Device; PlanarUndulator
       Ophyd Device; STI_Undulator

   APS Use: 13 devices, including 4ID.

   EXAMPLE::

       undulator = STI_Undulator("S04ID:USID:", name="undulator")


   .. py:attribute:: tracking


   .. py:attribute:: energy_offset


   .. py:attribute:: energy_deadband


   .. py:attribute:: energy


   .. py:attribute:: version_hpmu
      :value: None



.. py:class:: PhaseShifterDevice(*args, **kwargs)

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


   .. py:attribute:: gap


   .. py:attribute:: start_button


   .. py:attribute:: stop_button


   .. py:attribute:: done


   .. py:attribute:: gap_deadband


   .. py:attribute:: device_limit


   .. py:attribute:: device


   .. py:attribute:: location


   .. py:attribute:: message1


   .. py:attribute:: message2


.. py:class:: PolarUndulatorPair(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

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


   .. py:attribute:: us


   .. py:attribute:: ds


   .. py:attribute:: phase_shifter
