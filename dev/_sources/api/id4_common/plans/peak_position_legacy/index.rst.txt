id4_common.plans.peak_position_legacy
=====================================

.. py:module:: id4_common.plans.peak_position_legacy

.. autoapi-nested-parse::

   DEPRECATED — kept temporarily for reference (issue #59).

   This is the pre-#59 ``peak_position.py`` (xy_statistics-based
   ``peak`` / ``pmax`` / ``pmin`` / ``peak_pos``).  The new
   ``peak_position.py`` alongside it provides scipy-backed ``cen`` /
   ``com`` / ``maxi`` / ``mini`` with native 2D ``grid_scan`` support,
   plus backward-compatible ``peak`` / ``pmax`` / ``pmin`` aliases.

   This file is not imported by anything — verify with
   ``grep -rn 'peak_position_legacy' src/`` before deleting.

   TODO(#59): remove after the new module has been validated at the
   beamline.





Module Contents
---------------

.. py:function:: peak_pos(scan_id=-1, x=None, y=None)

   Compute peak statistics for one or more detectors of a previous scan.

   Loads scan data from the shared session catalog
   (``id4_common.utils.run_engine.cat``) and computes statistics with
   :func:`apstools.utils.xy_statistics` — the same numpy-based machinery
   used by ``apstools.plans.alignment.lineup2``.

   :param scan_id: Catalog index. Default ``-1`` (last scan); negative indices count
                   from the end.
   :type scan_id: int, optional
   :param x: Motor (x-axis) field name. If None, uses the first entry in the
             scan's ``start["motors"]``.
   :type x: str, optional
   :param y: Detector (y-axis) field name(s). If None, uses every entry in
             ``start["hints"]["detectors"]``.
   :type y: str or list of str, optional

   :returns:

             Nested dict mirroring ``bluesky.callbacks.best_effort.peaks``::

                 {
                     "com":  {detector: x_centroid, ...},
                     "max":  {detector: (x_at_max_y, max_y), ...},
                     "min":  {detector: (x_at_min_y, min_y), ...},
                     "fwhm": {detector: fwhm, ...},
                 }
   :rtype: dict


.. py:function:: peak(scan_id=-1, feature='centroid', positioner=None, detector=None, confirm=True)

   Plan that moves a positioner to the peak position of a previous scan.

   Uses :func:`peak_pos` (which calls :func:`apstools.utils.xy_statistics`)
   to compute the requested ``feature`` from the scan data, then moves
   ``positioner`` there.

   For multi-positioner scans (``hklscan``, ...) the fastest-changing
   motor (largest range) is used as the default, but the user is
   prompted to confirm or pick a different scan motor. ``th2th`` scans
   are a special case: 2θ (``gamma``) is always the right axis, so no
   prompt is shown. Pass ``confirm=False`` to skip every interactive
   prompt (positioner choice and the >5-min move confirmation).

   :param scan_id: Catalog index. Default ``-1`` (last scan).
   :type scan_id: int, optional
   :param feature: Statistical measure to move to. Default ``"centroid"``.
   :type feature: str, optional
   :param positioner: Device to move. If None, the scan's fastest-changing motor is
                      used (with an interactive override for multi-motor scans).
   :type positioner: ophyd object, optional
   :param detector: Detector field name passed through to :func:`peak_pos` as ``y``.
   :type detector: str, optional
   :param confirm: If True (default), interactive prompts are shown when
                   appropriate (positioner selection for multi-motor scans and the
                   >5-min move confirmation). If False, all such prompts are
                   skipped.
   :type confirm: bool, optional


.. py:function:: pmax(scan_id=-1, positioner=None, detector=None, confirm=True)

   Plan that moves a positioner to the x value at peak maximum.

   Convenience wrapper for :func:`peak` with ``feature="x_at_max_y"``.

   :param scan_id: Catalog index of the scan to analyse. Default ``-1`` (last scan);
                   negative indices count from the end.
   :type scan_id: int, optional
   :param positioner: Device to move. If None, the scan's fastest-changing motor is
                      used (with an interactive override for multi-motor scans).
   :type positioner: ophyd object, optional
   :param detector: Detector field name passed through to :func:`peak_pos` as ``y``.
   :type detector: str, optional
   :param confirm: If True (default), interactive prompts are shown when appropriate
                   (positioner selection for multi-motor scans and the >5-min move
                   confirmation). If False, all such prompts are skipped.
   :type confirm: bool, optional

   .. seealso:: :func:`peak`, :func:`pmin`, :func:`peak_pos`


.. py:function:: pmin(scan_id=-1, positioner=None, detector=None, confirm=True)

   Plan that moves a positioner to the x value at peak minimum.

   Convenience wrapper for :func:`peak` with ``feature="x_at_min_y"``.

   :param scan_id: Catalog index of the scan to analyse. Default ``-1`` (last scan);
                   negative indices count from the end.
   :type scan_id: int, optional
   :param positioner: Device to move. If None, the scan's fastest-changing motor is
                      used (with an interactive override for multi-motor scans).
   :type positioner: ophyd object, optional
   :param detector: Detector field name passed through to :func:`peak_pos` as ``y``.
   :type detector: str, optional
   :param confirm: If True (default), interactive prompts are shown when appropriate
                   (positioner selection for multi-motor scans and the >5-min move
                   confirmation). If False, all such prompts are skipped.
   :type confirm: bool, optional

   .. seealso:: :func:`peak`, :func:`pmax`, :func:`peak_pos`


