"""
Experiment session setup.

Public API
==========

.. autosummary::

    ~experiment
    ~experiment_setup
    ~experiment_change_sample
    ~experiment_load_from_bluesky
    ~experiment_resume
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import chdir
from pathlib import Path
from typing import Any
from typing import Callable

import yaml
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from apstools.utils import dm_get_experiment_datadir_active_daq
from apstools.utils import dm_setup
from apstools.utils import dm_start_daq
from dm import DmException
from dm import ObjectNotFound

from ..callbacks.spec_data_file_writer import specwriter
from .dm_utils import dm_experiment_setup as dm_create_experiment
from .dm_utils import get_current_run
from .dm_utils import get_current_run_name
from .dm_utils import get_esaf_info
from .dm_utils import get_experiment
from .dm_utils import get_proposal_info
from .run_engine import RE
from .run_engine import cat

__all__ = """
    experiment
    experiment_setup
    experiment_change_sample
    experiment_load_from_bluesky
    experiment_resume
""".split()

logger = getLogger(__name__)
logger.info(__file__)

PERSIST_FILENAME = ".polar_experiment.yml"
RESET_SCAN_ID_NOOP = -1  # sentinel: leave RE.md["scan_id"] untouched


def _servers() -> dict[str, Path]:
    """Lazy lookup of server roots from iconfig (avoids import-time crash)."""
    cfg = get_config()
    return {
        "data management": Path(cfg["DM_ROOT_PATH"]),
        "dserv": Path(cfg["DSERV_ROOT_PATH"]),
    }


def _dm_available() -> bool:
    """Return True iff DM env loads and a trivial query succeeds.

    Probes once per setup. Catches everything (DmException for known
    failures plus OSError/timeouts for transport problems) and logs a
    single warning on failure so the user knows why ESAF/proposal
    prompts were skipped.
    """
    try:
        dm_setup(get_config()["DM_SETUP_FILE"])
        get_current_run()
        return True
    except Exception as exc:  # noqa: BLE001 — explicitly any DM failure
        logger.warning("DM not reachable (%s); falling back to dserv.", exc)
        return False


def _get_dm_experiment():
    dm = oregistry.find("dm_experiment", allow_none=True)
    if dm is None:
        raise ValueError(
            "The dm_experiment device was not found. "
            "Please load and register it."
        )
    return dm


class ExperimentClass:
    """
    Drives interactive experiment setup, server/path resolution, and
    optional Data Management (DM) integration.

    The class accepts ``prompt`` and ``printer`` callables so it can be
    driven deterministically from tests; the module-level singleton
    ``experiment`` uses :func:`input` and :func:`print`.

    Attributes
    ----------
    esaf : dict | str | None
        Cached ESAF record (or ``"dev"`` for development runs).
    proposal : dict | str | None
        Cached proposal record (or ``"dev"``).
    server : str | None
        ``"data management"`` or ``"dserv"``.
    base_experiment_path : Path | None
        Server root + run + experiment_name.
    windows_base_experiment_path : Path | None
        Windows-mounted equivalent (only set when running on dserv).
    experiment_name : str | None
    sample : str | None
    file_base_name : str | None
    spec_file : str | None
    data_management : dict | None
        Cached DM experiment record when ``server == "data management"``.
    start_daq : bool
        If True, ``setup_dm_daq`` will start the DAQ. Off by default
        because the DAQ start changes file permissions and can prevent
        new files being written (TODO 2025-07-15).
    """

    start_daq: bool = False

    def __init__(
        self,
        *,
        prompt: Callable[[str], str] = input,
        printer: Callable[..., None] = print,
    ) -> None:
        self._prompt = prompt
        self._printer = printer

        self.esaf: dict | str | None = None
        self.proposal: dict | str | None = None
        self.server: str | None = None
        self.base_experiment_path: Path | None = None
        self.windows_base_experiment_path: Path | None = None
        self.experiment_name: str | None = None
        self.data_management: dict | None = None
        self.sample: str | None = None
        self.file_base_name: str | None = None
        self.spec_file: str | None = None
        self.dm_experiment = None  # set lazily inside setup() when DM is up

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def experiment_path(self) -> Path:
        """Linux-side experiment folder: ``base_experiment_path / sample``."""
        if None in (self.base_experiment_path, self.sample):
            raise ValueError(
                "The base folder or sample name are not defined. "
                "Please run experiment_setup()."
            )
        return Path(self.base_experiment_path) / self.sample

    @property
    def windows_experiment_path(self) -> Path | None:
        """Windows-mounted experiment folder, or None when DM owns the data."""
        if self.windows_base_experiment_path is None or self.sample is None:
            return None
        return Path(self.windows_base_experiment_path) / self.sample

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return a human-readable summary; no side effects."""
        if isinstance(self.proposal, dict):
            proposal_line = (
                f"Proposal #{self.proposal['id']} - {self.proposal['title']}"
            )
        else:
            proposal_line = "No proposal entered"

        if isinstance(self.esaf, dict):
            esaf_line = f"ESAF #{self.esaf['esafId']}"
        else:
            esaf_line = "No ESAF entered"

        try:
            current_path = self.experiment_path
        except ValueError:
            current_path = None

        last_id = RE.md.get("scan_id")
        next_id = last_id + 1 if isinstance(last_id, int) else None

        return (
            "\n-- Experiment setup --\n"
            f"{proposal_line}\n"
            f"{esaf_line}\n"
            f"Data server: {self.server}\n"
            f"Sample: {self.sample}\n"
            f"Experiment name: {self.experiment_name}\n"
            f"Base experiment folder: {self.base_experiment_path}\n"
            f"Current experiment folder: {current_path}\n"
            f"Spec file name: {self.spec_file}\n"
            f"Next Bluesky scan_id: {next_id}\n"
        )

    def __str__(self) -> str:
        return self.__repr__()

    # ------------------------------------------------------------------
    # User-input methods
    # ------------------------------------------------------------------

    def esaf_input(self, esaf_id: int | str | None = None) -> None:
        """Resolve the ESAF; accepts ``"dev"`` to skip DM lookup."""
        while True:
            esaf_id = esaf_id or self._prompt("Enter ESAF number: ") or None
            if esaf_id == "dev":
                self._printer("No ESAF will be associated to this experiment.")
                self.esaf = "dev"
                break
            if esaf_id is None:
                self._printer("An ESAF ID must be provided.")
                continue
            try:
                esaf_id = int(esaf_id)
            except ValueError:
                self._printer(
                    f"ESAF must be a number, but {esaf_id} was entered."
                )
                esaf_id = None
                continue
            try:
                self.esaf = dict(get_esaf_info(esaf_id))
                self._printer(f"ESAF #{self.esaf['esafId']} found.")
                break
            except ObjectNotFound:
                self._printer(
                    f"The ESAF #{esaf_id} was not found. If this appears "
                    "to be an error, you can cancel this setup and check "
                    "the `list_esafs` function, or use ESAF = dev."
                )
                esaf_id = None
            except DmException as exc:
                logger.warning(
                    "DM ESAF lookup failed (%s); marking ESAF as dev.", exc
                )
                self.esaf = "dev"
                break

        RE.md["esaf_id"] = str(esaf_id)

    def proposal_input(self, proposal_id: int | str | None = None) -> None:
        """Resolve the proposal; accepts ``"dev"`` to skip DM lookup."""
        while True:
            proposal_id = (
                proposal_id or self._prompt("Enter proposal number: ") or None
            )
            if proposal_id == "dev":
                self._printer(
                    "No proposal will be associated to this experiment."
                )
                self.proposal = "dev"
                break
            if proposal_id is None:
                self._printer("Proposal ID must be provided.")
                continue
            try:
                proposal_id = int(proposal_id)
            except ValueError:
                self._printer(
                    "The proposal number must be a number, but "
                    f"{proposal_id} was entered."
                )
                proposal_id = None
                continue
            try:
                self.proposal = dict(get_proposal_info(proposal_id))
                self._printer(
                    f"Proposal #{self.proposal['id']} found - "
                    f"{self.proposal['title']}."
                )
                break
            except DmException as exc:
                logger.warning(
                    "DM proposal lookup failed (%s); marking proposal as dev.",
                    exc,
                )
                self.proposal = "dev"
                break

        RE.md["proposal_id"] = str(proposal_id)

    def sample_input(self, sample: str | None = None) -> None:
        """Set the sample name (default ``"DefaultSample"``)."""
        self.sample = (
            sample
            or self._prompt("Enter sample name [DefaultSample]: ")
            or "DefaultSample"
        )
        RE.md["sample"] = self.sample

    def base_name_input(self, base_name: str | None = None) -> None:
        """Set the file base name."""
        guess = self.file_base_name or "scan"
        self.file_base_name = (
            base_name
            or self._prompt(f"Enter files base name [{guess}]: ")
            or guess
        )
        RE.md["base_name"] = self.file_base_name

    def server_input(self, server: str | None = None) -> None:
        """Pick the data server: ``"data management"`` or ``"dserv"``."""
        servers = _servers()
        options = str(tuple(servers.keys()))
        guess = self.server or list(servers.keys())[0]
        while True:
            self.server = (
                server
                or self._prompt(
                    f"Which data server will be used? options - {options} "
                    f"[{guess}]: "
                )
                or guess
            )
            if self.server.strip().lower() not in servers:
                self._printer(f"Answer must be one of {options}")
                server = None
            else:
                self.server = self.server.strip().lower()
                break
        RE.md["server"] = self.server

    def experiment_name_input(self, experiment_name: str | None = None) -> None:
        """Set (or prompt for) the DM experiment name."""
        guess = self.experiment_name or None
        while True:
            self.experiment_name = experiment_name = (
                experiment_name
                or self._prompt(f"Enter experiment name ({guess}): ")
                or guess
            )
            if experiment_name is None:
                self._printer("An experiment name must be entered.")
            else:
                break
        RE.md["experiment_name"] = self.experiment_name

    def scan_number_input(
        self, reset_scan_id: int | None = RESET_SCAN_ID_NOOP
    ) -> None:
        """Set ``RE.md["scan_id"]`` to the *last completed* scan number.

        Semantics:
        - ``reset_scan_id`` is a non-negative int → write that value.
          Next scan = value + 1.
        - ``-1`` (default sentinel) → leave ``RE.md["scan_id"]`` alone.
          Used by ``load_from_bluesky``.
        - ``None`` → interactive prompt (default ``no``).
        - any other int → log a warning and leave it alone.
        """
        if reset_scan_id is None:
            while True:
                answer = (
                    self._prompt("Reset last scan_id to 0? [no]: ")
                    .strip()
                    .lower()
                    or "no"
                )
                if answer not in ("yes", "no"):
                    self._printer("Answer must be yes or no.")
                    continue
                if answer == "yes":
                    RE.md["scan_id"] = 0
                break
        elif isinstance(reset_scan_id, int):
            if reset_scan_id >= 0:
                RE.md["scan_id"] = reset_scan_id
            elif reset_scan_id == RESET_SCAN_ID_NOOP:
                pass  # explicit no-op
            else:
                logger.warning(
                    "Ignoring invalid reset_scan_id=%s; next scan = %s.",
                    reset_scan_id,
                    RE.md.get("scan_id", 0) + 1,
                )
        else:
            logger.warning(
                "Ignoring non-int reset_scan_id=%r; next scan = %s.",
                reset_scan_id,
                RE.md.get("scan_id", 0) + 1,
            )

    # ------------------------------------------------------------------
    # DM helpers (only called when DM is reachable AND requested)
    # ------------------------------------------------------------------

    def dm_experiment_setup(self, experiment_name: str) -> bool:
        """Configure (or look up + reuse) the DM experiment.

        Returns False if the user wants to pick a different name. On any
        DM error, demotes to ``server="dserv"`` and returns True so the
        caller continues without DM.
        """
        try:
            existing = get_experiment(experiment_name)
            while True:
                reuse = (
                    self._prompt(
                        f"The experiment name '{existing['name']}' already "
                        "exists. Do you want to re-use this experiment? "
                        "[no]: "
                    )
                    .lower()
                    .strip()
                    or "no"
                )
                if reuse not in ("yes", "no"):
                    self._printer("Answer must be yes or no.")
                    continue
                break
            if reuse == "no":
                return False
            new_record = existing
        except ObjectNotFound:
            while True:
                create = (
                    self._prompt(
                        f"\tExperiment {experiment_name} does not exist in "
                        "DM. Do you want to create a new experiment? "
                        "[yes]: "
                    )
                    .lower()
                    .strip()
                    or "yes"
                )
                if create not in ("yes", "no"):
                    self._printer("\tAnswer must be yes or no.")
                    continue
                break
            if create == "no":
                self._printer(
                    "\tData management will not be used. Switching to dserv."
                )
                self.data_management = None
                self.server = "dserv"
                return True
            esaf_id = (
                self.esaf["esafId"] if isinstance(self.esaf, dict) else None
            )
            try:
                new_record, _ = dm_create_experiment(
                    experiment_name, esaf_id=esaf_id
                )
            except DmException as exc:
                logger.warning(
                    "DM experiment creation failed (%s); falling back to "
                    "dserv.",
                    exc,
                )
                self.data_management = None
                self.server = "dserv"
                return True
        except DmException as exc:
            logger.warning(
                "DM experiment lookup failed (%s); falling back to dserv.",
                exc,
            )
            self.data_management = None
            self.server = "dserv"
            return True

        if self.server == "data management":
            self.data_management = dict(new_record)
            if self.dm_experiment is not None:
                self.dm_experiment.put(self.experiment_name)
        return True

    def setup_dm_daq(self) -> None:
        """
        Optionally start the DM voyager DAQ for this experiment.

        Disabled by default (``start_daq=False``) because starting the
        DAQ changes file permissions and prevents new files being
        written (TODO 2025-07-15). Enable per-class instance via
        ``experiment.start_daq = True``.

        Wrapped in try/except so a transient DM failure here does not
        abort the whole setup — we log a warning and demote to no-DM
        mode.
        """
        if not self.start_daq:
            logger.info(
                "DM DAQ start is disabled (experiment.start_daq=False)."
            )
            return

        try:
            cfg = get_config()
            data_directory = f"@sojourner:{self.base_experiment_path}"
            dm_setup(cfg["DM_SETUP_FILE"])
            if (
                dm_get_experiment_datadir_active_daq(
                    self.experiment_name, data_directory
                )
                is None
            ):
                logger.info(
                    "Starting DM voyager DAQ: experiment %r",
                    self.experiment_name,
                )
                dm_start_daq(self.experiment_name, "@sojourner")
        except Exception as exc:  # noqa: BLE001
            logger.warning("DM DAQ skipped (%s); continuing without DM.", exc)
            self.data_management = None

    # ------------------------------------------------------------------
    # Path / file helpers
    # ------------------------------------------------------------------

    def setup_path(self) -> None:
        """Make sure the experiment folder exists; chdir into it."""
        if not self.experiment_path.is_dir():
            self.experiment_path.mkdir(parents=True)
        self._printer(
            f"Moving to the sample folder: {self.base_experiment_path}"
        )
        chdir(self.base_experiment_path)

    def start_specwriter(self) -> None:
        """Open a new SPEC file for the current sample."""
        suffix = specwriter.make_default_filename()
        fname = self.experiment_path / f"{self.sample}_{suffix}"
        specwriter.newfile(fname)
        self.spec_file = specwriter.spec_filename.name

    # ------------------------------------------------------------------
    # YAML persistence (Tier 4.1)
    # ------------------------------------------------------------------

    def _persist_path(self) -> Path | None:
        if self.base_experiment_path is None:
            return None
        return Path(self.base_experiment_path) / PERSIST_FILENAME

    def save_params_to_yaml(self) -> None:
        """Write a minimal snapshot of current state to the experiment dir.

        Best-effort — any write error is logged and swallowed so failure
        here never aborts a setup.
        """
        path = self._persist_path()
        if path is None:
            return

        def _id(value: Any, key: str) -> Any:
            if isinstance(value, dict):
                return value.get(key)
            return value  # already an int, "dev", or None

        snapshot = {
            "esaf_id": _id(self.esaf, "esafId"),
            "proposal_id": _id(self.proposal, "id"),
            "server": self.server,
            "experiment_name": self.experiment_name,
            "sample": self.sample,
            "file_base_name": self.file_base_name,
            "base_experiment_path": str(self.base_experiment_path)
            if self.base_experiment_path is not None
            else None,
            "last_scan_id": RE.md.get("scan_id"),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            with path.open("w") as fp:
                yaml.safe_dump(snapshot, fp)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "Could not save experiment state to %s: %s", path, exc
            )

    def load_params_from_yaml(self, path: str | Path) -> dict | None:
        """Load a previously-saved snapshot. Returns the parsed dict or None."""
        path = Path(path)
        if path.is_dir():
            path = path / PERSIST_FILENAME
        if not path.is_file():
            logger.warning("No saved experiment state at %s.", path)
            return None
        try:
            with path.open() as fp:
                return yaml.safe_load(fp)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("Could not load %s: %s", path, exc)
            return None

    def resume(self, path: str | Path) -> None:
        """Restore an experiment from a saved YAML snapshot.

        Does NOT contact DM. Use this when DM is down or you want to
        pick up a previous session quickly. The next scan continues
        numbering from ``last_scan_id``.
        """
        snapshot = self.load_params_from_yaml(path)
        if snapshot is None:
            return

        self.esaf = snapshot.get("esaf_id")
        self.proposal = snapshot.get("proposal_id")
        self.server = snapshot.get("server")
        self.experiment_name = snapshot.get("experiment_name")
        self.sample = snapshot.get("sample")
        self.file_base_name = snapshot.get("file_base_name")
        self.base_experiment_path = (
            Path(snapshot["base_experiment_path"])
            if snapshot.get("base_experiment_path")
            else None
        )

        for key in (
            "esaf_id",
            "proposal_id",
            "server",
            "experiment_name",
            "sample",
            "base_name",
        ):
            value = snapshot.get({"base_name": "file_base_name"}.get(key, key))
            if value is not None:
                RE.md[key] = str(value) if key.endswith("_id") else value

        last_scan = snapshot.get("last_scan_id")
        if isinstance(last_scan, int) and last_scan >= 0:
            RE.md["scan_id"] = last_scan
        else:
            RE.md.setdefault("scan_id", 0)

        if self.base_experiment_path is not None and self.sample is not None:
            self.setup_path()
            self.start_specwriter()

        self._printer(self.__repr__())

    # ------------------------------------------------------------------
    # Bluesky catalog round-trip
    # ------------------------------------------------------------------

    def load_from_bluesky(
        self,
        scan_id: int = -1,
        reset_scan_id: int = RESET_SCAN_ID_NOOP,
        useRE: bool = False,
    ) -> None:
        """Restore experiment state from a previous Bluesky run document."""
        metadata = RE.md if useRE else cat[scan_id].metadata["start"]

        kwargs = {}
        for key in (
            "esaf_id",
            "proposal_id",
            "base_name",
            "sample",
            "server",
            "experiment_name",
        ):
            if key in metadata:
                kwargs[key] = metadata[key]

        # Restore scan_id from the loaded run so numbering continues
        # from where it left off (1.1).
        loaded_scan_id = metadata.get("scan_id")
        if isinstance(loaded_scan_id, int) and loaded_scan_id >= 0:
            reset_scan_id = loaded_scan_id

        self.setup(reset_scan_id=reset_scan_id, **kwargs)

    # ------------------------------------------------------------------
    # Top-level setup / change_sample
    # ------------------------------------------------------------------

    def _resolve_base_path(self) -> None:
        """Set ``base_experiment_path`` based on ``self.server``."""
        if self.server == "data management" and self.data_management:
            self.base_experiment_path = Path(
                self.data_management["dataDirectory"]
            )
            # Windows can't see DM-mounted data.
            self.windows_base_experiment_path = None
        else:
            servers = _servers()
            self.base_experiment_path = (
                servers[self.server]
                / get_current_run_name()
                / self.experiment_name
            )
            # Windows variant (if a DSERV_WINDOWS_ROOT_PATH is configured).
            cfg = get_config()
            win_root = cfg.get("DSERV_WINDOWS_ROOT_PATH")
            if win_root and self.server == "dserv":
                self.windows_base_experiment_path = (
                    Path(win_root)
                    / get_current_run_name()
                    / self.experiment_name
                )
            else:
                self.windows_base_experiment_path = None

    def setup(
        self,
        esaf_id: int | str | None = None,
        proposal_id: int | str | None = None,
        base_name: str | None = None,
        sample: str | None = None,
        server: str | None = None,
        experiment_name: str | None = None,
        reset_scan_id: int | None = RESET_SCAN_ID_NOOP,
    ) -> None:
        """Run the full experiment setup.

        DM availability is auto-detected. When DM is unreachable, the
        ESAF/proposal prompts are skipped, ``server`` is forced to
        ``"dserv"``, and metadata is stamped as ``"dev"``. To force
        bypass even when DM is up, pass ``server="dserv"`` or use
        ``esaf_id="dev"``/``proposal_id="dev"``.
        """
        dm_ok = _dm_available()

        if dm_ok:
            try:
                self.dm_experiment = _get_dm_experiment()
            except ValueError as exc:
                logger.warning(
                    "%s — falling back to dserv (no dm_experiment device).",
                    exc,
                )
                dm_ok = False

        if dm_ok:
            self.esaf_input(esaf_id)
            self.proposal_input(proposal_id)
            self.server_input(server)
        else:
            self.esaf = "dev"
            self.proposal = "dev"
            self.server = "dserv"
            RE.md["esaf_id"] = "dev"
            RE.md["proposal_id"] = "dev"
            RE.md["server"] = "dserv"

        # If we still want DM, resolve the experiment name (which may
        # need to differ from the input name to avoid DM collisions).
        while True:
            self.experiment_name_input(experiment_name)
            if self.server == "data management":
                if not self.dm_experiment_setup(self.experiment_name):
                    experiment_name = None
                    continue
            break

        self._resolve_base_path()
        if self.server == "data management":
            self.setup_dm_daq()

        self.sample_input(sample)
        self.setup_path()
        self.base_name_input(base_name)
        self.scan_number_input(reset_scan_id)

        # Always make sure scan_id is at least defined (1.1).
        RE.md.setdefault("scan_id", 0)

        self.start_specwriter()
        self.save_params_to_yaml()

        self._printer(self.__repr__())

    def change_sample(
        self,
        sample_name: str | None = None,
        base_name: str | None = None,
        reset_scan_id: int | None = RESET_SCAN_ID_NOOP,
    ) -> None:
        """Switch sample, refresh paths, and start a new SPEC file."""
        self.sample_input(sample_name)
        self.setup_path()
        self.scan_number_input(reset_scan_id)
        self.base_name_input(base_name)
        self.start_specwriter()
        self.save_params_to_yaml()

    def __call__(
        self,
        esaf_id: int | str | None = None,
        proposal_id: int | str | None = None,
        base_name: str | None = None,
        sample: str | None = None,
        server: str | None = None,
        experiment_name: str | None = None,
        reset_scan_id: int | None = RESET_SCAN_ID_NOOP,
    ) -> None:
        """Shortcut for :meth:`setup`."""
        self.setup(
            esaf_id=esaf_id,
            proposal_id=proposal_id,
            base_name=base_name,
            sample=sample,
            server=server,
            experiment_name=experiment_name,
            reset_scan_id=reset_scan_id,
        )


experiment = ExperimentClass()


def experiment_setup(
    esaf_id: int | str | None = None,
    proposal_id: int | str | None = None,
    base_name: str | None = None,
    sample: str | None = None,
    server: str | None = None,
    experiment_name: str | None = None,
    reset_scan_id: int | None = RESET_SCAN_ID_NOOP,
) -> None:
    """Run the full experiment setup (delegates to ``experiment.setup``)."""
    experiment.setup(
        esaf_id=esaf_id,
        proposal_id=proposal_id,
        base_name=base_name,
        sample=sample,
        server=server,
        experiment_name=experiment_name,
        reset_scan_id=reset_scan_id,
    )


def experiment_change_sample(
    sample_name: str | None = None,
    base_name: str | None = None,
    reset_scan_id: int | None = RESET_SCAN_ID_NOOP,
) -> None:
    """Switch sample (delegates to ``experiment.change_sample``)."""
    experiment.change_sample(
        sample_name=sample_name,
        base_name=base_name,
        reset_scan_id=reset_scan_id,
    )


def experiment_load_from_bluesky(
    reset_scan_id: int = RESET_SCAN_ID_NOOP,
) -> None:
    """Restore experiment state from a previous Bluesky run."""
    experiment.load_from_bluesky(reset_scan_id=reset_scan_id)


def experiment_resume(path: str | Path) -> None:
    """Restore experiment state from a saved YAML snapshot."""
    experiment.resume(path)
