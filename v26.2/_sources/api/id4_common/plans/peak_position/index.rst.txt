id4_common.plans.peak_position
==============================

.. py:module:: id4_common.plans.peak_position

.. autoapi-nested-parse::

   Peak / centroid plans for 1D scans and 2D ``grid_scan``s (issue #59).

   Public surface:

   - :func:`peak_pos` — diagnostic; returns a stats dict for any scan
     (1D or 2D).  No motion.
   - :func:`cen` — move to the FWHM midpoint of a previous scan.
   - :func:`com` — move to the centroid (center-of-mass).
   - :func:`maxi` — move to the x at peak max.
   - :func:`mini` — move to the x at peak min.

   For 2D ``grid_scan`` runs the move plans default to moving **both**
   scan motors to the 2D feature.  Pass ``positioner=`` a single motor to
   project onto that axis instead, or ``positioner=[m1, m2]`` to be
   explicit.

   Backward-compat aliases for callers from PR #54: ``peak`` (= ``com``),
   ``pmax`` (= ``maxi``), ``pmin`` (= ``mini``).

   Backend choice (no new pip deps):

   - ``apstools.utils.xy_statistics`` for 1D ``com`` / ``max`` / ``min`` /
     ``fwhm`` (already a dep).
   - ``scipy.signal`` for the FWHM-midpoint (``cen``) calculation in 1D.
   - ``scipy.ndimage`` for ``com`` / ``max`` / ``min`` / ``cen`` in 2D.





Module Contents
---------------

.. py:function:: peak_pos(scan_id=-1, x=None, y=None)

   Compute peak statistics for one or more detectors of a previous scan.

   Loads the scan from the shared session catalog
   (``id4_common.utils.run_engine.cat``), dispatches to the 1D or 2D
   backend based on the scan's plan, and returns a nested dict.

   :param scan_id: Catalog index. Default ``-1`` (last scan); negative indices count
                   from the end.
   :type scan_id: int, optional
   :param x: For 1D scans: motor (x-axis) field name. If None, picks the
             single motor or, for multi-motor 1D scans, the motor with the
             largest range. Ignored for 2D scans.
   :type x: str, optional
   :param y: Detector (y-axis) field name(s). If None, uses every entry in
             ``start["hints"]["detectors"]``.
   :type y: str or list of str, optional

   :returns: Always carries ``"shape"`` and ``"axes"`` so callers can branch
             on dimensionality:

             - 1D: ``{"shape": (N,), "axes": [motor], "com": {det: x, ...},
               "max": {det: (x, h), ...}, "min": {det: (x, h), ...},
               "fwhm": {det: w, ...}, "cen": {det: x, ...}}``
             - 2D: ``{"shape": (M, N), "axes": [m1, m2], "com": {det:
               (m1, m2), ...}, "max": {det: (m1, m2, h), ...}, "min": {det:
               (m1, m2, h), ...}, "cen": {det: (m1, m2), ...},
               "fwhm": {det: (fwhm_m1, fwhm_m2), ...}}``
   :rtype: dict


.. py:function:: cen(scan_id=-1, positioner=None, detector=None, confirm=True)

   Move to the FWHM-midpoint of a previous scan.

   Equivalent to bluesky ``PeakStats.cen``.  For asymmetric peaks this
   differs from :func:`com`.

   :param scan_id: Catalog index of the scan. Default ``-1`` (last scan).
   :type scan_id: int, optional
   :param positioner: Device(s) to move.  None → autodetected from the scan's motors
                      (single for 1D scans, both motors for 2D ``grid_scan``).
   :type positioner: ophyd object or list, optional
   :param detector: Detector field name. None → first hint from the scan.
   :type detector: str, optional
   :param confirm: If True (default), prompts for multi-motor 1D scans and for
                   scans older than 5 minutes.  False skips every prompt.
   :type confirm: bool, optional

   .. seealso:: :func:`com`, :func:`maxi`, :func:`mini`, :func:`peak_pos`


.. py:function:: com(scan_id=-1, positioner=None, detector=None, confirm=True)

   Move to the centroid (center-of-mass) of a previous scan.

   See :func:`cen` for parameter details.

   .. seealso:: :func:`cen`, :func:`maxi`, :func:`mini`, :func:`peak_pos`


.. py:function:: maxi(scan_id=-1, positioner=None, detector=None, confirm=True)

   Move to the x-value at peak maximum of a previous scan.

   See :func:`cen` for parameter details.

   .. seealso:: :func:`cen`, :func:`com`, :func:`mini`, :func:`peak_pos`


.. py:function:: mini(scan_id=-1, positioner=None, detector=None, confirm=True)

   Move to the x-value at peak minimum of a previous scan.

   See :func:`cen` for parameter details.

   .. seealso:: :func:`cen`, :func:`com`, :func:`maxi`, :func:`peak_pos`


.. py:function:: peak(scan_id=-1, feature='centroid', positioner=None, detector=None, confirm=True)

   Backward-compat: dispatch by ``feature`` to :func:`cen` / :func:`com` /
   :func:`maxi` / :func:`mini`.

   Accepts the PR-#54 feature names (``"centroid"`` / ``"x_at_max_y"`` /
   ``"x_at_min_y"``) and the new short names (``"com"`` / ``"max"`` /
   ``"min"`` / ``"cen"``).


.. py:function:: pmax(scan_id=-1, positioner=None, detector=None, confirm=True)

   Alias of :func:`maxi` (PR #54 name).


.. py:function:: pmin(scan_id=-1, positioner=None, detector=None, confirm=True)

   Alias of :func:`mini` (PR #54 name).


