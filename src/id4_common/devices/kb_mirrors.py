"""
KB mirror
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class KBMirror(Device):
    """Kirkpatrick-Baez mirror with X translation and rotation motors."""

    # Overal motors
    x = Component(EpicsMotor, "m16", labels=("motor",))
    rot = Component(EpicsMotor, "m15", labels=("motor",))

    # KB mirror setup
    # TODO
