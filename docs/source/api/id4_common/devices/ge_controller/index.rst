id4_common.devices.ge_controller
================================

.. py:module:: id4_common.devices.ge_controller

.. autoapi-nested-parse::

   GE pressure controllers



Classes
-------

.. autoapisummary::

   id4_common.devices.ge_controller.GEController


Module Contents
---------------

.. py:class:: GEController(*args, timeout=60 * 60 * 10, **kwargs)

   Bases: :py:obj:`apstools.devices.PVPositionerSoftDoneWithStop`


   General controller as a PVPositioner


   .. py:attribute:: units


   .. py:attribute:: control


   .. py:attribute:: slew_mode


   .. py:attribute:: slew


   .. py:attribute:: effort


   .. py:property:: settle_time


   .. py:property:: egu


   .. py:method:: stop(*, success=False)


