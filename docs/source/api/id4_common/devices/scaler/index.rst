id4_common.devices.scaler
=========================

.. py:module:: id4_common.devices.scaler

.. autoapi-nested-parse::

   Scalers





Module Contents
---------------

.. py:class:: PresetMonitorSignal(*args, **kwargs)

   Bases: :py:obj:`ophyd.signal.Signal`


   Signal that control the selected monitor channel


   .. py:method:: get(**kwargs)

      The readback value



   .. py:method:: put(value, *, timestamp=None, force=False, metadata=None)

      Put updates the internal readback value.

      The value is optionally checked first, depending on the value of force.
      In addition, VALUE subscriptions are run.
      Extra kwargs are ignored (for API compatibility with EpicsSignal kwargs
      pass through).
      :param value: Value to set
      :type value: any
      :param timestamp: The timestamp associated with the value, defaults to time.time()
      :type timestamp: float, optional
      :param metadata: Further associated metadata with the value (such as alarm status,
                       severity, etc.)
      :type metadata: dict, optional
      :param force: Check the value prior to setting it, defaults to False
      :type force: bool, optional



.. py:class:: LocalScalerCH(*args, **kwargs)

   Bases: :py:obj:`ophyd.scaler.ScalerCH`


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


   .. py:attribute:: preset_time
      :value: None



   .. py:attribute:: preset_monitor


   .. py:attribute:: freq


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


