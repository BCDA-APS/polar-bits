id4_common.plans.grid_scans
===========================

.. py:module:: id4_common.plans.grid_scans

.. autoapi-nested-parse::

   Local mesh-scan plans: ``grid_scan`` and ``rel_grid_scan``.

   Polar-bits versions of :func:`bluesky.plans.grid_scan` /
   :func:`bluesky.plans.rel_grid_scan` that wire in the standard counters /
   dichro / lockin / softgluezynq / NeXus / baseline machinery.





Module Contents
---------------

.. py:function:: grid_scan(*args, detectors=None, snake_axes=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Scan over a mesh; each motor is on an independent trajectory.

   :param ``*args``:
                     patterned like (``motor1, start1, stop1, num1,``
                                     ``motor2, start2, stop2, num2,``
                                     ``motor3, start3, stop3, num3,`` ...
                                     ``motorN, startN, stopN, numN``)
                     The first motor is the "slowest", the outer loop. For all motors
                     except the first motor, there is a "snake" argument: a boolean
                     indicating whether to following snake-like, winding trajectory or a
                     simple left-to-right trajectory.
   :param time: If a number is passed, it will modify the counts over time. All
                detectors need to have a .preset_monitor signal.
   :type time: float, optional
   :param detectors: List of detectors to be used in the scan. If None, will use the
                     detectors defined in `counters.detectors`.
   :type detectors: list, optional
   :param snake_axes: which axes should be snaked, either ``False`` (do not snake any axes),
                      ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
                      is defined as following snake-like, winding trajectory instead of a
                      simple left-to-right trajectory. The elements of the list are motors
                      that are listed in `args`. The list must not contain the slowest
                      (first) motor, since it can't be snaked.
   :type snake_axes: boolean or iterable, optional
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
   :param md: metadata
   :type md: dict, optional

   .. seealso:: :func:`bluesky.plans.grid_scan`, :func:`bluesky.plans.rel_grid_scan`, :func:`bluesky.plans.inner_product_scan`, :func:`bluesky.plans.scan_nd`


.. py:function:: rel_grid_scan(*args, detectors=None, snake_axes=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Scan over a mesh relative to current position.

   Each motor is on an independent trajectory.

   :param ``*args``:
                     patterned like (``motor1, start1, stop1, num1,``
                                     ``motor2, start2, stop2, num2,``
                                     ``motor3, start3, stop3, num3,`` ...
                                     ``motorN, startN, stopN, numN``)
                     The first motor is the "slowest", the outer loop. For all motors
                     except the first motor, there is a "snake" argument: a boolean
                     indicating whether to following snake-like, winding trajectory or a
                     simple left-to-right trajectory.
   :param snake_axes: which axes should be snaked, either ``False`` (do not snake any axes),
                      ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
                      is defined as following snake-like, winding trajectory instead of a
                      simple left-to-right trajectory. The elements of the list are motors
                      that are listed in `args`. The list must not contain the slowest
                      (first) motor, since it can't be snaked.
   :type snake_axes: boolean or iterable, optional
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
   :param md: metadata
   :type md: dict, optional

   .. seealso:: :func:`grid_scan`, :func:`bluesky.plans.grid_scan`, :func:`bluesky.plans.rel_grid_scan`, :func:`bluesky.plans.inner_product_scan`, :func:`bluesky.plans.scan_nd`
