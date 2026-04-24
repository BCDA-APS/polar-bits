"""
Chopper
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent


class ChopperDevice(Device):
    """Photon chopper with translation motor, Newport controller, and frequency readback."""

    # In/out motor
    translation = FormattedComponent(
        EpicsMotor, "4idbSoft:m14", labels=("motor",)
    )

    # Newport controller
    status = Component(EpicsSignalRO, "Connected", kind="config")

    frequency_readback = Component(EpicsSignalRO, "FreqSync")
    frequency_setpoint = Component(EpicsSignal, "FrequencySet")

    phase = Component(EpicsSignal, "PhaseDelaySet", kind="config")

    wheel = Component(EpicsSignal, "WheelSet", string=True, kind="config")
    sync = Component(EpicsSignal, "SyncSourceSet", string=True, kind="config")
    mode = Component(EpicsSignal, "ModeSet", string=True, kind="config")
