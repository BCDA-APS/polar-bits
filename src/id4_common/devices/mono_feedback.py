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

    status = Component(EpicsSignal, ":on", string=True)

    readback_pv = Component(EpicsSignal, ".INP", string=True)
    control_pv = Component(EpicsSignal, ".OUTL", string=True)

    setpoint = Component(EpicsSignal, ".VAL")
    readback = Component(EpicsSignalRO, ".CVAL")
    following_error = Component(EpicsSignalRO, ".ERR")

    scan = Component(EpicsSignal, ".SCAN", string=True)

    kp = Component(EpicsSignal, ".KP")
    ki = Component(EpicsSignal, ".KI")
    kd = Component(EpicsSignal, ".KD")

    p = Component(EpicsSignalRO, ".P")
    i = Component(EpicsSignal, ".I")
    d = Component(EpicsSignalRO, ".D")

    low_limit = Component(EpicsSignal, ".DRVL")
    high_limit = Component(EpicsSignal, ".DRVH")


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
            kind = "config" if value.lower() == item else "omitted"
            getattr(self, item).kind = kind

    def default_settings(self):
        """Subscribe to the station signal so per-station kinds track it."""
        self.station.subscribe(self._kind_setup)
