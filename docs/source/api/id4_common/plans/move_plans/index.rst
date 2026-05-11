id4_common.plans.move_plans
===========================

.. py:module:: id4_common.plans.move_plans

.. autoapi-nested-parse::

   Local move plans: ``mv``, ``mvr``, ``abs_set``.

   Thin wrappers around the corresponding bluesky plan stubs that also stage
   the 9-Tesla magnet (``magnet911``) when its field is one of the targets.





Module Contents
---------------

.. py:function:: mv(*args, **kwargs)

   Move one or more devices to a setpoint, and wait for all to complete.

   This is a local version of `bluesky.plan_stubs.mv`. If more than one device
   is specifed, the movements are done in parallel.

   :param args: device1, value1, device2, value2, ...
   :param kwargs: passed to bluesky.plan_stubs.mv

   :Yields: **msg** (*Msg*)

   .. seealso:: :func:`bluesky.plan_stubs.mv`


.. py:function:: mvr(*args, **kwargs)

   Move one or more devices to a relative setpoint. Wait for all to complete.

   If more than one device is specified, the movements are done in parallel.

   This is a local version of `bluesky.plan_stubs.mvr`.

   :param args: device1, value1, device2, value2, ...
   :param kwargs: passed to bluesky.plan_stub.mvr

   :Yields: **msg** (*Msg*)

   .. seealso:: :func:`bluesky.plan_stubs.rel_set`, :func:`bluesky.plan_stubs.mv`


.. py:function:: abs_set(*args, **kwargs)

   Set a value. Optionally, wait for it to complete before continuing.

   This is a local version of `bluesky.plan_stubs.abs_set`. If more than one
   device is specifed, the movements are done in parallel.

   :param obj:
   :type obj: Device
   :param group: identifier used by 'wait'
   :type group: string (or any hashable object), optional
   :param wait: If True, wait for completion before processing any more messages.
                False by default.
   :type wait: boolean, optional
   :param args: passed to obj.set()
   :param kwargs: passed to obj.set()

   :Yields: **msg** (*Msg*)

   .. seealso:: :func:`bluesky.plan_stubs.rel_set`, :func:`bluesky.plan_stubs.wait`, :func:`bluesky.plan_stubs.mv`
