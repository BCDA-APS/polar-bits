"""Centralized bluesky-session logging configuration for POLAR beamlines."""

import contextlib
import io
import logging
import os
import pathlib
import shutil
import socket
import tempfile

import yaml

# Importing `apsbits.utils.logging_setup` triggers `apsbits/__init__.py`,
# which calls `configure_logging()` itself at module-init time.  That fires
# `%logstart` against `<cwd>/.logs/ipython_log.py` and adds a file handler
# to the same wrong location, before our own `setup_logging()` ever runs.
# Both are immediately replaced by the centralized override below, so
# silence the import-time print/log output here and tear down the stray
# handler in `setup_logging()`.
#
# apsbits resolves that wrong location to `<cwd>/.logs` (its package-root
# helper falls back to the cwd in an interactive session).  At the beamline
# the cwd is the read-only DM experiment directory (e.g.
# `/gdata/dm/4ID/<cycle>/`), so the import-time `os.makedirs()` raises
# `PermissionError` and aborts the whole import before we can redirect it.
# Run the import from a private temp dir so the throwaway `.logs` lands
# somewhere writable; `setup_logging()` removes the handler and the temp dir.
_silenced_init = io.StringIO()
_init_cwd = os.getcwd()
_init_tmp = tempfile.mkdtemp(prefix="polar-apsbits-init-")
with (
    contextlib.redirect_stdout(_silenced_init),
    contextlib.redirect_stderr(_silenced_init),
):
    try:
        os.chdir(_init_tmp)
    except OSError:
        pass
    try:
        from apsbits.utils.logging_setup import configure_logging
    finally:
        try:
            os.chdir(_init_cwd)
        except OSError:
            pass

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

# Filename stems for the session logs.  Each session gets its own file
# (``<stem>.<host>.<pid>.log``) so that concurrent sessions never rotate or
# delete the file another session holds open — a shared RotatingFileHandler on
# NFS produces "[Errno 116] Stale file handle" errors when one process rotates
# the file others have open.  The IPython stem also overrides the apsbits
# default (`ipython_log.py`) so the file reads as a log, not a runnable script.
_IPYTHON_LOG_STEM = "ipython_logs"
_FILE_LOG_STEM = "logging"

# Loggers whose DEBUG output floods the session log (and, once a file handle
# goes stale, floods the console with "Logging error" tracebacks).  pymongo's
# monitor thread emits a "Server heartbeat" DEBUG record every few seconds.
# Setting an explicit level here survives the root-logger DEBUG that startup
# applies later (an explicit child level wins over the root effective level).
_SILENCED_MODULES = {"pymongo": "warning"}

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
    filesystem.  Each session writes its own files
    (``logging.<host>.<pid>.log`` and ``ipython_logs.<host>.<pid>.log``),
    regardless of which directory wins, and pymongo is silenced to WARNING.

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
    # The throwaway `.logs` apsbits created during import (under the temp dir
    # used while importing) is now orphaned; remove the temp tree.
    shutil.rmtree(_init_tmp, ignore_errors=True)

    cfg = _read_iconfig_logging_block()
    log_path = cfg.get("LOG_PATH")

    if log_path:
        try:
            _apply_overrides(log_path=log_path, cfg=cfg)
        except (PermissionError, OSError) as exc:
            fallback = _fallback_log_dir()
            print(
                "POLAR centralized log directory unavailable "
                f"({exc}); falling back to {fallback}."
            )
            # Tear down whatever partial handlers the failed run left behind
            # and try again with a guaranteed-writable directory.
            _drop_apsbits_init_file_handlers()
            _stop_active_ipython_log()
            _apply_overrides(log_path=fallback, cfg=cfg)
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

    Per-session filenames and the pymongo silence are always applied.  The
    directory override and any file_logs knobs (max bytes, backup count) are
    applied only when log_path is non-None.
    """
    suffix = _session_suffix()
    ipython_logs = {"log_filename_base": f"{_IPYTHON_LOG_STEM}.{suffix}.log"}
    file_logs = {"log_filename_base": f"{_FILE_LOG_STEM}.{suffix}.log"}
    if log_path:
        ipython_logs["log_directory"] = log_path
        file_logs["log_directory"] = log_path
        for src_key, dst_key in _FILE_LOGS_KEY_MAP.items():
            if src_key in cfg:
                file_logs[dst_key] = cfg[src_key]

    return {
        "ipython_logs": ipython_logs,
        "file_logs": file_logs,
        "modules": dict(_SILENCED_MODULES),
    }


def _session_suffix():
    """Return a per-session filename suffix: ``<short-host>.<pid>``."""
    return f"{socket.gethostname().split('.')[0]}.{os.getpid()}"


def _fallback_log_dir():
    """Return a guaranteed-writable directory for logs.

    Prefer ``<cwd>/.logs`` (apsbits' historical default, convenient on a
    developer machine).  At the beamline the cwd is the read-only DM
    experiment directory, so when it isn't writable fall back to a private
    temp directory instead of letting ``os.makedirs`` raise PermissionError.
    """
    cwd = pathlib.Path.cwd()
    if os.access(cwd, os.W_OK):
        return str(cwd / ".logs")
    return tempfile.mkdtemp(prefix="polar-logs-")


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
