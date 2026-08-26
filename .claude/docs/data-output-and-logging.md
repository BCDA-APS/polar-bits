# Data Output, Logging, and Temperature Controllers

Read this when touching SPEC/NeXus file writing, session logging config, or
temperature-controller setup.

## Data Output

- **SPEC files** (`.dat`): enabled by default in `iconfig.yml`; `newSpecFile()`, `spec_comment()` available in session. The local writer (`id4_common.callbacks.apstools_spec_file_writer.SpecWriterCallback2`) collapses non-scalar metadata to one line via `_one_line()` and replaces array-valued scan args with a `<array len=N>` summary in the `#S` line so pymca can parse `qxscan` files.
- **NeXus/HDF5** (`.hdf`): opt-in via `iconfig.yml`
- **Dichro stream**: circular dichroism data processing, always loaded

## Logging

Bluesky session logs are configured by the `LOGGING` block of `iconfig.yml`,
not by apsbits' default `logging.yml`. `id4_common.utils.logging_helper.
setup_logging()` (called from each beamline's `__init__.py`) reads the block,
translates `LOG_PATH`/`MAX_BYTES`/`NUMBER_OF_PREVIOUS_BACKUPS` to the apsbits
`file_logs`/`ipython_logs` schema, writes a temp YAML, and passes it via
`configure_logging(extra_logging_configs_path=...)`. If the centralized log
directory cannot be created (developer machine without `/net/...` access)
the helper falls back to apsbits' default `<cwd>/.logs/`. Add a new
user-friendly key here by extending the `_FILE_LOGS_KEY_MAP` dict in
`logging_helper.py`.

Each session writes its **own** files in `LOG_PATH`
(`logging.<host>.<pid>.log` and `ipython_logs.<host>.<pid>.log`), not a shared
`logging.log`. Sharing one file across sessions is unsafe: apsbits uses a
`RotatingFileHandler` with `rotate_on_startup`, so on NFS a new (or rotating)
session renames the file others hold open, staling their handle and producing
repeating `OSError: [Errno 116] Stale file handle` tracebacks. Per-session
filenames keep each rotation self-contained. The helper also silences noisy
third-party loggers via the apsbits `modules` override — see `_SILENCED_MODULES`
in `logging_helper.py` (e.g. `pymongo`, whose monitor thread logs a heartbeat
every few seconds; the explicit level survives the `root`→`DEBUG` that startup
sets later). Add more noisy-at-DEBUG libraries there.

## Temperature Controllers

There are several temperature controllers across the four 4-ID stations
(LakeShore 336/340 at 4IDG, the 9-Tesla magnet's VTI sensors and needle
valve at 4IDH, …).  `id4_common.utils.temperature_setup.temperature_setup
(label)` picks one and binds three names into the session:

- ``tc`` — the **control** signal (movable, the loop setpoint)
- ``ts`` — the **sample** signal (readable, the readback)
- ``TEMPERATURE_CONTROLLER`` — the active label string

Once set, ``mv tc 295`` and ``RE(count(1, 1, detectors=[ts]))`` work; ``ts``
is added to ``sd.baseline`` by default so the sample temperature lands in
every scan.  ``te(temperature)`` in ``shorts.py`` is now a thin shortcut
over the active ``tc``.

Adding a new controller is a one-line edit to the ``TEMPERATURE_CONTROLLERS``
dict in ``id4_common/utils/temperature_setup.py`` — each row is
``label → (device_name, setpoint_attr_path, readback_attr_path)`` and the
dotted paths are resolved against ``oregistry.find(device_name)``.  No
device-class changes required.
