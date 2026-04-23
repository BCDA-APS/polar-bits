"""
Huber filters
"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import FormattedComponent


class SlotDevice(Device):
    """Single Huber filter slot with label, thickness, and insertion status signals."""

    label = FormattedComponent(
        EpicsSignal,
        "{prefix}text{i}_in",
        write_pv="{prefix}text{i}_out",
        string=True,
        kind="config",
    )
    thickness = FormattedComponent(
        EpicsSignal,
        "{prefix}thickness{i}_in",
        write_pv="{prefix}thickness{i}_out",
        string=True,
        kind="config",
    )
    status = FormattedComponent(
        EpicsSignal, "{prefix}a{i}_in", write_pv="{prefix}a{i}_out"
    )

    def __init__(self, *args, slot=1, **kwargs):
        """Initialize the slot device and record the slot index for FormattedComponent substitution."""
        self.i = slot
        super().__init__(*args, **kwargs)


class HuberFilter(Device):
    """Six-slot Huber filter wheel device."""

    slot1 = Component(SlotDevice, "", slot=1)
    slot2 = Component(SlotDevice, "", slot=2)
    slot3 = Component(SlotDevice, "", slot=3)
    slot4 = Component(SlotDevice, "", slot=4)
    slot5 = Component(SlotDevice, "", slot=5)
    slot6 = Component(SlotDevice, "", slot=6)
