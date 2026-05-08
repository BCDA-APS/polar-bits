"""Centralized bluesky-session logging configuration for POLAR beamlines."""

import logging
import os
import pathlib
import tempfile

import yaml
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


def setup_logging():
    """
    Configure bluesky logging from the LOGGING block of iconfig.yml.

    The block is translated to the apsbits `file_logs`/`ipython_logs` schema
    on the fly (via a temporary YAML file passed to apsbits'
    ``configure_logging(extra_logging_configs_path=...)``) so polar-bits keeps
    a single config file.

    Falls back to the apsbits default (``<cwd>/.logs/``) when no LOG_PATH is
    configured or when the centralized directory cannot be created — typically
    a developer machine without access to the beamline filesystem.
    """
    # `apsbits/__init__.py` calls `configure_logging()` itself at import
    # time (transitively triggered by the `from apsbits.utils.logging_setup
    # import configure_logging` above), which fires `%logstart` against the
    # apsbits default `<cwd>/.logs/ipython_log.py`.  IPython's `%logstart`
    # is idempotent, so when our own `configure_logging` re-runs with the
    # centralized override the second `%logstart` no-ops and the IPython
    # log stays on the wrong path.  Stop the existing logger first so the
    # next `%logstart` actually lands on the override.
    _stop_active_ipython_log()

    overrides = _build_overrides()
    if not overrides:
        configure_logging()
        return

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False
    ) as fh:
        yaml.safe_dump(overrides, fh)
        tmp_path = fh.name

    try:
        configure_logging(extra_logging_configs_path=tmp_path)
    except (PermissionError, OSError) as exc:
        print(
            "POLAR centralized log directory unavailable "
            f"({exc}); falling back to <cwd>/.logs/."
        )
        configure_logging()
    finally:
        os.unlink(tmp_path)


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


def _build_overrides():
    """Translate iconfig.yml's LOGGING block into the apsbits logging schema."""
    if not _ICONFIG.exists():
        return None

    with open(_ICONFIG) as f:
        iconfig = yaml.safe_load(f) or {}

    cfg = iconfig.get("LOGGING") or {}
    log_path = cfg.get("LOG_PATH")
    if not log_path:
        return None

    file_logs = {"log_directory": log_path}
    for src_key, dst_key in _FILE_LOGS_KEY_MAP.items():
        if src_key in cfg:
            file_logs[dst_key] = cfg[src_key]

    return {
        "file_logs": file_logs,
        "ipython_logs": {"log_directory": log_path},
    }
