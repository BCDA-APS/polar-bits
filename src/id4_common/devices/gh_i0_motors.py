"""I0 monitor motor stages for 4IDG and 4IDH hutches."""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class I04idg(Device):
    """Two-axis (X, Y) I0 motor stage for the 4IDG hutch."""

    x = Component(EpicsMotor, "m52", labels=("motor",))
    y = Component(EpicsMotor, "m53", labels=("motor",))


class I04idh(Device):
    """Two-axis (X, Y) I0 motor stage for the 4IDH hutch."""

    x = Component(EpicsMotor, "m20", labels=("motor",))
    y = Component(EpicsMotor, "m21", labels=("motor",))
