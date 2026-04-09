id4_common.devices.ad_vimba
===========================

.. py:module:: id4_common.devices.ad_vimba

.. autoapi-nested-parse::

   Vimba cameras



Classes
-------

.. autoapisummary::

   id4_common.devices.ad_vimba.Trigger
   id4_common.devices.ad_vimba.VimbaCam
   id4_common.devices.ad_vimba.VimbaDetector


Module Contents
---------------

.. py:class:: Trigger(*args, image_name=None, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:method:: setup_manual_trigger()


   .. py:method:: setup_external_trigger()
      :abstractmethod:



   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:method:: trigger()


.. py:class:: VimbaCam

   Bases: :py:obj:`ophyd.areadetector.CamBase`


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


