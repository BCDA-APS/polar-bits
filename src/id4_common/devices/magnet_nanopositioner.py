"""
Magnet Nanopositioner motors
"""

from ophyd import Component
from ophyd import EpicsMotor
from ophyd import MotorBundle


class NanoPositioner(MotorBundle):
    """Three-axis (X, Y, Z) nanopositioning motor bundle."""

    x = Component(EpicsMotor, "m1", labels=("motor",))
    y = Component(EpicsMotor, "m2", labels=("motor",))
    z = Component(EpicsMotor, "m3", labels=("motor",))
