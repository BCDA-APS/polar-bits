id4_common.devices.vortex_xspress3_me4
======================================

.. py:module:: id4_common.devices.vortex_xspress3_me4

.. autoapi-nested-parse::

   Eiger 1M setup



Attributes
----------

.. autoapisummary::

   id4_common.devices.vortex_xspress3_me4.logger
   id4_common.devices.vortex_xspress3_me4.MAX_IMAGES
   id4_common.devices.vortex_xspress3_me4.MAX_ROIS


Classes
-------

.. autoapisummary::

   id4_common.devices.vortex_xspress3_me4.Trigger
   id4_common.devices.vortex_xspress3_me4.ROIStatN
   id4_common.devices.vortex_xspress3_me4.VortexROIStatPlugin
   id4_common.devices.vortex_xspress3_me4.VortexSCA
   id4_common.devices.vortex_xspress3_me4.VortexHDF1Plugin
   id4_common.devices.vortex_xspress3_me4.TotalCorrectedSignal
   id4_common.devices.vortex_xspress3_me4.VortexXspress34


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


   .. py:method:: setup_external_trigger()


   .. py:method:: setup_sgzbca_trigger()


   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:method:: trigger()


   .. py:method:: arm_plan()


.. py:class:: ROIStatN

   Bases: :py:obj:`ophyd.Device`


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


   Remove property attribute found in AD IOCs now.


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


   Remove property attribute found in AD IOCs now.


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


.. py:class:: VortexHDF1Plugin(*args, write_path_template='', **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.PolarHDF5Plugin`


   Using the filename from EPICS.


   .. py:attribute:: array_counter


   .. py:attribute:: array_counter_readback


.. py:class:: TotalCorrectedSignal(prefix, roi_index, **kwargs)

   Bases: :py:obj:`ophyd.SignalRO`


   Signal that returns the deadtime corrected total counts


   .. py:attribute:: roi_index


   .. py:method:: get(**kwargs)


.. py:class:: VortexXspress34(*args, default_folder=Path('/net/s4data/export/sector4/4idd/bluesky_images/vortex'), hdf1_file_format='%s/%s_%6.6d.h5', **kwargs)

   Bases: :py:obj:`Trigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:attribute:: cam


   .. py:attribute:: chan1


   .. py:attribute:: chan2


   .. py:attribute:: chan3


   .. py:attribute:: chan4


   .. py:attribute:: stats1


   .. py:attribute:: stats2


   .. py:attribute:: stats3


   .. py:attribute:: stats4


   .. py:attribute:: sca1


   .. py:attribute:: sca2


   .. py:attribute:: sca3


   .. py:attribute:: sca4


   .. py:attribute:: total


   .. py:attribute:: hdf1


   .. py:attribute:: default_folder


   .. py:attribute:: hdf1_file_format
      :value: '%s/%s_%6.6d.h5'



   .. py:property:: preset_monitor


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


