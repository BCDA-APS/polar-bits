"""
HHL mirror
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent


class HHLMirror(Device):
    """Beamline high heat load mirror components."""

    # Motors
    y = Component(EpicsMotor, "m1", labels=("motor",))
    x1 = Component(EpicsMotor, "m2", labels=("motor",), kind="omitted")
    x2 = Component(EpicsMotor, "m3", labels=("motor",), kind="omitted")
    us_bend = Component(EpicsMotor, "m4", labels=("motor",), kind="omitted")
    ds_bend = Component(EpicsMotor, "m5", labels=("motor",), kind="omitted")

    # Combined motions
    x = Component(EpicsMotor, "pm1", labels=("motor",))
    pitch = Component(EpicsMotor, "pm2", labels=("motor",))
    fine_pitch = FormattedComponent(
        EpicsMotor, "4idaSoft:m1", labels=("motor",)
    )
    curvature = Component(EpicsMotor, "pm3", labels=("motor",))
    elipticity = Component(EpicsMotor, "pm4", labels=("motor",))

    # Other parameters
    stripe = Component(EpicsSignal, "stripe", string=True, kind="config")
    radius_estimated = Component(EpicsSignalRO, "EstimatedRoC", kind="config")
    radius_target = Component(EpicsSignal, "RoCReq.VAL", kind="config")
    critical_energy = Component(EpicsSignalRO, "Ecritical", kind="config")
    beam_offset = Component(EpicsSignalRO, "beam_offset", kind="config")
    alpha = Component(EpicsSignalRO, "alpha", kind="config")
