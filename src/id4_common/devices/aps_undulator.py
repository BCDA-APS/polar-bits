"""
Undulator support
"""

from typing import Any
from typing import Callable

from apstools.devices import STI_Undulator
from apstools.devices import TrackingSignal
from apstools.devices.aps_undulator import UndulatorPositioner
from numpy import abs
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd.status import Status
from ophyd.status import StatusBase


class PolarUndulatorPositioner(UndulatorPositioner):
    """UndulatorPositioner that skips waiting if the target is within the energy deadband."""

    def set(
        self,
        new_position: Any,
        *,
        timeout: float = None,
        moved_cb: Callable = None,
        wait: bool = False,
    ) -> StatusBase:
        """Move to new_position; return immediately done if already within the energy deadband."""
        # If position is within the deadband --> move, but do not wait
        # for it?
        if (
            abs(new_position - self.readback.get())
            < self.parent.energy_deadband.get()
            * self.parent.harmonic_value.get()
        ):
            _status = Status()
            _status.set_finished()
        else:
            _status = super().set(
                new_position, timeout=timeout, moved_cb=moved_cb, wait=wait
            )
        return _status


class PolarUndulator(STI_Undulator):
    """STI undulator subclass with energy tracking, offset, and deadband signals."""

    # TODO: The energy should really follow the gap 1 um deadband...

    tracking = Component(TrackingSignal, value=False, kind="config")
    energy_offset = Component(Signal, value=0, kind="config")
    energy_deadband = Component(Signal, value=0.002, kind="config")
    # energy_deadband = Component(Signal, value=0.001, kind='config')
    energy = Component(PolarUndulatorPositioner, "Energy")
    version_hpmu = None


class PhaseShifterDevice(Device):
    """Phase shifter device with gap positioner and start/stop control signals."""

    gap = Component(UndulatorPositioner, "Gap")

    start_button = Component(EpicsSignal, "StartC.VAL")
    stop_button = Component(EpicsSignal, "StopC.VAL")
    done = Component(EpicsSignalRO, "BusyM.VAL", kind="omitted")

    gap_deadband = Component(EpicsSignal, "DeadbandGapC")
    device_limit = Component(EpicsSignal, "DeviceLimitM.VAL")
    device = Component(EpicsSignalRO, "DeviceM", kind="config")
    location = Component(EpicsSignalRO, "LocationM", kind="config")
    message1 = Component(
        EpicsSignalRO, "Message1M.VAL", kind="config", string=True
    )
    message2 = Component(
        EpicsSignalRO, "Message2M.VAL", kind="config", string=True
    )

    def __init__(self, *args, **kwargs):
        """Initialize PhaseShifterDevice and set the gap done-value to 0."""
        super().__init__(*args, **kwargs)
        self.gap.done_value = 0


class PolarUndulatorPair(Device):
    """Composite device grouping upstream and downstream undulators with a phase shifter."""

    us = Component(PolarUndulator, "USID:", labels=("track_energy",))
    ds = Component(PolarUndulator, "DSID:", labels=("track_energy",))
    phase_shifter = Component(PhaseShifterDevice, "ILPS:")
