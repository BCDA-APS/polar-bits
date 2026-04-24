id4_common.devices.scaler_dual_ctr8
===================================

.. py:module:: id4_common.devices.scaler_dual_ctr8

.. autoapi-nested-parse::

   Setup for two CTR8 devices used together









Module Contents
---------------

.. py:data:: NUMCHANNELS
   :value: 8


.. py:data:: PREFIX1
   :value: '4idCTR8_1:scaler1'


.. py:data:: PREFIX2
   :value: '4idCTR8_1:scaler2'


.. py:class:: LocalScalerChannel(*args, ch_num=0, **kwargs)

   Bases: :py:obj:`ophyd.scaler.ScalerChannel`


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


.. py:function:: make_channels()

.. py:class:: DualCTR8Scaler(prefix1, prefix2, **kwargs)

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


   .. py:attribute:: prefix1


   .. py:attribute:: prefix2


   .. py:attribute:: channels


   .. py:attribute:: scaler1


   .. py:attribute:: scaler2


   .. py:attribute:: freq


   .. py:attribute:: preset_time
      :value: None



   .. py:attribute:: preset_monitor


   .. py:method:: match_names()


   .. py:method:: select_channels(chan_names=None)

      Select channels based on the EPICS name PV

      :param chan_names: The names (as reported by the ``channel.chname`` signal)
                         of the channels to select.
                         If ``None``, select **all** channels named in the EPICS scaler.
      :type chan_names: Iterable[str] or None



   .. py:property:: trigger_scaler


   .. py:method:: trigger()

      Start acquisition



   .. py:property:: channels_name_map


   .. py:method:: select_plot_channels(chan_names=None)


   .. py:method:: select_read_channels(chan_names=None)

      Select channels based on the EPICS name PV.

      :param chan_names: The names (as reported by the channel.chname signal)
                         of the channels to select.
                         If *None*, select all channels named in the EPICS scaler.
      :type chan_names: Iterable[str] or None



   .. py:property:: monitor


   .. py:property:: plot_options


   .. py:method:: select_plot(channels)


   .. py:method:: default_settings()
