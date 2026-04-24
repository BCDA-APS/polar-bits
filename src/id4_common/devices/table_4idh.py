"""
Table in middle of 4idb
"""

from apstools.devices import PVPositionerSoftDoneWithStop
from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class Table4idh(Device):
    """
    Optical table in 4IDH with individual leg motors and combined X/Y/pitch/yaw
    pseudo-axes.
    """

    x_us = Component(EpicsMotor, "m1", labels=("motor",))
    x_ds = Component(EpicsMotor, "m2", labels=("motor",))

    y_us = Component(EpicsMotor, "m3", labels=("motor",))
    y_ds = Component(EpicsMotor, "m4", labels=("motor",))

    # TODO: add the combined motion pseudomotors.
    x = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="table1.EX",
        setpoint_pv="table1.X",
        tolerance=0.0003,
        labels=("motor",),
    )

    y = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="table1.EY",
        setpoint_pv="table1.Y",
        tolerance=0.0003,
        labels=("motor",),
    )

    ax = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="table1.EAX",
        setpoint_pv="table1.AX",
        tolerance=0.0003,
        labels=("motor",),
    )

    ay = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="table1.EAY",
        setpoint_pv="table1.AY",
        tolerance=0.0003,
        labels=("motor",),
    )
