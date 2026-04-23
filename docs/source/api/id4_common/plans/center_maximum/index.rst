id4_common.plans.center_maximum
===============================

.. py:module:: id4_common.plans.center_maximum




Module Contents
---------------

.. py:function:: cen(positioner=None, detector=None)

   Plan that moves motor to center of last scan.

   Uses the position found by the
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional


.. py:function:: maxi(positioner=None, detector=None)

   Plan that moves motor to maximum of last scan.

   Uses the position found by the
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional


.. py:function:: mini(positioner=None, detector=None)

   Plan that moves motor to minimum of last scan.

   Uses the position found by the
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional
