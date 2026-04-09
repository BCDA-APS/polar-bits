id4_common.devices.softgluezynq_vortex
======================================

.. py:module:: id4_common.devices.softgluezynq_vortex


Classes
-------

.. autoapisummary::

   id4_common.devices.softgluezynq_vortex.SGZVortex


Module Contents
---------------

.. py:class:: SGZVortex(*args, reset_sleep_time=0.1, reference_clock=10000000.0, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: preset_monitor


   .. py:attribute:: buffers


   .. py:attribute:: io


   .. py:attribute:: up_counter_status


   .. py:attribute:: down_counter_pulse


   .. py:attribute:: div_by_n


   .. py:attribute:: gate_sync


   .. py:attribute:: gate_trigger


   .. py:attribute:: and_1


   .. py:attribute:: and_3


   .. py:attribute:: or_1


   .. py:attribute:: dff_2


   .. py:attribute:: dff_3


   .. py:attribute:: histscal


   .. py:attribute:: histdma


   .. py:attribute:: clocks


   .. py:attribute:: clock_freq


   .. py:property:: frequency


   .. py:method:: start_softglue()


   .. py:method:: stop_softglue()


   .. py:method:: reset()


   .. py:method:: stage()


   .. py:method:: unstage()


   .. py:method:: trigger()


   .. py:method:: default_settings(timeout=10)


