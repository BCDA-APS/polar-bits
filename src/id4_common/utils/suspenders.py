from ophyd import EpicsSignalRO
from bluesky.suspenders import SuspendBoolHigh
from .run_engine import RE
from logging import getLogger

logger = getLogger(__name__)

# TODO: I'll leave it zero for now because somebody may want to just
# go inside A... Maybe I can add a "post_plan" that includes
# an option to force resume?
SUSPENDER_SLEEP = 0  # 10*60  # 10 min

run_engine_suspenders = {
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

# for sus in run_engine_suspenders.values():
#     RE.install_suspender(sus)


def _query_label():
    while True:
        options = ["all"] + list(run_engine_suspenders.keys())
        suspender_label = input(
            f"Which suspender? options: {options} - "
        ).split()
        check = [label not in options for label in suspender_label]
        if any(check):
            logger.info("One of the options {labels} is invalid.")
        else:
            return suspender_label


def _query_sleep_time():
    while True:
        sleep_time = (
            input(
                "How long the to wait after beam returns in seconds? "
                f"({SUSPENDER_SLEEP}) "
            )
            or SUSPENDER_SLEEP
        )

        try:
            return float(sleep_time)
        except ValueError:
            logger.info("Invalid entry. Please enter a number.")


def suspender_stop(suspender_label=None):
    if suspender_label is None:
        suspender_label = _query_label()

    if "all" in suspender_label:
        suspender_label = list(run_engine_suspenders.keys())

    for label in suspender_label:
        logger.info(f"Stopping suspender {label}")
        run_engine_suspenders[label].remove()


def suspender_restart(suspender_label=None):

    if suspender_label is None:
        suspender_label = _query_label()

    if isinstance(suspender_label, str):
        suspender_label = [suspender_label]

    if "all" in suspender_label:
        suspender_label = list(run_engine_suspenders.keys())

    for label in suspender_label:
        logger.info(f"Restarting suspender {label}")
        run_engine_suspenders[label].install(RE)


def suspender_change_sleep(suspender_label=None, sleep_time=None):
    if suspender_label is None:
        suspender_label = _query_label()

    if sleep_time is None:
        sleep_time = _query_sleep_time()

    if isinstance(suspender_label, str):
        suspender_label = [suspender_label]

    if "all" in suspender_label:
        suspender_label = list(run_engine_suspenders.keys())

    for label in suspender_label:
        logger.info(f"Changing sleep time of suspender {label} to {sleep_time}")
        run_engine_suspenders[label]._sleep = sleep_time
