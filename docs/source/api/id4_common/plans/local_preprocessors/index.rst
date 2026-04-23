id4_common.plans.local_preprocessors
====================================

.. py:module:: id4_common.plans.local_preprocessors

.. autoapi-nested-parse::

   Local decorators







Module Contents
---------------

.. py:data:: logger

.. py:function:: extra_devices_wrapper(plan, extras)

.. py:function:: configure_counts_wrapper(plan, detectors, count_time)

   Set all devices with a `preset_monitor` to the same value.

   The original setting is stashed and restored at the end.

   :param plan: a generator, list, or similar containing `Msg` objects
   :type plan: iterable or iterator
   :param monitor: If None, the plan passes through unchanged.
   :type monitor: float or None

   :Yields: **msg** (*Msg*) -- messages from plan, with 'set' messages inserted


.. py:function:: stage_dichro_wrapper(plan, dichro, lockin, sgz, positioner)

   Stage dichoic scans.

   :param plan: a generator, list, or similar containing `Msg` objects
   :type plan: iterable or iterator
   :param dichro: Flag that triggers the stage/unstage process of dichro scans.
   :type dichro: boolean
   :param lockin: Flag that triggers the stage/unstage process of lockin scans.
   :type lockin: boolean

   :Yields: **msg** (*Msg*) -- messages from plan, with 'subscribe' and 'unsubscribe' messages
            inserted and appended


.. py:function:: stage_magnet911_wrapper(plan, magnet, persistent=True)

   Stage the 911T magnet.

   Turns on/off the persistence switch heater before/after the magnetic field
   scan or move.

   :param plan: a generator, list, or similar containing `Msg` objects
   :type plan: iterable or iterator
   :param magnet: Flag that triggers the stage/unstage.
   :type magnet: boolean

   :Yields: **msg** (*Msg*) -- messages from plan, with 'subscribe' and 'unsubscribe' messages
            inserted and appended


.. py:function:: stage_4idg_softglue_wrapper(plan, use_sg)

.. py:data:: extra_devices_decorator

.. py:data:: configure_counts_decorator

.. py:data:: stage_dichro_decorator

.. py:data:: stage_magnet911_decorator

.. py:data:: stage_4idg_softglue_decorator
