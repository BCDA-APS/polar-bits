"""Offline tests for the Lambda, LightField, and Dante file path handling.

These IOCs cannot write to the experiment folder. They write to
``<ioc_files_root>/<experiment_name>/...`` and the files are moved
afterwards, so the folder seen by the IOC differs from the final one used by
bluesky. These tests use ophyd fake devices, no IOC needed.
"""

from pathlib import Path
from pathlib import PureWindowsPath

import pytest

pytest.importorskip("apstools.devices")

from id4_common.devices.ad_lambda import LambdaDetector  # noqa: E402
from id4_common.devices.ad_lightfield import LightFieldDetector  # noqa: E402
from id4_common.devices.vortex_dante_me1 import VortexDante1  # noqa: E402
from ophyd.areadetector.filestore_mixins import FileStoreBase  # noqa: E402
from ophyd.sim import make_fake_device  # noqa: E402

EXP_NAME = "smith"
BASE_PATH = Path("/gdata/dm/4ID/2026-3/smith/data")
EXP_PATH = BASE_PATH / "sample1"
RAMAN_ROOT = r"Z:\4idd\bluesky_images\raman"


@pytest.fixture(autouse=True)
def current_experiment(monkeypatch):
    """Pretend experiment_setup() ran for EXP_NAME at BASE_PATH."""
    from id4_common.utils.experiment_utils import experiment

    monkeypatch.setattr(experiment, "experiment_name", EXP_NAME)
    monkeypatch.setattr(experiment, "base_experiment_path", BASE_PATH)
    return experiment


@pytest.fixture
def lamb():
    """Fake Lambda writing below /extdisk/polar."""
    return make_fake_device(LambdaDetector)(
        "4idLambda:", name="lamb", ioc_files_root="/extdisk/polar"
    )


@pytest.fixture
def raman():
    """Fake LightField writing below the raman dserv share."""
    det = make_fake_device(LightFieldDetector)(
        "4LF1:", name="raman", ioc_files_root=RAMAN_ROOT
    )
    det.cam.file_template.sim_put("%s_%3.3d")
    return det


def test_posix_mapping_uses_experiment_name(lamb):
    """IOC folder is <root>/<experiment_name>/<path below the base>."""
    ioc = lamb.bluesky_to_ioc_path(EXP_PATH / "lamb")
    assert ioc == "/extdisk/polar/smith/sample1/lamb/"
    assert lamb.ioc_to_bluesky_path(ioc) == EXP_PATH / "lamb"


def test_windows_mapping_uses_experiment_name(raman):
    """Windows IOC folders use backslashes and map back to POSIX."""
    ioc = raman.bluesky_to_ioc_path(EXP_PATH)
    assert ioc == RAMAN_ROOT + r"\smith\sample1" + "\\"
    assert raman.ioc_to_bluesky_path(ioc) == EXP_PATH
    # Windows paths are case insensitive.
    assert raman.ioc_to_bluesky_path(ioc.lower()) == EXP_PATH


def test_folder_outside_experiment_raises(lamb):
    """Only folders of the current experiment can be mapped."""
    with pytest.raises(ValueError, match="experiment folder"):
        lamb.bluesky_to_ioc_path("/somewhere/else")
    with pytest.raises(ValueError, match="setup_images"):
        lamb.ioc_to_bluesky_path("/extdisk/polar/other_exp/sample1")


def test_experiment_not_setup_raises(lamb, current_experiment, monkeypatch):
    """Mapping needs experiment_setup() to have run."""
    monkeypatch.setattr(current_experiment, "experiment_name", None)
    with pytest.raises(ValueError, match="experiment_setup"):
        lamb.bluesky_to_ioc_path(EXP_PATH)


def test_direct_write_when_no_ioc_root(lamb):
    """Without ioc_files_root the IOC writes straight to the final path."""
    lamb.ioc_files_root = None
    assert lamb.bluesky_to_ioc_path(EXP_PATH) == str(EXP_PATH) + "/"
    assert lamb.ioc_to_bluesky_path(str(EXP_PATH)) == EXP_PATH


def test_default_write_folder(lamb):
    """Before a scan the IOC folder is the root, or default_folder."""
    assert lamb.default_write_folder == "/extdisk/polar"
    lamb.ioc_files_root = None
    lamb.default_folder = "/some/folder"
    assert lamb.default_write_folder == "/some/folder"


def test_lambda_setup_images(lamb):
    """setup_images writes to the IOC folder, returns the final path."""
    full, rel = lamb.setup_images(EXP_PATH, "scan", 12)

    hdf1 = lamb.hdf1
    assert hdf1.file_path.get() == "/extdisk/polar/smith/sample1/lamb/"
    # Create smith/sample1/lamb, but not the root itself.
    assert hdf1.create_directory.get() == -3
    assert hdf1.file_name.get() == "scan"
    assert hdf1.file_number.get() == 12
    assert hdf1.autosave.get() == "on"

    assert full == EXP_PATH / "lamb" / "scan_000012.h5"
    assert rel == Path("lamb/scan_000012.h5")
    assert (full, rel) == lamb.predict_save_path(EXP_PATH, "scan", 12)

    # At stage the folder comes from EPICS, the full path is still final.
    write, full2, _ = hdf1.make_write_read_paths()
    assert write == hdf1.file_path.get()
    assert Path(full2) == full


def test_lambda_resource_points_to_final_path(lamb):
    """Staging the HDF5 plugin registers the final (moved) file."""
    lamb.setup_images(EXP_PATH, "scan", 12)
    hdf1 = lamb.hdf1
    # As in default_settings() (the fake enable never finishes set(1)).
    hdf1.stage_sigs.pop("enable")
    hdf1.enable.sim_put("Enable")
    hdf1.plugin_type.sim_put("NDFileHDF5")
    hdf1.file_path_exists.sim_put(1)
    hdf1.file_write_mode.sim_put("Stream")
    for axis in ("height", "width"):  # pretend the plugin is primed
        getattr(hdf1.array_size, axis).sim_put(10)
    lamb.cam.num_images.sim_put(1)

    hdf1.stage()
    try:
        # The IOC folder was written back, not the final one.
        assert hdf1.file_path.get().startswith("/extdisk/polar/smith/")
        (name, resource), *_ = hdf1.collect_asset_docs()
        assert name == "resource"
        assert Path(resource["root"]) / resource["resource_path"] == (
            EXP_PATH / "lamb" / "scan_000012.h5"
        )
    finally:
        hdf1.unstage()


def test_lambda_flyscan_not_supported(lamb):
    """Lambda has no flyscan setup yet."""
    with pytest.raises(NotImplementedError):
        lamb.setup_external_trigger()


def test_lightfield_setup_images(raman):
    """SPE and HDF5 folders are mapped to the raman share."""
    full, rel = raman.setup_images(EXP_PATH, "scan", 7)

    win_exp = RAMAN_ROOT + r"\smith\sample1"
    assert raman.cam.file_path.get() == win_exp + r"\raman\scan_007" + "\\"
    assert raman.cam.file_number.get() == 1
    assert raman.cam.file_name_base.get() == "scan"

    hdf1 = raman.hdf1
    assert hdf1.file_path.get() == win_exp + r"\raman" + "\\"
    assert hdf1.create_directory.get() == -3
    assert hdf1.file_name.get() == "scan"
    assert hdf1.file_number.get() == 7

    assert full == EXP_PATH / "raman" / "scan_000007.h5"
    assert rel == Path("raman/scan_000007.h5")
    assert (full, rel) == raman.predict_save_path(EXP_PATH, "scan", 7)

    # The SPE file for the first point, at its final location.
    write, spe_full, spe_rel = raman.file.make_write_read_paths()
    assert PureWindowsPath(write).name == "scan_007"
    assert spe_full == EXP_PATH / "raman" / "scan_007" / "scan_001.spe"
    assert spe_rel == Path("scan_007/scan_001.spe")


def test_lightfield_datum_kwargs_not_shared(raman, monkeypatch):
    """The SPE datum must not modify the kwargs dict it was given."""
    seen = []
    monkeypatch.setattr(
        FileStoreBase,
        "generate_datum",
        lambda self, key, ts, kw: seen.append((key, kw)),
    )
    raman.cam.file_number.sim_put(3)
    shared = {}
    raman.file.generate_datum("raman_image", 0, shared)
    assert shared == {}
    assert seen == [("raman_image_spe", {"point_number": 3})]


def test_lightfield_module_has_no_device():
    """Importing the module must not create (and connect) a device."""
    import id4_common.devices.ad_lightfield as module

    assert not hasattr(module, "spectrometer")


def test_dante_setup_images():
    """Dante writes below the dpuser folder by default."""
    dante = make_fake_device(VortexDante1)("X:", name="vortex")
    # Written by default_settings() on connect.
    dante.hdf1.file_template.sim_put(dante.hdf1_file_format)
    full, rel = dante.setup_images(EXP_PATH, "scan", 5)

    assert dante.hdf1.file_path.get() == (
        "/local/home/dpuser/sector4/smith/sample1/vortex/"
    )
    assert full == EXP_PATH / "vortex" / "scan_000005.h5"
    assert rel == Path("vortex/scan_000005.h5")
    assert (full, rel) == dante.predict_save_path(EXP_PATH, "scan", 5)

    # With ioc_files_root=None the IOC writes to the final folder.
    dante.ioc_files_root = None
    dante.setup_images(EXP_PATH, "scan", 6)
    assert dante.hdf1.file_path.get() == str(EXP_PATH) + "/vortex/"
