"""
X-Spectrum Lambda area detector

The Lambda IOC cannot write to the experiment file server, so the HDF5 files
are written to the IOC's local disk and moved afterwards. See
``IOCPathMixin`` for the folder layout.
"""

from pathlib import Path
from time import sleep
from time import time as ttime

from apstools.devices import CamMixin_V34
from ophyd import ADComponent
from ophyd import EpicsSignalRO
from ophyd import Staged
from ophyd.areadetector import CamBase
from ophyd.areadetector import DetectorBase
from ophyd.areadetector import EpicsSignalWithRBV

from .ad_mixins import ADTriggerStatus
from .ad_mixins import CodecPlugin
from .ad_mixins import IOCPathMixin
from .ad_mixins import MappedPathHDF5Plugin
from .ad_mixins import ProcessPlugin
from .ad_mixins import ROIPlugin
from .ad_mixins import StatsPlugin
from .ad_mixins import TriggerBase
from .counters_mixin import CountersMixin


class Trigger(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """

    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, delay=0.1, **kwargs):
        """
        Initialize Trigger with an optional image name and post-acquisition
        delay.
        """
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = "_".join([self.name, "image"])
        self._image_name = image_name
        self._flysetup = False
        self._status = None
        self._delay = delay

    def setup_manual_trigger(self):
        """Configure stage_sigs for single-image manual-trigger mode."""
        # Stage signals
        self.cam.stage_sigs["image_mode"] = "Single"
        # TriggerMode choices are driver specific, 0 is Internal.
        self.cam.stage_sigs["trigger_mode"] = 0
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"

    def setup_external_trigger(self):
        """Raise NotImplementedError; flyscans are not supported yet."""
        raise NotImplementedError(
            f"Cannot use external trigger with the {self.name} detector."
        )

    def stage(self):
        """
        Stop any acquisition, subscribe to the busy signal, and stage.
        """
        if self._flysetup:
            self.setup_external_trigger()

        # Make sure that detector is not acquiring.
        self._acquisition_signal.set(0).wait(timeout=10)
        self._acquire_busy_signal.subscribe(self._acquire_changed)

        super().stage()

    def unstage(self):
        """
        Unstage, stop acquisition, clear the busy subscription, and restore
        manual trigger.
        """
        super().unstage()
        self._acquisition_signal.set(0).wait(timeout=10)
        self._flysetup = False
        self._acquire_busy_signal.clear_sub(self._acquire_changed)
        self.setup_manual_trigger()

    def trigger(self):
        """
        Trigger one acquisition and return a status object that completes when
        acquire_busy drops.
        """
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        self._status = self._status_type(self)
        self._acquisition_signal.put(1, wait=False)
        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self.generate_datum(self._image_name, ttime(), {})

        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire_busy' signal changes."

        if self._status is None:
            return
        if (old_value != 0) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            sleep(self._delay)
            self._status.set_finished()
            self._status = None


class LambdaCam(CamMixin_V34, CamBase):
    """
    Support for the X-Spectrum Lambda detectors.

    https://x-spectrum.de/products/lambda/
    """

    _default_configuration_attrs = CamBase._default_configuration_attrs + (
        "serial_number",
        "firmware_version",
        "operating_mode",
        "energy_threshold",
        "dual_threshold",
        "wait_for_plugins",
    )

    serial_number = ADComponent(EpicsSignalRO, "SerialNumber_RBV")
    firmware_version = ADComponent(EpicsSignalRO, "FirmwareVersion_RBV")

    operating_mode = ADComponent(EpicsSignalWithRBV, "OperatingMode")
    energy_threshold = ADComponent(EpicsSignalWithRBV, "EnergyThreshold")
    dual_threshold = ADComponent(EpicsSignalWithRBV, "DualThreshold")


class LambdaDetector(Trigger, IOCPathMixin, CountersMixin, DetectorBase):
    """
    Lambda area detector with HDF5 file writing and statistics plugins.

    The HDF5 files are written under ``ioc_files_root/<experiment_name>`` on
    the IOC host and have to be moved to the experiment folder after the
    scan.
    """

    _default_configuration_attrs = (
        "cam",
        "roi1",
        "roi2",
        "roi3",
        "roi4",
        "codec",
    )
    _default_read_attrs = (
        "hdf1",
        "stats1",
        "stats2",
        "stats3",
        "stats4",
    )

    cam = ADComponent(LambdaCam, "cam1:")
    hdf1 = ADComponent(MappedPathHDF5Plugin, "HDF1:")

    roi1 = ADComponent(ROIPlugin, "ROI1:")
    roi2 = ADComponent(ROIPlugin, "ROI2:")
    roi3 = ADComponent(ROIPlugin, "ROI3:")
    roi4 = ADComponent(ROIPlugin, "ROI4:")

    stats1 = ADComponent(StatsPlugin, "Stats1:")
    stats2 = ADComponent(StatsPlugin, "Stats2:")
    stats3 = ADComponent(StatsPlugin, "Stats3:")
    stats4 = ADComponent(StatsPlugin, "Stats4:")

    codec = ADComponent(CodecPlugin, "Codec1:")
    proc = ADComponent(ProcessPlugin, "Proc1:")

    def __init__(
        self,
        *args,
        ioc_files_root=None,
        default_folder="",
        hdf1_name_template="%s/%s_%6.6d",
        hdf1_file_extension="h5",
        max_num_images=65535,
        **kwargs,
    ):
        """
        Initialize LambdaDetector with the IOC/bluesky folder mapping, HDF5
        file naming, and max image count.
        """
        self.ioc_files_root = ioc_files_root
        self.default_folder = default_folder
        self.hdf1_name_format = hdf1_name_template + "." + hdf1_file_extension
        self.max_num_images = max_num_images
        super().__init__(*args, **kwargs)

    _preset_monitor_attr = "cam.acquire_time"

    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.num_images.set(self.max_num_images).wait(timeout=10)
        self.cam.image_mode.set("Continuous").wait(timeout=10)
        self.preset_monitor.set(time).wait(timeout=10)
        self.cam.acquire.set(1).wait(timeout=10)

    def align_off(self):
        """Stop detector"""
        self.cam.acquire.set(0).wait(timeout=10)

    def save_images_on(self):
        """Enable HDF5 image saving."""
        self.hdf1.enable.set("Enable").wait(timeout=10)

    def save_images_off(self):
        """Disable HDF5 image saving."""
        self.hdf1.enable.set("Disable").wait(timeout=10)

    def auto_save_on(self):
        """Enable automatic HDF5 saving on each acquisition."""
        self.hdf1.autosave.put("on")

    def auto_save_off(self):
        """Disable automatic HDF5 saving on each acquisition."""
        self.hdf1.autosave.put("off")

    def default_settings(self):
        """Apply default detector settings and stage signal configuration."""
        self.cam.num_images.put(1)
        self.cam.image_mode.put("Single")
        self.cam.acquire.put(0)

        self.hdf1.file_template.put(self.hdf1_name_format)
        if self.default_write_folder:
            self.hdf1.file_path.put(self.default_write_folder)
        self.hdf1.num_capture.put(0)

        if "enable" in self.hdf1.stage_sigs.keys():
            self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
        self.hdf1.stage_sigs["capture"] = 1

        self.setup_manual_trigger()
        self.save_images_off()
        self.auto_save_off()
        self.plot_stats1()

        # Now that EPICS is connected, install the auto-kind subscriptions
        # on each StatsPlugin.
        for stats in (self.stats1, self.stats2, self.stats3, self.stats4):
            stats.start_auto_kind()

        self.hdf1.warmup_signals = [
            (self.hdf1.enable, 1),
            (self.hdf1.parent.cam.array_callbacks, 1),  # set by number
            (self.hdf1.parent.cam.image_mode, 0),  # Single, set by number
            (self.hdf1.parent.cam.trigger_mode, 0),  # Internal
            (self.hdf1.parent.cam.acquire_time, 0.01),
            (self.hdf1.parent.cam.acquire, 1),  # set by number
        ]

    def plot_select(self, stats):
        """
        Selects which stats will be plotted. All are being read.

        PARAMETERS
        ----------
        stats : iterable of ints
            List with the stats numbers to be plotted.
        """
        for i in range(1, 4 + 1):
            getattr(self, f"stats{i}").total.kind = (
                "hinted" if i in stats else "normal"
            )

    def plot_all(self):
        """Set all four stats channels to be plotted."""
        self.plot_select([1, 2, 3, 4])

    def plot_stats1(self):
        """Set only Stats1 total to be plotted."""
        self.plot_select([1])

    def plot_stats2(self):
        """Set only Stats2 total to be plotted."""
        self.plot_select([2])

    def plot_stats3(self):
        """Set only Stats3 total to be plotted."""
        self.plot_select([3])

    def plot_stats4(self):
        """Set only Stats4 total to be plotted."""
        self.plot_select([4])

    def setup_images(
        self, base_path, name_template, file_number, flyscan=False
    ):
        """
        Configure HDF5 folder, name, and number for the upcoming scan.

        The IOC writes to the folder mapped from ``base_path/<name>`` (see
        ``IOCPathMixin``); the returned paths are the final ones.
        """
        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.hdf1.file_name.set(name_template).wait(timeout=10)
        # Re-assert the template, an IOC restart may have changed it.
        self.hdf1.file_template.set(self.hdf1_name_format).wait(timeout=10)
        # Make sure the detector will save images
        self.auto_save_on()
        # Changes the stage_sigs to the external trigger mode
        self._flysetup = flyscan

        write_path = self.hdf1.set_write_folder(Path(base_path) / self.name)

        _, full_path, relative_path = self.hdf1.make_write_read_paths(
            write_path
        )

        return Path(full_path), Path(relative_path)

    @property
    def save_image_flag(self):
        """Return True if images will be saved on next acquisition."""
        _hdf1_auto = True if self.hdf1.autosave.get() == "on" else False
        _hdf1_on = True if self.hdf1.enable.get() == "Enable" else False
        return _hdf1_on or _hdf1_auto

    @property
    def label_option_map(self):
        """
        Return mapping of stats channel label names to their index numbers.
        """
        return {f"Stats{i} Total": i for i in range(1, 4 + 1)}

    @property
    def plot_options(self):
        """Return list of available channel names for plot selection."""
        return list(self.label_option_map.keys())

    def select_plot(self, channels):
        """Select which stats channels to plot by label name."""
        chans = [self.label_option_map[i] for i in channels]
        self.plot_select(chans)

    def field_for_label(self, label):
        """Return the ophyd field name for a plot-option label."""
        stats_index = self.label_option_map[label]
        return getattr(self, f"stats{stats_index}").total.name
