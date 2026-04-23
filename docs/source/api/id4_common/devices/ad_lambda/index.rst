id4_common.devices.ad_lambda
============================

.. py:module:: id4_common.devices.ad_lambda

.. autoapi-nested-parse::

   Lambda area detector







Module Contents
---------------

.. py:data:: LAMBDA_FILES_ROOT
   :value: '/extdisk/4idd/'


.. py:data:: BLUESKY_FILES_ROOT
   :value: '/home/sector4/4idd/bluesky_images'


.. py:data:: TEST_IMAGE_DIR
   :value: '%Y/%m/%d/'


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



.. py:class:: Lambda250kCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.CamBase`


   support for X-Spectrum Lambda 750K detector
   https://x-spectrum.de/products/lambda-350k750k/


   .. py:attribute:: serial_number


   .. py:attribute:: firmware_version


   .. py:attribute:: operating_mode


   .. py:attribute:: energy_threshold


   .. py:attribute:: dual_threshold


   .. py:attribute:: file_number_sync
      :value: None



   .. py:attribute:: file_number_write
      :value: None



   .. py:attribute:: pool_max_buffers
      :value: None



.. py:class:: MyHDF5Plugin(*args, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.filestore_mixins.FileStoreHDF5SingleIterativeWrite`, :py:obj:`ophyd.areadetector.plugins.HDF5Plugin_V34`


   Used for running Areadetectors hdf5 plugin in `Single` mode, with
   `point_number` in the kwargs.


   .. py:attribute:: filestore_spec
      :value: 'AD_HDF5_Lambda250k_APSPolar'



.. py:class:: Lambda250kDetector(*args, image_name=None, delay_time=0.1, **kwargs)

   Bases: :py:obj:`MySingleTrigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   This trigger mixin class takes one acquisition per trigger.
   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


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


   .. py:attribute:: codec


   .. py:attribute:: proc


   .. py:property:: preset_monitor


   .. py:method:: default_kinds()


   .. py:method:: default_settings()
