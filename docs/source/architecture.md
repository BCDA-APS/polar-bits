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
| Core shared devices | `id4_common/devices/` | undulator, monochromator, KB mirrors, CRL |
| Shared scan plans | `id4_common/plans/` | `lup`, `ascan`, `grid_scan`, `hklscan`, `cen`/`com`/`maxi`/`mini` |
| Data callbacks | `id4_common/callbacks/` | SPEC writer, NeXus writer, dichro stream |
| Session utilities | `id4_common/utils/` | device loader, counters, HKL utilities, session-state restore |
| Per-session macros | `id4_common/macros/` | curated `macros_api`, `startup_common`, motor shortcuts |
| Safety suspenders | `id4_common/suspenders/` | shutter-based suspenders |
| Instrument overrides | `id4_{b,g,h,raman}/` | startup.py, iconfig_extras.yml |

---

## Startup Flow

The per-beamline `id4_{b,g,h,raman}/startup.py` files orchestrate session
initialization in this order:

1. Load `iconfig.yml`
2. Set up APS DM integration (`aps_dm_setup`)
3. Initialize `RE` (RunEngine), `cat` (databroker catalog), `bec`, and
   supplementary data streams
4. Conditionally load SPEC / NeXus callbacks based on `iconfig.yml`
5. Load dichro stream callback
6. Import scan plans, peak-finding plans, counters, attenuators
7. Expose `restore_session_state` in the interactive namespace
8. Call `make_devices(connect=False)` — instantiates every device entry
   from `devices.yml` without making EPICS connections
9. Iterate `oregistry.findall([...])` for the beamline's station labels
   and call `connect_device(...)` for each
10. Install the A-shutter suspender on the RunEngine

After startup the user can `import id4_common.macros.startup_common` to
re-apply the auto-saved per-experiment knobs (PR setup, energy tracking,
counters, undulator offsets, qxscan params) from `RE.md["session_state"]`.

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
- Optics: `kb_generic` (KB mirror factory), `crl_device` (CRL factory)
- Monochromator / energy: `monochromator`, `energy_device`, `mono_feedback`
- Diffractometer: `polar_diffractometer_hklpy2` (Cradle / HP cradles + `_psi` engines)
- Fluorescence detectors: `vortex_xmap`, `vortex_xspress3_me{4,7}`, `vortex_dante_me{1,4}`
- Area detectors: `ad_eiger1M`, `ad_lambda`, `ad_lightfield`, `ad_vimba`
- Scalers / electrometers: `scaler`, `quadems`, `sydor_device`
- Magnets / sample environment: `electromagnet`, `magnet_911`, `lakeshore_gaussmeter`
- Utilities: `shutters`, `chopper_device`, `phaseplates`, `qxscan_device`

### `plans/`

- `base_scans` — `lup`, `ascan`, `count`, `qxscan`, `th2th`
- `grid_scans` — `grid_scan`, `rel_grid_scan`
- `hkl_scans` — `hklscan`, `hscan`, `kscan`, `lscan`, `psiscan`
- `move_plans` — `mv`, `mvr`, `abs_set` (with magnet911 staging)
- `peak_position` — `cen` / `com` / `maxi` / `mini` / `peak` / `peak_pos` /
  `pmax` / `pmin` (scipy-backed; 2-D `grid_scan` support)
- `peak_position_legacy` — `cen2` / `maxi2` / `mini2` (apstools `lineup2` backed)
- `center_maximum` — single-pass center / maximum helpers
- `dm_plans` — `dm_kickoff_workflow`, `dm_submit_workflow_job`,
  `dm_list_processing_jobs`
- `local_scans` — back-compat shim that re-exports from the focused
  modules above (so old `from id4_common.plans.local_scans import …`
  imports still work)
- `local_preprocessors` — staging decorators (dichro, magnet911,
  4idg softglue, extra devices)
- `flyscan_demo`, `workflow_plan`

### `macros/` (new, PR #65)

- `macros_api` — curated star-import surface for plans, peak finders,
  session singletons. The recommended import line for user macros is
  `from id4_common.macros.macros_api import *`.
- `startup_common` — one-line restart helper
  (`experiment_resume()` + `restore_session_state()`).
- `shortcuts_4idg_euler` / `shortcuts_4idg_hp` / `shortcuts_4idh_9T` —
  prebuilt motor-shortcut modules. Importing a module binds its
  diffractometer or magnet sub-devices into `__main__` under short
  names.

### `callbacks/`

- `spec_data_file_writer` — SPEC `.dat` output
- `nexus_data_file_writer` — NeXus/HDF5 output
- `dichro_stream` — circular dichroism processing
- `apstools_spec_file_writer` — local subclass of apstools' SPEC writer
  (collapses non-scalar metadata so qxscan files parse in pymca)

### `utils/`

~28 utility modules. Highlights:

- `device_loader` — `load_device`, `find_loadable_devices`, `reload_all_devices`
- `counters_class` — `CountersClass.plotselect()` (auto-saved into session state)
- `temperature_setup` — `temperature_setup(label)` injects `tc` / `ts` /
  `TEMPERATURE_CONTROLLER` into the session
- `pr_setup` — interactive phase-retarder setup (auto-saved into session state)
- `undulator_setup` — undulator offset / harmonic helpers
- `session_state` — auto-save / `restore_session_state()` against
  `RE.md["session_state"]`
- `experiment_utils` — `experiment_setup`, `experiment_resume`,
  `experiment_load_from_scan`
- `hkl_utils` — hklpy2 wrappers
- `polartools_hklpy2_imports` — re-exports
- `shorts` — `crl_setup`, `crl_size`, `te`, `opt`
