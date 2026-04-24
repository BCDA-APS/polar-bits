"""
Nanopositioner motors
"""

from ophyd import Component
from ophyd import EpicsMotor
from ophyd import MotorBundle


class MyEpicsMotor(EpicsMotor):
    """
    EpicsMotor subclass that removes velocity from stage signals on unstage.
    """

    def unstage(self):
        """
        Remove velocity from stage_sigs before delegating to parent unstage.
        """
        try:
            self.stage_sigs.pop("velocity")
        except KeyError:
            pass
        return super().unstage()


class NanoPositioner(MotorBundle):
    """Three-axis nanopositioner (X, Y, Z) using Jena piezo motors."""

    nanoy = Component(MyEpicsMotor, "m1")
    nanox = Component(MyEpicsMotor, "m2")
    nanoz = Component(MyEpicsMotor, "m3")
