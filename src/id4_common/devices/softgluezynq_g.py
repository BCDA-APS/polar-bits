"""
SoftGlueZynq
"""

from logging import getLogger

from bluesky.plan_stubs import mv
from ophyd import Component
from ophyd import Device
from ophyd import DynamicDeviceComponent
from ophyd import Signal

from .softgluezynq_parts import SampleXY
from .softgluezynq_parts import SGZClocks
from .softgluezynq_parts import SGZDevideByN
from .softgluezynq_parts import SGZGateDly
from .softgluezynq_parts import SGZUpCounter
from .softgluezynq_parts import SoftGlueScalToStream
from .softgluezynq_parts import _buffer_fields
from .softgluezynq_parts import _dma_fields
from .softgluezynq_parts import _io_fields

logger = getLogger(__name__)


class SoftGlueZynqDevice(Device):
    """
    SoftGlue Zynq FPGA timing device for 4IDG flyscans (counters, DMA, I/O).
    """

    preset_monitor = Component(Signal, value=0, kind="omitted")  # Dummy for API

    # DMA
    dma = DynamicDeviceComponent(_dma_fields())

    # Buffer fields
    buffers = DynamicDeviceComponent(_buffer_fields())

    # I/O fields
    io = DynamicDeviceComponent(_io_fields())

    # Using channel #4 to count when the gate is off.
    up_counter_count = Component(SGZUpCounter, "SG:UpCntr-1_", kind="config")
    up_counter_trigger = Component(SGZUpCounter, "SG:UpCntr-2_", kind="config")
    up_counter_gate_on = Component(SGZUpCounter, "SG:UpCntr-3_", kind="config")
    up_counter_gate_off = Component(SGZUpCounter, "SG:UpCntr-4_", kind="config")

    # Setup the frequency of the count and trigger based on 10 MHz clock.
    div_by_n_count = Component(SGZDevideByN, "SG:DivByN-1_", kind="config")
    div_by_n_trigger = Component(SGZDevideByN, "SG:DivByN-2_", kind="config")
    div_by_n_interrupt = Component(SGZDevideByN, "SG:DivByN-3_", kind="config")

    # Create a gate pulse
    gate_trigger = Component(SGZGateDly, "SG:GateDly-1_", kind="config")

    # Send data to DMA
    scaltostream = Component(
        SoftGlueScalToStream, "SG:scalToStream-1_", kind="config"
    )

    # Clocks
    clocks = Component(SGZClocks, "SG:", kind="config")
    clock_freq = Component(Signal, value=1e7, kind="config")

    # Sample position
    sample_pos = Component(SampleXY, "SG:")

    def __init__(
        self, *args, reset_sleep_time=0.2, reference_clock=1e7, **kwargs
    ):
        """
        Initialize SoftGlueZynqDevice with reset sleep duration and reference
        clock rate.
        """
        super().__init__(*args, **kwargs)
        self._reset_sleep_time = reset_sleep_time
        self._reference_clock = reference_clock

    def start_softglue(self):
        """Bluesky plan stub to assert the global enable buffer (in1 = '1')."""
        yield from mv(self.buffers.in1.signal, "1")

    def stop_softglue(self):
        """
        Bluesky plan stub to de-assert the global enable buffer (in1 = '0').
        """
        yield from mv(self.buffers.in1.signal, "0")

    def start_detectors(self):
        """
        Bluesky plan stub to assert the detector enable buffer (in2 = '1').
        """
        yield from mv(self.buffers.in2.signal, "1")

    def stop_detectors(self):
        """
        Bluesky plan stub to de-assert the detector enable buffer (in2 = '0').
        """
        yield from mv(self.buffers.in2.signal, "0")

    def reset_plan(self):
        """
        Bluesky plan stub to pulse the counter-reset and DMA-reset buffers.
        """
        yield from mv(
            self.buffers.in3.signal, "1!", self.buffers.in4.signal, "1!"
        )

    def clear_enable_dma(self):
        """
        Bluesky plan stub to clear the DMA buffer and then enable DMA
        acquisition.
        """
        yield from mv(self.dma.clear_button, 1, self.dma.clear_buffer, 1)
        yield from mv(self.dma.enable, 1)

    def clear_disable_dma(self):
        """
        Bluesky plan stub to clear the DMA buffer and then disable DMA
        acquisition.
        """
        yield from mv(self.dma.clear_button, 1, self.dma.clear_buffer, 1)
        yield from mv(self.dma.enable, 0)

    def setup_trigger_plan(
        self, period_time, pulse_width_time, pulse_delay_time=0
    ):
        """
        Bluesky plan stub to configure the trigger period, pulse width, and
        delay in clock ticks.
        """
        yield from mv(
            self.div_by_n_trigger.n,
            self._reference_clock * period_time,
            self.gate_trigger.delay,
            self._reference_clock * pulse_delay_time,
            self.gate_trigger.width,
            self._reference_clock * pulse_width_time,
        )

    def setup_count_plan(self, time):
        """
        Bluesky plan stub to set the count divider N for the given count time in
        seconds.
        """
        yield from mv(self.div_by_n_count.n, self._reference_clock * time)

    def default_settings(self, timeout=10):
        """
        Apply default FPGA settings (no-op for this class; subclasses override).
        """
        pass
