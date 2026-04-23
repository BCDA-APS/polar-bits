"""
4-ID-B diamond window motors
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class WindowStages(Device):
    """Two-axis (X, Y) motorized stage for diamond window positioning."""

    x = Component(EpicsMotor, "m1", labels=("motor",))
    y = Component(EpicsMotor, "m2", labels=("motor",))
