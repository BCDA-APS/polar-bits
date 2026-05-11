"""Centralized bluesky-session logging configuration for POLAR beamlines."""

import contextlib
import io
import logging
import os
import pathlib
import tempfile

import yaml

# Importing `apsbits.utils.logging_setup` triggers `apsbits/__init__.py`,
# which calls `configure_logging()` itself at module-init time.  That fires
# `%logstart` against `<cwd>/.logs/ipython_log.py` and adds a file handler
# to the same wrong location, before our own `setup_logging()` ever runs.
# Both are immediately replaced by the centralized override below, so
# silence the import-time print/log output here and tear down the stray
# handler in `setup_logging()`.
_silenced_init = io.StringIO()
with (
    contextlib.redirect_stdout(_silenced_init),
    contextlib.redirect_stderr(_silenced_init),
):
    from apsbits.utils.logging_setup import configure_logging

logger = logging.getLogger(__name__)

# iconfig.yml is the single source of truth — including the LOGGING block.
_ICONFIG = (
    pathlib.Path(__file__).resolve().parent.parent / "configs" / "iconfig.yml"
)

# Translation from POLAR-friendly keys (uppercase, in iconfig.yml's LOGGING
# block) to the apsbits `file_logs` schema.
_FILE_LOGS_KEY_MAP = {
    "MAX_BYTES": "maxBytes",
    "NUMBER_OF_PREVIOUS_BACKUPS": "backupCount",
}

# Filename for the IPython session log.  Override the apsbits default
# (`ipython_log.py`) so the file is clearly a log, not a runnable script.
_IPYTHON_LOG_FILENAME = "ipython_logs.log"

# Idempotency guard: every beamline's package `__init__.py` calls
# `setup_logging()` and they all transitively import id4_common (which also
# calls `setup_logging()`), so without this guard the IPython-logging
# settings block prints once per import.
_setup_done = False


def setup_logging():
    """
    Configure bluesky logging from the LOGGING block of iconfig.yml.

    The block is translated to the apsbits `file_logs`/`ipython_logs` schema
    on the fly (via a temporary YAML file passed to apsbits'
    ``configure_logging(extra_logging_configs_path=...)``) so polar-bits keeps
    a single config file.

    Falls back to the apsbits default directory (``<cwd>/.logs/``) when no
    LOG_PATH is configured or when the centralized directory cannot be
    created — typically a developer machine without access to the beamline
    filesystem.  The IPython log file always uses our filename
    (``ipython_logs.log``), regardless of which directory wins.

    Idempotent: subsequent calls are no-ops so importing several beamline
    packages (or importing one whose ``__init__.py`` chains through
    id4_common) doesn't re-run `%logstart` and re-print the settings block.
    """
    global _setup_done
    if _setup_done:
        return

    # Tear down handlers/loggers left over from the apsbits import-time
    # configure_logging() so file logs don't get written twice and the next
    # `%logstart` actually lands on our override path.
    _drop_apsbits_init_file_handlers()
    _stop_active_ipython_log()

    cfg = _read_iconfig_logging_block()
    log_path = cfg.get("LOG_PATH")

    if log_path:
        try:
            _apply_overrides(log_path=log_path, cfg=cfg)
        except (PermissionError, OSError) as exc:
            print(
                "POLAR centralized log directory unavailable "
                f"({exc}); falling back to <cwd>/.logs/."
            )
            # Tear down whatever partial handlers the failed run left behind
            # and try again with the apsbits default directory.
            _drop_apsbits_init_file_handlers()
            _stop_active_ipython_log()
            _apply_overrides(log_path=None, cfg=cfg)
    else:
        _apply_overrides(log_path=None, cfg=cfg)

    _setup_done = True


def _apply_overrides(log_path, cfg):
    """Run apsbits' configure_logging with the polar overrides applied."""
    overrides = _build_overrides(log_path=log_path, cfg=cfg)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False
    ) as fh:
        yaml.safe_dump(overrides, fh)
        tmp_path = fh.name

    try:
        configure_logging(extra_logging_configs_path=tmp_path)
    finally:
        os.unlink(tmp_path)


def _build_overrides(log_path, cfg):
    """Build the apsbits-shape override dict for one configure_logging run.

    The IPython filename override is always applied.  The directory override
    and any file_logs knobs (max bytes, backup count) are applied only when
    log_path is non-None.
    """
    ipython_logs = {"log_filename_base": _IPYTHON_LOG_FILENAME}
    file_logs = {}
    if log_path:
        ipython_logs["log_directory"] = log_path
        file_logs["log_directory"] = log_path
        for src_key, dst_key in _FILE_LOGS_KEY_MAP.items():
            if src_key in cfg:
                file_logs[dst_key] = cfg[src_key]

    overrides = {"ipython_logs": ipython_logs}
    if file_logs:
        overrides["file_logs"] = file_logs
    return overrides


def _read_iconfig_logging_block():
    """Return iconfig.yml's LOGGING block as a dict (empty if missing)."""
    if not _ICONFIG.exists():
        return {}
    with open(_ICONFIG) as f:
        iconfig = yaml.safe_load(f) or {}
    return iconfig.get("LOGGING") or {}


def _drop_apsbits_init_file_handlers():
    """Remove FileHandlers added by the apsbits import-time configure_logging."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)
            handler.close()


def _stop_active_ipython_log():
    """Stop any active IPython `%logstart` so the next one takes effect."""
    try:
        from IPython import get_ipython
    except ImportError:
        return
    ip = get_ipython()
    if ip is None:
        return
    if getattr(ip.logger, "log_active", False):
        ip.run_line_magic("logstop", "")
