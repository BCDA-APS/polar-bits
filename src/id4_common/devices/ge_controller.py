"""
GE pressure controllers
"""

from apstools.devices import PVPositionerSoftDoneWithStop
from ophyd import Component
from ophyd import EpicsSignalRO
from ophyd import EpicsSignalWithRBV


class GEController(PVPositionerSoftDoneWithStop):
    """General controller as a PVPositioner"""

    # configuration
    units = Component(EpicsSignalWithRBV, "Units", kind="config")
    control = Component(EpicsSignalWithRBV, "Control", kind="config")
    slew_mode = Component(EpicsSignalWithRBV, "SlewMode", kind="config")
    slew = Component(EpicsSignalWithRBV, "Slew", kind="config")
    effort = Component(EpicsSignalRO, "Effort_RBV", auto_monitor=True, kind="config")

    def __init__(self, *args, timeout=60 * 60 * 10, **kwargs):
        """Initialize GEController with a default 10-hour timeout and zero settle time."""
        super().__init__(*args, timeout=timeout, **kwargs)
        self._settle_time = 0

    @property
    def settle_time(self):
        """Return the settle time in seconds after a move completes."""
        return self._settle_time

    @settle_time.setter
    def settle_time(self, value):
        if value < 0:
            raise ValueError("Settle value needs to be >= 0.")
        else:
            self._settle_time = value

    @property
    def egu(self):
        """Return the engineering units string from the EPICS units signal."""
        return self.units.get(as_string=True)

    def stop(self, *, success=False):
        """Stop the positioner; hold current position if not successful."""
        if success is False:
            self.setpoint.put(self._position)
        super().stop(success=success)
