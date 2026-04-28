"""
Lakeshore Gaussmeter 475
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import Signal


class GaussmeterDevice(Device):
    """Lakeshore 475 gaussmeter with field readback and scan trigger."""

    field = Component(EpicsSignalRO, "Fld.VAL", kind="hinted")
    field_unit = Component(EpicsSignalRO, "FldUnit.SVAL", kind="normal")
    field_unit_setpoint = Component(EpicsSignal, "Unit.VAL", kind="omitted")
    scan = Component(EpicsSignal, "ReadFld.SCAN", kind="config")
    acquire_dummy = Component(Signal, value=0, kind="omitted")

    @property
    def preset_monitor(self):
        """Return the dummy acquire signal used as a no-op preset monitor."""
        return self.acquire_dummy
