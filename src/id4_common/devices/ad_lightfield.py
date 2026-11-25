"""
LightField based area detector

The LightField IOC runs on Windows and cannot write to the experiment file
server, so both the SPE files (saved by LightField) and the HDF5 file are
written under ``ioc_files_root`` (e.g. a dserv share) and moved into the
experiment folder afterwards. See ``IOCPathMixin`` for the folder layout.
"""

from os.path import join
from pathlib import Path
from time import sleep
from time import time as ttime

from apstools.devices import CamMixin_V34
from ophyd import ADComponent
from ophyd import Device
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd import Staged
from ophyd.areadetector import DetectorBase
from ophyd.areadetector import EpicsSignal
from ophyd.areadetector import EpicsSignalWithRBV
from ophyd.areadetector import LightFieldDetectorCam
from ophyd.areadetector.filestore_mixins import FileStoreBase

from .ad_mixins import ADTriggerStatus
from .ad_mixins import ImagePlugin
from .ad_mixins import IOCPathMixin
from .ad_mixins import MappedPathHDF5Plugin
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
        # ImageMode 1 is "Preview" in LightField, 0 is "Normal".
        self.stage_sigs["cam.image_mode"] = 0

    def setup_manual_trigger(self):
        """Configure stage_sigs for manual-trigger mode."""
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"

    def setup_external_trigger(self):
        """Raise NotImplementedError; flyscans are not supported."""
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
        # LightField always saves the SPE file.
        timestamp = ttime()
        self.file.generate_datum(self._image_name, timestamp, {})
        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self.hdf1.generate_datum(self._image_name, timestamp, {})

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


class LightFieldFilePlugin(Device, FileStoreBase):
    """
    SPE files saved by LightField, one file per point.

    The file PVs are in the cam, the folder is mapped by the parent's
    ``IOCPathMixin``.
    """

    enable = ADComponent(Signal, value=True, kind="config")

    def __init__(self, *args, **kwargs):
        """
        Initialize LightFieldFilePlugin and set the POLAR SPE filestore spec.
        """
        self.filestore_spec = "AD_SPE_APSPolar"
        super().__init__(*args, write_path_template="", **kwargs)
        self.enable.subscribe(self._set_kind)

    def _set_kind(self, value, **kwargs):
        if value in (True, 1, "on", "enable"):
            self.kind = "normal"
        else:
            self.kind = "omitted"

    @property
    def base_name(self):
        """Return the base filename from the LightField camera."""
        return self.parent.cam.file_name_base.get()

    @base_name.setter
    def base_name(self, value):
        """Set the base filename on the LightField camera."""
        self.parent.cam.file_name_base.put(value)

    def make_write_read_paths(self, write_path=None):
        """
        Return the IOC folder, full SPE file path, and relative SPE file path.

        ``write_path`` is the IOC-side folder (defaults to the cam
        ``file_path``); the full path returned is the bluesky-side one.
        """
        if write_path is None:
            write_path = self.parent.cam.file_path.get(as_string=True)
        read_path = self.parent.ioc_to_bluesky_path(write_path)

        fname_template = (
            self.parent.cam.file_template.get(as_string=True) + ".spe"
        )
        fname_base = self.parent.cam.file_name_base.get()
        fname_number = self.parent.cam.file_number.get()
        fname = fname_template % (fname_base, fname_number)

        full_path = read_path / fname
        relative_path = Path(read_path.name) / fname

        return str(write_path), full_path, relative_path

    def stage(self):
        """
        Stage the file plugin, verifying the output file does not already exist.
        """
        _, full_path, _ = self.make_write_read_paths()

        # Only checks the final location, the IOC may not see it.
        if full_path.is_file():
            raise FileExistsError(
                f"The file {full_path} already exists! "
                "Please change the file name."
            )

        self._fn = str(full_path.parent)

        super().stage()

        ipf = int(self.parent.cam.num_images.get())

        fname_template = (
            self.parent.cam.file_template.get(as_string=True) + ".spe"
        )

        res_kwargs = {
            "template": join("%s", fname_template),
            "filename": self.parent.cam.file_name_base.get(),
            "frame_per_point": ipf,
        }
        self._generate_resource(res_kwargs)

    def generate_datum(self, key, timestamp, datum_kwargs):
        """Using the cam file_number to pick image from scan."""
        # Copy, the dict may be shared with other plugins.
        datum_kwargs = dict(datum_kwargs or {})
        datum_kwargs["point_number"] = int(self.parent.cam.file_number.get())
        return super().generate_datum(key + "_spe", timestamp, datum_kwargs)


class LightFieldCam(CamMixin_V34, LightFieldDetectorCam):
    """
    LightField camera with additional file naming and grating wavelength PVs.
    """

    file_name_base = ADComponent(EpicsSignal, "FileName", string=True)
    file_path = ADComponent(
        EpicsSignalWithRBV, "FilePath", string=True, kind="normal"
    )
    file_name = ADComponent(
        EpicsSignalRO, "LFFileName_RBV", string=True, kind="normal"
    )
    file_number = ADComponent(EpicsSignalWithRBV, "FileNumber")
    file_template = ADComponent(EpicsSignalWithRBV, "FileTemplate")
    num_images_counter = ADComponent(EpicsSignalRO, "NumImagesCounter_RBV")
    # The PV below works better as an EpicsSignal as it gets reported done after
    # the grating reached the target.
    grating_wavelength = ADComponent(EpicsSignal, "LFGratingWL")
    background_file = ADComponent(
        EpicsSignalWithRBV, "LFBackgroundFile", string=True
    )
    background_full_file = ADComponent(
        EpicsSignalRO, "LFBackgroundFullFile_RBV", string=True
    )
    background_path = ADComponent(
        EpicsSignalWithRBV, "LFBackgroundPath", string=True
    )


class LightFieldDetector(Trigger, IOCPathMixin, CountersMixin, DetectorBase):
    """
    Princeton Instruments LightField spectrometer detector with HDF5 and SPE
    file writing.

    Both files are written under ``ioc_files_root/<experiment_name>`` and
    have to be moved to the experiment folder after the scan.
    """

    _default_read_attrs = ("cam", "file", "hdf1")
    _default_configuration_attrs = ("cam", "image")

    cam = ADComponent(LightFieldCam, "cam1:")
    image = ADComponent(ImagePlugin, "image1:")
    hdf1 = ADComponent(MappedPathHDF5Plugin, "HDF1:")
    file = ADComponent(LightFieldFilePlugin, "cam1:")

    def __init__(
        self,
        *args,
        ioc_files_root=None,
        default_folder="",
        hdf1_name_template="%s/%s_%6.6d",
        hdf1_file_extension="h5",
        **kwargs,
    ):
        """
        Initialize LightFieldDetector with the IOC folder mapping and HDF5
        file naming.
        """
        self.ioc_files_root = ioc_files_root
        self.default_folder = default_folder
        self.hdf1_name_format = hdf1_name_template + "." + hdf1_file_extension
        super().__init__(*args, **kwargs)

    _preset_monitor_attr = "cam.acquire_time"

    @property
    def label_option_map(self) -> dict:
        """No selectable plot channels — LightField saves full spectra."""
        return {}

    @property
    def plot_options(self) -> list:
        """Return empty list — LightField has no selectable plot channels."""
        return []

    def select_plot(self, channels: list) -> None:
        """No-op — LightField has no selectable plot channels."""

    def field_for_label(self, label: str) -> str:
        """Return label unchanged — LightField has no channel mapping."""
        return label

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
        # TODO: confirm, kept from the previous setup.
        self.cam.trigger_mode.put(1)

        self.save_images_on()
        self.auto_save_on()

        self.hdf1.file_template.put(self.hdf1_name_format)
        if self.default_write_folder:
            self.hdf1.file_path.put(self.default_write_folder)
        self.hdf1.num_capture.put(0)

        if "enable" in self.hdf1.stage_sigs.keys():
            self.hdf1.stage_sigs.pop("enable")
        self.hdf1.stage_sigs["num_capture"] = 0
        self.hdf1.stage_sigs["capture"] = 1

        self.setup_manual_trigger()

        self.hdf1.warmup_signals = [
            (self.hdf1.enable, 1),
            (self.hdf1.parent.cam.array_callbacks, 1),  # set by number
            (self.hdf1.parent.cam.image_mode, 0),  # Normal, set by number
            (self.hdf1.parent.cam.trigger_mode, 1),
            (self.hdf1.parent.cam.acquire_time, 0.01),
            (self.hdf1.parent.cam.acquire, 1),  # set by number
        ]

    def setup_images(
        self, base_path, name_template, file_number, flyscan=False
    ):
        """
        Configure HDF5 and SPE folders and names for the upcoming scan.

        The IOC writes to the folders mapped from ``base_path/<name>`` (see
        ``IOCPathMixin``); the returned paths are the final HDF5 ones.
        """
        read_path = Path(base_path) / self.name

        # SPE has to be one file per point, so I'll put it in a new folder!
        # In the new folder, the file number will follow the point number.
        # LightField creates the folder.
        scan_folder = self.cam.file_template.get(as_string=True) % (
            name_template,
            file_number,
        )
        self.cam.file_path.set(
            self.bluesky_to_ioc_path(read_path / scan_folder)
        ).wait(timeout=10)
        self.cam.file_number.set(1).wait(timeout=10)
        self.cam.file_name_base.set(name_template).wait(timeout=10)

        # HDF1 is one file per scan
        self.hdf1.file_number.set(file_number).wait(timeout=10)
        self.hdf1.file_name.set(name_template).wait(timeout=10)
        # Re-assert the template, an IOC restart may have changed it.
        self.hdf1.file_template.set(self.hdf1_name_format).wait(timeout=10)
        write_path = self.hdf1.set_write_folder(read_path)

        # Changes the stage_sigs to the external trigger mode
        self._flysetup = flyscan

        self.auto_save_on()

        _, full_path, relative_path = self.hdf1.make_write_read_paths(
            write_path
        )

        return Path(full_path), Path(relative_path)

    @property
    def save_image_flag(self):
        """Return True; LightField detector always saves images."""
        return True  # Forced to always save images.
