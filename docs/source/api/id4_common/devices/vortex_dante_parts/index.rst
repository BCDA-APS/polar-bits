id4_common.devices.vortex_dante_parts
=====================================

.. py:module:: id4_common.devices.vortex_dante_parts

.. autoapi-nested-parse::

   Dante CAM





Module Contents
---------------

.. py:class:: DanteCAM1(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.ADBase`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: port_name


   .. py:attribute:: manufacturer


   .. py:attribute:: model


   .. py:attribute:: firmware


   .. py:attribute:: sdk_version


   .. py:attribute:: driver_version


   .. py:attribute:: adcore_version


   .. py:attribute:: connected

      If the device is connected.

      Subclasses should override this


   .. py:attribute:: array_size


   .. py:attribute:: color_mode


   .. py:attribute:: data_type


   .. py:attribute:: acquire_start


   .. py:attribute:: acquire_stop


   .. py:attribute:: acquire_status


   .. py:attribute:: acquire_busy


   .. py:attribute:: real_time_preset


   .. py:attribute:: real_time_elapsed


   .. py:attribute:: real_time_live


   .. py:attribute:: instant_deadtime


   .. py:attribute:: average_deadtime


   .. py:attribute:: current_pixel


   .. py:attribute:: poll_time


   .. py:attribute:: read_rate


   .. py:attribute:: read_rate_button


   .. py:attribute:: queued_arrays


   .. py:attribute:: wait_for_plugins


   .. py:attribute:: array_counter


   .. py:attribute:: image_rate


   .. py:attribute:: array_callbacks


   .. py:attribute:: mca_mode


   .. py:attribute:: mca_channels


   .. py:attribute:: mca_mapping_points


   .. py:attribute:: num_images


   .. py:attribute:: mca_gatting


   .. py:attribute:: mca_list_buffer_size


.. py:class:: DanteCAM4(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`DanteCAM1`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: snl_connected


.. py:class:: DanteSCA(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.ADBase`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: real_time


   .. py:attribute:: live_time


   .. py:attribute:: icr


   .. py:attribute:: ocr


   .. py:attribute:: triggers


   .. py:attribute:: events


   .. py:attribute:: fast_deadtime


   .. py:attribute:: f1_deadtime


   .. py:attribute:: zero_counts


   .. py:attribute:: baseline_counts


   .. py:attribute:: pileup


   .. py:attribute:: f1_pileup


   .. py:attribute:: not_f1_pileup


   .. py:attribute:: reset_counts


   .. py:attribute:: enable


   .. py:attribute:: fast_peaking_time


   .. py:attribute:: fast_threshold


   .. py:attribute:: fast_flat_top_time


   .. py:attribute:: peaking_time


   .. py:attribute:: max_peaking_time


   .. py:attribute:: energy_threshold


   .. py:attribute:: baseline_threshold


   .. py:attribute:: max_rise_time


   .. py:attribute:: reset_recovery_time


   .. py:attribute:: zero_peak_frequency


   .. py:attribute:: baseline_samples


   .. py:attribute:: gain


   .. py:attribute:: input_mode


   .. py:attribute:: input_polarity


   .. py:attribute:: analog_offset


   .. py:attribute:: base_offset


   .. py:attribute:: reset_threshold


   .. py:attribute:: time_constant


   .. py:attribute:: max_energy


.. py:class:: DanteHDF1Plugin(*args, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.PolarHDF5Plugin`


   .. py:attribute:: array_counter


   .. py:attribute:: array_counter_readback


   .. py:method:: warmup()
