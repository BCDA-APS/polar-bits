id4_common.devices.ad_vimba
===========================

.. py:module:: id4_common.devices.ad_vimba

.. autoapi-nested-parse::

   Vimba cameras





Module Contents
---------------

.. py:class:: Trigger(*args, image_name=None, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:method:: setup_manual_trigger()


   .. py:method:: setup_external_trigger()
      :abstractmethod:



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



.. py:class:: VimbaCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.CamBase`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: pool_max_buffers
      :value: None



   .. py:attribute:: serial_number


   .. py:attribute:: sdk_version


   .. py:attribute:: driver_version


   .. py:attribute:: adcore_version


   .. py:attribute:: num_exposures


   .. py:attribute:: connected_signal


   .. py:attribute:: trigger_source


   .. py:attribute:: trigger_overlap


   .. py:attribute:: trigger_exposure_mode


   .. py:attribute:: trigger_button


   .. py:attribute:: exposure_auto


   .. py:attribute:: frame_rate


   .. py:attribute:: image_mode


   .. py:attribute:: acquire_busy


   .. py:attribute:: wait_for_plugins


   .. py:attribute:: frames_delivered


   .. py:attribute:: frames_dropped


   .. py:attribute:: frames_underrun


   .. py:attribute:: packets_received


   .. py:attribute:: packets_missed


   .. py:attribute:: packets_errors


   .. py:attribute:: packets_requested


   .. py:attribute:: packets_resent


   .. py:attribute:: poll_features


   .. py:attribute:: temperature


   .. py:attribute:: gain_auto


.. py:class:: VimbaDetector(*args, default_folder='', hdf1_name_template='%s/%s_%6.6d', hdf1_file_extension='h5', max_num_images=65535, **kwargs)

   Bases: :py:obj:`Trigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:attribute:: cam


   .. py:attribute:: hdf1


   .. py:attribute:: roi1


   .. py:attribute:: roi2


   .. py:attribute:: roi3


   .. py:attribute:: roi4


   .. py:attribute:: stats1


   .. py:attribute:: stats2


   .. py:attribute:: stats3


   .. py:attribute:: stats4


   .. py:attribute:: stats5


   .. py:attribute:: default_folder
      :value: ''



   .. py:attribute:: hdf1_name_format
      :value: '%s/%s_%6.6d.h5'



   .. py:attribute:: max_num_images
      :value: 65535



   .. py:method:: wait_for_connection(all_signals=False, timeout=2)

      Wait for signals to connect

      :param all_signals: Wait for all signals to connect (including lazy ones)
      :type all_signals: bool, optional
      :param timeout: Overall timeout
      :type timeout: float or None



   .. py:property:: preset_monitor


   .. py:method:: align_on(time=0.1)

      Start detector in alignment mode



   .. py:method:: align_off()

      Stop detector



   .. py:method:: save_images_on()


   .. py:method:: save_images_off()


   .. py:method:: auto_save_on()


   .. py:method:: auto_save_off()


   .. py:method:: default_settings()


   .. py:method:: plot_select(rois)

      Selects which ROIs will be plotted. All are being read.

      This assumes that 4 ROIs are setup in Bluesky.

      :param rois: List with the ROIs numbers to be plotted.
      :type rois: iterable of ints



   .. py:method:: plot_allrois()


   .. py:method:: plot_roi1()


   .. py:method:: plot_roi2()


   .. py:method:: plot_roi3()


   .. py:method:: plot_roi4()


   .. py:method:: plot_roi5()


   .. py:method:: setup_images(base_path, name_template, file_number, flyscan=False)


   .. py:property:: save_image_flag


   .. py:property:: label_option_map


   .. py:property:: plot_options


   .. py:method:: select_plot(channels)
