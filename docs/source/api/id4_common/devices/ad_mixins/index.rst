id4_common.devices.ad_mixins
============================

.. py:module:: id4_common.devices.ad_mixins

.. autoapi-nested-parse::

   AD mixins







Module Contents
---------------

.. py:data:: logger

.. py:data:: USE_DM_PATH
   :value: True


.. py:data:: DM_ROOT_PATH
   :value: '/gdata/dm/4ID'


.. py:class:: PluginMixin(*args, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.plugins.PluginBase_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: TransformPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.TransformPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ImagePlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ImagePlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: PvaPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.PvaPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ProcessPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ProcessPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIPlugin(*args, **kwargs)

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


.. py:class:: CodecPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.CodecPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIStatPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ROIStatPlugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: ROIStatNPlugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.ROIStatNPlugin_V25`


   Remove property attribute found in AD IOCs now.


.. py:class:: AttributePlugin(*args, **kwargs)

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



.. py:class:: EigerDetectorCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

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



.. py:class:: VortexDetectorCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`apstools.devices.CamMixin_V34`, :py:obj:`ophyd.areadetector.Xspress3DetectorCam`


   Update cam support to AD release 3.1.1.


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


   Base class for FileStore mixin classes

   This class provides

     - python side path management (root, seperate write / read paths)
     - provides :meth:`generate_datum` to work with
       :meth:`~ophyd.areadetector.detectors.DetectorBase.dispatch`
     - cooperative stage / unstage methods
     - cooperative read / describe methods that inject datums

   Separate read and write paths are supported because the IOC that
   writes the files may not have the data storage mounted at the same
   place as the computers that are expected to access it later (for
   example, if the IOC is running on a windows machine and mounting a
   NFS share via samba).

   ``write_path_template`` must always be provided, only provide
   ``read_path_template`` if the writer and reader will not have the
   same mount point.

   The properties :attr:`read_path_template` and
   :attr:`write_path_template` do the following check against
   ``root``

     - if the only ``write_path_template`` is provided

       - Used to generate read and write paths (which are identical)
       - verify that the path starts with :attr:`root` or the path is
         a relative, prepend :attr:`root`

     - if ``read_path_template`` is also provided then the above
       checks are applied to it, but ``write_path_template`` is
       returned without any validation.

   This mixin assumes that it's peers provide an ``enable`` signal

   :param write_path_template: Template feed to :py:meth:`~datetime.datetime.strftime` to generate the
                               path to set the IOC to write saved files to.

                               See above for interactions with root and read_path_template
   :type write_path_template: str
   :param root: The 'root' of the file path.  This is inserted into filestore and
                enables files to be renamed or re-mounted with only some pain.

                This represents the part of the full path that is not
                'semantic'.  For example in the path
                '/data/XF42ID/2248/05/01/', the first two parts,
                '/data/XF42ID/', would be part of the 'root', where as the
                final 3 parts, '2248/05/01' is the date the data was taken.
                If the files were to be renamed, it is likely that only the
                'root' will be changed (for example of the whole file tree is
                copied to / mounted on another system or external hard drive).
   :type root: str, optional
   :param path_semantics:
   :type path_semantics: {'posix', 'windows'}, optional
   :param read_path_template: The read path template, if different from the write path.   See the
                              docstrings for ``write_path_template`` and ``root``.
   :type read_path_template: str, optional
   :param reg: If None provided, try to import the top-level api from
               filestore.api This will be deprecated 17Q3.

               This object must provide::

                  def register_resource(spec: str,
                                        root: str, rpath: str,
                                        rkwargs: dict,
                                        path_semantics: Optional[str]) -> str:
                      ...

                  def register_datum(resource_uid: str, datum_kwargs: dict) -> str:
                      ...
   :type reg: Registry

   .. rubric:: Notes

   This class in cooperative and expected to particpate in multiple
   inheritance, all ``*args`` and extra ``**kwargs`` are passed up the
   MRO chain.

   This class may be collapsed with :class:`FileStorePluginBase`


   .. py:property:: use_dm


   .. py:method:: make_write_read_paths(path=None)


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



.. py:class:: FileStoreHDF5IterativeWriteEpicsName(*args, **kwargs)

   Bases: :py:obj:`FileStorePluginBaseEpicsName`


   Base class for FileStore mixin classes

   This class provides

     - python side path management (root, seperate write / read paths)
     - provides :meth:`generate_datum` to work with
       :meth:`~ophyd.areadetector.detectors.DetectorBase.dispatch`
     - cooperative stage / unstage methods
     - cooperative read / describe methods that inject datums

   Separate read and write paths are supported because the IOC that
   writes the files may not have the data storage mounted at the same
   place as the computers that are expected to access it later (for
   example, if the IOC is running on a windows machine and mounting a
   NFS share via samba).

   ``write_path_template`` must always be provided, only provide
   ``read_path_template`` if the writer and reader will not have the
   same mount point.

   The properties :attr:`read_path_template` and
   :attr:`write_path_template` do the following check against
   ``root``

     - if the only ``write_path_template`` is provided

       - Used to generate read and write paths (which are identical)
       - verify that the path starts with :attr:`root` or the path is
         a relative, prepend :attr:`root`

     - if ``read_path_template`` is also provided then the above
       checks are applied to it, but ``write_path_template`` is
       returned without any validation.

   This mixin assumes that it's peers provide an ``enable`` signal

   :param write_path_template: Template feed to :py:meth:`~datetime.datetime.strftime` to generate the
                               path to set the IOC to write saved files to.

                               See above for interactions with root and read_path_template
   :type write_path_template: str
   :param root: The 'root' of the file path.  This is inserted into filestore and
                enables files to be renamed or re-mounted with only some pain.

                This represents the part of the full path that is not
                'semantic'.  For example in the path
                '/data/XF42ID/2248/05/01/', the first two parts,
                '/data/XF42ID/', would be part of the 'root', where as the
                final 3 parts, '2248/05/01' is the date the data was taken.
                If the files were to be renamed, it is likely that only the
                'root' will be changed (for example of the whole file tree is
                copied to / mounted on another system or external hard drive).
   :type root: str, optional
   :param path_semantics:
   :type path_semantics: {'posix', 'windows'}, optional
   :param read_path_template: The read path template, if different from the write path.   See the
                              docstrings for ``write_path_template`` and ``root``.
   :type read_path_template: str, optional
   :param reg: If None provided, try to import the top-level api from
               filestore.api This will be deprecated 17Q3.

               This object must provide::

                  def register_resource(spec: str,
                                        root: str, rpath: str,
                                        rkwargs: dict,
                                        path_semantics: Optional[str]) -> str:
                      ...

                  def register_datum(resource_uid: str, datum_kwargs: dict) -> str:
                      ...
   :type reg: Registry

   .. rubric:: Notes

   This class in cooperative and expected to particpate in multiple
   inheritance, all ``*args`` and extra ``**kwargs`` are passed up the
   MRO chain.

   This class may be collapsed with :class:`FileStorePluginBase`


   .. py:attribute:: filestore_spec
      :value: 'AD_HDF5'



   .. py:method:: get_frames_per_point()


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



   .. py:method:: generate_datum(key, timestamp, datum_kwargs)

      Generate a uid and cache it with its key for later insertion.



.. py:class:: HDF5Plugin(*args, **kwargs)

   Bases: :py:obj:`PluginMixin`, :py:obj:`ophyd.areadetector.plugins.HDF5Plugin_V34`


   Remove property attribute found in AD IOCs now.


.. py:class:: PolarHDF5Plugin(*args, write_path_template='', **kwargs)

   Bases: :py:obj:`HDF5Plugin`, :py:obj:`FileStoreHDF5IterativeWriteEpicsName`


   Using the filename from EPICS.


   .. py:attribute:: autosave


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



   .. py:property:: warmup_signals


   .. py:method:: warmup()

      A convenience method for 'priming' the plugin.

      The plugin has to 'see' one acquisition before it is ready to capture.
      This sets the array size, etc.



.. py:class:: TriggerBase(*args, acquisition_signal_dev='cam.acquire', acquire_busy_signal_dev='cam.acquire_busy', **kwargs)

   Bases: :py:obj:`ophyd.BlueskyInterface`


   Base class for trigger mixin classes

   Subclasses must define a method with this signature:

   ``acquire_changed(self, value=None, old_value=None, **kwargs)``


.. py:class:: ADTriggerStatus(device, *args, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.trigger_mixins.ADTriggerStatus`


   A Status for AreaDetector triggers

   A special status object that notifies watches (progress bars)
   based on comparing device.cam.array_counter to  device.cam.num_images.


