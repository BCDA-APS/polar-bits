# Devices Guide

## Device Loading at Runtime

Devices are managed through a set of helper functions available after startup:

```python
# List all available devices (from devices.yml)
find_loadable_devices()

# Filter by label
find_loadable_devices(label="4idg")
find_loadable_devices(name="transfocator")   # substring match
find_loadable_devices(name="kb", exact_name=False)

# Connect a device
load_device("transfocator")

# Disconnect and remove from baseline
remove_device("transfocator")

# Reload everything from YAML (useful after devices.yml edits)
reload_all_devices()
reload_all_devices(stations=["core", "4idh"])
```

These are thin wrappers around
`id4_common.utils.device_loader` — see the
[API reference](api/id4_common/utils/device_loader/index.rst) for full
parameter documentation.

---

## Deferred EPICS Connection Pattern

`make_devices()` instantiates every device object from `devices.yml` **without**
making EPICS connections. This means startup is fast and does not depend on the
EPICS network being reachable.

Only `connect_device()` — called internally by `load_device()` — triggers actual
EPICS interaction via `wait_for_connection()`.

### `_post_connect_setup()` hook

If your device needs to subscribe to PV values or perform any post-connection
work, implement this method:

```python
from ophyd import Device, Component, EpicsSignalRO

class MyDevice(Device):
    signal = Component(EpicsSignalRO, "PV:NAME")

    def _post_connect_setup(self):
        """Called by connect_device() after EPICS connection is live."""
        self.signal.subscribe(self._on_change, run=False)

    def _on_change(self, value, **kwargs):
        ...
```

`connect_device()` calls `_post_connect_setup()` automatically after
`wait_for_connection()` succeeds. For sub-components (not top-level
`devices.yml` entries), always use `run=False` on any `subscribe()` calls
inside `__init__` to avoid fetching PV values before the connection is live.

---

## PV-Agnostic Pattern {#pv-agnostic-pattern}

Device classes must not hardcode absolute EPICS PV strings. Accept
site-specific PV details as `__init__` kwargs and reference them inside
`FormattedComponent` templates:

```python
from ophyd import Device, FormattedComponent, EpicsMotor

class KBMirror(Device):
    hx = FormattedComponent(EpicsMotor, "{_ioc}m1", labels=("motor",))
    hy = FormattedComponent(EpicsMotor, "{_ioc}m2", labels=("motor",))

    def __init__(self, prefix, *, ioc_prefix, **kwargs):
        self._ioc = ioc_prefix
        super().__init__(prefix, **kwargs)
```

```yaml
# devices.yml
id4_common.devices.kb_generic.GKBDevice:
- name: kb_4idb
  prefix: ""
  ioc_prefix: "4IDB:KB:"
  labels: ["4idb", "mirror", "baseline"]
```

---

## Factory Pattern for Dynamic Components

Where a `DynamicDeviceComponent` must be assembled at class-definition time
(e.g. a variable number of channels), use a factory function that returns a
new class:

```python
def make_transfocator_class(ioc="4idgSoft:"):
    class Transfocator(Device):
        lenses = DynamicDeviceComponent(_build_lens_dict(ioc))
        ...
    return Transfocator

# Module-level default (what devices.yml points to)
Transfocator = make_transfocator_class()
```

Real examples in the codebase:

| Factory | Module |
|---------|--------|
| `make_kb_class()` | `id4_common.devices.kb_generic` |
| `make_transfocator_class()` | `id4_common.devices.transfocator_device` |

---

## Notable Device Classes

### Area Detectors

| Class | Module | Notes |
|-------|--------|-------|
| `Eiger1M` | `ad_eiger1M` | Dectris Eiger 1M |
| `Lambda` | `ad_lambda` | X-Spectrum Lambda |
| `LightField` | `ad_lightfield` | Princeton LightField spectrometer |
| `Vimba` | `ad_vimba` | Allied Vision Vimba camera |

### Fluorescence Detectors

| Class | Module |
|-------|--------|
| `VortexXmap` | `vortex_xmap` |
| `VortexXspress3_1Element` | `vortex_xspress3_1element` |
| `VortexXspress3_4Element` | `vortex_xspress3_4element` |

### Optics and Beam Delivery

| Class | Module | Notes |
|-------|--------|-------|
| `GKBDevice` / `HKBDevice` | `kb_generic` | KB mirror pair (factory-built) |
| `Transfocator` | `transfocator_device` | Compound refractive lens (factory-built) |
| `Monochromator` | `monochromator` | Si(111) DCM |
| `EnergySignal` | `energy_device` | Tracks mono energy; other devices can subscribe |
| `PolarUndulatorPair` | `aps_undulator` | Upstream/downstream undulators |
| `MyXBPM` | `aps_xbpm` | X-ray beam position monitor |

### Diffractometer

| Class | Module | Notes |
|-------|--------|-------|
| `PolarDiffractometer` | `polar_diffractometer` | Huber Euler 6-circle (hklpy2) |

### Experiment Utilities

| Class | Module | Notes |
|-------|--------|-------|
| `Electromagnet` | `electromagnet` | Magnet power supply control |
| `Chopper` | `chopper_device` | Time-resolved chopper |
| `Shutter` | `shutters` | Fast shutter |
| `Scaler` | `scaler` | Multi-channel scaler (SIS3820) |

---

## Counters Class

`CountersClass` (from `id4_common.utils.counters_class`) holds the active
detector and monitor selection used by all scan plans:

```python
# Default counters object is available as `counters` after startup
counters.detectors        # list of active detectors
counters.monitor          # scaler channel used as monitor
counters.extra_devices    # devices read but not plotted

# Change the selection
counters.plotselect(det_idx=0, mon_idx=1)
```

Scan plans automatically read `counters.detectors` and `counters.monitor`
unless overridden by explicit arguments.
