id4_common.plans.hkl_scans
==========================

.. py:module:: id4_common.plans.hkl_scans

.. autoapi-nested-parse::

   Diffractometer scan plans: ``th2th``, ``hklscan``, ``hscan``, ``kscan``,
   ``lscan``, ``psiscan``.

   These all run on the active hklpy2 diffractometer (see
   :func:`hklpy2.user.set_diffractometer`).  Most are thin wrappers over
   :func:`ascan` / :func:`lup` from :mod:`base_scans`; ``psiscan`` wraps
   :func:`hklpy2.scan_psi` because it owns its own inner loop.





Module Contents
---------------

.. py:function:: th2th(tth_start, tth_end, number_of_points, time_per_point, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Relative horizontal theta/2theta scan. It will scan the mu and gamma motors.

   :param tth_start: Relative 2theta start. The relative theta will be half of
                     the 2theta.
   :type tth_start: float
   :param tth_end: Relative 2theta end. The relative theta will be half of the 2theta.
   :type tth_end: float
   :param number_of_points: Number of points to be measured.
   :type number_of_points: int
   :param time_per_point: Measurement time per point.
   :type time_per_point: float
   :param detectors: List of detectors to be used in the scan. If None, will use the
                     detectors defined in `counters.detectors`.
   :type detectors: list, optional
   :param lockin: Flag to do a lock-in scan. Please run pr_setup.config() prior do a
                  lock-in scan.
   :type lockin: boolean, optional
   :param dichro: Flag to do a dichro scan. Please run pr_setup.config() prior do a
                  dichro scan. Note that this will switch the x-ray
                  polarization at every point using the +, -, -, + sequence,
                  thus increasing the number of
                  points by a factor of 4
   :type dichro: boolean, optional
   :param fixq: Flag for fixQ scans. If True, it will fix the diffractometer hkl
                position during the scan. This is particularly useful for
                energy scan.
                Note that hkl is moved ~after~ the other motors!
   :type fixq: boolean, optional
   :param vortex_sgz: Measures the Vortex detector using the softgluezynq
                      triggers. This is a special mode that requires the 'vortex'
                      and 'sgz_vortex' devices to
                      exist otherwise an error will be thrown.
   :type vortex_sgz: boolean, optional
   :param per_step: hook for customizing action of inner loop (messages per step).
                    See docstring of
                    :func:`bluesky.plan_stubs.one_nd_step` (the default)
                    for details.
   :type per_step: callable, optional
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`lup`, :func:`ascan`


.. py:function:: hklscan(h1, h2, k1, k2, l1, l2, number_of_points, time, detectors=None, lockin=False, dichro=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Linear hkl trajectory scan.

   Sweeps the active diffractometer's (h, k, l) pseudo axes along a straight
   line in reciprocal space from (h1, k1, l1) to (h2, k2, l2) in
   ``number_of_points`` points. Delegates to :func:`ascan`; ``fixq`` is
   forced off because the scan *is* the trajectory.

   :param h1: Initial and final ``h`` of the trajectory.
   :type h1: float
   :param h2: Initial and final ``h`` of the trajectory.
   :type h2: float
   :param k1: Initial and final ``k`` of the trajectory.
   :type k1: float
   :param k2: Initial and final ``k`` of the trajectory.
   :type k2: float
   :param l1: Initial and final ``l`` of the trajectory.
   :type l1: float
   :param l2: Initial and final ``l`` of the trajectory.
   :type l2: float
   :param number_of_points: Number of points (inclusive of endpoints).
   :type number_of_points: int
   :param time: Count time per point (seconds).
   :type time: float
   :param detectors: Detectors to read. If None, uses ``counters.detectors``.
   :type detectors: list, optional
   :param lockin: Run as a lock-in scan. Requires ``pr_setup.config()`` to have
                  been run beforehand.
   :type lockin: bool, optional
   :param dichro: Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
                  Switches the x-ray polarization at every point using the
                  ``+ - - +`` sequence, multiplying the point count by 4.
   :type dichro: bool, optional
   :param vortex_sgz: Trigger the Vortex detector via softgluezynq.  Requires both
                      the ``vortex`` and ``sgz_vortex`` devices to exist.
   :type vortex_sgz: bool, optional
   :param g_sgz: Add the ``pos_stream`` position-stream device to the scan so
                 motor positions are captured through the softgluezynq pipeline.
   :type g_sgz: bool, optional
   :param per_step: Hook for customizing the inner-loop messages.  See
                    :func:`bluesky.plan_stubs.one_nd_step` (the default).
   :type per_step: callable, optional
   :param md: Metadata to add to the run start.
   :type md: dict, optional

   .. seealso:: :func:`ascan`, :func:`psiscan`


.. py:function:: hscan(start, stop, number_of_points, time, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Sweep the active diffractometer's ``h`` pseudo axis.

   Thin wrapper around :func:`ascan(diff.h, start, stop, number_of_points,
   time, ...)` that tags the run with ``plan_name="hscan"`` so
   :func:`peak` can identify the scan axis.

   :param start: Initial and final ``h`` value.
   :type start: float
   :param stop: Initial and final ``h`` value.
   :type stop: float
   :param number_of_points: Number of points (inclusive of endpoints).
   :type number_of_points: int
   :param time: Count time per point (seconds).
   :type time: float
   :param detectors: Detectors to read. If None, uses ``counters.detectors``.
   :type detectors: list, optional
   :param lockin: Run as a lock-in scan. Requires ``pr_setup.config()`` to have
                  been run beforehand.
   :type lockin: bool, optional
   :param dichro: Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
                  Switches the x-ray polarization at every point using the
                  ``+ - - +`` sequence, multiplying the point count by 4.
   :type dichro: bool, optional
   :param fixq: Fix the diffractometer hkl during the scan.  Note: hkl is moved
                *after* the other motors.
   :type fixq: bool, optional
   :param vortex_sgz: Trigger the Vortex detector via softgluezynq.  Requires both
                      the ``vortex`` and ``sgz_vortex`` devices to exist.
   :type vortex_sgz: bool, optional
   :param g_sgz: Add the ``pos_stream`` position-stream device to the scan so
                 motor positions are captured through the softgluezynq pipeline.
   :type g_sgz: bool, optional
   :param per_step: Hook for customizing the inner-loop messages.  See
                    :func:`bluesky.plan_stubs.one_nd_step` (the default).
   :type per_step: callable, optional
   :param md: Metadata to add to the run start.
   :type md: dict, optional

   .. seealso:: :func:`ascan`, :func:`hklscan`, :func:`kscan`, :func:`lscan`


.. py:function:: kscan(start, stop, number_of_points, time, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Sweep the active diffractometer's ``k`` pseudo axis.

   Thin wrapper around :func:`ascan(diff.k, start, stop, number_of_points,
   time, ...)` that tags the run with ``plan_name="kscan"`` so
   :func:`peak` can identify the scan axis.

   :param start: Initial and final ``k`` value.
   :type start: float
   :param stop: Initial and final ``k`` value.
   :type stop: float
   :param number_of_points: Number of points (inclusive of endpoints).
   :type number_of_points: int
   :param time: Count time per point (seconds).
   :type time: float
   :param detectors: Detectors to read. If None, uses ``counters.detectors``.
   :type detectors: list, optional
   :param lockin: Run as a lock-in scan. Requires ``pr_setup.config()`` to have
                  been run beforehand.
   :type lockin: bool, optional
   :param dichro: Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
                  Switches the x-ray polarization at every point using the
                  ``+ - - +`` sequence, multiplying the point count by 4.
   :type dichro: bool, optional
   :param fixq: Fix the diffractometer hkl during the scan.  Note: hkl is moved
                *after* the other motors.
   :type fixq: bool, optional
   :param vortex_sgz: Trigger the Vortex detector via softgluezynq.  Requires both
                      the ``vortex`` and ``sgz_vortex`` devices to exist.
   :type vortex_sgz: bool, optional
   :param g_sgz: Add the ``pos_stream`` position-stream device to the scan so
                 motor positions are captured through the softgluezynq pipeline.
   :type g_sgz: bool, optional
   :param per_step: Hook for customizing the inner-loop messages.  See
                    :func:`bluesky.plan_stubs.one_nd_step` (the default).
   :type per_step: callable, optional
   :param md: Metadata to add to the run start.
   :type md: dict, optional

   .. seealso:: :func:`ascan`, :func:`hklscan`, :func:`hscan`, :func:`lscan`


.. py:function:: lscan(start, stop, number_of_points, time, detectors=None, lockin=False, dichro=False, fixq=False, vortex_sgz=False, g_sgz=False, per_step=None, md=None)

   Sweep the active diffractometer's ``l`` pseudo axis.

   Thin wrapper around :func:`ascan(diff.l, start, stop, number_of_points,
   time, ...)` that tags the run with ``plan_name="lscan"`` so
   :func:`peak` can identify the scan axis.

   :param start: Initial and final ``l`` value.
   :type start: float
   :param stop: Initial and final ``l`` value.
   :type stop: float
   :param number_of_points: Number of points (inclusive of endpoints).
   :type number_of_points: int
   :param time: Count time per point (seconds).
   :type time: float
   :param detectors: Detectors to read. If None, uses ``counters.detectors``.
   :type detectors: list, optional
   :param lockin: Run as a lock-in scan. Requires ``pr_setup.config()`` to have
                  been run beforehand.
   :type lockin: bool, optional
   :param dichro: Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
                  Switches the x-ray polarization at every point using the
                  ``+ - - +`` sequence, multiplying the point count by 4.
   :type dichro: bool, optional
   :param fixq: Fix the diffractometer hkl during the scan.  Note: hkl is moved
                *after* the other motors.
   :type fixq: bool, optional
   :param vortex_sgz: Trigger the Vortex detector via softgluezynq.  Requires both
                      the ``vortex`` and ``sgz_vortex`` devices to exist.
   :type vortex_sgz: bool, optional
   :param g_sgz: Add the ``pos_stream`` position-stream device to the scan so
                 motor positions are captured through the softgluezynq pipeline.
   :type g_sgz: bool, optional
   :param per_step: Hook for customizing the inner-loop messages.  See
                    :func:`bluesky.plan_stubs.one_nd_step` (the default).
   :type per_step: callable, optional
   :param md: Metadata to add to the run start.
   :type md: dict, optional

   .. seealso:: :func:`ascan`, :func:`hklscan`, :func:`hscan`, :func:`kscan`


.. py:function:: psiscan(psi_start, psi_stop, number_of_points, time, hkl=None, hkl2=None, orientation='horizontal', detectors=None, psi_axis=None, fail_on_exception=False, md=None)

   Azimuthal psi scan at fixed (h, k, l).

   Wraps `hklpy2.scan_psi`, holding (h, k, l) fixed while sweeping the
   azimuthal extra parameter from ``psi_start`` to ``psi_stop`` in
   ``number_of_points`` points. Runs on the active diffractometer (e.g.
   ``huber_euler``) — its hkl engine exposes the ``psi constant
   horizontal`` / ``psi constant vertical`` modes used here.

   :param psi_start: Azimuthal angle range (degrees).
   :type psi_start: float
   :param psi_stop: Azimuthal angle range (degrees).
   :type psi_stop: float
   :param number_of_points: Number of points (inclusive of endpoints).
   :type number_of_points: int
   :param time: Count time per point. Must be > 0.
   :type time: float
   :param hkl: Fixed reflection (h, k, l). If None (default), use the current
               diffractometer position.
   :type hkl: sequence of float, optional
   :param hkl2: Reference reflection (h2, k2, l2) defining psi=0. If None (default),
                read from the active diffractometer's ``core.all_extras`` (the
                non-psi entries, in order). Must not be parallel to (h, k, l).
   :type hkl2: sequence of float, optional
   :param orientation: Scattering plane. Selects the psi mode passed to
                       ``hklpy2.scan_psi``: ``"psi constant horizontal"`` (default) or
                       ``"psi constant vertical"``.
   :type orientation: {'horizontal', 'vertical'}, optional
   :param detectors: Detectors to read. If None, uses ``counters.detectors``.
   :type detectors: list, optional
   :param psi_axis: Name of the psi extra axis. Auto-detected when None.
   :type psi_axis: str, optional
   :param fail_on_exception: Forwarded to `hklpy2.scan_psi`. When False (default), per-point
                             forward-calculation failures are printed and the scan continues.
   :type fail_on_exception: bool, optional
   :param md: Metadata to add to the run start.
   :type md: dict, optional

   .. rubric:: Notes

   Unlike `ascan`/`grid_scan`, this plan does not support `dichro`,
   `lockin`, `fixq`, or `vortex_sgz` because `hklpy2.scan_psi` runs its own
   inner loop and does not accept a `per_step` hook.

   .. seealso:: :func:`hklpy2.scan_psi`


