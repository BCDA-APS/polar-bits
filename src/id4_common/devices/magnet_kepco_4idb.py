"""
Kepko power supply
"""

from time import sleep

from apstools.devices import PVPositionerSoftDone
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent
from ophyd import Kind


class LocalPositioner(PVPositionerSoftDone):
    """Voltage/Current positioner"""

    readback = FormattedComponent(
        EpicsSignalRO,
        "{prefix}d{_type}",
        kind="hinted",
    )

    setpoint = FormattedComponent(
        EpicsSignal,
        "{prefix}{_type}",
        write_pv="{prefix}set{_type}",
    )

    def __init__(self, *args, progtype, **kwargs):
        """
        Initialize LocalPositioner with the program type ('V' for voltage, 'C'
        for current).
        """
        self._type = progtype
        self._sleep = 0.005
        super().__init__(*args, readback_pv="1", **kwargs)

    def _setup_move(self, position):
        """Move and do not wait until motion is complete (asynchronous)"""
        self.log.debug("%s.setpoint = %s", self.name, position)
        self.setpoint.put(position, wait=True)
        self.done.put(False)
        sleep(self._sleep)
        if self.actuate is not None:
            self.log.debug("%s.actuate = %s", self.name, self.actuate_value)
            self.actuate.put(self.actuate_value, wait=False)
        self.cb_readback()  # This is needed to force the first check.


class KepcoController(Device):
    """
    Kepco bipolar power supply with voltage and current positioners and mode
    control.
    """

    # Inputs
    voltage = Component(LocalPositioner, "", progtype="V", tolerance=0.02)
    current = Component(LocalPositioner, "", progtype="C", tolerance=0.03)

    # Control toggles
    mode = Component(
        EpicsSignal, "setMode", kind="config", string=True, auto_monitor=True
    )

    remote = Component(
        EpicsSignal, "setRemote", kind="config", string=True, auto_monitor=True
    )

    enable_setpoint = Component(
        EpicsSignal, "Enable", kind="config", string=True
    )
    enable_readback = Component(
        EpicsSignalRO, "Output", kind="config", string=True
    )

    external_mode_setpoint = Component(EpicsSignal, "setExtMode", kind="config")
    external_mode_readback = Component(EpicsSignal, "ExtModeStr", kind="config")

    # Extras
    id = Component(EpicsSignalRO, "IDN", kind="config")
    id_read = Component(EpicsSignal, "IDN.PROC", kind="omitted")

    scan_rate = Component(
        EpicsSignal, "seq_rd.SCAN", kind="omitted", string=True
    )

    @mode.sub_value
    def mode_change(self, value=None, **kwargs):
        """
        Update readback visibility when the Kepco mode (Current/Voltage)
        changes.
        """
        if value == "Current":
            self.current.readback.kind = Kind.hinted
            self.voltage.readback.kind = Kind.normal

        if value == "Voltage":
            self.current.readback.kind = Kind.normal
            self.voltage.readback.kind = Kind.hinted

    def default_settings(self):
        """
        Configure scan rate, remote control, model ID, and set current mode.
        """
        self.scan_rate.set(".1 second").wait(5)
        self.remote.set("Remote").wait(5)
        self.id_read.set(1).wait(5)
        self.mode.set("Current").wait(5)
        self.mode_change(value=self.mode.get())
