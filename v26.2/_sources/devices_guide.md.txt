# Devices Guide

## Device Loading at Runtime

Devices are managed through a set of helper functions available after startup:

```python
# List all available devices (from devices.yml)
find_loadable_devices()

# Filter by label
find_loadable_devices(label="4idg")
find_loadable_devices(name="crl")            # substring match
find_loadable_devices(name="kb", exact_name=False)

# Connect a device
load_device("crl")

# Disconnect and remove from baseline
remove_device("crl")

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

## Factory Pattern for Dynamic Components

Where a `DynamicDeviceComponent` must be assembled at class-definition time
(e.g. a variable number of channels), use a factory function that returns a
new class:

```python
def make_crl_class(ioc="4idgSoft:"):
    class CRLClass(Device):
        lenses = DynamicDeviceComponent(_build_lens_dict(ioc))
        ...
    return CRLClass

# Module-level default (what devices.yml points to)
CRLClass = make_crl_class()
```

Real examples in the codebase:

| Factory | Module |
|---------|--------|
| `make_kb_class()` | `id4_common.devices.kb_generic` |
| `make_crl_class()` | `id4_common.devices.crl_device` |

---

## Notable Device Classes

### Area Detectors

| Class | Module | Notes |
|-------|--------|-------|
| `Eiger1MDetector` | `ad_eiger1M` | Dectris Eiger 1M |
| `Lambda250kDetector` | `ad_lambda` | X-Spectrum Lambda 250k |
| `LightFieldDetector` | `ad_lightfield` | Princeton LightField spectrometer |
| `VimbaDetector` | `ad_vimba` | Allied Vision Vimba camera |

### Fluorescence Detectors

| Class | Module | Notes |
|-------|--------|-------|
| `VortexXMAP` | `vortex_xmap` | Vortex with XMAP electronics |
| `VortexXspress37` | `vortex_xspress3_me7` | Vortex 7-element with Xspress3 |
| `VortexXspress34` | `vortex_xspress3_me4` | Vortex 4-element with Xspress3 |
| `VortexDante1` | `vortex_dante_me1` | Vortex 1-element with Dante |
| `VortexDante4` | `vortex_dante_me4` | Vortex 4-element with Dante |

### Optics and Beam Delivery

| Class | Module | Notes |
|-------|--------|-------|
| `GKBDevice` / `HKBDevice` | `kb_generic` | KB mirror pair (factory-built) |
| `CRLClass` | `crl_device` | Compound refractive lens (factory-built) |
| `MonoDevice` | `monochromator` | Si(111) DCM |
| `EnergySignal` | `energy_device` | Tracks mono energy; other devices can subscribe |
| `PolarUndulatorPair` | `aps_undulator` | Upstream/downstream undulators |
| `MyXBPM` | `aps_xbpm` | APS-source XBPM |
| `XBPM` | `xbpm` | Generic XBPM (used by `gxbpm` / `hxbpm`) |
| `HHLMirror` | `hhl_mirror` | High-heat-load mirror |

### Diffractometer

| Class | Module | Notes |
|-------|--------|-------|
| `CradleDiffractometer` / `HPDiffractometer` | `polar_diffractometer_hklpy2` | Huber Euler / HP cradles (hklpy2) |
| `CradleDiffractometerPSI` / `HPDiffractometerPSI` | `polar_diffractometer_hklpy2` | Companion `_psi` engines |

### Experiment Utilities

| Class | Module | Notes |
|-------|--------|-------|
| `Magnet2T` | `electromagnet` | 2 T electromagnet power supply |
| `Magnet911` | `magnet_911` | 4IDH 9-Tesla magnet (table + sample + VTI) |
| `ChopperDevice` | `chopper_device` | Time-resolved chopper |
| `PolarShutter` | `shutters` | Local fast shutter (the A/B PSS shutters use `apstools.devices.ApsPssShutterWithStatus`) |
| `LocalScalerCH` | `scaler` | Multi-channel scaler (USB-CTR8) |

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
counters.plotselect(0, 1)                  # detector index 0, monitor index 1
counters.plotselect(dets=0, mon=1)         # equivalent (named args)
counters.plotselect()                      # interactive prompt
```

`plotselect()` accepts integer indices into the scaler channel list,
single device objects, or lists/tuples of either; pass nothing to enter
the interactive prompt. The active selection is auto-snapshotted into
`RE.md["session_state"]` so a bluesky restart can re-apply it via
`restore_session_state()` (see [Recoverable session
state](examples/writing_macros.md#recoverable-session-state)).

Scan plans automatically read `counters.detectors` and `counters.monitor`
unless overridden by explicit arguments.
