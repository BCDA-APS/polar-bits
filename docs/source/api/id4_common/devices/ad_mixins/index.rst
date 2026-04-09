id4_common.devices.ad_mixins
============================

.. py:module:: id4_common.devices.ad_mixins

.. autoapi-nested-parse::

   AD mixins



Attributes
----------

.. autoapisummary::

   id4_common.devices.ad_mixins.logger
   id4_common.devices.ad_mixins.USE_DM_PATH
   id4_common.devices.ad_mixins.DM_ROOT_PATH


Classes
-------

.. autoapisummary::

   id4_common.devices.ad_mixins.PluginMixin
   id4_common.devices.ad_mixins.TransformPlugin
   id4_common.devices.ad_mixins.ImagePlugin
   id4_common.devices.ad_mixins.PvaPlugin
   id4_common.devices.ad_mixins.ProcessPlugin
   id4_common.devices.ad_mixins.ROIPlugin
   id4_common.devices.ad_mixins.StatsPlugin
   id4_common.devices.ad_mixins.CodecPlugin
   id4_common.devices.ad_mixins.ROIStatPlugin
   id4_common.devices.ad_mixins.ROIStatNPlugin
   id4_common.devices.ad_mixins.AttributePlugin
   id4_common.devices.ad_mixins.EigerDetectorCam
   id4_common.devices.ad_mixins.VortexDetectorCam
   id4_common.devices.ad_mixins.FileStorePluginBaseEpicsName
   id4_common.devices.ad_mixins.FileStoreHDF5IterativeWriteEpicsName
   id4_common.devices.ad_mixins.HDF5Plugin
   id4_common.devices.ad_mixins.PolarHDF5Plugin
   id4_common.devices.ad_mixins.TriggerBase
   id4_common.devices.ad_mixins.ADTriggerStatus


Module Contents
---------------

.. py:data:: logger

.. py:data:: USE_DM_PATH
   :value: True


.. py:data:: DM_ROOT_PATH
   :value: '/gdata/dm/4ID'


.. py:class:: PluginMixin

   Bases: :py:obj:`ophyd.areadetector.plugins.PluginBase_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: TransformPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.TransformPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ImagePlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ImagePlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: PvaPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.PvaPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ProcessPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ProcessPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ROIPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: StatsPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.StatsPlugin_V34`


   Remove property attribute found in AD IOCs now.


   .. py:attribute:: sigma_x
      :value: None



   .. py:attribute:: sigma_y
      :value: None



   .. py:method:: start_auto_kind()


   .. py:method:: stop_auto_kind()


.. py:class:: CodecPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.CodecPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIStatPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ROIStatPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIStatNPlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ROIStatNPlugin_V25`


   Remove property attribute found in AD IOCs now.


.. py:class:: AttributePlugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.AttributePlugin_V34`


   Remove property attribute found in AD IOCs now.


   .. py:attribute:: ts_acquiring
      :value: None



   .. py:attribute:: ts_control
      :value: None



   .. py:attribute:: ts_current_point
      :value: None



   .. py:attribute:: ts_num_points
      :value: None



   .. py:attribute:: ts_read
      :value: None



.. py:class:: EigerDetectorCam

   Bases: :py:obj:`apstools.devices.CamMixin_V34`, :py:obj:`EigerDetectorCam`


   Revise EigerDetectorCam for ADCore revisions.


   .. py:attribute:: initialize


   .. py:attribute:: counting_mode


   .. py:attribute:: file_number_sync
      :value: None



   .. py:attribute:: file_number_write
      :value: None



   .. py:attribute:: fw_clear
      :value: None



   .. py:attribute:: link_0
      :value: None



   .. py:attribute:: link_1
      :value: None



   .. py:attribute:: link_2
      :value: None



   .. py:attribute:: link_3
      :value: None



   .. py:attribute:: dcu_buff_free
      :value: None



   .. py:attribute:: offset
      :value: None



.. py:class:: VortexDetectorCam

   Bases: :py:obj:`apstools.devices.CamMixin_V34`, :py:obj:`ophyd.areadetector.Xspress3DetectorCam`


   .. py:attribute:: trigger_mode


   .. py:attribute:: erase_on_start


   .. py:attribute:: offset
      :value: None



   .. py:attribute:: num_exposures
      :value: None



   .. py:attribute:: acquire_period
      :value: None



.. py:class:: FileStorePluginBaseEpicsName(*args, ioc_path_root=None, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.filestore_mixins.FileStoreBase`


   .. py:property:: use_dm


   .. py:method:: make_write_read_paths(path=None)


   .. py:method:: stage()


.. py:class:: FileStoreHDF5IterativeWriteEpicsName(*args, **kwargs)

   Bases: :py:obj:`FileStorePluginBaseEpicsName`


   .. py:attribute:: filestore_spec
      :value: 'AD_HDF5'



   .. py:method:: get_frames_per_point()


   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:method:: generate_datum(key, timestamp, datum_kwargs)


.. py:class:: HDF5Plugin

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.HDF5Plugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: PolarHDF5Plugin(*args, write_path_template='', **kwargs)

   Bases: :py:obj:`HDF5Plugin`, :py:obj:`FileStoreHDF5IterativeWriteEpicsName`


   Using the filename from EPICS.


   .. py:attribute:: autosave


   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:property:: warmup_signals


   .. py:method:: warmup()


.. py:class:: TriggerBase(*args, acquisition_signal_dev='cam.acquire', acquire_busy_signal_dev='cam.acquire_busy', **kwargs)

   Bases: :py:obj:`ophyd.BlueskyInterface`


   Base class for trigger mixin classes

   Subclasses must define a method with this signature:

   ``acquire_changed(self, value=None, old_value=None, **kwargs)``


.. py:class:: ADTriggerStatus

   Bases: :py:obj:`ophyd.areadetector.trigger_mixins.ADTriggerStatus`


