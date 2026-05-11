id4_common.plans.base_scans
===========================

.. py:module:: id4_common.plans.base_scans

.. autoapi-nested-parse::

   Local 1-D scan plans: ``count``, ``ascan``, ``lup``, ``qxscan``.

   These are the polar-bits versions of the generic bluesky scan plans.  They
   add the standard polar-bits machinery (counters / dichro / lockin /
   softgluezynq stage signals, NeXus writer subscription, baseline file paths)
   on top of the underlying ``bluesky.plans`` calls.





Module Contents
---------------

.. py:function:: count(num, time, detectors=None, lockin=False, dichro=False, vortex_sgz=False, g_sgz=False, delay=None, per_shot=None, md=None)

   Take one or more readings from detectors.

   This is a local version of `bluesky.plans.count`. Note that the `per_shot`
   cannot be set here, as it is used for dichro scans.

   :param num: number of readings to take
               If None, capture data until canceled
   :type num: integer
   :param time: If a number is passed, it will modify the counts over time. All
                detectors need to have a .preset_monitor signal.
   :type time: float
   :param detectors: List of 'readable' objects. If None, will use the detectors defined in
                     `counters.detectors`.
   :type detectors: list, optional
   :param lockin: Flag to do a lock-in scan. Please run pr_setup.config() prior do a
                  lock-in scan.
   :type lockin: boolean, optional
   :param dichro: Flag to do a dichro scan. Please run pr_setup.config() prior do a
                  dichro scan. Note that this will switch the x-ray polarization at every
                  point using the +, -, -, + sequence, thus increasing the number of
                  points by a factor of 4
   :type dichro: boolean, optional
   :param vortex_sgz: Measures the Vortex detector using the softgluezynq triggers. This is a
                      special mode that requires the 'vortex' and 'sgz_vortex' devices to
                      exist otherwise an error will be thrown.
   :type vortex_sgz: boolean, optional
   :param delay: Time delay in seconds between successive readings; default is 0.
   :type delay: iterable or scalar, optional
   :param per_shot: Hook for customizing action of inner loop (messages per step).
                    See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
                    for details.
   :type per_shot: callable, optional
   :param md: metadata
   :type md: dict, optional

   .. rubric:: Notes

   If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
   the plan will raise a ``ValueError`` during iteration.


.. py:function:: ascan(*args, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Scan over one multi-motor trajectory.

   This is a local version of `bluesky.plans.scan`. Note that the `per_step`
   cannot be set here, as it is used for dichro scans.

   :param \*args: For one dimension, ``motor, start, stop, number of points, time``.
                  In general:
                  .. code-block:: python
                      motor1, start1, stop1,
                      motor2, start2, start2,
                      ...,
                      motorN, startN, stopN,
                      number of points,
                      time
                  Motors can be any 'settable' object (motor, temp controller, etc.)
   :param detectors: List of detectors to be used in the scan. If None, will use the
                     detectors defined in `counters.detectors`.
   :type detectors: list, optional
   :param lockin: Flag to do a lock-in scan. Please run pr_setup.config() prior do a
                  lock-in scan.
   :type lockin: boolean, optional
   :param dichro: Flag to do a dichro scan. Please run pr_setup.config() prior do a
                  dichro scan. Note that this will switch the x-ray polarization at every
                  point using the +, -, -, + sequence, thus increasing the number of
                  points by a factor of 4
   :type dichro: boolean, optional
   :param fixq: Flag for fixQ scans. If True, it will fix the diffractometer hkl
                position during the scan. This is particularly useful for energy scan.
                Note that hkl is moved ~after~ the other motors!
   :type fixq: boolean, optional
   :param vortex_sgz: Measures the Vortex detector using the softgluezynq triggers. This is a
                      special mode that requires the 'vortex' and 'sgz_vortex' devices to
                      exist otherwise an error will be thrown.
   :type vortex_sgz: boolean, optional
   :param per_step: hook for customizing action of inner loop (messages per step).
                    See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
                    for details.
   :type per_step: callable, optional
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plans.scan`, :func:`lup`


.. py:function:: lup(*args, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Scan over one multi-motor trajectory relative to current position.

   This is a local version of `bluesky.plans.rel_scan`. Note that the
   `per_step` cannot be set here, as it is used for dichro scans.

   :param \*args: For one dimension, ``motor, start, stop, number of points``.
                  In general:
                  .. code-block:: python
                      motor1, start1, stop1,
                      motor2, start2, start2,
                      ...,
                      motorN, startN, stopN,
                      number of points
                  Motors can be any 'settable' object (motor, temp controller, etc.)
   :param detectors: List of detectors to be used in the scan. If None, will use the
                     detectors defined in `counters.detectors`.
   :type detectors: list, optional
   :param lockin: Flag to do a lock-in scan. Please run pr_setup.config() prior do a
                  lock-in scan.
   :type lockin: boolean, optional
   :param dichro: Flag to do a dichro scan. Please run pr_setup.config() prior do a
                  dichro scan. Note that this will switch the x-ray polarization at every
                  point using the +, -, -, + sequence, thus increasing the number of
                  points by a factor of 4
   :type dichro: boolean, optional
   :param fixq: Flag for fixQ scans. If True, it will fix the diffractometer hkl
                position during the scan. This is particularly useful for energy scan.
                Note that hkl is moved ~after~ the other motors!
   :type fixq: boolean, optional
   :param vortex_sgz: Measures the Vortex detector using the softgluezynq triggers. This is a
                      special mode that requires the 'vortex' and 'sgz_vortex' devices to
                      exist otherwise an error will be thrown.
   :type vortex_sgz: boolean, optional
   :param per_step: hook for customizing action of inner loop (messages per step).
                    See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
                    for details.
   :type per_step: callable, optional
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plans.rel_scan`, :func:`ascan`


.. py:function:: qxscan(edge_energy, time, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Energy scan with fixed delta_K steps.

   WARNING: please run qxscan_params() before using this plan! It will
   use the parameters set in qxscan_params to determine the energy points.

   :param edge_energy: Absorption edge energy. The parameters in qxscan_params offset by this
                       energy.
   :type edge_energy: float
   :param time: If a number is passed, it will modify the counts over time. All
                detectors need to have a .preset_monitor signal.
   :type time: float
   :param detectors: List of detectors to be used in the scan. If None, will use the
                     detectors defined in `counters.detectors`.
   :type detectors: list, optional
   :param lockin: Flag to do a lock-in scan. Please run pr_setup.config() prior do a
                  lock-in scan
   :type lockin: boolean, optional
   :param dichro: Flag to do a dichro scan. Please run pr_setup.config() prior do a
                  dichro scan. Note that this will switch the x-ray polarization at every
                  point using the +, -, -, + sequence, thus increasing the number of
                  points by a factor of 4
   :type dichro: boolean, optional
   :param fixq: Flag for fixQ scans. If True, it will fix the diffractometer hkl
                position during the scan. Note that hkl is moved ~after~ the other
                motors!
   :type fixq: boolean, optional
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plans.scan`, :func:`lup`


