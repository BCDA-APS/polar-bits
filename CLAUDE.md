# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`polar-bits` is a Bluesky-based data acquisition instrument package for the POLAR beamline (4ID sector) at the Advanced Photon Source (APS). It is built on the [BITS (Bluesky Instrument Toolkit Structure)](https://BCDA-APS.github.io/BITS/) framework from the `apsbits` package.

## Development Setup

```bash
conda create -y -n polar-bits python=3.11 hkl pyepics
conda activate polar-bits
pip install -e ".[dev]"
```

## Commands

**Linting:**
```bash
pre-commit run --all-files
```

**Testing:**
```bash
pytest
pytest path/to/test_file.py::test_name  # single test
```

**QueueServer (per beamline):**
```bash
./src/id4_b_qserver/qs_host.sh restart   # start/restart
./src/id4_b_qserver/qs_host.sh status
queue-monitor &                           # GUI client
```

**Start interactive session (IPython):**
```bash
ipython
# then:
from id4_common.startup import *
```

## Architecture

### Multi-Beamline Structure

All beamlines share `id4_common` and have beamline-specific packages:

- `id4_common/` — shared devices, plans, callbacks, utils for all beamlines
- `id4_b/`, `id4_g/`, `id4_h/`, `id4_raman/` — beamline-specific overrides and startup
- `id4_{b,g,h,raman}_qserver/` — QueueServer configs and launch scripts per beamline
- `id4_common_qserver/` — shared QueueServer components

### Configuration System

Configuration is YAML-driven. The main file is `src/id4_common/configs/iconfig.yml`, which controls:
- RunEngine metadata (station, proposal, catalog)
- Enabled output formats (SPEC `.dat` files enabled by default, NeXus `.hdf` optional)
- APS Data Management (DM) integration paths
- Area detector defaults (Eiger 1M, Lambda, Vortex, LightField, Vimba)
- EPICS timeouts and logging paths

Device definitions live in YAML files under `src/id4_common/configs/`:
- `devices.yml` — main device list (all beamlines)
- `devices_4idb.yml`, `devices_4idg.yml`, `devices_4idh.yml` — beamline-specific additions
- `devices_basic.yml`, `devices_core.yml`, `devices_extras.yml` — grouped subsets

Each device entry maps a Python class path to EPICS PV prefixes and labels. Labels like `"4idb"`, `"baseline"`, `"detector"` are used to filter and organize devices at runtime.

### Startup Flow

`startup.py` orchestrates the session:
1. Load `iconfig.yml`
2. Set up APS DM integration (`aps_dm_setup`)
3. Initialize RunEngine (`RE`), databroker catalog (`cat`), BEC, and supplementary data streams
4. Conditionally load SPEC/NeXus callbacks based on `iconfig.yml`
5. Load dichro stream callback
6. Prompt user to load devices (calls `make_devices` which reads `devices.yml`)
7. Connect devices tagged with station labels (`source`, `4ida`, `4idb`, etc.)
8. Install shutter suspenders on the RunEngine

### Key Components in `id4_common/`

- **`devices/`** — 67 ophyd device classes (motors, area detectors, undulators, diffractometer, electromagnet, chopper, etc.)
- **`plans/`** — Bluesky scan plans: `local_scans.py` (lup, ascan, grid_scan), `dm_plans.py` (DM workflow submission), `center_maximum.py`, `flyscan_demo.py`
- **`callbacks/`** — `spec_data_file_writer.py`, `nexus_data_file_writer.py`, `dichro_stream.py`
- **`utils/`** — ~36 modules including HKL/crystallography utilities, DM integration, counters class, attenuator control, device loader (`device_loader.py`), experiment utilities, and `polartools`/`hklpy2` import wrappers
- **`suspenders/`** — shutter-based RunEngine suspenders for beamline safety

### Device Loading at Runtime

Devices can be dynamically managed:
```python
find_loadable_devices()       # list available devices
load_device("device_name")    # connect a specific device
remove_device("device_name")  # disconnect
reload_all_devices()          # reload all from YAML
```

The `oregistry` (from `apsbits`) is the central device registry.

### Data Output

- **SPEC files** (`.dat`): enabled by default in `iconfig.yml`; `newSpecFile()`, `spec_comment()` available in session
- **NeXus/HDF5** (`.hdf`): opt-in via `iconfig.yml`
- **Dichro stream**: circular dichroism data processing, always loaded

### QueueServer

Each beamline has a `qs-config.yml` and `qs_host.sh`. The QS uses Redis (localhost:6379) for communication and an IPython kernel backend. `startup.py` detects QueueServer context via `running_in_queueserver()` and adjusts imports accordingly (e.g., no interactive prompts, no shutter suspenders).

## Code Style

- Line length: 115 (black/flake8), 88 (ruff)
- Python 3.11+
- Linting: ruff (replaces flake8/isort/black in pre-commit)
- Docstrings required for all public classes/functions/methods/modules (ruff rules D100-D107)
