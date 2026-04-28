"""
Lambda area detector
"""

import time as ttime
from pathlib import Path

from ophyd import ADComponent
from ophyd import BlueskyInterface
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd import Staged
from ophyd.areadetector import ADBase
from ophyd.areadetector import DetectorBase
from ophyd.areadetector import EpicsSignalWithRBV
from ophyd.areadetector.trigger_mixins import DeviceStatus

from .ad_mixins import PolarHDF5Plugin


class PositionStreamCam(ADBase):
    """
    ADBase subclass for position-stream cameras with acquire, counter, and
    callback signals.
    """

    _default_configuration_attrs = ADBase._default_configuration_attrs + (
        "port_name",
        "adcore_version",
        "array_callbacks",
        "wait_for_plugins",
    )

    # Shared among all cams and plugins
    port_name = ADComponent(EpicsSignalRO, "PortName_RBV", string=True)
    adcore_version = ADComponent(
        EpicsSignalRO, "ADCoreVersion_RBV", string=True
    )

    acquire = ADComponent(EpicsSignalWithRBV, "Acquire")
    acquire_busy = ADComponent(EpicsSignalRO, "AcquireBusy")
    acquire_time = ADComponent(Signal, value=0)  # Dummy
    array_counter = ADComponent(EpicsSignalWithRBV, "ArrayCounter")
    queued_arrays = ADComponent(EpicsSignalRO, "NumQueuedArrays")
    array_rate = ADComponent(EpicsSignalRO, "ArrayRate_RBV")
    array_callbacks = ADComponent(EpicsSignalWithRBV, "ArrayCallbacks")
    wait_for_plugins = ADComponent(EpicsSignal, "WaitForPlugins")

    nd_attributes_file = ADComponent(
        EpicsSignal, "NDAttributesFile", string=True
    )


class MySingleTrigger(BlueskyInterface):
    """
    BlueskyInterface mixin that triggers a single acquisition and waits for the
    busy signal.
    """

    _status_type = DeviceStatus

    def __init__(self, *args, image_name=None, delay_time=0.1, **kwargs):
        """
        Initialize MySingleTrigger with an optional image name and post-acquire
        delay.
        """
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = "_".join([self.name, "image"])
        self._image_name = image_name
        self._acquire_busy_pv = "cam.acquire_busy"
        self._acquire_pv = "cam.acquire"
        self._sleep_time = delay_time

    @property
    def _acquire(self):
        return getattr(self, self._acquire)

    @property
    def _acquire_busy(self):
        return getattr(self, self._acquire_busy)

    def stage(self):
        """
        Subscribe to acquire_busy changes and call the parent stage method.
        """
        self._acquire_busy.subscribe(self._acquire_changed)
        super().stage()

    def unstage(self):
        """Call parent unstage and unsubscribe the acquire_busy callback."""
        super().unstage()
        self._acquire_busy.clear_sub(self._acquire_changed)

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        self._status = self._status_type(self)
        self._acquire.put(1, wait=False)
        self.dispatch(self._image_name, ttime.time())
        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if (old_value != 0) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            ttime.sleep(self._sleep_time)
            self._status.set_finished()
            self._status = None


class PositionStreamDevice(MySingleTrigger, DetectorBase):
    """AreaDetector device for position-stream data with HDF5 file output."""

    _default_configuration_attrs = ("cam",)
    _default_read_attrs = ("hdf1",)

    cam = ADComponent(PositionStreamCam, "SG1:")
    hdf1 = ADComponent(PolarHDF5Plugin, "HDF1:")

    def __init__(
        self,
        *args,
        default_folder="",
        hdf1_name_template="%s/%s_%6.6d",
        hdf1_file_extension="h5",
        **kwargs,
    ):
        """
        Initialize PositionStreamDevice with default HDF5 folder and filename
        template.
        """
        self.default_folder = default_folder
        self.hdf1_name_format = hdf1_name_template + "." + hdf1_file_extension
        super().__init__(*args, **kwargs)

    @property
    def preset_monitor(self):
        """
        Return the dummy acquire_time signal used as a no-op preset monitor.
        """
        return self.cam.acquire_time

    def default_settings(self):
        """
        Set the HDF1 plugin warmup signal sequence for proper plugin
        initialization.
        """
        self.hdf1.warmup_signals = [
            (self.hdf1.enable, 1),
            (self.hdf1.parent.cam.array_callbacks, 1),  # set by number
            (self.hdf1.parent.cam.acquire, 1),  # set by number
            (self.hdf1.parent.cam.acquire, 0),  # set by number
        ]

    def setup_images(
        self, base_path, name_template, file_number, flyscan=False
    ):
        """
        Configure HDF1 file path, name, and number for an upcoming acquisition.
        """
        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.hdf1.file_name.set(name_template).wait(timeout=10)
        # Make sure eiger will save image
        # Changes the stage_sigs to the external trigger mode
        self._flysetup = flyscan

        base_path = str(base_path) + f"/{self.name}/"
        self.hdf1.file_path.set(base_path).wait(timeout=10)

        _, full_path, relative_path = self.hdf1.make_write_read_paths(base_path)

        return Path(full_path), Path(relative_path)

    @property
    def save_image_flag(self):
        """Return True if the HDF1 plugin is enabled or autosave is active."""
        _hdf1_auto = True if self.hdf1.autosave.get() == "on" else False
        _hdf1_on = True if self.hdf1.enable.get() == "Enable" else False
        return _hdf1_on or _hdf1_auto
