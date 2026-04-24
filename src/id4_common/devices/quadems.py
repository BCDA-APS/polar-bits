"""
QuadEMs for POLAR
"""

from collections import OrderedDict

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO
from ophyd import QuadEM
from ophyd import Signal
from ophyd.quadem import QuadEMPort

from .ad_mixins import ImagePlugin
from .ad_mixins import StatsPlugin


class StatsPluginQuadEM(StatsPlugin):
    """StatsPlugin variant for QuadEM that disables auto-kind subscriptions."""

    # Remove subscriptions from StatsPlugin
    def __init__(self, *args, **kwargs):
        """
        Initialize and immediately stop auto-kind updates, setting kind to
        config.
        """
        super().__init__(*args, **kwargs)
        self.stop_auto_kind()
        self.kind = "config"


class QuadEMPOLAR(QuadEM):
    """
    QuadEM device with POLAR-specific statistics plugins and fast readback
    signals.
    """

    image = Component(ImagePlugin, "image1:")
    current1 = Component(StatsPluginQuadEM, "Current1:")
    current2 = Component(StatsPluginQuadEM, "Current2:")
    current3 = Component(StatsPluginQuadEM, "Current3:")
    current4 = Component(StatsPluginQuadEM, "Current4:")

    sum_all = Component(StatsPluginQuadEM, "SumAll:")

    # The way the QuadEM support computes things is a bit complicated, so
    # will expose main screen here eventhough it will be a duplicate of the
    # stats, and will leave the stats as config.

    sumall_mean = Component(EpicsSignalRO, "SumAll:MeanValue_RBV")
    sumall_fast = Component(EpicsSignalRO, "SumAllAve")
    sumall_sigma = Component(EpicsSignalRO, "SumAll:Sigma_RBV")

    sumx_mean = Component(EpicsSignalRO, "SumX:MeanValue_RBV")
    sumx_fast = Component(EpicsSignalRO, "SumXAve")
    sumx_sigma = Component(EpicsSignalRO, "SumX:Sigma_RBV")

    sumy_mean = Component(EpicsSignalRO, "SumY:MeanValue_RBV")
    sumy_fast = Component(EpicsSignalRO, "SumYAve")
    sumy_sigma = Component(EpicsSignalRO, "SumY:Sigma_RBV")

    diffx_mean = Component(EpicsSignalRO, "DiffX:MeanValue_RBV")
    diffx_fast = Component(EpicsSignalRO, "DiffXAve")
    diffx_sigma = Component(EpicsSignalRO, "DiffX:Sigma_RBV")

    diffy_mean = Component(EpicsSignalRO, "DiffY:MeanValue_RBV")
    diffy_fast = Component(EpicsSignalRO, "DiffYAve")
    diffy_sigma = Component(EpicsSignalRO, "DiffY:Sigma_RBV")

    posx_mean = Component(EpicsSignalRO, "PosX:MeanValue_RBV")
    posx_fast = Component(EpicsSignalRO, "PositionXAve")
    posx_sigma = Component(EpicsSignalRO, "PosX:Sigma_RBV")

    posy_mean = Component(EpicsSignalRO, "PosY:MeanValue_RBV")
    posy_fast = Component(EpicsSignalRO, "PositionYAve")
    posy_sigma = Component(EpicsSignalRO, "PosY:Sigma_RBV")

    @property
    def preset_monitor(self):
        """
        Return the averaging_time signal as the count-time preset for scan
        plans.
        """
        return self.averaging_time


class TetrAMM(QuadEMPOLAR):
    """QuadEMPOLAR subclass for the Sydor TetrAMM 4-channel electrometer."""

    conf = Component(QuadEMPort, port_name="TetrAMM")

    # TODO: If we ever want to trigger the TetrAMM, we need
    # to check if changes are needed to the trigger procedure.


class QuadEMRO_mixins(Device):
    """
    Mixin that replaces the QuadEM trigger/preset with a no-op for read-only
    use.
    """

    # Disables preset_monitor and trigger

    dummy = Component(Signal, value=0, kind="omitted")

    @property
    def preset_monitor(self):
        """Return a dummy signal so scan plans have a no-op preset target."""
        return self.dummy

    def trigger(self):
        """
        Immediately mark acquisition complete without driving the hardware.
        """
        self._status = self._status_type(self)
        self._status.set_finished()
        return self._status

    def stage(self):
        """Stage using base Device logic, bypassing QuadEM staging."""
        Device.stage(self)

    def unstage(self):
        """Unstage using base Device logic, bypassing QuadEM unstaging."""
        Device.unstage(self)


class SydorEMRO(QuadEMRO_mixins, QuadEMPOLAR):
    """Read-only Sydor T4U beam position monitor using the QuadEM framework."""

    conf = Component(QuadEMPort, port_name="T4U_BPM")

    # These are TetrAMM specific!
    num_channels = None
    read_format = None
    trigger_mode = None
    bias_interlock = None
    bias_state = None
    bias_voltage = None
    hvi_readback = None
    hvs_readback = None
    hvv_readback = None

    image = None

    def default_settings(self):
        """
        Set calibration and configuration signals to config kind and clear
        stage_sigs.
        """
        # Remove all these from read_attrs
        for item in (
            "conf",
            "current_names",
            "current_names.ch1",
            "current_names.ch2",
            "current_names.ch3",
            "current_names.ch4",
            "current_offsets",
            "current_offsets.ch1",
            "current_offsets.ch2",
            "current_offsets.ch3",
            "current_offsets.ch4",
            "current_offset_calcs",
            "current_offset_calcs.ch1",
            "current_offset_calcs.ch2",
            "current_offset_calcs.ch3",
            "current_offset_calcs.ch4",
            "current_scales",
            "current_scales.ch1",
            "current_scales.ch2",
            "current_scales.ch3",
            "current_scales.ch4",
            "position_offset_x",
            "position_offset_y",
            "position_offset_calc_x",
            "position_offset_calc_y",
            "position_scale_x",
            "position_scale_y",
        ):
            getattr(self, item).kind = "config"

        self.stage_sigs = OrderedDict()


class TetrAMMRO(QuadEMRO_mixins, TetrAMM):
    """
    Read-only TetrAMM 4-channel electrometer that disables staging and
    triggering.
    """

    def default_settings(self):
        """
        Set calibration and configuration signals to config kind and clear
        stage_sigs.
        """
        # Remove all these from read_attrs
        for item in (
            "conf",
            "current_names",
            "current_names.ch1",
            "current_names.ch2",
            "current_names.ch3",
            "current_names.ch4",
            "current_offsets",
            "current_offsets.ch1",
            "current_offsets.ch2",
            "current_offsets.ch3",
            "current_offsets.ch4",
            "current_offset_calcs",
            "current_offset_calcs.ch1",
            "current_offset_calcs.ch2",
            "current_offset_calcs.ch3",
            "current_offset_calcs.ch4",
            "current_scales",
            "current_scales.ch1",
            "current_scales.ch2",
            "current_scales.ch3",
            "current_scales.ch4",
            "position_offset_x",
            "position_offset_y",
            "position_offset_calc_x",
            "position_offset_calc_y",
            "position_scale_x",
            "position_scale_y",
        ):
            getattr(self, item).kind = "config"

        self.stage_sigs = OrderedDict()
