# Architecture

## Overview

polar-bits supports three hutches and a Raman setup at the 4ID-POLAR beamline, all
sharing a common codebase in `id4_common` with beamline-specific overrides in
separate packages.

```
src/
├── id4_common/            # Shared: devices, plans, callbacks, utils
├── id4_b/                 # 4IDB-specific startup and config extras
├── id4_g/                 # 4IDG-specific startup and config extras
├── id4_h/                 # 4IDH-specific startup and config extras
├── id4_raman/             # Raman-specific startup and config extras
├── id4_common_qserver/    # Shared QueueServer components
├── id4_b_qserver/         # 4IDB QueueServer config and launch script
├── id4_g_qserver/         # 4IDG QueueServer config and launch script
├── id4_h_qserver/         # 4IDH QueueServer config and launch script
└── id4_raman_qserver/     # Raman QueueServer config and launch script
```

### What goes where

| Layer | Location | Examples |
|-------|----------|---------|
| Core shared devices | `id4_common/devices/` | undulator, monochromator, KB mirrors |
| Shared scan plans | `id4_common/plans/` | `lup`, `ascan`, `grid_scan` |
| Data callbacks | `id4_common/callbacks/` | SPEC writer, NeXus writer, dichro stream |
| Session utilities | `id4_common/utils/` | device loader, counters, HKL utilities |
| Safety suspenders | `id4_common/suspenders/` | shutter-based suspenders |
| Instrument overrides | `id4_{b,g,h,raman}/` | startup.py, iconfig_extras.yml |

---

## Startup Flow

`startup.py` orchestrates session initialization in this order:

1. Load `iconfig.yml`
2. Set up APS DM integration (`aps_dm_setup`)
3. Initialize `RE` (RunEngine), `cat` (databroker catalog), `bec`, and supplementary data streams
4. Conditionally load SPEC / NeXus callbacks based on `iconfig.yml`
5. Load dichro stream callback
6. Prompt user to load devices — calls `make_devices()` which reads `devices.yml`
7. Connect devices tagged with that beamline's station labels
8. Install shutter suspenders on the RunEngine

---

## Station Labels

Device loading is controlled by labels defined in `devices.yml`. Each beamline
connects only devices whose labels intersect with its `stations` list:

| Beamline | Stations loaded |
|----------|----------------|
| 4IDB | `["core", "4idb"]` |
| 4IDG | `["core", "4idg"]` |
| 4IDH | `["core", "4idh"]` |
| Raman | `["raman",]`|

Common labels:

| Label | Meaning |
|-------|---------|
| `"core"` | Loaded by all hutches (shared upstream/optics devices) |
| `"4idb"`, `"4idg"`, `"4idh", "raman"` | Instrument-specific devices |
| `"baseline"` | Added to the supplemental baseline data stream |
| `"detector"`, `"motor"`, `"slit"` | Functional category — used for filtering |

To make a device available to an additional beamline, add that beamline's label
to its entry in `devices.yml`. That is the only change required.

---

## Device Registry (`devices.yml`)

`src/id4_common/configs/devices.yml` is the single source of truth for all
device definitions. Each entry maps a Python class path to EPICS PV details:

```yaml
id4_common.devices.aps_xbpm.MyXBPM:
- name: aps_xbpm
  prefix: S04
  labels: ["core", "source", "baseline"]
```

Multiple instances of the same class are listed as a YAML sequence under **one**
class key. See [Configuration](configuration.md) for the full YAML schema.

---

## Deferred EPICS Connection Pattern

`make_devices()` instantiates all device objects **without** making EPICS
connections. Only `connect_device()` (via `wait_for_connection()`) triggers
actual EPICS interaction.

**Rule:** Never subscribe to or read from EPICS/PVA signals inside `__init__`.
Instead, implement `_post_connect_setup()` on the device class:

```python
class MyDevice(Device):
    signal = Component(EpicsSignalRO, "PV:NAME")

    def _post_connect_setup(self):
        """Called by connect_device() after EPICS connection is live."""
        self.signal.subscribe(self._my_callback, run=False)
```

`connect_device()` calls this hook automatically after `wait_for_connection()`
succeeds.

---

## Key Components in `id4_common/`

### `devices/`

~66 device modules covering the full instrument:

- Area detectors: `ad_eiger1M`, `ad_lambda`, `ad_lightfield`, `ad_vimba`
- X-ray diagnostics: `aps_xbpm`, `aps_undulator`, `aps_status`
- Optics: `kb_generic` (KB mirror factory), `transfocator_device` (transfocator factory)
- Monochromator / energy: `monochromator`, `energy_device`
- Diffractometer: `polar_diffractometer`
- Detectors: `scaler`, `vortex_xmap`, `vortex_xspress3_*`
- Utilities: `shutters`, `electromagnet`, `chopper_device`

### `plans/`

- `local_scans` — `lup`, `ascan`, `grid_scan`, `rel_grid_scan`, `count`, `qxscan`
- `dm_plans` — APS Data Management workflow submission
- `center_maximum`, `flyscan_demo`, `workflow_plan`

### `callbacks/`

- `spec_data_file_writer` — SPEC `.dat` output
- `nexus_data_file_writer` — NeXus/HDF5 output
- `dichro_stream` — circular dichroism processing

### `utils/`

~33 utility modules including device loader, counters class, HKL/crystallography
helpers, DM integration, attenuator control, and more.
