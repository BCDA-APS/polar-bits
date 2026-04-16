id4_common.devices.shutters
===========================

.. py:module:: id4_common.devices.shutters

.. autoapi-nested-parse::

   Shutters





Module Contents
---------------

.. py:class:: PolarShutter(prefix, state_pv: str, *args, **kwargs)

   Bases: :py:obj:`apstools.devices.ApsPssShutterWithStatus`


   APS PSS shutter with separate status PV

   .. index:: Ophyd Device; ApsPssShutterWithStatus
   * APS PSS shutters have separate bit PVs for open and close
   * set either bit, the shutter moves, and the bit resets a short time later
   * a separate status PV tells if the shutter is open or closed
     (see :func:`ApsPssShutter()` for alternative)

   PARAMETERS

   prefix *str* :
       EPICS PV prefix

   state_pv *str* :
       Name of EPICS PV that provides shutter's current state.

   name *str* :
       (kwarg, required) object's canonical name

   EXAMPLE::

       A_shutter = ApsPssShutterWithStatus(
           "2bma:A_shutter:",
           "PA:02BM:STA_A_FES_OPEN_PL",
           name="A_shutter")
       B_shutter = ApsPssShutterWithStatus(
           "2bma:B_shutter:",
           "PA:02BM:STA_B_SBS_OPEN_PL",
           name="B_shutter")
       A_shutter.wait_for_connection()
       B_shutter.wait_for_connection()

       A_shutter.open()
       A_shutter.close()

       or

       A_shutter.set("open")
       A_shutter.set("close")

   When using the shutter in a plan, be sure to use `yield from`.

       def in_a_plan(shutter):
           yield from abs_set(shutter, "open", wait=True)
           # do something
           yield from abs_set(shutter, "close", wait=True)

       RE(in_a_plan(A_shutter))



   .. py:attribute:: sleep_time
      :value: 5



   .. py:method:: start_auto_shutter()


   .. py:method:: stop_auto_shutter()


