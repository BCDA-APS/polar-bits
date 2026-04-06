"""Generic XBPM device with configurable motor PV suffixes."""

from ophyd import Device
from ophyd import EpicsMotor
from ophyd import FormattedComponent


class XBPM(Device):
    """X-ray Beam Position Monitor with parametric motor PV suffixes."""

    x = FormattedComponent(EpicsMotor, "{_motors[x]}", labels=("motor",))
    y = FormattedComponent(EpicsMotor, "{_motors[y]}", labels=("motor",))

    def __init__(self, prefix, *, motorsDict, **kwargs):
        """Initialize XBPM with a motor PV suffix mapping."""
        self._motors = motorsDict
        super().__init__(prefix, **kwargs)
