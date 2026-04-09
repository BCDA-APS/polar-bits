id4_common.devices.vortex_xmap
==============================

.. py:module:: id4_common.devices.vortex_xmap

.. autoapi-nested-parse::

   Vortex with DXP



Attributes
----------

.. autoapisummary::

   id4_common.devices.vortex_xmap.MAX_ROIS


Classes
-------

.. autoapisummary::

   id4_common.devices.vortex_xmap.MyDXP
   id4_common.devices.vortex_xmap.MyMCA
   id4_common.devices.vortex_xmap.SingleTrigger
   id4_common.devices.vortex_xmap.TotalCorrectedSignal
   id4_common.devices.vortex_xmap.VortexXMAP


Module Contents
---------------

.. py:data:: MAX_ROIS
   :value: 32


.. py:class:: MyDXP

   Bases: :py:obj:`ophyd.mca.SaturnDXP`


   .. py:attribute:: live_time_output
      :value: None



   .. py:attribute:: trigger_output
      :value: None



.. py:class:: MyMCA

   Bases: :py:obj:`ophyd.mca.EpicsMCARecord`


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


   .. py:method:: unstage()


   .. py:method:: trigger()

      Trigger one acquisition.



.. py:class:: TotalCorrectedSignal(prefix, roi_index=0, **kwargs)

   Bases: :py:obj:`ophyd.SignalRO`


   Signal that returns the deadtime corrected total counts


   .. py:attribute:: roi_index
      :value: 0



   .. py:method:: get(**kwargs)


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


