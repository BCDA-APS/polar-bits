id4_common.devices.ad_lightfield
================================

.. py:module:: id4_common.devices.ad_lightfield

.. autoapi-nested-parse::

   LightField based area detector







Module Contents
---------------

.. py:class:: MySingleTrigger(*args, image_name=None, delay_time=0.1, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.
   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


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

      Trigger one acquisition.



.. py:class:: LF_HDF

   Bases: :py:obj:`id4_common.devices.ad_mixins.PolarHDF5Plugin`


   .. py:method:: make_write_read_paths(write_path=None, read_path=None)


.. py:class:: LightFieldFilePlugin(*args, **kwargs)

   Bases: :py:obj:`ophyd.Device`, :py:obj:`ophyd.areadetector.filestore_mixins.FileStoreBase`


   Using the filename from EPICS.


   .. py:attribute:: enable


   .. py:attribute:: filestore_spec
      :value: 'AD_SPE_APSPolar'



   .. py:property:: base_name


   .. py:method:: make_write_read_paths(write_path=None, read_path=None)


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



   .. py:method:: generate_datum(key, timestamp, datum_kwargs)

      Using the num_images_counter to pick image from scan.



.. py:class:: MyLightFieldCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.LightFieldDetectorCam`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: file_name_base


   .. py:attribute:: file_path


   .. py:attribute:: file_name


   .. py:attribute:: file_number


   .. py:attribute:: file_template


   .. py:attribute:: num_images_counter


   .. py:attribute:: grating_wavelength


   .. py:attribute:: pool_max_buffers
      :value: None



   .. py:attribute:: background_file


   .. py:attribute:: background_full_file


   .. py:attribute:: background_path


.. py:class:: LightFieldDetector(*args, hdf1_name_template='%s/%s_%6.6d', hdf1_file_extension='h5', bluesky_files_root='', windows_files_root='', relative_default_folder='', **kwargs)

   Bases: :py:obj:`MySingleTrigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.
   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


   .. py:attribute:: cam


   .. py:attribute:: image


   .. py:attribute:: hdf1


   .. py:attribute:: file


   .. py:attribute:: hdf1_name_format
      :value: '%s/%s_%6.6d.h5'



   .. py:attribute:: default_ioc_folder
      :value: ''



   .. py:attribute:: bluesky_files_root
      :value: ''



   .. py:attribute:: windows_files_root
      :value: ''



   .. py:property:: preset_monitor


   .. py:method:: save_images_on()


   .. py:method:: save_images_off()


   .. py:method:: auto_save_on()


   .. py:method:: auto_save_off()


   .. py:method:: default_settings()


   .. py:method:: setup_images(base_path, name_template, file_number, flyscan=False)


   .. py:property:: save_image_flag


.. py:data:: spectrometer

