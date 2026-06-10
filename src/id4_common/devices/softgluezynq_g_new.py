"""SoftGlueZynq implementation for ISN.

Coexists with :class:`id4_common.devices.softgluezynq_g.SoftGlueZynqDevice`.
Shares the SoftGlueSignal-based block library with
:mod:`id4_common.devices.softgluezynq_parts` — only the blocks that
``softgluezynq_parts`` does not provide (UpDown counter, pulse-train
generator, per-interferometer trackers, dual-RAM components, DAC1 mux,
threshold trigger) are defined locally.

Physical axis mapping (POLAR)
-----------------------------
* **Fast = X piezo**, driven by the ``mem`` / ``driveRAM`` channel via
  :meth:`snake_x` and :meth:`write_RAM_x`. DAC1 (``dac1_*``) is wired to
  this channel for manual / waveform mode switching.
* **Slow = Y piezo**, driven by the ``mem2`` / ``driveRAMx`` channel via
  :meth:`snake_y` and :meth:`write_RAM_y`. Advances one increment per
  fast-axis snake cycle via the ``driveRAMx_START / _INC / _END`` ramp.

The Python attribute names (``mem_x_*`` / ``ram_x_*`` for fast,
``mem_y_*`` / ``ram_y_*`` for slow) match the physical axes. The
underlying EPICS PV names (``SG:mem_*``, ``SG:mem2_*``,
``SG:driveRAM_*``, ``SG:driveRAMx_*``) are inherited from the IOC and
do *not* reflect the physical axis.
"""

from collections import OrderedDict
from logging import getLogger

import numpy as np
from bluesky.plan_stubs import mv
from bluesky.plan_stubs import sleep
from ophyd import Component
from ophyd import Device
from ophyd import DynamicDeviceComponent
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd.status import DeviceStatus
from ophyd.status import SubscriptionStatus

from .softgluezynq_parts import SGZDFF
from .softgluezynq_parts import SGZDevideByN
from .softgluezynq_parts import SGZDownCounter
from .softgluezynq_parts import SGZGateDly
from .softgluezynq_parts import SGZGates
from .softgluezynq_parts import SGZUpCounter
from .softgluezynq_parts import SoftGlueScalToStream
from .softgluezynq_parts import SoftGlueSignal
from .softgluezynq_parts import _buffer_fields
from .softgluezynq_parts import _dma_fields
from .softgluezynq_parts import _io_fields

logger = getLogger(__name__)


# ---------------------------------------------------------------------------
# Local blocks (no equivalent in softgluezynq_parts yet)
# ---------------------------------------------------------------------------


class UpDownCounter(Device):
    """SoftGlue up/down counter block with direction control."""

    enable = Component(SoftGlueSignal, "ENABLE", kind="config")
    clock = Component(SoftGlueSignal, "CLOCK", kind="config")
    clear = Component(SoftGlueSignal, "CLEAR", kind="config")
    updown = Component(SoftGlueSignal, "UPDOWN", kind="config")
    load = Component(SoftGlueSignal, "LOAD", kind="config")
    preset = Component(EpicsSignal, "PRESET", kind="config")
    counts = Component(EpicsSignalRO, "COUNTS", kind="config")


class PulseTrain(Device):
    """SoftGlue pulse-train generator (number of pulses, period, width)."""

    clock = Component(SoftGlueSignal, "Clk", kind="config")
    n = Component(EpicsSignal, "NPULSES", kind="config")
    period = Component(EpicsSignal, "PERIOD", kind="config")
    width = Component(EpicsSignal, "WIDTH", kind="config")


def _interferometer_tracker(if_tracker, num=6):
    """Return DDC definition for the ``if_tracker``-th tracker block."""
    defn = OrderedDict()
    for i in range(1, 1 + num):
        defn[f"if{i}"] = (
            EpicsSignal,
            f"SG:IF_tracker-{if_tracker}_IN{i}",
            {"kind": "normal"},
        )
    return defn


# ---------------------------------------------------------------------------
# Top-level device
# ---------------------------------------------------------------------------


class SoftGlueZynq(Device):
    """SoftGlueZynq FPGA timing device for ISN flyscans."""

    _status_type = DeviceStatus

    _default_read_attrs = (
        "if_tracker_1",
        "if_tracker_2",
        "if_tracker_3",
    )

    # Shared block library (from softgluezynq_parts).
    io = DynamicDeviceComponent(_io_fields())
    dma = DynamicDeviceComponent(_dma_fields())
    buffers = DynamicDeviceComponent(_buffer_fields())

    and_1 = Component(SGZGates, "SG:AND-1_", kind="config")
    or_1 = Component(SGZGates, "SG:OR-1_", kind="config")

    # 1 MHz clock
    div_by_n_1 = Component(SGZDevideByN, "SG:DivByN-1_", kind="config")
    div_by_n_2 = Component(SGZDevideByN, "SG:DivByN-2_", kind="config")
    # User clock
    div_by_n_3 = Component(SGZDevideByN, "SG:DivByN-3_", kind="config")
    div_by_n_4 = Component(SGZDevideByN, "SG:DivByN-4_", kind="config")

    # 1 MHz clock
    up_counter_1 = Component(SGZUpCounter, "SG:UpCntr-1_")
    # User clock
    up_counter_2 = Component(SGZUpCounter, "SG:UpCntr-2_")
    up_counter_3 = Component(SGZUpCounter, "SG:UpCntr-3_")
    up_counter_4 = Component(SGZUpCounter, "SG:UpCntr-4_")

    down_counter_1 = Component(SGZDownCounter, "SG:DnCntr-1_")

    up_down_counter_1 = Component(UpDownCounter, "SG:UpDnCntr-1_")
    up_down_counter_2 = Component(UpDownCounter, "SG:UpDnCntr-2_")

    gate_delay_1 = Component(SGZGateDly, "SG:GateDly-1_")

    pulse_train = Component(PulseTrain, "SG:plsTrn-1_")

    flip_flop_1 = Component(SGZDFF, "SG:DFF-1_")

    scal_to_stream_1 = Component(
        SoftGlueScalToStream, "SG:scalToStream-1_"
    )

    # Fast-axis RAM (X piezo): mem + driveRAM. DAC1 (mux/val/write/init)
    # is wired to this channel and is used to switch between RAM-driven
    # waveform mode and manual position writes.
    mem_x_address = Component(EpicsSignal, "SG:mem_ADDRA")
    mem_x_data = Component(EpicsSignal, "SG:mem_DINA")
    mem_x_clk = Component(EpicsSignal, "SG:mem_CLK_Signal")
    mem_x_write = Component(EpicsSignal, "SG:mem_WRT_Signal")
    mem_x_enable = Component(EpicsSignal, "SG:mem_EN_Signal")

    ram_x_enable = Component(EpicsSignal, "SG:driveRAM_en_Signal")
    ram_x_n = Component(EpicsSignal, "SG:driveRAM_N")

    # Slow-axis RAM (Y piezo): mem2 + driveRAMx. The START / INC / END
    # registers ramp the stored waveform across the full scan extent,
    # advancing one increment per fast-axis snake cycle.
    mem_y_address = Component(EpicsSignal, "SG:mem2_ADDRA")
    mem_y_data = Component(EpicsSignal, "SG:mem2_DINA")
    mem_y_clk = Component(EpicsSignal, "SG:mem2_CLK_Signal")
    mem_y_write = Component(EpicsSignal, "SG:mem2_WRT_Signal")

    ram_y_enable = Component(EpicsSignal, "SG:driveRAMx_en_Signal")
    ram_y_n = Component(EpicsSignal, "SG:driveRAMx_N")
    ram_y_start = Component(EpicsSignal, "SG:driveRAMx_START")
    ram_y_inc = Component(EpicsSignal, "SG:driveRAMx_INC")
    ram_y_end = Component(EpicsSignal, "SG:driveRAMx_END")
    # Scan-complete indicator: SoftGlue sets this to 1 when driveRAMx
    # finishes the full slow-axis ramp (i.e. the fly-scan is done).
    ram_y_done = Component(EpicsSignal, "SG:driveRAMx_done_BI")

    # DAC1 (fast-axis manual control).
    dac1_man = Component(EpicsSignal, "SG:mux32_SEL_Signal")
    dac1_val = Component(EpicsSignal, "SG:DAC1_VAL")
    dac1_write = Component(EpicsSignal, "SG:DAC_WRITE_Signal")
    dac1_init = Component(EpicsSignal, "SG:DAC_INIT_Signal")

    # Fast-axis threshold trigger.
    threshold_pos = Component(EpicsSignal, "SG:threshTrig-1_POSTHR")
    threshold_neg = Component(EpicsSignal, "SG:threshTrig-1_NEGTHR")

    if_tracker_1 = DynamicDeviceComponent(_interferometer_tracker(1))
    if_tracker_2 = DynamicDeviceComponent(_interferometer_tracker(2))
    if_tracker_3 = DynamicDeviceComponent(
        _interferometer_tracker(3, num=3)
    )

    # Detector output mapping (instance-overridable via __init__ kwarg
    # or devices.yml entry).
    det_keymap = None

    def __init__(self, *args, det_keymap=None, **kwargs):
        """Initialise SoftGlueZynq, optionally with a detector keymap.

        Parameters
        ----------
        det_keymap : dict, optional
            Mapping of detector name (uppercase) to SoftGlue FO channel
            number used by :meth:`enable_detector_trigger` to route the
            ``trigger`` signal to the correct output field. Configure
            per-instance via the ``det_keymap`` key in ``devices.yml``.
        """
        super().__init__(*args, **kwargs)
        if det_keymap is not None:
            self.det_keymap = dict(det_keymap)

    # ----- Plan stubs --------------------------------------------------

    def start(self):
        """Bluesky plan stub to assert the global enable buffer."""
        yield from mv(self.buffers.in4.signal, "1")

    def start_flyscan(self):
        """Arm DMA + assert the enable buffer; finish when flip-flop falls."""
        yield from mv(self.dma.enable, 1)
        yield from mv(self.dma.clear_button, 1)
        yield from mv(self.dma.clear_buffer, 1)
        yield from sleep(1)

        yield from mv(self.buffers.in4.signal, "1")
        yield from sleep(1)

        self._status = self._status_type(self)

        enable_out = self.flip_flop_1.out.bi.get()

        while enable_out == 1:
            enable_out = self.flip_flop_1.out.bi.get()

        self._status.set_finished()
        return self._status

    def prepare(self):
        """Arm and clear DMA in preparation for triggering."""
        self.dma.enable.set(1).wait()
        self.dma.clear_button.set(1).wait()
        self.dma.clear_buffer.set(1).wait()

    def trigger(self):
        """Issue a software trigger.

        Returns a ``SubscriptionStatus`` that completes on the rising
        edge (``0 -> 1``) of :attr:`ram_y_done`, the SoftGlue scan-
        complete indicator wired to ``4idgACQ:SG:driveRAMx_done``.
        """
        def check_done(*, old_value, value, **kwargs):
            return old_value == 0 and value == 1

        # Arm the subscription BEFORE the puts so we cannot miss the edge.
        status = SubscriptionStatus(self.ram_y_done, check_done)
        # set().wait() instead of put() so a silently-rejected CA write
        # raises here rather than stalling on the ram_y_done subscription.
        self.and_1.in2.signal.set("1").wait(timeout=10)
        self.buffers.in4.signal.set("1").wait(timeout=10)
        return status

    def stop_softglue(self):
        """Latch the OR-1 reset path and de-assert the enable buffer."""
        self.or_1.in2.signal.put("1!")
        self.buffers.in4.signal.set("0").wait()

    def pause_softglue(self):
        """Pause the AND-1 gate (in2 -> "0")."""
        # Renamed from ``pause`` so it does not shadow ``Device.pause``.
        self.and_1.in2.signal.set("0").wait()

    def resume_softglue(self):
        """Resume the AND-1 gate (in2 -> "1")."""
        # Renamed from ``resume`` so it does not shadow ``Device.resume``.
        self.and_1.in2.signal.set("1").wait()

    def reset(self):
        """Pulse buffer-1 twice to clear the ScalToStream-1 FIFO."""
        # Repeated on purpose to clear ScalToStream 1 FIFO CT.
        self.buffers.in1.signal.set("1!").wait()
        self.buffers.in1.signal.set("1!").wait()

    def reset_interferometers(self):
        """Bluesky plan stub to pulse buffer-2 (interferometer reset)."""
        yield from mv(self.buffers.in2.signal, "1!")

    def setup_gated_trigger(self, period_time, pulse_width, pulse_delay=0):
        """Configure div_by_n_3 and gate_delay_1 for a gated trigger."""
        yield from mv(
            self.div_by_n_3.n,
            1e7 * period_time,
            self.gate_delay_1.delay,
            1e7 * pulse_delay,
            self.gate_delay_1.width,
            1e7 * pulse_width,
        )

    def enable_waveform(self):
        """Switch the DAC1 mux to RAM-driven (fast axis) waveform mode.

        Only ``dac1_man`` (mux SEL) and ``dac1_write`` are touched.
        ``mem_x_enable`` is intentionally left alone — toggling it
        between scans clears the RAM-armed state on the POLAR IOC.
        """
        # ``memDrive`` matches POLAR_scan.py; 19-ID's name was
        # ``funcGenPulse``.
        yield from mv(
            self.dac1_man, "0",
            self.dac1_write, "memDrive",
        )

    def disable_waveform(self):
        """Switch the DAC1 mux back to manual (fast axis) control.

        Only the mux SEL signal (``dac1_man``, PV
        ``SG:mux32_SEL_Signal``) is toggled — ``mem_x_enable`` must
        stay asserted so the mem RAM remains armed for the next scan.
        """
        yield from mv(self.dac1_man, "1")

    def _write_ram(
        self, array, mem_addr, mem_data, mem_clk, mem_wrt, ram_en, ram_n
    ):
        """Plan-stub helper: write ``array`` into the given SoftGlue RAM.

        Sequence matches POLAR_scan.py: assert WRT and de-assert EN, pulse
        the clock once per (address, data) pair, then de-assert WRT,
        assert EN, write the length, and route the clock to ``memDrive``.
        """
        yield from mv(mem_wrt, "1", ram_en, "0")
        yield from sleep(0.001)

        for i, value in enumerate(array):
            mem_addr.put(i)
            mem_data.put(value)
            yield from sleep(0.001)
            yield from mv(mem_clk, "1!")
            yield from sleep(0.001)

        yield from mv(mem_wrt, "0", ram_en, "1")
        ram_n.put(len(array))
        yield from sleep(0.001)
        mem_clk.put("memDrive")

    def write_RAM_x(self, array):
        """Write ``array`` into the fast-axis (X piezo) RAM (driveRAM)."""
        yield from self._write_ram(
            array,
            self.mem_x_address,
            self.mem_x_data,
            self.mem_x_clk,
            self.mem_x_write,
            self.ram_x_enable,
            self.ram_x_n,
        )

    def write_RAM_y(self, array):
        """Write ``array`` into the slow-axis (Y piezo) RAM (driveRAMx)."""
        yield from self._write_ram(
            array,
            self.mem_y_address,
            self.mem_y_data,
            self.mem_y_clk,
            self.mem_y_write,
            self.ram_y_enable,
            self.ram_y_n,
        )

    def create_snake_bits(self, A=32767, F=0.9, npts=1000, offset=0):
        """Build a snake waveform (linear ramp joined to quarter-sines)."""
        # Take one half cycle of a sine wave, from -pi/2 to pi/2, and cut
        # it at the zero crossing. If the sine has amplitude 1, then the
        # slope at the zero crossing is 1. Move both parts of the sine
        # away from the origin along the line x = y. If we want the line
        # to be the fraction F of the total y extent A, and the y extent
        # of the line is L, then L = F*(L+1), which yields L = F/(1-F).
        L = F / (1.0 - F)

        # A is the user-specified amplitude of the entire function, so
        # the scale factor Sy is given by Sy*(L+1) = A.
        Sy = A / (L + 1.0)

        # The function is the line S*L joined to 1/4 of a sine function
        # with amplitude S from 0 to pi/2. Along x, the line extends over
        # L and the quarter-sine extends over pi/2. The total length in
        # equally spaced points along x is Sx * (L + pi/2) = npts/4.
        Sx = (npts / 4.0) / (L + np.pi / 2)
        arr1 = np.linspace(-np.pi / 2, 0, int(Sx * np.pi / 2))
        sinArr1 = Sy * np.sin(arr1)

        arr2 = np.linspace(-L, L, int(Sx * 2 * L))
        arr3 = np.linspace(0, np.pi / 2, int(Sx * np.pi / 2))
        sinArr3 = Sy * np.sin(arr3)

        # Assemble, skipping the first and last points of the line
        # because they're already in the quarter-sine functions.
        half = np.concatenate(
            [sinArr1 - Sy * L, Sy * arr2[1:-1], sinArr3 + Sy * L]
        )
        waveform = np.concatenate([half, np.flip(half, 0)])

        return waveform + offset

    def um_to_bits(self, position):
        """Convert a DAC offset (microns, 0..+40) to a DAC bit value.

        POLAR piezo / DAC calibration:

        * The PiezoJena modulation input is **summed** with the EPICS-
          driven setpoint:  ``piezo = nanox.setpoint + dac_offset``.
        * The SoftGlue DAC outputs 0..5 V, which the PiezoJena
          interprets as a 0..+40 um offset on top of the EPICS
          setpoint (0 V = 0 um added, 5 V = +40 um added).
        * The DAC's 0..32767 unsigned bit range maps linearly to
          0..5 V, and therefore to 0..+40 um offset at the piezo.

        ``position`` here is the **DAC offset in microns**, not an
        absolute piezo position. The same calibration is assumed for
        both DAC1 (fast X) and DAC2 (slow Y) channels.
        """
        if position < 0 or position > 40:
            raise RuntimeError(
                f"DAC offset must be in 0..+40 um (DAC 0..5 V → "
                f"0..+40 um). Got {position!r}."
            )

        # bits = position / 40 * 32767
        return int(position / 40 * 32767)

    def snake_x(self, x_min=0, x_max=32767, F=0.9, npts=1000):
        """Build a fast-axis (X piezo) snake waveform and load mem.

        ``x_min`` / ``x_max`` are raw DAC bit values; defaults span the
        full 16-bit unsigned range. The waveform shape (linear ramp
        joined to quarter sines, with snake reversal) matches
        ``snakeYoff`` in ``POLAR_scan.py``.
        """
        # TODO: allow reversed direction when max < min.
        amplitude = (x_max - x_min) / 2.0
        offset = (x_max + x_min) / 2.0

        snake_array = self.create_snake_bits(
            A=amplitude, F=F, npts=npts, offset=offset
        )
        yield from self.write_RAM_x(snake_array)

    def snake_y(self, F=0.9, dy=7.28156, npts=1000, y_start=0, y_end=100):
        """Build a slow-axis (Y piezo) step waveform and load mem2.

        Also configures ``driveRAMx_START`` / ``_INC`` / ``_END`` so the
        Y ramp covers ``[y_start, y_end]`` (DAC bit units) in steps of
        ``2*dy`` (one stored RAM period covers two line spacings ``dy``).
        Matches ``snakeX`` in ``POLAR_scan.py``.
        """
        # driveRAMx output = START + (cycle_counter * INC) + RAM_value.
        # The RAM waveform is a "step transition" centred on 0, so the
        # SLOW-AXIS STEP positions (the plateaus between transitions)
        # land at START, START + dy, START + 2*dy, ... — i.e. the
        # first slow-axis step sits exactly at START. So we want
        # START = y_start (not y_start - 1.5*dy as POLAR_scan.py had
        # it; that legacy offset shifts the first step below y_start).
        #
        # driveRAMx_START / _INC / _END are 16-bit integer registers —
        # the IOC truncates floats, so round and cast here to keep
        # ``mv``'s readback-wait happy.
        start_val = int(round(y_start))
        # Each stored RAM period covers two slow-axis steps (the
        # waveform is half + (dy + half) — two dy-wide transitions
        # stacked), so the counter advances by 2*dy per RAM cycle.
        inc_val = int(round(2.0 * dy))
        # Verilog uses strict less-than: ``if ((inVal + addVal) < endVal)``.
        end_val = int(round(y_end))

        yield from mv(
            self.ram_y_start, start_val,
            self.ram_y_inc, inc_val,
            self.ram_y_end, end_val,
        )

        # Build the step "transition" waveform: a half period made of
        # quarter-sine, flat, quarter-sine, then a second period offset
        # by dy.
        L = F / (1.0 - F)
        Sx = (npts / 4.0) / (L + np.pi / 2)

        arr1 = np.linspace(0, np.pi / 2, int(Sx * np.pi / 2))
        sinArr1 = (dy / 2.0) * (np.sin(arr1) - 1)

        arr2 = np.linspace(0, 0, int(Sx * 2 * L))

        arr3 = np.linspace(-np.pi / 2, 0, int(Sx * np.pi / 2))
        sinArr3 = (dy / 2.0) * (np.sin(arr3) + 1)

        half = np.concatenate([sinArr1, arr2[1:-1], sinArr3])
        waveform = np.concatenate([half, dy + half])

        yield from self.write_RAM_y(waveform)

    def move_x_analog(self, position):
        """Move the fast-axis (X piezo) to ``position`` um via DAC1.

        Uses manual DAC1 control: switches the mux away from RAM-drive,
        writes the bit value, and pulses the DAC write strobe. Microns
        are converted via :meth:`um_to_bits` (19-ID 0-90 um piezo
        calibration).
        """
        # TODO: confirm the sample piezo is in analog control mode.
        x_bits = self.um_to_bits(position)
        yield from self.disable_waveform()
        yield from mv(self.dac1_init, "1!")
        yield from mv(self.dac1_val, x_bits)
        yield from mv(self.dac1_write, "1!")

    def enable_detector_trigger(self, detector_name, det_keymap=None):
        """Route the SoftGlue ``trigger`` signal to ``detector_name``'s FO."""
        if det_keymap is None:
            det_keymap = self.det_keymap
            logger.debug(
                "Using default softglue detector key mapping: %s",
                det_keymap,
            )

        if not det_keymap:
            # No mapping configured: nothing to wire up. Set
            # ``self.det_keymap`` (or pass ``det_keymap=``) to enable
            # per-detector FO routing.
            logger.debug(
                "Softglue det_keymap is empty; skipping trigger wiring "
                "for %s.",
                detector_name,
            )
            return

        try:
            trigger_output = det_keymap[detector_name.upper()]
        except KeyError:
            logger.debug(
                "%s is not configured for TTL triggering.", detector_name
            )
            return
        output_field = getattr(self.io, f"fo{trigger_output}")
        output_field.signal.put("trigger")

    def clear_output_fields(self):
        """Clear the first eight SoftGlue output fields."""
        for i in range(1, 9):
            output_field = getattr(self.io, f"fo{i}")
            output_field.signal.put("0")
