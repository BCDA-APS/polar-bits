"""
Monochromator feedback
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO


class FeedbackDirection(Device):
    """
    Single-axis PID feedback loop device for monochromator position
    stabilization.
    """

    status = Component(EpicsSignal, ":on", string=True, kind="config")

    readback_pv = Component(EpicsSignal, ".INP", string=True, kind="config")
    control_pv = Component(EpicsSignal, ".OUTL", string=True, kind="config")

    setpoint = Component(EpicsSignal, ".VAL")
    readback = Component(EpicsSignalRO, ".CVAL")
    following_error = Component(EpicsSignalRO, ".ERR")

    scan = Component(EpicsSignal, ".SCAN", string=True, kind="config")

    kp = Component(EpicsSignal, ".KP", kind="config")
    ki = Component(EpicsSignal, ".KI", kind="config")
    kd = Component(EpicsSignal, ".KD", kind="config")

    p = Component(EpicsSignalRO, ".P", kind="omitted")
    i = Component(EpicsSignal, ".I", kind="omitted")
    d = Component(EpicsSignalRO, ".D", kind="omitted")

    low_limit = Component(EpicsSignal, ".DRVL", kind="config")
    high_limit = Component(EpicsSignal, ".DRVH", kind="config")


class FeedbackStation(Device):
    """
    Pair of horizontal and vertical PID feedback loops for one beamline station.
    """

    horizontal = Component(FeedbackDirection, "h")
    vertical = Component(FeedbackDirection, "v")


class MonoFeedback(Device):
    """
    Top-level monochromator feedback device with per-station feedback loops.
    """

    station = Component(
        EpicsSignal, "MonoFBStation", string=True, kind="config"
    )
    enable = Component(EpicsSignal, "MonoFBEnable", string=True, kind="config")

    b = Component(FeedbackStation, "epidB", labels=("4idb",), kind="omitted")
    g = Component(FeedbackStation, "epidG", labels=("4idg",), kind="omitted")
    h = Component(FeedbackStation, "epidH", labels=("4idh",), kind="omitted")

    def _kind_setup(self, value=None, **kwargs):
        for item in "b g h".split():
            kind = "normal" if value.lower() == item else "omitted"
            getattr(self, item).kind = kind

    def default_settings(self):
        """Subscribe to the station signal so per-station kinds track it."""
        self.station.subscribe(self._kind_setup)
