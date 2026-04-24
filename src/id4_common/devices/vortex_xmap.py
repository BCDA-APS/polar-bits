"""Vortex with DXP"""

from collections import OrderedDict

from ophyd import Component
from ophyd import Device
from ophyd import DynamicDeviceComponent
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import EpicsSignalWithRBV
from ophyd import SignalRO
from ophyd import Staged
from ophyd.mca import EpicsMCARecord
from ophyd.mca import SaturnDXP
from ophyd.status import DeviceStatus

MAX_ROIS = 32


class MyDXP(SaturnDXP):
    """
    SaturnDXP subclass that removes unused live_time_output and trigger_output
    components.
    """

    live_time_output = None
    trigger_output = None


class MyMCA(EpicsMCARecord):
    """
    EpicsMCARecord subclass that adds a check_acquiring signal for polling
    acquisition state.
    """

    check_acquiring = Component(
        EpicsSignal, ".ACQG", kind="omitted", string=False
    )


class SingleTrigger(Device):
    """
    This trigger mixin class takes one acquisition per trigger.
    Examples
    --------
    >>> class SimDetector(SingleTrigger):
    ...     pass
    >>> det = SimDetector('..pv..')
    # optionally, customize name of image
    >>> det = SimDetector('..pv..', image_name='fast_detector_image')
    """

    _status_type = DeviceStatus

    def __init__(self, *args, **kwargs):
        """
        Initialize SingleTrigger and wire the erase_start and status signals.
        """
        super().__init__(*args, **kwargs)
        self._acquisition_signal = self.erase_start
        self._status_signal = self.status

    def stage(self):
        """Subscribe the status-signal callback and delegate to parent stage."""
        self._status_signal.subscribe(self._acquire_changed)
        super().stage()

    def unstage(self):
        """
        Unsubscribe the status-signal callback and delegate to parent unstage.
        """
        super().unstage()
        self._status_signal.clear_sub(self._acquire_changed)

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if (old_value == 1) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            self._status.set_finished()
            self._status = None


class TotalCorrectedSignal(SignalRO):
    """Signal that returns the deadtime corrected total counts"""

    def __init__(self, prefix, roi_index=0, **kwargs):
        """
        Initialize TotalCorrectedSignal, storing the ROI index for deadtime-
        corrected summation.
        """
        self.roi_index = roi_index
        super().__init__(**kwargs)

    def get(self, **kwargs):
        """
        Return the sum of deadtime-corrected ROI counts across all XMAP
        channels.
        """
        value = 0
        for ch_num in range(1, 4 + 1):
            roi = getattr(self.root, f"mca{ch_num}.rois.roi{self.roi_index}")
            dxp = getattr(self.root, f"dxp{ch_num}")
            _ocr = dxp.output_count_rate.get(**kwargs)
            correction = (
                1.0 if _ocr == 0 else dxp.input_count_rate.get(**kwargs) / _ocr
            )
            value += roi.count.get(**kwargs) * correction
        return value


def _totals(attr_fix, id_range):
    defn = OrderedDict()
    for k in id_range:
        _kind = "normal" if k == 0 else "omitted"
        defn["{}{:d}".format(attr_fix, k)] = (
            TotalCorrectedSignal,
            "",
            {"roi_index": k, "kind": _kind},
        )
    return defn


class VortexXMAP(SingleTrigger):
    """Four-element Vortex detector driven by an XIA XMAP DXP controller."""

    # Buttons
    start = Component(EpicsSignal, "StartAll", kind="omitted")
    stop_ = Component(EpicsSignal, "StopAll", kind="omitted")
    erase_start = Component(EpicsSignal, "EraseStart", kind="omitted")
    erase = Component(EpicsSignal, "EraseAll", kind="omitted")

    # Status and configs
    status = Component(EpicsSignal, "Acquiring", kind="config")
    collection_mode = Component(EpicsSignal, "CollectMode", kind="config")
    preset_mode = Component(EpicsSignal, "PresetMode", kind="config")
    instant_deadtime = Component(EpicsSignalRO, "IDeadTime", kind="normal")
    average_deadtime = Component(EpicsSignalRO, "DeadTime", kind="normal")
    poll_time = Component(EpicsSignalWithRBV, "PollTime", kind="config")

    # Times
    real_preset = Component(EpicsSignal, "PresetReal", kind="config")
    live_preset = Component(EpicsSignal, "PresetLive", kind="config")
    real_elapsed = Component(EpicsSignal, "ElapsedReal", kind="normal")
    live_elapsed = Component(EpicsSignal, "ElapsedLive", kind="normal")

    events_preset = Component(EpicsSignal, "PresetEvents", kind="config")
    triggers_preset = Component(EpicsSignal, "PresetTriggers", kind="config")

    total = DynamicDeviceComponent(_totals("roi", range(MAX_ROIS)))

    # MCAs
    mca1 = Component(MyMCA, "mca1", kind="config")
    mca2 = Component(MyMCA, "mca2", kind="config")
    mca3 = Component(MyMCA, "mca3", kind="config")
    mca4 = Component(MyMCA, "mca4", kind="config")

    # DXPs
    dxp1 = Component(MyDXP, "dxp1:", kind="config")
    dxp2 = Component(MyDXP, "dxp2:", kind="config")
    dxp3 = Component(MyDXP, "dxp3:", kind="config")
    dxp4 = Component(MyDXP, "dxp4:", kind="config")

    _read_rois = [1]

    @property
    def preset_monitor(self):
        """Return the real_preset signal as the scan count-time control."""
        return self.real_preset

    def default_kinds(self):
        """
        Set default read/configuration attribute lists for MCA channels
        (placeholder).
        """
        # TODO: This is setting A LOT of stuff as "configuration_attrs", should
        # be revised at some point.

        # self.mca1.configuration_attrs += [
        #     item for item in self.mca1.component_names
        # ]

        # self.dxp.configuration_attrs += [
        #     item for item in self.dxp.component_names
        # ]

        self.mca1.read_attrs = [
            "preset_real_time",
            "preset_live_time",
            "elapsed_real_time",
            "elapsed_live_time",
            "rois.roi0",
            "rois.roi1",
        ]

    def default_settings(self):
        """
        Set default stage signals for erase-on-start and real-time preset mode.
        """
        self.stage_sigs["stop_"] = 1
        self.stage_sigs["erase"] = 1
        self.stage_sigs["preset_mode"] = "Real time"

    @property
    def read_rois(self):
        """
        Return the list of ROI indices that are currently included in reads.
        """
        return self._read_rois

    @read_rois.setter
    def read_rois(self, rois):
        """Set which ROI indices are read."""
        self._read_rois = list(rois)

    def select_roi(self, rois):
        """
        Set the hinted ROI totals to those in rois, keeping other read_rois as
        normal.
        """
        for i in range(MAX_ROIS):
            k = (
                "hinted"
                if i in rois
                else "normal"
                if i in self.read_rois
                else "omitted"
            )

            getattr(self.total, f"roi{i}").kind = k

            if k == "hinted" and i not in self.read_rois:
                self.read_rois.append(i)

    def plot_roi0(self):
        """Set ROI 0 as the hinted plot channel."""
        self.select_roi([0])

    def plot_roi1(self):
        """Set ROI 1 as the hinted plot channel."""
        self.select_roi([1])

    def plot_roi2(self):
        """Set ROI 2 as the hinted plot channel."""
        self.select_roi([2])

    def plot_roi3(self):
        """Set ROI 3 as the hinted plot channel."""
        self.select_roi([3])

    def plot_roi4(self):
        """Set ROI 4 as the hinted plot channel."""
        self.select_roi([4])

    @property
    def label_option_map(self):
        """
        Return a mapping from human-readable ROI label strings to ROI index
        integers.
        """
        return {f"ROI{i} Total": i for i in range(0, 8)}

    @property
    def plot_options(self):
        """Return all available ROI label strings for plot channel selection."""
        # Return all named scaler channels
        return list(self.label_option_map.keys())

    def select_plot(self, channels):
        """Select which ROI channels are plotted by label name."""
        chans = [self.label_option_map[i] for i in channels]
        self.select_roi(chans)
