id4_common.devices.ad_eiger1M
=============================

.. py:module:: id4_common.devices.ad_eiger1M

.. autoapi-nested-parse::

   Eiger 1M setup



Classes
-------

.. autoapisummary::

   id4_common.devices.ad_eiger1M.TriggerTime
   id4_common.devices.ad_eiger1M.Eiger1MDetector


Module Contents
---------------

.. py:class:: TriggerTime(*args, image_name=None, min_period=0.0, delay=0.3, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:property:: acquisition_signal


   .. py:property:: delay


   .. py:property:: min_period


   .. py:method:: setup_manual_trigger()


   .. py:method:: setup_external_trigger(trigger_type='gate')


   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:method:: trigger()

      Trigger one acquisition.



.. py:class:: Eiger1MDetector(*args, default_folder='', hdf1_name_template='%s/%s_%6.6d', hdf1_file_extension='h5', max_num_images=600000, **kwargs)

   Bases: :py:obj:`TriggerTime`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:attribute:: cam


   .. py:attribute:: codec1


   .. py:attribute:: codec2


   .. py:attribute:: proc


   .. py:attribute:: trans


   .. py:attribute:: image


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
      :value: 600000



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


   .. py:method:: plot_all()


   .. py:method:: plot_stats1()


   .. py:method:: plot_stats2()


   .. py:method:: plot_stats3()


   .. py:method:: plot_stats4()


   .. py:method:: plot_stats5()


   .. py:method:: setup_images(base_path, name_template, file_number, flyscan=False)


   .. py:method:: plot_select(stats)

      Selects which stats will be plotted. All are being read.

      This assumes that 5 stats are setup in Bluesky.

      :param stats: List with the stats numbers to be plotted.
      :type stats: iterable of ints



   .. py:property:: save_image_flag


   .. py:property:: label_option_map


   .. py:property:: plot_options


   .. py:method:: select_plot(channels)


