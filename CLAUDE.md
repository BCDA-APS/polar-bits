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
# Combined session (prompts to load all stations' devices):
from id4_common.startup import *
# Or per-beamline (loads only that station's devices, no prompt):
from id4_b.startup import *      # 4IDB
from id4_g.startup import *      # 4IDG
from id4_h.startup import *      # 4IDH
from id4_raman.startup import *  # Raman
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

Device definitions live in `src/id4_common/configs/devices.yml` — the single source of truth for all beamlines. Each device entry maps a Python class path to EPICS PV prefixes, labels, and any extra kwargs the class `__init__` requires.

Labels control which devices get connected at each beamline:
- `"core"` — loaded by all hutches (shared upstream/optics devices)
- Station labels (`"4idb"`, `"4idg"`, `"4idh"`) — hutch-specific devices
- `"baseline"` — included in supplemental data stream
- Functional labels (`"detector"`, `"motor"`, `"slit"`, etc.) — for filtering via `find_loadable_devices()`

To make a device available to an additional beamline, add that beamline's label to its entry in `devices.yml` — one edit, one file.

**PV-agnostic device pattern:** Device classes must not hardcode absolute EPICS PV strings. Instead, accept site-specific PV details as `__init__` kwargs and reference them in `FormattedComponent` templates. Example:

```python
class MyDevice(Device):
    motor = FormattedComponent(EpicsMotor, "{_ioc}m1", labels=("motor",))

    def __init__(self, prefix, *, ioc_prefix, **kwargs):
        self._ioc = ioc_prefix
        super().__init__(prefix, **kwargs)
```

```yaml
id4_common.devices.my_device.MyDevice:
- name: mydev
  prefix: ""
  ioc_prefix: "4idbSoft:"
  labels: ["4idb", "baseline"]
```

Where a `DynamicDeviceComponent` must be built at class-definition time, use a factory function instead:

```python
def make_mydevice_class(ioc="4idgSoft:"):
    class MyDevice(Base):
        ddc = DynamicDeviceComponent(_make_dict(ioc))
        ...
    return MyDevice

MyDevice = make_mydevice_class()  # module-level default for devices.yml
```

Multiple devices sharing a class must all be listed under **one** class key in `devices.yml` (YAML sequences continue until the next mapping key — a misplaced `- name:` entry silently falls under the preceding class).

### Startup Flow

There are two startup entry points:

1. `id4_{b,g,h,raman}/startup.py` — per-beamline. Loads station-specific config, then `from id4_common._common_startup import *`, then `make_devices(..., connect=False)`, then `connect_device(...)` for devices matching that beamline's stations list. No interactive prompt.
2. `id4_common/startup.py` — combined. Loads the shared config and prompts the user `"Do you want to load all devices?"`. If yes, loads every station (`["core", "4idb", "4idg", "4idh"]`).

Both paths share `id4_common/_common_startup.py`, which in order:
1. Calls `init_instrument("guarneri")` and clears `oregistry`
2. Sets up APS DM integration (`aps_dm_setup`)
3. Registers Bluesky and POLAR-local IPython magics
4. Imports `RE`, `bec`, `cat`, `cat_legacy`, `peaks`, `sd`
5. Conditionally loads NeXus and SPEC callbacks based on `iconfig.yml`
6. Loads dichro stream callbacks
7. In non-QueueServer sessions, imports plans, suspenders, counters, attenuators, etc.
8. Installs the A-shutter suspender on the RunEngine

Each beamline startup connects only the devices whose labels match its `stations` list:

| Beamline | stations list |
|----------|--------------|
| 4IDB | `["core", "4idb"]` |
| 4IDG | `["core", "4idg"]` |
| 4IDH | `["core", "4idh"]` |
| Raman | `["4idb"]` |

Devices shared between beamlines (e.g. `transfocator`, `gslt`) carry the `"core"` label in `devices.yml`.

### Key Components in `id4_common/`

- **`devices/`** — ophyd device classes (motors, area detectors, undulators, diffractometer, electromagnet, chopper, etc.). Notable files: `xbpm.py` (generic XBPM with `motorsDict`), `kb_generic.py` (`make_kb_class` factory + `GKBDevice`/`HKBDevice`), `transfocator_device.py` (`make_transfocator_class` factory), `counters_mixin.py` (detector plotting API — see below)
- **`plans/`** — Bluesky scan plans: `local_scans.py` (lup, ascan, grid_scan, qxscan, count, mv/mvr), `_local_scan_utils.py` (private helpers shared by local_scans — `_hkl_motors`, `reset_real_motors_decorator` for fixQ position restore, `_setup_file_io`, etc.), `local_preprocessors.py` (decorators: `configure_counts`, `stage_dichro`, `stage_magnet911`, `stage_4idg_softglue`, `extra_devices`), `dm_plans.py` (DM workflow submission), `center_maximum.py`, `flyscan_demo.py`
- **`callbacks/`** — `spec_data_file_writer.py`, `nexus_data_file_writer.py`, `dichro_stream.py`
- **`utils/`** — ~30 modules including HKL/crystallography utilities, DM integration, counters class (`counters_class.py`, provides `CountersClass` with `is_scaler_monitor`, `monitor_field`, `plotselect()`), attenuator control, device loader (`device_loader.py`), local `make_devices` shim (`make_devices.py`, see "Deferred EPICS Connection Pattern"), experiment utilities, and `polartools`/`hklpy2` import wrappers
- **`suspenders/`** — shutter-based RunEngine suspenders for beamline safety

### Detector Plotting API

All detectors used with `CountersClass.plotselect()` must inherit from one of:

- **`CountersMixin`** (abstract) — defines the five-method contract: `plot_options`, `label_option_map`, `select_plot`, `field_for_label`, `select_read` (no-op default). Also provides `preset_monitor` resolved from a dotted-path class attribute.
- **`ROICountersMixin(CountersMixin)`** — concrete shared implementation for MCA detectors (Xspress3, Dante, XMAP). Subclasses supply `label_option_map` and `select_roi`; everything else is inherited.

Set the count-time signal via a class attribute instead of overriding the property:

```python
class MyDetector(Trigger, CountersMixin, DetectorBase):
    _preset_monitor_attr = "cam.acquire_time"  # dotted path, resolved at runtime
```

For devices where `preset_monitor` is an ophyd `Component` (e.g. `LocalScalerCH`), the class-body descriptor shadows the inherited property automatically — no override needed.

### Device Loading at Runtime

Devices can be dynamically managed:
```python
find_loadable_devices()                          # list available devices
find_loadable_devices(label="4idg")              # filter by label
load_device("device_name")                       # connect a specific device
remove_device("device_name")                     # disconnect and remove from baseline
reload_all_devices()                             # reload all from YAML (all stations)
reload_all_devices(stations=["core", "4idh"])  # reload for a specific beamline
```

The `oregistry` (from `apsbits`) is the central device registry.

### Deferred EPICS Connection Pattern

All beamline `startup.py` files use the local `make_devices` from
`id4_common.utils.make_devices` and call it with `connect=False`. With that
flag, `make_devices()` only instantiates and registers devices in `oregistry`
/ `__main__` — it does **not** trigger EPICS connections. The subsequent
`for device in oregistry.findall([...]): connect_device(device, raise_error=False)`
loop owns all EPICS I/O.

This local module is a near-line-for-line copy of `apsbits.core.instrument_init`'s
`make_devices` and `guarneri_namespace_loader`, with a single `connect: bool = True`
flag added to each. Remove it once the same flag is available upstream in apsbits.
Until then, every call site (the four beamline startups, the orphan
`id4_common/startup.py`, and `reload_all_devices` in `device_loader.py`) must use
`connect=False`; the upstream apsbits `make_devices` eagerly calls
`await instrument.connect()` and waits up to `DEFAULT_TIMEOUT` per disconnected
device, generating ~70 s of dead time and `NotConnectedError` log spam when any
IOC is off.

**Rule:** Never subscribe to or read from EPICS/PVA signals inside `__init__`. Instead,
implement a `_post_connect_setup()` method on the device class. `connect_device()` calls
this hook automatically after `wait_for_connection()` succeeds:

```python
class MyDevice(Device):
    signal = Component(EpicsSignalRO, "PV:NAME")

    def _post_connect_setup(self):
        """Called by connect_device() after EPICS connection is live."""
        self.signal.subscribe(self._my_callback, run=False)
```

For sub-components (not top-level `devices.yml` entries), use `run=False` on all
`subscribe()` calls in `__init__` to avoid fetching PV values before connection.

### Data Output

- **SPEC files** (`.dat`): enabled by default in `iconfig.yml`; `newSpecFile()`, `spec_comment()` available in session
- **NeXus/HDF5** (`.hdf`): opt-in via `iconfig.yml`
- **Dichro stream**: circular dichroism data processing, always loaded

### QueueServer

Each beamline has a `qs-config.yml` and `qs_host.sh`. The QS uses Redis (localhost:6379) for communication and an IPython kernel backend. `startup.py` detects QueueServer context via `running_in_queueserver()` and adjusts imports accordingly (e.g., no interactive prompts, no shutter suspenders).

## Documentation

The documentation site is built with **Sphinx + PyData theme + sphinx-autoapi**
and hosted on GitHub Pages. Source files live in `docs/source/`.

**Build locally:**
```bash
conda run -n p313 sphinx-build -M html docs/source docs/build
# open docs/build/html/index.html
```

**Deploy:** `.github/workflows/docs.yml` builds and publishes automatically:
- Push to `main` → deploys to `.../latest/`
- Git tag (`v*`) → deploys to `.../v0.x.y/`

**Structure:**
```
docs/source/
├── conf.py                      # Sphinx config (autoapi, theme, extensions)
├── index.md                     # Landing page (card grid)
├── getting_started.md
├── architecture.md
├── configuration.md
├── devices_guide.md
├── devices_reference.md         # Device lookup tables (core/4IDB/4IDG/4IDH)
├── plans.md
├── callbacks.md
├── queueserver.md
├── examples/
│   ├── general.md               # experiment_setup, counters.plotselect, magics
│   ├── writing_macros.md        # startup scripts, motor shortcuts, Bluesky plans
│   ├── 4idg_diffractometer.md   # HKL, orientation, reciprocal-space scans
│   └── 4idh_magnet.md           # field sweeps, XMCD, qxscan
└── api/                         # auto-generated by sphinx-autoapi (do not edit)
```

**Maintenance notes:**
- API docs are auto-generated from docstrings — keep docstrings up to date
- `devices_reference.md` is hand-maintained from `devices.yml` — update when devices change
- Example pages only document functions **defined in this repo**; user-defined macros belong in `examples/writing_macros.md` as patterns, not as calls
- `docs/source/api/` is committed but regenerated on every build; consider adding it to `.gitignore` if it becomes a maintenance burden

## Code Style

- Line length: 80 (both ruff and black configs in `pyproject.toml`)
- Python 3.11+
- Linting: ruff (replaces flake8/isort/black in pre-commit)
- Docstrings required for all public classes/functions/methods/modules (ruff rules D100-D107)
