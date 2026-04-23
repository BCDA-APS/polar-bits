id4_common.devices.vortex_xmap
==============================

.. py:module:: id4_common.devices.vortex_xmap

.. autoapi-nested-parse::

   Vortex with DXP







Module Contents
---------------

.. py:data:: MAX_ROIS
   :value: 32


.. py:class:: MyDXP(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.mca.SaturnDXP`


   All high-level DXP parameters for each channel


   .. py:attribute:: live_time_output
      :value: None



   .. py:attribute:: trigger_output
      :value: None



.. py:class:: MyMCA(*args, **kwargs)

   Bases: :py:obj:`ophyd.mca.EpicsMCARecord`


   SynApps MCA Record interface


   .. py:attribute:: check_acquiring


.. py:class:: SingleTrigger(*args, **kwargs)

   Bases: :py:obj:`ophyd.Device`


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



.. py:class:: TotalCorrectedSignal(prefix, roi_index=0, **kwargs)

   Bases: :py:obj:`ophyd.SignalRO`


   Signal that returns the deadtime corrected total counts


   .. py:attribute:: roi_index
      :value: 0



   .. py:method:: get(**kwargs)

      The readback value



.. py:class:: VortexXMAP(*args, **kwargs)

   Bases: :py:obj:`SingleTrigger`


   This trigger mixin class takes one acquisition per trigger.
   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


   .. py:attribute:: start


   .. py:attribute:: stop_


   .. py:attribute:: erase_start


   .. py:attribute:: erase


   .. py:attribute:: status


   .. py:attribute:: collection_mode


   .. py:attribute:: preset_mode


   .. py:attribute:: instant_deadtime


   .. py:attribute:: average_deadtime


   .. py:attribute:: poll_time


   .. py:attribute:: real_preset


   .. py:attribute:: live_preset


   .. py:attribute:: real_elapsed


   .. py:attribute:: live_elapsed


   .. py:attribute:: events_preset


   .. py:attribute:: triggers_preset


   .. py:attribute:: total


   .. py:attribute:: mca1


   .. py:attribute:: mca2


   .. py:attribute:: mca3


   .. py:attribute:: mca4


   .. py:attribute:: dxp1


   .. py:attribute:: dxp2


   .. py:attribute:: dxp3


   .. py:attribute:: dxp4


   .. py:property:: preset_monitor


   .. py:method:: default_kinds()


   .. py:method:: default_settings()


   .. py:property:: read_rois


   .. py:method:: select_roi(rois)


   .. py:method:: plot_roi0()


   .. py:method:: plot_roi1()


   .. py:method:: plot_roi2()


   .. py:method:: plot_roi3()


   .. py:method:: plot_roi4()


   .. py:property:: label_option_map


   .. py:property:: plot_options


   .. py:method:: select_plot(channels)


