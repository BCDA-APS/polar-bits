id4_common.devices.vortex_xspress3_me7
======================================

.. py:module:: id4_common.devices.vortex_xspress3_me7

.. autoapi-nested-parse::

   Eiger 1M setup







Module Contents
---------------

.. py:data:: logger

.. py:data:: MAX_IMAGES
   :value: 12216


.. py:data:: MAX_ROIS
   :value: 8


.. py:class:: Trigger(*args, image_name=None, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.trigger_mixins.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:method:: setup_manual_trigger()


   .. py:method:: setup_sgzbca_trigger()


   .. py:method:: setup_external_trigger()


   .. py:method:: stage()

      Stage the device for data collection.

      This method is expected to put the device into a state where
      repeated calls to :meth:`~BlueskyInterface.trigger` and
      :meth:`~BlueskyInterface.read` will 'do the right thing'.

      Staging not idempotent and should raise
      :obj:`RedundantStaging` if staged twice without an
      intermediate :meth:`~BlueskyInterface.unstage`.

      This method should be as fast as is feasible as it does not return
      a status object.

      The return value of this is a list of all of the (sub) devices
      stage, including it's self.  This is used to ensure devices
      are not staged twice by the :obj:`~bluesky.run_engine.RunEngine`.

      This is an optional method, if the device does not need
      staging behavior it should not implement `stage` (or
      `unstage`).

      :returns: **devices** -- list including self and all child devices staged
      :rtype: list



   .. py:method:: unstage()

      Unstage the device.

      This method returns the device to the state it was prior to the
      last `stage` call.

      This method should be as fast as feasible as it does not
      return a status object.

      This method must be idempotent, multiple calls (without a new
      call to 'stage') have no effect.

      :returns: **devices** -- list including self and all child devices unstaged
      :rtype: list



   .. py:method:: trigger()

      Trigger the device and return status object.

      This method is responsible for implementing 'trigger' or
      'acquire' functionality of this device.

      If there is an appreciable time between triggering the device
      and it being able to be read (via the
      :meth:`~BlueskyInterface.read` method) then this method is
      also responsible for arranging that the
      :obj:`~ophyd.status.StatusBase` object returned by this method
      is notified when the device is ready to be read.

      If there is no delay between triggering and being readable,
      then this method must return a :obj:`~ophyd.status.StatusBase`
      object which is already completed.

      :returns: **status** -- :obj:`~ophyd.status.StatusBase` object which will be marked
                as complete when the device is ready to be read.
      :rtype: StatusBase



   .. py:method:: arm_plan()


.. py:class:: ROIStatN(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

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


   .. py:attribute:: roi_name


   .. py:attribute:: use


   .. py:attribute:: max_sizex


   .. py:attribute:: roi_startx


   .. py:attribute:: roi_sizex


   .. py:attribute:: max_sizey


   .. py:attribute:: roi_startxy


   .. py:attribute:: roi_sizey


   .. py:attribute:: bdg_width


   .. py:attribute:: min_value


   .. py:attribute:: max_value


   .. py:attribute:: mean_value


   .. py:attribute:: total_value


   .. py:attribute:: net_value


   .. py:attribute:: reset_button


.. py:class:: VortexROIStatPlugin

   Bases: :py:obj:`id4_common.devices.ad_mixins.ROIStatPlugin`


   .. py:attribute:: roi1


   .. py:attribute:: roi2


   .. py:attribute:: roi3


   .. py:attribute:: roi4


   .. py:attribute:: roi5


   .. py:attribute:: roi6


   .. py:attribute:: roi7


   .. py:attribute:: roi8


.. py:class:: VortexSCA

   Bases: :py:obj:`id4_common.devices.ad_mixins.AttributePlugin`


   .. py:attribute:: clock_ticks


   .. py:attribute:: reset_ticks


   .. py:attribute:: reset_counts


   .. py:attribute:: all_events


   .. py:attribute:: all_good


   .. py:attribute:: window1


   .. py:attribute:: window2


   .. py:attribute:: pileup


   .. py:attribute:: event_width


   .. py:attribute:: dt_factor


   .. py:attribute:: dt_percent


.. py:class:: VortexHDF1Plugin

   Bases: :py:obj:`id4_common.devices.ad_mixins.PolarHDF5Plugin`


   .. py:attribute:: array_counter


   .. py:attribute:: array_counter_readback


.. py:class:: TotalCorrectedSignal(prefix, roi_index, **kwargs)

   Bases: :py:obj:`ophyd.SignalRO`


   Signal that returns the deadtime corrected total counts


   .. py:attribute:: roi_index


   .. py:method:: get(**kwargs)

      The readback value



.. py:class:: VortexXspress37(*args, default_folder=Path('/net/s4data/export/sector4/4idd/bluesky_images/vortex'), hdf1_file_format='%s/%s_%6.6d.h5', **kwargs)

   Bases: :py:obj:`Trigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:attribute:: cam


   .. py:attribute:: chan1


   .. py:attribute:: chan2


   .. py:attribute:: chan3


   .. py:attribute:: chan4


   .. py:attribute:: chan5


   .. py:attribute:: chan6


   .. py:attribute:: chan7


   .. py:attribute:: stats1


   .. py:attribute:: stats2


   .. py:attribute:: stats3


   .. py:attribute:: stats4


   .. py:attribute:: stats5


   .. py:attribute:: stats6


   .. py:attribute:: stats7


   .. py:attribute:: sca1


   .. py:attribute:: sca2


   .. py:attribute:: sca3


   .. py:attribute:: sca4


   .. py:attribute:: sca5


   .. py:attribute:: sca6


   .. py:attribute:: sca7


   .. py:attribute:: total


   .. py:attribute:: hdf1


   .. py:attribute:: default_folder


   .. py:attribute:: hdf1_file_format
      :value: '%s/%s_%6.6d.h5'



   .. py:property:: preset_monitor


   .. py:property:: num_channels


   .. py:method:: align_on(time=0.1)

      Start detector in alignment mode



   .. py:method:: align_off()

      Stop detector



   .. py:method:: save_images_on()


   .. py:method:: save_images_off()


   .. py:method:: auto_save_on()


   .. py:method:: auto_save_off()


   .. py:method:: wait_for_detector()


   .. py:method:: default_settings()


   .. py:property:: read_rois


   .. py:method:: select_roi(rois)


   .. py:method:: plot_roi1()


   .. py:method:: plot_roi2()


   .. py:method:: plot_roi3()


   .. py:method:: plot_roi4()


   .. py:property:: label_option_map


   .. py:property:: plot_options


   .. py:method:: select_plot(channels)


   .. py:method:: setup_images(base_folder, file_name_base, file_number, flyscan=False)


   .. py:property:: save_image_flag


