id4_common.devices.ad_positionstream
====================================

.. py:module:: id4_common.devices.ad_positionstream

.. autoapi-nested-parse::

   Lambda area detector





Module Contents
---------------

.. py:class:: PositionStreamCam(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.areadetector.ADBase`


   The AreaDetector base class

   This serves as the base for all detectors and plugins


   .. py:attribute:: port_name


   .. py:attribute:: adcore_version


   .. py:attribute:: acquire


   .. py:attribute:: acquire_busy


   .. py:attribute:: acquire_time


   .. py:attribute:: array_counter


   .. py:attribute:: queued_arrays


   .. py:attribute:: array_rate


   .. py:attribute:: array_callbacks


   .. py:attribute:: wait_for_plugins


   .. py:attribute:: nd_attributes_file


.. py:class:: MySingleTrigger(*args, image_name=None, delay_time=0.1, **kwargs)

   Bases: :py:obj:`ophyd.BlueskyInterface`


   Classes that inherit from this can safely customize the
   these methods without breaking mro.



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



.. py:class:: PositionStreamDevice(*args, default_folder='', hdf1_name_template='%s/%s_%6.6d', hdf1_file_extension='h5', **kwargs)

   Bases: :py:obj:`MySingleTrigger`, :py:obj:`ophyd.areadetector.DetectorBase`


   Classes that inherit from this can safely customize the
   these methods without breaking mro.



   .. py:attribute:: cam


   .. py:attribute:: hdf1


   .. py:attribute:: default_folder
      :value: ''



   .. py:attribute:: hdf1_name_format
      :value: '%s/%s_%6.6d.h5'



   .. py:property:: preset_monitor


   .. py:method:: default_settings()


   .. py:method:: setup_images(base_path, name_template, file_number, flyscan=False)


   .. py:property:: save_image_flag


