# Configuration

polar-bits is driven by two YAML files:

| File | Purpose |
|------|---------|
| `src/id4_common/configs/iconfig.yml` | Instrument runtime settings |
| `src/id4_common/configs/devices.yml` | Device registry (single source of truth) |

---

## Instrument Configuration (`iconfig.yml`)

### Top-level keys

```yaml
ICONFIG_VERSION: 2.0.1    # schema version — do not change
STATION: dev               # station identifier (used in RunEngine metadata)
DATABROKER_CATALOG: 4id_polar
```

### RunEngine metadata

```yaml
RUN_ENGINE:
  DEFAULT_METADATA:
    beamline_id: 4id-polar
    instrument_name: polar-dev
    proposal_id: commissioning
  MD_PATH: /home/beams/POLAR/.config/Bluesky_RunEngine_md_dev
  USE_PROGRESS_BAR: true
```

`MD_PATH` is where RunEngine autosaves its metadata dictionary between sessions.

### Data output formats

```yaml
SPEC_DATA_FILES:
  ENABLE: true          # write SPEC .dat files (default: true)
  FILE_EXTENSION: dat

NEXUS_DATA_FILES:
  ENABLE: false         # write NeXus/HDF5 files (opt-in)
  FILE_EXTENSION: hdf
```

### Best Effort Callback

```yaml
BEC:
  BASELINE: true    # show baseline readings
  HEADING: true     # print scan header
  PLOTS: false      # disable live plots (set true for interactive use)
  TABLE: true       # print tabular scan output
```

### APS Data Management

```yaml
DM_SETUP_FILE: "/home/dm/etc/dm.setup.sh"
DM_ROOT_PATH: /gdata/dm/4ID
DM_USE_PATH: true
```

### EPICS / ophyd settings

```yaml
OPHYD:
  CONTROL_LAYER: PyEpics   # or "caproto"
  TIMEOUTS:
    PV_READ: 60
    PV_WRITE: 60
    PV_CONNECTION: 60
```

### Area detector defaults

```yaml
AREA_DETECTOR:
  HDF5_FILE_TEMPLATE: "%s/%s_%6.6d"
  HDF5_FILE_EXTENSION: h5
  EIGER_1M:
    DEFAULT_FOLDER: /net/s4data/export/sector4/4idd/bluesky_images/eiger1M
    ALLOW_PLUGIN_WARMUP: true
  LAMBDA:
    DEFAULT_FOLDER: /net/s4data/export/sector4/4idd/bluesky_images/lambda
    ALLOW_PLUGIN_WARMUP: true
  VORTEX:
    IOC_FILES_ROOT: /net/s4data/export/sector4/4idd
    DEFAULT_FOLDER: /net/s4data/export/sector4/4idd/bluesky_images/vortex
    ALLOW_PLUGIN_WARMUP: true
```

---

## Device Registry (`devices.yml`)

`devices.yml` maps Python class paths to EPICS PV details. It is the **single
source of truth** for all device definitions across all beamlines.

### Entry format

```yaml
<python.module.path.ClassName>:
- name: <unique_device_name>
  prefix: "<EPICS PV prefix>"
  labels: ["<label1>", "<label2>"]
  # any extra __init__ kwargs go here, e.g.:
  ioc_prefix: "4idbSoft:"
```

### Labels

Labels control which beamlines load a device:

| Label | Who loads it |
|-------|-------------|
| `"core"` | All hutches |
| `"4idb"` | 4IDB only |
| `"4idg"` | 4IDG only |
| `"4idh"` | 4IDH only |
| `"baseline"` | Added to baseline supplemental data stream |
| `"detector"`, `"motor"`, `"slit"` | Functional — used for `find_loadable_devices(label=...)` |

### Adding a new device

1. Create a device class in `id4_common/devices/` following the
   [PV-agnostic pattern](devices_guide.md#pv-agnostic-pattern).
2. Add an entry in `devices.yml` under the class's full dotted path.
3. Assign labels to control which beamlines load it.
4. No other files need to change.

### Multiple instances of the same class

List them as a YAML sequence under **one** class key:

```yaml
id4_common.devices.slits.Slits:
- name: white_slits
  prefix: "4IDB:Slit1"
  labels: ["core", "slit"]
- name: mono_slits
  prefix: "4IDB:Slit2"
  labels: ["4idb", "slit"]
```

:::{warning}
A misplaced `- name:` entry silently falls under the **preceding** class key.
Keep entries indented consistently and always under the intended class.
:::

### Beamline-specific extras (`iconfig_extras.yml`)

Each beamline package can provide an `iconfig_extras.yml` to override or extend
the shared `iconfig.yml` without editing the shared file.
