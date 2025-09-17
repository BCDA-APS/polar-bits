from ..utils.run_engine import RE
from .shutters_suspenders import shutter_suspenders
from logging import getLogger

logger = getLogger(__name__)


def _query_label():
    while True:
        options = ["all"] + list(shutter_suspenders.keys())
        suspender_label = input(
            f"Which suspender? options: {options} - "
        ).split()
        check = [label not in options for label in suspender_label]
        if any(check):
            logger.info("One of the options {labels} is invalid.")
        else:
            return suspender_label


def _query_sleep_time(label):
    while True:
        sleep_time = (
            input(
                "How long the to wait after beam returns in seconds? "
                f"({shutter_suspenders[label]._sleep}) "
            )
            or {shutter_suspenders[label]._sleep}
        )

        try:
            return float(sleep_time)
        except ValueError:
            logger.info("Invalid entry. Please enter a number.")


def suspender_stop(suspender_label=None):
    if suspender_label is None:
        suspender_label = _query_label()

    if "all" in suspender_label:
        suspender_label = list(shutter_suspenders.keys())

    for label in suspender_label:
        logger.info(f"Stopping suspender {label}")
        shutter_suspenders[label].remove()


def suspender_restart(suspender_label=None):

    if suspender_label is None:
        suspender_label = _query_label()

    if isinstance(suspender_label, str):
        suspender_label = [suspender_label]

    if "all" in suspender_label:
        suspender_label = list(shutter_suspenders.keys())

    for label in suspender_label:
        logger.info(f"Restarting suspender {label}")
        shutter_suspenders[label].install(RE)


def suspender_change_sleep(suspender_label=None, sleep_time=None):
    if suspender_label is None:
        suspender_label = _query_label()

    if isinstance(suspender_label, str):
        suspender_label = [suspender_label]
    if "all" in suspender_label:
        suspender_label = list(shutter_suspenders.keys())

    for label in suspender_label:
        if sleep_time is None:
            sleep_time = _query_sleep_time(label)
        logger.info(f"Changing sleep time of suspender {label} to {sleep_time}")
        shutter_suspenders[label]._sleep = sleep_time
