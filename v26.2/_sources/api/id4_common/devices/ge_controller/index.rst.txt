id4_common.devices.ge_controller
================================

.. py:module:: id4_common.devices.ge_controller

.. autoapi-nested-parse::

   GE pressure controllers





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

      Return the settle time in seconds after a move completes.


   .. py:property:: egu

      Return the engineering units string from the EPICS units signal.


   .. py:method:: stop(*, success=False)

      Stop the positioner; hold current position if not successful.



