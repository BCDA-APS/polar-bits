"""
Legacy ``cen2`` / ``maxi2`` / ``mini2`` plans driven by
`bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

Kept as a fallback path for runs where the BestEffortCallback was
running live.  For everything else, prefer the new
:mod:`id4_common.plans.peak_position` ``cen`` / ``com`` / ``maxi`` /
``mini`` plans, which compute peak statistics from the catalog and
support 2-D ``grid_scan`` runs (issue #59).
"""

from datetime import datetime
from datetime import timedelta
from logging import getLogger

from apsbits.core.instrument_init import oregistry
from bluesky.plan_stubs import null

from ..utils.run_engine import cat
from ..utils.run_engine import peaks
from .move_plans import mv

logger = getLogger(__name__)
logger.info(__file__)

__all__ = [
    "cen2",
    "maxi2",
    "mini2",
]


# TODO: Create the option to ask the user if there are multiple detectors or
# positioners. Probably add a timeout to it.


def _get_positioner():
    dimensions = cat[-1].metadata["start"]["hints"]["dimensions"]
    if len(dimensions) > 1:
        raise ValueError(
            "Positioner must be specified for scans with more than one dimension."
        )

    return oregistry.find(dimensions[0][0][0])


def _get_detector():
    if len(peaks["cen"].keys()) > 1:
        raise ValueError(
            "You need to provide a detector name if more than 1 detector was plotted."
        )

    return list(peaks["cen"].keys())[0]


def _get_current_pos(positioner):
    if hasattr(positioner, "position"):
        current_pos = positioner.position
    elif hasattr(positioner, "readback"):
        current_pos = positioner.readback.get()
    else:
        current_pos = positioner.get()

    return current_pos


def _move_to_pos(parameter, positioner=None, detector=None):
    if positioner is None:
        positioner = _get_positioner()

    if detector is None:
        detector = _get_detector()

    new_pos = (
        peaks[parameter][detector]
        if parameter == "cen"
        else peaks[parameter][detector][0]
    )
    current_pos = _get_current_pos(positioner)

    # If it doesn't find a stop metadata document, it will trigger the motion
    # question
    meta = cat[-1].metadata.get("stop", None)
    time = (
        datetime.now() - datetime.fromtimestamp(meta["time"])
        if meta is not None
        else timedelta(seconds=1000)
    )

    if time.seconds > 300:
        answer = (
            input(
                f"Move {positioner.name} from {current_pos} to {new_pos}? (Y/[N]) "
            )
            or "N"
        )
        if answer not in ["Y", "y", "yes"]:
            logger.info("No motion will be done.")
            yield from null()

    logger.info(
        "Moving {} from {} to {}".format(positioner.name, current_pos, new_pos)
    )

    yield from mv(positioner, new_pos)


def cen2(positioner=None, detector=None):
    """
    Legacy: move motor to FWHM-midpoint of last scan via the BEC peaks.

    Uses the position found by
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
    :func:`id4_common.plans.peak_position.cen` for new code.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("cen", positioner=positioner, detector=detector)


def maxi2(positioner=None, detector=None):
    """
    Legacy: move motor to maximum of last scan via the BEC peaks.

    Uses the position found by
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
    :func:`id4_common.plans.peak_position.maxi` for new code.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("max", positioner=positioner, detector=detector)


def mini2(positioner=None, detector=None):
    """
    Legacy: move motor to minimum of last scan via the BEC peaks.

    Uses the position found by
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.  Prefer
    :func:`id4_common.plans.peak_position.mini` for new code.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("min", positioner=positioner, detector=detector)
