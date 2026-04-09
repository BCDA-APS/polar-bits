id4_common.devices.scaler
=========================

.. py:module:: id4_common.devices.scaler

.. autoapi-nested-parse::

   Scalers



Classes
-------

.. autoapisummary::

   id4_common.devices.scaler.PresetMonitorSignal
   id4_common.devices.scaler.LocalScalerCH


Module Contents
---------------

.. py:class:: PresetMonitorSignal(*args, **kwargs)

   Bases: :py:obj:`ophyd.signal.Signal`


   Signal that control the selected monitor channel


   .. py:method:: get(**kwargs)


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


