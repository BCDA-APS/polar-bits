"""
SoftGlueZynq
"""

from collections import OrderedDict
from logging import getLogger

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

logger = getLogger(__name__)


def _dma_fields(num=8, first_letter="I"):
    defn = OrderedDict()
    defn["enable"] = (EpicsSignal, "1acquireDmaEnable", {"kind": "config"})
    defn["scan"] = (EpicsSignal, "1acquireDma.SCAN", {"kind": "config"})
    defn["read_button"] = (EpicsSignal, "1acquireDma.PROC", {"kind": "omitted"})
    defn["clear_button"] = (EpicsSignal, "1acquireDma.D", {"kind": "omitted"})
    defn["clear_buffer"] = (EpicsSignal, "1acquireDma.F", {"kind": "omitted"})
    defn["words_in_buffer"] = (
        EpicsSignalRO,
        "1acquireDma.VALJ",
        {"kind": "config"},
    )
    defn["events"] = (EpicsSignalRO, "1acquireDma.VALI", {"kind": "config"})
    for i in range(1, num + 1):
        defn[f"channel_{i}_name"] = (
            EpicsSignal,
            f"1s{i}name",
            {"kind": "config"},
        )
        defn[f"channel_{i}_scale"] = (
            EpicsSignal,
            f"1acquireDma.{chr(ord(first_letter) + i - 1)}",
            {"kind": "config"},
        )
    return defn


def _io_fields(num=16):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"fi{i}"] = (SoftGlueSignal, f"SG:FI{i}", {"kind": "config"})
        defn[f"fo{i}"] = (SoftGlueSignal, f"SG:FO{i}", {"kind": "config"})
    return defn


def _buffer_fields(num=4):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"in{i}"] = (
            SoftGlueSignal,
            f"SG:BUFFER-{i}_IN",
            {"kind": "config"},
        )
        defn[f"out{i}"] = (
            SoftGlueSignal,
            f"SG:BUFFER-{i}_OUT",
            {"kind": "config"},
        )
    return defn


class SoftGlueSignal(Device):
    """SoftGlue I/O signal device with signal and BI (binary-input) components."""

    signal = Component(EpicsSignal, "_Signal", kind="config")
    bi = Component(EpicsSignal, "_BI", kind="config")


class SGZDevideByN(Device):
    """SoftGlue divide-by-N frequency divider block."""

    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    reset = Component(SoftGlueSignal, "RESET", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")
    n = Component(EpicsSignal, "N", kind="config")


class SGZUpCounter(Device):
    """SoftGlue up-counter block that accumulates clock pulses while enabled."""

    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    reset = Component(SoftGlueSignal, "CLEAR", kind="config")
    counts = Component(EpicsSignalRO, "COUNTS", kind="config")


class SGZDownCounter(Device):
    """SoftGlue down-counter block that counts down from a preset value."""

    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    load = Component(SoftGlueSignal, "LOAD", kind="config")
    preset = Component(EpicsSignal, "PRESET", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZGateDly(Device):
    """SoftGlue gate-and-delay block that produces a programmable-width output pulse."""

    input = Component(SoftGlueSignal, "IN", kind="config")
    clock = Component(SoftGlueSignal, "CLK", kind="config")
    delay = Component(EpicsSignal, "DLY", kind="config")
    width = Component(EpicsSignal, "WIDTH", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZClocks(Device):
    """SoftGlue clock source block exposing 10/20/50 MHz and a variable-rate clock."""

    clock_10MHz = Component(SoftGlueSignal, "10MHZ_CLOCK", kind="config")
    clock_20MHz = Component(SoftGlueSignal, "20MHZ_CLOCK", kind="config")
    clock_50MHz = Component(SoftGlueSignal, "50MHZ_CLOCK", kind="config")
    clock_variable = Component(SoftGlueSignal, "VAR_CLOCK", kind="config")


class SGZGates(Device):
    """SoftGlue two-input gate (AND/OR) block."""

    in1 = Component(SoftGlueSignal, "IN1", kind="config")
    in2 = Component(SoftGlueSignal, "IN2", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZDFF(Device):
    """SoftGlue D flip-flop block with set, data, clock, clear, and output signals."""

    set_ = Component(SoftGlueSignal, "SET", kind="config")
    d = Component(SoftGlueSignal, "D", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    clear = Component(SoftGlueSignal, "CLEAR", kind="config")
    out = Component(SoftGlueSignal, "OUT", kind="config")


class SGZHistScal(Device):
    """SoftGlue histogram scaler block for time-resolved counting into histogram bins."""

    en = Component(SoftGlueSignal, "EN", kind="config")
    sync = Component(SoftGlueSignal, "SYNC", kind="config")
    det = Component(SoftGlueSignal, "DET", kind="config")
    det2 = Component(SoftGlueSignal, "DET2", kind="config")
    mode = Component(SoftGlueSignal, "MODE", kind="config")
    clock = Component(SoftGlueSignal, "CLK", kind="config")
    read_ = Component(SoftGlueSignal, "READ", kind="config")
    clear = Component(SoftGlueSignal, "CLEAR", kind="config")


class SGZhistScalerDma(Device):
    """SoftGlue DMA readout block for the histogram scaler data."""

    enable = Component(EpicsSignal, "Enable", kind="config")

    scan = Component(EpicsSignal, ".SCAN", kind="config", string=True)
    read_button = Component(EpicsSignal, ".PROC", kind="omitted")
    clear_button = Component(EpicsSignal, ".D", kind="omitted")

    debug = Component(EpicsSignal, ".H", kind="config")

    # TODO: maybe we can breakdown the histogram into channels here
    # already?
    hist = Component(EpicsSignalRO, ".VALA", kind="normal")


class SoftGlueScalToStream(Device):
    """SoftGlue scaler-to-DMA-stream block that serialises counter data for readout."""

    reset = Component(SoftGlueSignal, "RESET", kind="config")
    chadv = Component(SoftGlueSignal, "CHADV", kind="config")
    imtrig = Component(SoftGlueSignal, "IMTRIG", kind="config")
    flush = Component(SoftGlueSignal, "FLUSH", kind="config")
    full = Component(SoftGlueSignal, "FULL", kind="config")
    advdone = Component(SoftGlueSignal, "ADVDONE", kind="config")
    imdone = Component(SoftGlueSignal, "IMDONE", kind="config")
    fifo = Component(EpicsSignalRO, "FIFO", kind="config")
    dmawords = Component(EpicsSignal, "DMAWORDS", kind="config")


class SampleXY(Device):
    """SoftGlue sample-position device providing X/Y/pitch readbacks and offsets."""

    x_offset = Component(EpicsSignal, "SAMPLE_XOFF", kind="config")
    y_offset = Component(EpicsSignal, "SAMPLE_YOFF", kind="config")
    pitch_offset = Component(EpicsSignal, "SAMPLE_POFF", kind="config")

    x = Component(EpicsSignalRO, "SAMPLE_X")
    y = Component(EpicsSignalRO, "SAMPLE_Y")
    dx = Component(EpicsSignalRO, "SAMPLE_DX")
    pitch = Component(EpicsSignalRO, "SAMPLE_PITCH")
