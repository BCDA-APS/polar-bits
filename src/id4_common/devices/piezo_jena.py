"""PiezoJena control via the 4-ID-G MOXA serial gateway.

The PiezoJena controller is wired to channel 2 of the MOXA box exposed
by the asyn record at ``4idgSoftX:asyn_MOXA_G:2``. The asynRecord protocol
uses three fields:

    .TMOD   transmit mode (1 = write, 0 = read/write)
    .AOUT   ASCII output (the command sent on the wire)
    .TINP   ASCII input  (the response read back)

Wire commands:

    modon,<axis>,1   switch the modulation input on <axis> ON
                     (external modulation enabled)
    modon,<axis>,0   switch the modulation input on <axis> OFF
                     (external modulation disabled)
    modon,<axis>     query modulation-input state on <axis>;
                     response lands in .TINP

where <axis> is 0 (x), 1 (y), or 2 (z).
"""

import time

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

# Map user-facing axis labels to the channel number used in the wire command.
_AXIS_CHANNEL = {"x": 0, "y": 1, "z": 2, 0: 0, 1: 1, 2: 2}


def _resolve_axis(axis):
    """Return the integer channel number for ``axis`` ('x'/'y'/'z' or 0/1/2)."""
    if isinstance(axis, str):
        key = axis.lower()
        if key in _AXIS_CHANNEL:
            return _AXIS_CHANNEL[key]
        try:
            return _AXIS_CHANNEL[int(key)]
        except (KeyError, ValueError):
            pass
    else:
        try:
            return _AXIS_CHANNEL[int(axis)]
        except (KeyError, ValueError, TypeError):
            pass
    raise ValueError(f"Unknown axis {axis!r}; expected 'x'/'y'/'z' or 0/1/2.")


class PiezoJena(Device):
    """PiezoJena status / input control via MOXA channel 2."""

    tmod = Component(EpicsSignal, ".TMOD", kind="config")
    aout = Component(EpicsSignal, ".AOUT", string=True, kind="config")
    tinp = Component(EpicsSignalRO, ".TINP", string=True, kind="normal")

    def _send(self, command, tmod=1):
        """Write `command` to .AOUT after switching .TMOD."""
        self.tmod.put(tmod)
        self.aout.put(command)

    def modulation_input_on(self, axis):
        """Switch the modulation input on `axis` ON (external modulation
        enabled). Sends ``modon,<axis>,1``."""
        self._send(f"modon,{_resolve_axis(axis)},1")

    def modulation_input_off(self, axis):
        """Switch the modulation input on `axis` OFF (external modulation
        disabled). Sends ``modon,<axis>,0``."""
        self._send(f"modon,{_resolve_axis(axis)},0")

    def read_status(self, axis, settle_time=0.2):
        """Issue a status query for `axis` and return the .TINP response.

        Switches .TMOD to 0 (read/write), writes the bare ``modon,<axis>``
        query on .AOUT, waits ``settle_time`` seconds for the asyn
        record to push the response into .TINP, then returns the
        latest .TINP value.
        """
        self._send(f"modon,{_resolve_axis(axis)}", tmod=0)
        time.sleep(settle_time)
        return self.tinp.get()
