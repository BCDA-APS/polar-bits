id4_common.devices.softgluezynq_g
=================================

.. py:module:: id4_common.devices.softgluezynq_g

.. autoapi-nested-parse::

   SoftGlueZynq



Attributes
----------

.. autoapisummary::

   id4_common.devices.softgluezynq_g.logger


Classes
-------

.. autoapisummary::

   id4_common.devices.softgluezynq_g.SoftGlueZynqDevice


Module Contents
---------------

.. py:data:: logger

.. py:class:: SoftGlueZynqDevice(*args, reset_sleep_time=0.2, reference_clock=10000000.0, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: preset_monitor


   .. py:attribute:: dma


   .. py:attribute:: buffers


   .. py:attribute:: io


   .. py:attribute:: up_counter_count


   .. py:attribute:: up_counter_trigger


   .. py:attribute:: up_counter_gate_on


   .. py:attribute:: up_counter_gate_off


   .. py:attribute:: div_by_n_count


   .. py:attribute:: div_by_n_trigger


   .. py:attribute:: div_by_n_interrupt


   .. py:attribute:: gate_trigger


   .. py:attribute:: scaltostream


   .. py:attribute:: clocks


   .. py:attribute:: clock_freq


   .. py:attribute:: sample_pos


   .. py:method:: start_softglue()


   .. py:method:: stop_softglue()


   .. py:method:: start_detectors()


   .. py:method:: stop_detectors()


   .. py:method:: reset_plan()


   .. py:method:: clear_enable_dma()


   .. py:method:: clear_disable_dma()


   .. py:method:: setup_trigger_plan(period_time, pulse_width_time, pulse_delay_time=0)


   .. py:method:: setup_count_plan(time)


   .. py:method:: default_settings(timeout=10)


