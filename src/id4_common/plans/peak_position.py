"""Plans that compute peak statistics from a previous scan and move there."""

import warnings
from datetime import datetime
from datetime import timedelta

import numpy as np
from apsbits.core.instrument_init import oregistry
from apstools.utils import xy_statistics
from bluesky.plan_stubs import null
from polartools.load_data import load_catalog

from .local_scans import mv

# Short aliases for xy_statistics features (mirrors apstools.lineup2).
_FEATURE_ALIASES = {
    "com": "centroid",
    "max": "x_at_max_y",
    "min": "x_at_min_y",
}


def _resolve_x_motor(start, table, x=None):
    """
    Pick the scan x-motor field name.

    - If ``x`` is given, return it unchanged.
    - If the scan has a single motor, return that.
    - For multi-motor scans (th2th, hklscan, ...), return the motor with
      the largest range during the scan — the "fastest changing" axis,
      which is what makes sense to fit a peak against.
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


def peak_pos(scan_id=-1, x=None, y=None):
    """
    Compute peak statistics for one or more detectors of a previous scan.

    Loads scan data from the ``"4id_polar"`` catalog and computes
    statistics with :func:`apstools.utils.xy_statistics` — the same
    numpy-based machinery used by ``apstools.plans.alignment.lineup2``.

    Parameters
    ----------
    scan_id : int, optional
        Catalog index. Default ``-1`` (last scan); negative indices count
        from the end.
    x : str, optional
        Motor (x-axis) field name. If None, uses the first entry in the
        scan's ``start["motors"]``.
    y : str or list of str, optional
        Detector (y-axis) field name(s). If None, uses every entry in
        ``start["hints"]["detectors"]``.

    Returns
    -------
    dict
        Nested dict mirroring ``bluesky.callbacks.best_effort.peaks``::

            {
                "com":  {detector: x_centroid, ...},
                "max":  {detector: (x_at_max_y, max_y), ...},
                "min":  {detector: (x_at_min_y, min_y), ...},
                "fwhm": {detector: fwhm, ...},
            }
    """
    cat = load_catalog("4id_polar")
    run = cat[scan_id]
    start = run.metadata["start"]

    if y is None:
        det_fields = start.get("hints", {}).get("detectors") or []
        if not det_fields:
            raise ValueError("No detector hints in scan; pass y= explicitly.")
    elif isinstance(y, str):
        det_fields = [y]
    else:
        det_fields = list(y)

    with warnings.catch_warnings():
        # Silence FutureWarning from databroker/xarray about Dataset.dims.
        warnings.filterwarnings(
            "ignore",
            category=FutureWarning,
            message="The return type of `Dataset.dims`.*",
        )
        table = run.primary.read()

    x = _resolve_x_motor(start, table, x)
    x_arr = np.asarray(table[x].values)

    scan_n = start.get("scan_id")
    peaks_dict = {"com": {}, "max": {}, "min": {}, "fwhm": {}}
    for det in det_fields:
        y_arr = np.asarray(table[det].values)
        stats = xy_statistics(x_arr, y_arr)

        com = stats.get("centroid")
        x_max = stats.get("x_at_max_y")
        max_y = stats.get("max_y")
        x_min = stats.get("x_at_min_y")
        min_y = stats.get("min_y")
        fwhm = stats.get("fwhm")

        if com is not None:
            peaks_dict["com"][det] = float(com)
        if x_max is not None and max_y is not None:
            peaks_dict["max"][det] = (float(x_max), float(max_y))
        if x_min is not None and min_y is not None:
            peaks_dict["min"][det] = (float(x_min), float(min_y))
        if fwhm is not None:
            peaks_dict["fwhm"][det] = float(fwhm)

        parts = [f"Scan #{scan_n} ({x} vs {det}):"]
        if com is not None:
            parts.append(f"com = {float(com):.5f}")
        if x_max is not None:
            parts.append(f"max = {float(x_max):.5f}")
        if x_min is not None:
            parts.append(f"min = {float(x_min):.5f}")
        if fwhm is not None:
            parts.append(f"fwhm = {float(fwhm):.5f}")
        print("  ".join(parts))

    return peaks_dict


def peak(
    scan_id=-1,
    feature="centroid",
    positioner=None,
    detector=None,
    confirm=True,
):
    """
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

    Parameters
    ----------
    scan_id : int, optional
        Catalog index. Default ``-1`` (last scan).
    feature : str, optional
        Statistical measure to move to. Default ``"centroid"``.
    positioner : ophyd object, optional
        Device to move. If None, the scan's fastest-changing motor is
        used (with an interactive override for multi-motor scans).
    detector : str, optional
        Detector field name passed through to :func:`peak_pos` as ``y``.
    confirm : bool, optional
        If True (default), interactive prompts are shown when
        appropriate (positioner selection for multi-motor scans and the
        >5-min move confirmation). If False, all such prompts are
        skipped.
    """
    cat = load_catalog("4id_polar")
    run = cat[scan_id]
    start = run.metadata["start"]

    if start.get("plan_name") == "psiscan":
        print(
            "peak() is not available for psiscan: the scan axis is a "
            "virtual psi extra, not a movable positioner."
        )
        yield from null()
        return

    if positioner is None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=FutureWarning,
                message="The return type of `Dataset.dims`.*",
            )
            table = run.primary.read()
        default_motor = _resolve_x_motor(start, table)
        scan_motors = start.get("motors") or [default_motor]
        plan_name = start.get("plan_name", "")

        # th2th: 2θ (gamma) is always the right axis — never prompt.
        if plan_name == "th2th" or len(scan_motors) <= 1 or not confirm:
            motor_name = default_motor
        else:
            options = [default_motor] + [
                m for m in scan_motors if m != default_motor
            ]
            answer = (
                input(
                    f"Multi-motor scan. Move which positioner? "
                    f"({'/'.join(options)}) [{default_motor}] "
                ).strip()
                or default_motor
            )
            if answer not in scan_motors:
                print(
                    f"Unknown positioner '{answer}'. " f"Using {default_motor}."
                )
                answer = default_motor
            motor_name = answer

        positioner = oregistry.find(motor_name)

    if detector is None:
        det_hints = start.get("hints", {}).get("detectors") or []
        if not det_hints:
            raise ValueError(
                "No detector hints in scan; pass detector= explicitly."
            )
        detector = det_hints[0]

    # Map xy_statistics feature name to the key/index in the peaks-style
    # dict returned by peak_pos. ``fwhm`` is intentionally excluded: it is
    # a width, not a position to move to.
    feature_key = _FEATURE_ALIASES.get(feature, feature)
    feature_to_peaks = {
        "centroid": ("com", None),
        "x_at_max_y": ("max", 0),
        "x_at_min_y": ("min", 0),
    }
    if feature_key not in feature_to_peaks:
        raise ValueError(
            f"feature {feature!r} not supported by peak(); "
            f"choose one of {list(feature_to_peaks)} (or aliases "
            f"{list(_FEATURE_ALIASES)})."
        )
    pkey, pidx = feature_to_peaks[feature_key]

    peaks_dict = peak_pos(scan_id=scan_id, y=detector)
    entry = peaks_dict[pkey].get(detector)
    if entry is None:
        raise ValueError(
            f"No {pkey!r} value found for detector {detector!r} in scan."
        )
    new_pos = entry[pidx] if pidx is not None else entry

    if hasattr(positioner, "position"):
        current_pos = positioner.position
    elif hasattr(positioner, "readback"):
        current_pos = positioner.readback.get()
    else:
        current_pos = positioner.get()

    stop = run.metadata.get("stop")
    elapsed = (
        datetime.now() - datetime.fromtimestamp(stop["time"])
        if stop is not None
        else timedelta(seconds=1000)
    )

    if elapsed.seconds > 300 and confirm:
        answer = (
            input(
                f"Move {positioner.name} from {current_pos} to "
                f"{new_pos}? (Y/[N]) "
            )
            or "N"
        )
        if answer not in ("Y", "y", "yes"):
            print("No motion will be done.")
            yield from null()
            return

    print(f"Moving {positioner.name} from {current_pos} to {new_pos}")
    yield from mv(positioner, new_pos)


def pmax(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Plan that moves a positioner to the x value at peak maximum.

    Convenience wrapper for ``peak(scan_id, feature="x_at_max_y", ...)``.
    See :func:`peak` for parameters.
    """
    yield from peak(
        scan_id=scan_id,
        feature="x_at_max_y",
        positioner=positioner,
        detector=detector,
        confirm=confirm,
    )


def pmin(scan_id=-1, positioner=None, detector=None, confirm=True):
    """
    Plan that moves a positioner to the x value at peak minimum.

    Convenience wrapper for ``peak(scan_id, feature="x_at_min_y", ...)``.
    See :func:`peak` for parameters.
    """
    yield from peak(
        scan_id=scan_id,
        feature="x_at_min_y",
        positioner=positioner,
        detector=detector,
        confirm=confirm,
    )
