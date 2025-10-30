from logging import getLogger
from apsbits.core.instrument_init import oregistry
from .local_scans import mv
from ..utils.run_engine import peaks, cat
from datetime import datetime, timedelta
from bluesky.plan_stubs import null

logger = getLogger(__name__)
logger.info(__file__)

__all__ = [
    "cen",
    "maxi",
    "mini",
]


# TODO: Create the option to ask the user if there are multiple detectors or
# positioners. Probably add a timeout to it.

def _get_positioner():
    dimensions = cat[-1].metadata["start"]["hints"]["dimensions"]
    if len(dimensions) > 1:
        raise ValueError(
            "Positioner must be specified for scans with more than one "
            "dimension."
        )

    return oregistry.find(dimensions[0][0][0])


def _get_detector():
    if len(peaks["cen"].keys()) > 1:
        raise ValueError(
            "You need to provide a detector name if more than 1 detector "
            "was plotted."
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

    new_pos = peaks[parameter][detector]
    current_pos = _get_current_pos(positioner)

    # If it doesn't find a stop metadata document, it will trigger the motion
    # question
    meta = cat[-1].metadata.get("stop", None)
    time = (
        datetime.now() - datetime.fromtimestamp(meta['time'])
        if meta is not None else timedelta(seconds=1000)
    )

    if time.seconds > 300:
        answer = input(
            f"Move {positioner.name} from {current_pos} to {new_pos}? (Y/[N]) "
        ) or "N"
        if answer not in ['Y','y','yes']:
            logger.info("No motion will be done.")
            yield from null()

    logger.info(
        "Moving {} from {} to {}".format(positioner.name, current_pos, new_pos)
    )

    yield from mv(positioner, new_pos)


def cen(positioner=None, detector=None):
    """
    Plan that moves motor to center of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("cen", positioner=positioner, detector=detector)


def maxi(positioner=None, detector=None):
    """
    Plan that moves motor to maximum of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("max", positioner=positioner, detector=detector)


def mini(positioner=None, detector=None):
    """
    Plan that moves motor to minimum of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("min", positioner=positioner, detector=detector)
