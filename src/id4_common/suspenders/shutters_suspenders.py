from ophyd import EpicsSignalRO
from bluesky.suspenders import SuspendBoolHigh
from logging import getLogger

logger = getLogger(__name__)

# TODO: I'll leave it zero for now because somebody may want to just
# go inside A... Maybe I can add a "post_plan" that includes
# an option to force resume?
SUSPENDER_SLEEP = 0  # 10*60  # 10 min

shutter_suspenders = {
    "a_shutter": SuspendBoolHigh(
        EpicsSignalRO("4ID:BLEPS:FES_CLOSED", name="a_susp"),
        sleep=SUSPENDER_SLEEP,
        tripped_message="4-ID-A shutter is closed.",
    ),
    "b_shutter": SuspendBoolHigh(
        EpicsSignalRO("4ID:BLEPS:SBS_CLOSED", name="b_susp"),
        sleep=0,
        tripped_message="4-ID-B shutter is closed.",
    ),
}
