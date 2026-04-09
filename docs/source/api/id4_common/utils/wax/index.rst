id4_common.utils.wax
====================

.. py:module:: id4_common.utils.wax


Attributes
----------

.. autoapisummary::

   id4_common.utils.wax.cat


Functions
---------

.. autoapisummary::

   id4_common.utils.wax.wm
   id4_common.utils.wax.wax
   id4_common.utils.wax.wa_scan
   id4_common.utils.wax.wa_new


Module Contents
---------------

.. py:data:: cat

.. py:function:: wm(*args)

.. py:function:: wax(scan=None, motor=None, device='motor', display_missed=False)

   Display current and past motor values

   :param scan number: Scan number of any scan
   :type scan number: int, optional
   :param motor name: If None all motor positions will be deisplayed.
   :type motor name: string, optional
   :param device name: Default' is "motor", used to find devices in the registry.
                       Other possibilities include "detector", "sensor", "actuator", etc.
   :type device name: string: optional

   .. rubric:: Examples

   wa(): current position of all motors
   wa('motor'): current position of motors containing 'motor'
   wa(42, 'motor'): current position of motors containing 'motor' of scan
   wa(42): current position of all motors in scan 42


.. py:function:: wa_scan(scan=None, motor=None)

.. py:function:: wa_new(motor=None)

