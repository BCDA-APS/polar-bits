"""Interferometer setup"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO


class InterferometerDevice(Device):
    """
    Six-channel interferometer readout for mirror horizontal and vertical
    positions.
    """

    mhor_up = Component(EpicsSignalRO, "pixelTrig-1_POS1")

    mhor_down = Component(EpicsSignalRO, "pixelTrig-1_POS2")

    shor = Component(EpicsSignalRO, "pixelTrig-2_POS1")
    mvert_up = Component(EpicsSignalRO, "pixelTrig-2_POS2")

    mvert_down = Component(EpicsSignalRO, "pixelTrig-3_POS1")
    svert = Component(EpicsSignalRO, "pixelTrig-3_POS2")

    def plot_first_pos1(self):
        """Set only the mhor_up channel as hinted and all others to normal."""
        self.mhor_up.kind = "hinted"
        self.mhor_down.kind = "normal"
        self.shor.kind = "normal"
        self.mvert_up.kind = "normal"
        self.mvert_down.kind = "normal"
        self.svert.kind = "normal"

    def plot_all(self):
        """Set all six interferometer channels to hinted kind for plotting."""
        self.mhor_up.kind = "hinted"
        self.mhor_down.kind = "hinted"
        self.shor.kind = "hinted"
        self.mvert_up.kind = "hinted"
        self.mvert_down.kind = "hinted"
        self.svert.kind = "hinted"
