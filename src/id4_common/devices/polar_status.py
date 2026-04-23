"""
Polar status
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent


class HutchStatus(Device):
    """EPICS status device for a single APS sector-4 experimental hutch."""

    user_enable = FormattedComponent(
        EpicsSignalRO, "{prefix}{_hutch}:UserKey:CM", string=True
    )

    aps_enable = FormattedComponent(
        EpicsSignalRO, "{prefix}{_hutch}:APSKey:CM", string=True
    )

    searched = FormattedComponent(
        EpicsSignalRO, "{prefix}{_hutch}:Secure:BM", string=True
    )

    beam_present = FormattedComponent(
        EpicsSignalRO, "{prefix}{_hutch}:BeamPresent:CM", string=True
    )

    shutter = FormattedComponent(
        EpicsSignalRO, "{self.parent.prefix}S{_hutch}S:BLEPS_Status:CM", string=True
    )

    def __init__(self, prefix, hutch=None, **kwargs):
        """Initialize HutchStatus with the single-letter hutch identifier (e.g. 'B')."""
        self._hutch = hutch
        super().__init__(prefix, **kwargs)


class AStatus(HutchStatus):
    """HutchStatus variant for the A hutch with its front-end shutter PV."""

    shutter = FormattedComponent(
        EpicsSignalRO, "{self.parent.prefix}FES:BeamBlocking:CM", string=True
    )


class Status4ID(Device):
    """Aggregate status device for all hutches and the front-end at APS sector 4."""

    online = Component(EpicsSignalRO, "FES:GlobalOnline:CM", string=True)
    acis = Component(EpicsSignalRO, "FES:ACISPermit:CM", string=True)
    fe_eps = Component(EpicsSignalRO, "FES:FEEPSPermit:CM", string=True)

    a_hutch = Component(AStatus, "Sta", hutch="A", labels=("4ida",))
    b_hutch = Component(HutchStatus, "Sta", hutch="B", labels=("4idb",))
    g_hutch = Component(HutchStatus, "Sta", hutch="G", labels=("4idg",))
    h_hutch = Component(HutchStatus, "Sta", hutch="H", labels=("4idh",))
