id4_common.suspenders.suspender_utils
=====================================

.. py:module:: id4_common.suspenders.suspender_utils

.. autoapi-nested-parse::

   Utility functions for managing and configuring beamline shutter suspenders.







Module Contents
---------------

.. py:data:: logger

.. py:function:: suspender_stop(suspender_label=None)

   Remove one or more shutter suspenders from the RunEngine.


.. py:function:: suspender_restart(suspender_label=None)

   Re-install one or more shutter suspenders on the RunEngine.


.. py:function:: suspender_change_sleep(suspender_label=None, sleep_time=None)

   Change the post-beam-return sleep time for one or more shutter suspenders.


