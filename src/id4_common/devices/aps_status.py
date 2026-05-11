"""
APS status
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO


class StatusAPS(Device):
    """Device exposing APS ring current and operational status signals."""

    current = Component(EpicsSignalRO, "S-DCCT:CurrentM")
    machine_status = Component(
        EpicsSignalRO, "S:DesiredMode", string=True, kind="config"
    )
    operating_mode = Component(
        EpicsSignalRO, "S:ActualMode", string=True, kind="config"
    )
    shutter_status = Component(
        EpicsSignalRO,
        "RF-ACIS:FePermit:Sect1To35IdM",
        string=True,
        kind="config",
    )
