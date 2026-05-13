id4_common.plans.center_maximum
===============================

.. py:module:: id4_common.plans.center_maximum

.. autoapi-nested-parse::

   Legacy ``cen2`` / ``maxi2`` / ``mini2`` plans driven by
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

   Kept as a fallback path for runs where the BestEffortCallback was
   running live.  For everything else, prefer the new
   :mod:`id4_common.plans.peak_position` ``cen`` / ``com`` / ``maxi`` /
   ``mini`` plans, which compute peak statistics from the catalog and
   support 2-D ``grid_scan`` runs (issue #59).





Module Contents
---------------

.. py:function:: cen2(positioner=None, detector=None)

   Legacy: move motor to FWHM-midpoint of last scan via the BEC peaks.

   Uses the position found by
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
   :func:`id4_common.plans.peak_position.cen` for new code.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional


.. py:function:: maxi2(positioner=None, detector=None)

   Legacy: move motor to maximum of last scan via the BEC peaks.

   Uses the position found by
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
   :func:`id4_common.plans.peak_position.maxi` for new code.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional


.. py:function:: mini2(positioner=None, detector=None)

   Legacy: move motor to minimum of last scan via the BEC peaks.

   Uses the position found by
   `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
   :func:`id4_common.plans.peak_position.mini` for new code.

   :param positioner: Device to be moved to center.
   :type positioner: ophyd instance, optional
   :param detector: Ophyd instance name of the detector used to center. This is only needed
                    if the scan had more than one hinted detector.
   :type detector: str, optional


