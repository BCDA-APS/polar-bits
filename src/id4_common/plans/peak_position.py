"""
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
"""

from __future__ import annotations

import warnings
from datetime import datetime
from datetime import timedelta

import numpy as np
from apsbits.core.instrument_init import oregistry
from apstools.utils import xy_statistics
from bluesky.plan_stubs import null
from scipy import ndimage
from scipy import signal

from ..utils.run_engine import cat
from .move_plans import mv

__all__ = [
    "peak_pos",
    "cen",
    "com",
    "maxi",
    "mini",
    # Backwards-compat aliases.
    "peak",
    "pmax",
    "pmin",
]


# ---------------------------------------------------------------------------
# Helpers — dispatch / data extraction
# ---------------------------------------------------------------------------


def _is_grid_scan(start):
    """Return True when the start doc is from a 2D-or-higher grid scan."""
    plan_name = start.get("plan_name", "")
    motors = start.get("motors") or []
    return plan_name in {"grid_scan", "rel_grid_scan"} and len(motors) >= 2


def _grid_shape(start, table):
    """Return ``(motors, shape)`` for a grid scan.

    Prefer ``start["shape"]`` (which ``grid_scan`` / ``rel_grid_scan``
    always record) so noisy motor readbacks or step sizes below motor
    resolution don't collapse the inferred grid. Validate the recorded
    shape against the table length and fall back to a
    ``np.unique``-based derivation if it's missing or inconsistent.
    """
    motors = list(start["motors"])
    n_samples = len(table[motors[0]].values) if motors else 0
    recorded = start.get("shape")
    if recorded is not None and len(recorded) == len(motors):
        shape = tuple(int(s) for s in recorded)
        if int(np.prod(shape)) == n_samples:
            return motors, shape
    shape = tuple(int(np.unique(table[m].values).size) for m in motors)
    return motors, shape


def _resolve_x_motor(start, table, x=None):
    """Pick the scan x-motor field name for the 1D path.

    - If ``x`` is given, return it unchanged.
    - If the scan has a single motor, return that.
    - For multi-motor scans (th2th, hklscan, …), return the motor with
      the largest range during the scan.
    """
    if x is not None:
        return x
    motors = start.get("motors")
    if not motors:
        raise ValueError(
            "Scan has no 'motors' in start doc; pass x= explicitly."
        )
    if len(motors) == 1:
        return motors[0]
    ranges = {}
    for m in motors:
        if m in table:
            arr = np.asarray(table[m].values)
            if arr.size:
                ranges[m] = float(arr.max() - arr.min())
    if not ranges:
        raise ValueError(
            f"None of the scan motors {motors} were found in the primary "
            "stream; pass x= explicitly."
        )
    return max(ranges, key=ranges.get)


def _detector_fields(start, y):
    """Resolve the list of detector field names to analyse."""
    if y is None:
        det_fields = start.get("hints", {}).get("detectors") or []
        if not det_fields:
            raise ValueError("No detector hints in scan; pass y= explicitly.")
        return list(det_fields)
    if isinstance(y, str):
        return [y]
    return list(y)


def _read_table(run):
    """Read primary stream, suppressing the FutureWarning about Dataset.dims."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=FutureWarning,
            message="The return type of `Dataset.dims`.*",
        )
        return run.primary.read()


# ---------------------------------------------------------------------------
# Helpers — 1D statistics
# ---------------------------------------------------------------------------


def _fwhm_midpoint_1d(x, y):
    """Return the midpoint of the half-max crossings (the 'cen' of bluesky's
    PeakStats).  Falls back to ``x_at_max_y`` if no half-max crossing is found.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2:
        return float(x[0]) if x.size else None

    peaks_idx, _ = signal.find_peaks(y)
    if peaks_idx.size == 0:
        # No real peaks; fall back to the global max.
        peaks_idx = np.array([int(np.argmax(y))])

    # Use the tallest peak as the reference.
    main = peaks_idx[int(np.argmax(y[peaks_idx]))]
    widths = signal.peak_widths(y, [main], rel_height=0.5)
    # peak_widths returns (widths, width_heights, left_ips, right_ips) where
    # left_ips/right_ips are interpolated sample positions.
    left_ip = float(widths[2][0])
    right_ip = float(widths[3][0])
    # Convert sample-space crossings to motor units via linear interpolation.
    left_x = float(np.interp(left_ip, np.arange(x.size), x))
    right_x = float(np.interp(right_ip, np.arange(x.size), x))
    return 0.5 * (left_x + right_x)


def _compute_1d_stats(x, y):
    """Return the per-detector stats dict for a 1D (x, y) pair."""
    stats = xy_statistics(np.asarray(x), np.asarray(y))
    com_x = stats.get("centroid")
    x_max = stats.get("x_at_max_y")
    max_y = stats.get("max_y")
    x_min = stats.get("x_at_min_y")
    min_y = stats.get("min_y")
    fwhm = stats.get("fwhm")
    cen_x = _fwhm_midpoint_1d(x, y)

    out = {}
    if com_x is not None:
        out["com"] = float(com_x)
    if x_max is not None and max_y is not None:
        out["max"] = (float(x_max), float(max_y))
    if x_min is not None and min_y is not None:
        out["min"] = (float(x_min), float(min_y))
    if fwhm is not None:
        out["fwhm"] = float(fwhm)
    if cen_x is not None:
        out["cen"] = float(cen_x)
    return out


# ---------------------------------------------------------------------------
# Helpers — 2D statistics
# ---------------------------------------------------------------------------


def _pix_to_motor(idx_tuple, motor_axes):
    """Convert a sub-pixel index tuple to motor-unit coordinates.

    ``idx_tuple`` is ``(i, j, …)`` with possibly fractional indices (as
    returned by ``scipy.ndimage.center_of_mass``).  ``motor_axes`` is the
    list of 1-D arrays of unique motor positions, one per axis.
    """
    out = []
    for ax_idx, axis_vals in zip(idx_tuple, motor_axes, strict=False):
        out.append(
            float(np.interp(ax_idx, np.arange(axis_vals.size), axis_vals))
        )
    return tuple(out)


def _compute_2d_stats(motor_axes, img):
    """Return the per-detector stats dict for a 2D image.

    ``motor_axes`` is a list of two 1-D arrays of unique motor positions
    (one per axis).  ``img`` is the 2-D detector intensity array reshaped
    to ``(len(motor_axes[0]), len(motor_axes[1]))``.
    """
    img = np.asarray(img, dtype=float)
    out = {}

    # com — full-image weighted centroid (motor units).
    com_pix = ndimage.center_of_mass(img)
    out["com"] = _pix_to_motor(com_pix, motor_axes)

    # maxi / mini — pixel-exact; report the height/depth too.
    max_pix = ndimage.maximum_position(img)
    max_motor = _pix_to_motor(max_pix, motor_axes)
    out["max"] = (*max_motor, float(img[max_pix]))

    min_pix = ndimage.minimum_position(img)
    min_motor = _pix_to_motor(min_pix, motor_axes)
    out["min"] = (*min_motor, float(img[min_pix]))

    # cen — centroid of the half-max region (the 2-D analogue of the 1-D
    # FWHM midpoint).  Falls back to com if every pixel is below half-max
    # (shouldn't happen but defensive).
    half_max = float(img.max() / 2.0)
    mask = img >= half_max
    if mask.any():
        cen_pix = ndimage.center_of_mass(img, labels=mask.astype(int))
        out["cen"] = _pix_to_motor(cen_pix, motor_axes)
    else:
        out["cen"] = out["com"]

    # fwhm — per-axis, derived from the 1-D projections (sum the orthogonal
    # axis).  Two numbers, one per motor.
    proj0 = img.sum(axis=1)
    proj1 = img.sum(axis=0)
    fwhm0 = xy_statistics(motor_axes[0], proj0).get("fwhm")
    fwhm1 = xy_statistics(motor_axes[1], proj1).get("fwhm")
    out["fwhm"] = (
        float(fwhm0) if fwhm0 is not None else None,
        float(fwhm1) if fwhm1 is not None else None,
    )

    return out


# ---------------------------------------------------------------------------
# Helpers — confirmation / move-plan glue
# ---------------------------------------------------------------------------


def _confirm_old_scan(stop, confirm, positioner_name, current, target):
    """Prompt the user when confirm=True and the scan finished > 5 min ago."""
    elapsed = (
        datetime.now() - datetime.fromtimestamp(stop["time"])
        if stop is not None
        else timedelta(seconds=1000)
    )
    if elapsed.seconds <= 300 or not confirm:
        return True
    answer = (
        input(f"Move {positioner_name} from {current} to {target}? (Y/[N]) ")
        or "N"
    )
    return answer in ("Y", "y", "yes")


def _current_position(positioner):
    """Read the current position of an ophyd positioner / signal."""
    if hasattr(positioner, "position"):
        return positioner.position
    if hasattr(positioner, "readback"):
        return positioner.readback.get()
    return positioner.get()


# ---------------------------------------------------------------------------
# Public — diagnostic
# ---------------------------------------------------------------------------


def peak_pos(scan_id=-1, x=None, y=None):
    """
    Compute peak statistics for one or more detectors of a previous scan.

    Loads the scan from the shared session catalog
    (``id4_common.utils.run_engine.cat``), dispatches to the 1D or 2D
    backend based on the scan's plan, and returns a nested dict.

    Parameters
    ----------
    scan_id : int, optional
        Catalog index. Default ``-1`` (last scan); negative indices count
        from the end.
    x : str, optional
        For 1D scans: motor (x-axis) field name. If None, picks the
        single motor or, for multi-motor 1D scans, the motor with the
        largest range. Ignored for 2D scans.
    y : str or list of str, optional
        Detector (y-axis) field name(s). If None, uses every entry in
        ``start["hints"]["detectors"]``.

    Returns
    -------
    dict
        Always carries ``"shape"`` and ``"axes"`` so callers can branch
        on dimensionality:

        - 1D: ``{"shape": (N,), "axes": [motor], "com": {det: x, ...},
          "max": {det: (x, h), ...}, "min": {det: (x, h), ...},
          "fwhm": {det: w, ...}, "cen": {det: x, ...}}``
        - 2D: ``{"shape": (M, N), "axes": [m1, m2], "com": {det:
          (m1, m2), ...}, "max": {det: (m1, m2, h), ...}, "min": {det:
          (m1, m2, h), ...}, "cen": {det: (m1, m2), ...},
          "fwhm": {det: (fwhm_m1, fwhm_m2), ...}}``
    """
    run = cat[scan_id]
    start = run.metadata["start"]
    table = _read_table(run)
    det_fields = _detector_fields(start, y)
    scan_n = start.get("scan_id")

    result = {"com": {}, "max": {}, "min": {}, "fwhm": {}, "cen": {}}

    if _is_grid_scan(start):
        motors, shape = _grid_shape(start, table)
        motor_axes = [np.unique(table[m].values) for m in motors]
        result["shape"] = shape
        result["axes"] = motors
        for det in det_fields:
            flat = np.asarray(table[det].values)
            if flat.size != int(np.prod(shape)):
                raise ValueError(
                    f"Detector {det!r} has {flat.size} samples but the "
                    f"inferred grid shape is {shape}."
                )
            img = flat.reshape(shape)
            stats = _compute_2d_stats(motor_axes, img)
            for k, v in stats.items():
                result[k][det] = v
            print(
                f"Scan #{scan_n} ({'/'.join(motors)} vs {det}): "
                f"com={stats.get('com')}  max={stats.get('max')}  "
                f"fwhm={stats.get('fwhm')}"
            )
    else:
        x_field = _resolve_x_motor(start, table, x)
        result["shape"] = (len(table[x_field].values),)
        result["axes"] = [x_field]
        x_arr = np.asarray(table[x_field].values)
        for det in det_fields:
            y_arr = np.asarray(table[det].values)
            stats = _compute_1d_stats(x_arr, y_arr)
            for k, v in stats.items():
                result[k][det] = v
            parts = [f"Scan #{scan_n} ({x_field} vs {det}):"]
            for tag in ("com", "cen", "max", "min", "fwhm"):
                if tag in stats:
                    val = stats[tag]
                    if isinstance(val, tuple):
                        parts.append(f"{tag} = {val[0]:.5f}")
                    else:
                        parts.append(f"{tag} = {float(val):.5f}")
            print("  ".join(parts))

    return result


# ---------------------------------------------------------------------------
# Public — move plans
# ---------------------------------------------------------------------------


_FEATURE_TO_KEY = {
    "cen": "cen",
    "com": "com",
    "max": "max",
    "min": "min",
}


def _move_to_feature(feature, scan_id, positioner, detector, confirm):
    """Internal: move the positioner(s) to ``feature`` of the requested scan."""
    run = cat[scan_id]
    start = run.metadata["start"]
    stop = run.metadata.get("stop")

    if start.get("plan_name") == "psiscan":
        print(
            f"{feature}() is not available for psiscan: the scan axis is a "
            "virtual psi extra, not a movable positioner."
        )
        yield from null()
        return

    table = _read_table(run)
    det_fields = _detector_fields(start, detector)
    detector_name = det_fields[0]

    if _is_grid_scan(start):
        motors, shape = _grid_shape(start, table)
        motor_axes = [np.unique(table[m].values) for m in motors]
        flat = np.asarray(table[detector_name].values)
        img = flat.reshape(shape)

        if positioner is None:
            # Default: move all scan motors to the 2-D feature.
            stats = _compute_2d_stats(motor_axes, img)
            target = stats[feature]
            if feature in ("max", "min"):
                target = target[: len(motors)]
            positioners = [oregistry.find(m) for m in motors]
            mv_args = []
            current_for_msg = []
            for p, t in zip(positioners, target, strict=False):
                mv_args.extend([p, t])
                current_for_msg.append((p.name, _current_position(p), t))
            label = " / ".join(f"{n}: {c}->{t}" for n, c, t in current_for_msg)
            if not _confirm_old_scan(
                stop, confirm, "(2D)", "(see above)", label
            ):
                print("No motion will be done.")
                yield from null()
                return
            print(f"Moving {label}")
            yield from mv(*mv_args)
            return

        # User passed positioner(s): if a single one (or single-element list)
        # is asked for, project to that axis.
        if isinstance(positioner, (list, tuple)) and len(positioner) > 1:
            positioners = list(positioner)
        else:
            positioners = [
                positioner[0]
                if isinstance(positioner, (list, tuple))
                else positioner
            ]

        if len(positioners) == 1:
            p = positioners[0]
            axis_idx = motors.index(p.name) if p.name in motors else 0
            proj = img.sum(
                axis=tuple(i for i in range(img.ndim) if i != axis_idx)
            )
            stats = _compute_1d_stats(motor_axes[axis_idx], proj)
            new_pos = _select_target(feature, stats)
            yield from _do_single_move(p, new_pos, stop, confirm)
            return

        # Two or more explicit positioners — move each to its 2-D coord.
        stats = _compute_2d_stats(motor_axes, img)
        target = stats[feature]
        if feature in ("max", "min"):
            target = target[: len(motors)]
        mv_args = []
        for p, t in zip(positioners, target, strict=False):
            mv_args.extend([p, t])
        print(f"Moving {', '.join(p.name for p in positioners)} to {target}")
        yield from mv(*mv_args)
        return

    # ---- 1D path ----
    if positioner is None:
        x_field = _resolve_x_motor(start, table, None)
        scan_motors = start.get("motors") or [x_field]
        plan_name = start.get("plan_name", "")
        if plan_name == "th2th" or len(scan_motors) <= 1 or not confirm:
            motor_name = x_field
        else:
            options = [x_field] + [m for m in scan_motors if m != x_field]
            answer = (
                input(
                    f"Multi-motor scan. Move which positioner? "
                    f"({'/'.join(options)}) [{x_field}] "
                ).strip()
                or x_field
            )
            if answer not in scan_motors:
                print(f"Unknown positioner '{answer}'. Using {x_field}.")
                answer = x_field
            motor_name = answer
        positioner = oregistry.find(motor_name)
        x_arr = np.asarray(table[motor_name].values)
    else:
        x_arr = np.asarray(table[positioner.name].values)

    y_arr = np.asarray(table[detector_name].values)
    stats = _compute_1d_stats(x_arr, y_arr)
    new_pos = _select_target(feature, stats)
    yield from _do_single_move(positioner, new_pos, stop, confirm)


def _select_target(feature, stats):
    """Resolve the scalar target value from a 1D stats dict for ``feature``."""
    if feature not in stats:
        raise ValueError(
            f"feature {feature!r} not present in stats {sorted(stats)}."
        )
    val = stats[feature]
    if isinstance(val, tuple):
        return val[0]
    return val


def _do_single_move(positioner, new_pos, stop, confirm):
    """Confirm + emit a single-axis ``mv`` plan."""
    current = _current_position(positioner)
    if not _confirm_old_scan(stop, confirm, positioner.name, current, new_pos):
        print("No motion will be done.")
        yield from null()
        return
    print(f"Moving {positioner.name} from {current} to {new_pos}")
    yield from mv(positioner, new_pos)


def cen(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Move to the FWHM-midpoint of a previous scan.

    Equivalent to bluesky ``PeakStats.cen``.  For asymmetric peaks this
    differs from :func:`com`.

    Parameters
    ----------
    scan_id : int, optional
        Catalog index of the scan. Default ``-1`` (last scan).
    positioner : ophyd object or list, optional
        Device(s) to move.  None → autodetected from the scan's motors
        (single for 1D scans, both motors for 2D ``grid_scan``).
    detector : str, optional
        Detector field name. None → first hint from the scan.
    confirm : bool, optional
        If True (default), prompts for multi-motor 1D scans and for
        scans older than 5 minutes.  False skips every prompt.

    See Also
    --------
    :func:`com`
    :func:`maxi`
    :func:`mini`
    :func:`peak_pos`
    """
    yield from _move_to_feature("cen", scan_id, positioner, detector, confirm)


def com(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Move to the centroid (center-of-mass) of a previous scan.

    See :func:`cen` for parameter details.

    See Also
    --------
    :func:`cen`
    :func:`maxi`
    :func:`mini`
    :func:`peak_pos`
    """
    yield from _move_to_feature("com", scan_id, positioner, detector, confirm)


def maxi(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Move to the x-value at peak maximum of a previous scan.

    See :func:`cen` for parameter details.

    See Also
    --------
    :func:`cen`
    :func:`com`
    :func:`mini`
    :func:`peak_pos`
    """
    yield from _move_to_feature("max", scan_id, positioner, detector, confirm)


def mini(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Move to the x-value at peak minimum of a previous scan.

    See :func:`cen` for parameter details.

    See Also
    --------
    :func:`cen`
    :func:`com`
    :func:`maxi`
    :func:`peak_pos`
    """
    yield from _move_to_feature("min", scan_id, positioner, detector, confirm)


# ---------------------------------------------------------------------------
# Backward-compat aliases (PR #54 names)
# ---------------------------------------------------------------------------


def peak(
    scan_id=-1, feature="centroid", positioner=None, detector=None, confirm=True
):
    """Backward-compat: dispatch by ``feature`` to :func:`cen` / :func:`com` /
    :func:`maxi` / :func:`mini`.

    Accepts the PR-#54 feature names (``"centroid"`` / ``"x_at_max_y"`` /
    ``"x_at_min_y"``) and the new short names (``"com"`` / ``"max"`` /
    ``"min"`` / ``"cen"``).
    """
    feature_map = {
        "centroid": "com",
        "com": "com",
        "x_at_max_y": "max",
        "max": "max",
        "x_at_min_y": "min",
        "min": "min",
        "cen": "cen",
    }
    short = feature_map.get(feature)
    if short is None:
        raise ValueError(
            f"Unknown feature {feature!r}; choose one of {sorted(feature_map)}."
        )
    yield from _move_to_feature(short, scan_id, positioner, detector, confirm)


def pmax(scan_id=-1, positioner=None, detector=None, confirm=True):
    """Alias of :func:`maxi` (PR #54 name)."""
    yield from maxi(scan_id, positioner, detector, confirm)


def pmin(scan_id=-1, positioner=None, detector=None, confirm=True):
    """Alias of :func:`mini` (PR #54 name)."""
    yield from mini(scan_id, positioner, detector, confirm)
