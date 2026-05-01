"""Test fixtures and import-time mocks for polar-bits unit tests.

Many polar-bits modules import third-party packages (``dm``, ``apsbits``,
``apstools``, EPICS shims) at module load time. To run targeted unit
tests without those packages installed, this conftest stubs them out
before any test module imports the code under test. Tests that need
real behaviour from those packages should be skipped via the
``has_<pkg>`` fixtures defined here.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _ensure_module(name: str) -> types.ModuleType:
    """Insert an empty module into sys.modules if it isn't already there."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _stub_dm() -> None:
    """Provide minimal stubs for the ``dm`` package."""
    if "dm" in sys.modules and not isinstance(sys.modules["dm"], MagicMock):
        return
    dm = _ensure_module("dm")

    class DmException(Exception):
        pass

    class ObjectNotFound(DmException):
        pass

    class ObjectAlreadyExists(DmException):
        pass

    for attr in (
        "BssApsDbApi",
        "EsafApsDbApi",
        "ExperimentDsApi",
        "UserDsApi",
    ):
        setattr(dm, attr, MagicMock())

    dm.DmException = DmException
    dm.ObjectNotFound = ObjectNotFound
    dm.ObjectAlreadyExists = ObjectAlreadyExists


def _stub_apsbits() -> None:
    """Provide minimal stubs for the ``apsbits`` namespace."""
    apsbits = _ensure_module("apsbits")
    core = _ensure_module("apsbits.core")
    instrument_init = _ensure_module("apsbits.core.instrument_init")
    utils = _ensure_module("apsbits.utils")
    config_loaders = _ensure_module("apsbits.utils.config_loaders")
    helper_functions = _ensure_module("apsbits.utils.helper_functions")

    apsbits.core = core
    core.instrument_init = instrument_init
    apsbits.utils = utils
    utils.config_loaders = config_loaders
    utils.helper_functions = helper_functions

    instrument_init.oregistry = MagicMock(name="oregistry")
    instrument_init.init_instrument = MagicMock(name="init_instrument")
    instrument_init.make_devices = MagicMock(name="make_devices")

    _config: dict = {
        "DM_SETUP_FILE": "/tmp/fake_dm_setup",
        "DM_ROOT_PATH": "/tmp/dm_root",
        "DSERV_ROOT_PATH": "/tmp/dserv_root",
    }

    def _get_config():
        return _config

    config_loaders.get_config = _get_config
    config_loaders.load_config = MagicMock()
    config_loaders.load_config_yaml = MagicMock()
    config_loaders.update_config = MagicMock()

    helper_functions.register_bluesky_magics = MagicMock()
    helper_functions.running_in_queueserver = lambda: False

    logging_setup = _ensure_module("apsbits.utils.logging_setup")
    utils.logging_setup = logging_setup
    logging_setup.configure_logging = MagicMock()


def _stub_apstools() -> None:
    """Stub the apstools.utils symbols experiment_utils imports."""
    apstools = _ensure_module("apstools")
    utils = _ensure_module("apstools.utils")
    apstools.utils = utils
    utils.dm_get_experiment_datadir_active_daq = MagicMock(return_value=None)
    utils.dm_setup = MagicMock()
    utils.dm_start_daq = MagicMock()
    # Also stubbed because dm_utils transitively imports them.
    utils.dm_api_daq = MagicMock()
    utils.dm_api_ds = MagicMock()
    utils.dm_api_proc = MagicMock()
    aps_dm = _ensure_module("apstools.utils.aps_data_management")
    aps_dm.DEFAULT_UPLOAD_POLL_PERIOD = 1
    aps_dm.DEFAULT_UPLOAD_TIMEOUT = 60


def _stub_run_engine() -> None:
    """Stub id4_common.utils.run_engine with a minimal RE/cat."""
    mod = _ensure_module("id4_common.utils.run_engine")
    mod.RE = MagicMock(name="RE")
    mod.RE.md = {}
    mod.cat = MagicMock(name="cat")
    mod.bec = MagicMock()
    mod.peaks = MagicMock()
    mod.sd = MagicMock()
    mod.cat_legacy = MagicMock()


def _stub_specwriter() -> None:
    """Stub id4_common.callbacks.spec_data_file_writer.specwriter."""
    pkg = _ensure_module("id4_common.callbacks")
    mod = _ensure_module("id4_common.callbacks.spec_data_file_writer")
    pkg.spec_data_file_writer = mod
    sw = MagicMock(name="specwriter")
    sw.make_default_filename.return_value = "20260430-1200.dat"
    sw.spec_filename = MagicMock()
    sw.spec_filename.name = "fake.dat"
    mod.specwriter = sw


def _stub_dm_utils() -> None:
    """Stub the project's own dm_utils module before experiment_utils imports it."""
    mod = _ensure_module("id4_common.utils.dm_utils")
    mod.get_current_run = MagicMock(return_value={"name": "2026-2"})
    mod.get_current_run_name = MagicMock(return_value="2026-2")
    mod.get_esaf_info = MagicMock()
    mod.get_proposal_info = MagicMock()
    mod.get_experiment = MagicMock()
    mod.dm_experiment_setup = MagicMock()


def pytest_configure(config):
    """Install all import-time stubs before any test collection happens."""
    _stub_dm()
    _stub_apsbits()
    _stub_apstools()
    _stub_specwriter()
    _stub_run_engine()
    _stub_dm_utils()
