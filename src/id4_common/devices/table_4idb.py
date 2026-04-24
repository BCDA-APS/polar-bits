"""
Table in middle of 4idb
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class Table4idb(Device):
    """
    Optical table in 4IDB with upstream/downstream X and Y positioning motors.
    """

    x_us = Component(EpicsMotor, "m5", labels=("motor",))
    x_ds = Component(EpicsMotor, "m8", labels=("motor",))

    y_us = Component(EpicsMotor, "m4", labels=("motor",))
    y_ds_in = Component(EpicsMotor, "m7", labels=("motor",))
    y_ds_out = Component(EpicsMotor, "m6", labels=("motor",))

    # TODO: add the combined motion pseudomotors.
