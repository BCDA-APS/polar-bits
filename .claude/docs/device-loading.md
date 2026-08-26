# Device Loading, Connection Pattern, and Detector Plotting API

Read this before writing a new device class, touching `device_loader.py`,
adding a new area detector, or debugging a connection/`_post_connect_setup`
issue.

## Key Components in `id4_common/`

- **`devices/`** — ophyd device classes (motors, area detectors, undulators, diffractometer, electromagnet, chopper, etc.). Notable files: `xbpm.py` (generic XBPM with `motorsDict`), `kb_generic.py` (`make_kb_class` factory + `GKBDevice`/`HKBDevice`), `crl_device.py` (`make_crl_class` factory; CRL / transfocator), `counters_mixin.py` (detector plotting API — see below)
- **`plans/`** — Bluesky scan plans: `local_scans.py` (lup, ascan, grid_scan, qxscan, count, mv/mvr), `_local_scan_utils.py` (private helpers shared by local_scans — `_hkl_motors`, `reset_real_motors_decorator` for fixQ position restore, `_setup_file_io`, etc.), `local_preprocessors.py` (decorators: `configure_counts`, `stage_dichro`, `stage_magnet911`, `stage_4idg_softglue`, `extra_devices`), `dm_plans.py` (DM workflow submission), `center_maximum.py`, `flyscan_demo.py`
- **`callbacks/`** — `spec_data_file_writer.py`, `nexus_data_file_writer.py`, `dichro_stream.py`
- **`utils/`** — ~30 modules including HKL/crystallography utilities, DM integration, counters class (`counters_class.py`, provides `CountersClass` with `is_scaler_monitor`, `monitor_field`, `plotselect()`), attenuator control, device loader (`device_loader.py`), local `make_devices` shim (`make_devices.py`, see "Deferred EPICS Connection Pattern" below), experiment utilities, and `polartools`/`hklpy2` import wrappers
- **`suspenders/`** — shutter-based RunEngine suspenders for beamline safety

## Device Loading at Runtime

Devices can be dynamically managed:
```python
find_loadable_devices()                          # list available devices
find_loadable_devices(label="4idg")              # filter by label
load_device("device_name")                       # connect a specific device
remove_device("device_name")                     # disconnect and remove from baseline
reload_all_devices()                             # reload all from YAML (all stations)
reload_all_devices(stations=["core", "4idh"])  # reload for a specific beamline
```

`load_device(name)` is also the canonical way to **reconnect** a device that
is already in the registry — it routes existing entries through
`connect_device(...)` rather than skipping. Users who want to retry a flaky
IOC connection can just call `load_device("...")` again.

The vortex-specific helper `load_vortex(electronic, ...)` (used because vortex
electronics are picked at runtime rather than from `devices.yml`) follows the
same contract as `load_device`: it delegates to `connect_device`, runs
`_post_connect_setup`/`default_settings`/HDF1 priming, and adds the device to
`__main__` regardless of whether the connection succeeded.

The `oregistry` (from `apsbits`, imported as
`from apsbits.core.instrument_init import oregistry`) is the central device
registry — see `../../CLAUDE.md`'s "Implementing New Devices & Code" section
for how to find and use devices/signals from it in new code.

## Deferred EPICS Connection Pattern

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

**HDF1 plugin priming.** `connect_device()` automatically calls
`AD_prime_plugin2(device.hdf1)` after `default_settings()` runs, which fires
`hdf1.warmup()` when the plugin has never received an array. The contract is
that each area-detector class wires `self.hdf1.warmup_signals` inside its
`default_settings()` — a list of `(signal, value)` pairs that briefly trigger
one acquisition. Reference patterns: `Eiger1MDetector`, `VimbaDetector` (ADCore
`acquire`); `VortexDante1`/`VortexDante4` (MCA `acquire_start`/`mca_mode`).
A camera with no warmup signals logs a warning and skips priming.

## Detector Plotting API

All detectors used with `CountersClass.plotselect()` must inherit from one of:

- **`CountersMixin`** (abstract) — defines the five-method contract: `plot_options`, `label_option_map`, `select_plot`, `field_for_label`, `select_read` (no-op default). Also provides `preset_monitor` resolved from a dotted-path class attribute.
- **`ROICountersMixin(CountersMixin)`** — concrete shared implementation for MCA detectors (Xspress3, Dante, XMAP). Subclasses supply `label_option_map` and `select_roi`; everything else is inherited.

Set the count-time signal via a class attribute instead of overriding the property:

```python
class MyDetector(Trigger, CountersMixin, DetectorBase):
    _preset_monitor_attr = "cam.acquire_time"  # dotted path, resolved at runtime
```

For devices where `preset_monitor` is an ophyd `Component` (e.g. `LocalScalerCH`), the class-body descriptor shadows the inherited property automatically — no override needed.
