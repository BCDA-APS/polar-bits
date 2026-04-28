id4_common.devices.preamps
==========================

.. py:module:: id4_common.devices.preamps

.. autoapi-nested-parse::

   SRS 570 pre-amplifiers





Module Contents
---------------

.. py:class:: LocalPreAmp(*args, scaler_channel=None, shutter=None, **kwargs)

   Bases: :py:obj:`apstools.devices.SRS570_PreAmplifier`


   Ophyd support for Stanford Research Systems 570 preamplifier from synApps.


   .. py:property:: shutter


   .. py:method:: opt_sens_plan(scaler_channel=None, time=0.1, delay=1)


   .. py:method:: opt_offset_plan(scaler_channel=None, time=0.1, delay=1)


   .. py:method:: opt_fine_plan(scaler_channel=None, start=None, end=None, steps=11, time=0.1, delay=1)


   .. py:method:: optimize_plan(scaler_channel=None, time=0.1, delay=1)


   .. py:method:: default_settings()
