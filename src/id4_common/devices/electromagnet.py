"""Electromagnet."""

from ophyd import Device
from ophyd import EpicsMotor
from ophyd import FormattedComponent

from .magnet_kepco_4idb import KepcoController


class Magnet2T(Device):
    """2 Tesla electromagnet with sample and magnet positioning motors."""

    sx = FormattedComponent(EpicsMotor, "{_mp}m18", labels=("motor",))
    sy = FormattedComponent(EpicsMotor, "{_mp}m17", labels=("motor",))
    srot = FormattedComponent(EpicsMotor, "{_mp}m19", labels=("motor",))

    mx = FormattedComponent(EpicsMotor, "{_mp}m22", labels=("motor",))
    my = FormattedComponent(EpicsMotor, "{_mp}m21", labels=("motor",))
    mrot = FormattedComponent(EpicsMotor, "{_mp}m20", labels=("motor",))

    kepco = FormattedComponent(KepcoController, "{_kp}", labels=("magnet",))

    def __init__(self, prefix, *, motor_prefix, kepco_prefix, **kwargs):
        """Initialize Magnet2T with separate motor and Kepco IOC prefixes."""
        self._mp = motor_prefix
        self._kp = kepco_prefix
        super().__init__(prefix, **kwargs)

    def default_settings(self):
        """Apply default settings to the Kepco controller."""
        self.kepco.default_settings()
