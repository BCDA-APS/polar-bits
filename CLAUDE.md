# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`polar-bits` is a [BITS](https://BCDA-APS.github.io/BITS/) (Bluesky Instrument for Synchrotron Science) instrument package for the POLAR beamline at APS (Argonne National Laboratory, sector 4-ID). It controls real hardware via EPICS PVs using the ophyd/bluesky framework.

## Environment Setup

```bash
conda create -y -n polar-bits python=3.11 hkl pyepics
conda activate polar-bits
pip install -e ".[dev]"
```

## Session Startup

In IPython or Jupyter:
```python
from id4_b.startup import *   # 4-ID-B station
# or
from id4_g.startup import *   # 4-ID-G station
# or
from id4_h.startup import *   # 4-ID-H station
# or
from id4_raman.startup import *  # Raman station
```

## QueueServer

```bash
# Start/restart the QS host process (runs in background screen session)
./src/id4_b_qserver/qs_host.sh restart

# Monitor the GUI client
queue-monitor &

# Other commands: start, stop, status, checkup, console, run
```

## Linting and Formatting

```bash
# Lint and auto-fix
ruff check --fix src/

# Format
ruff format src/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Architecture

### Package Structure

The repo contains multiple station packages plus a shared common package:

- `src/id4_common/` — shared devices, plans, callbacks, utils used by all stations
- `src/id4_b/` — 4-ID-B station (magnetic dichroism, soft X-ray)
- `src/id4_g/` — 4-ID-G station (diffraction)
- `src/id4_h/` — 4-ID-H station
- `src/id4_raman/` — Raman spectroscopy station
- `src/id4_{b,g,h,raman}_qserver/` — QueueServer configs per station

Each station package has:
- `startup.py` — session entry point; loads config, creates devices, imports plans
- `configs/iconfig_extras.yml` — station-specific config overrides (STATION name, MD_PATH, etc.)

### Configuration System

- `src/id4_common/configs/iconfig.yml` — master config (EPICS timeouts, data paths, feature flags, area detector settings)
- `src/id4_{station}/configs/iconfig_extras.yml` — per-station overrides merged via `update_config()`
- `src/id4_common/configs/devices.yml` — primary device list (all beamline devices)
- `src/id4_common/configs/devices_*.yml` — grouped device lists (core, 4idb, 4idg, 4idh, extras)

Devices are defined in YAML as `module.ClassName: [{name, prefix, labels, ...}]` entries. The `labels` field is critical — it groups devices for `oregistry.findall(label)` lookups. Station labels are: `"source"`, `"4ida"`, `"4idb"`, `"4idg"`, `"4idh"`. The `"baseline"` label marks devices recorded in the baseline stream.

### Device Registry (`oregistry`)

`oregistry` from `apsbits.core.instrument_init` is the central device registry. Use:
- `oregistry.find("device_name")` — find a single device by name
- `oregistry.findall("label")` — find all devices with a given label
- `oregistry.find("name", allow_none=True)` — returns None if not found (preferred in plans)

### Plans

All scan plans are in `src/id4_common/plans/local_scans.py` and exported via `src/id4_common/plans/__init__.py`. Key plans:

- `count(num, time, ...)` — repeated readings
- `ascan(motor, start, stop, ..., npts, time)` — absolute scan
- `lup(motor, start, stop, ..., npts, time)` — relative scan (returns to start)
- `grid_scan(...)` / `rel_grid_scan(...)` — 2D mesh scans
- `qxscan(edge_energy, time, ...)` — energy scan with fixed Δk steps
- `mv(device, value, ...)` / `mvr(device, delta, ...)` — move motors

All scan plans accept `dichro=True` (switches X-ray polarization using phase retarders), `lockin=True`, `fixq=True` (fixes HKL during scan), and `vortex_sgz=True` flags. These modify the inner step via decorators (`configure_counts_decorator`, `stage_dichro_decorator`, `extra_devices_decorator`, `stage_magnet911_decorator`).

The `LocalFlag` singleton (`flag`) stores scan-mode state (dichro, fixq, vortex_sgz, etc.) shared between plan functions.

Detectors are managed by the `counters` object (`id4_common/utils/counters_class.py`). Call `counters.plotselect(det_index, monitor_index)` to choose what to plot/monitor.

### Callbacks

- `nexus_data_file_writer.py` — writes NeXus/HDF5 master files; `nxwriter` is the callback instance
- `spec_data_file_writer.py` — writes SPEC-format data files
- `dichro_stream.py` — streaming callback for dichroism data reduction

### IPython Magics

Custom magics are registered from `LocalMagics` (extends `BlueskyMagics`):
- `%wm motor1 motor2` — where motors (position + limits)
- `%wa label` — where all devices for a label
- `%mov motor pos` / `%movr motor delta` — move motors

### Diffractometer

HKL calculations use `hklpy` (via `polartools_hklpy_imports.py`). The active diffractometer is tracked via `current_diffractometer()` from `id4_common/utils/hkl_utils.py`. Multiple diffractometer configurations exist: `huber_euler` (CradleDiffractometer), `huber_hp` (HPDiffractometer), with PSI engine variants.

### Experiment Metadata

The `experiment` object (`id4_common/utils/experiment_utils.py`) tracks ESAF, proposal, data paths, and DM (Data Management) workflow settings. Must call `experiment_setup()` before scanning.

### Data Management (DM)

APS Data Management integration via `aps_dm_setup()` at startup and `id4_common/plans/dm_plans.py`. The DM setup file is `/home/dm/etc/dm.setup.sh` on the beamline machines.
