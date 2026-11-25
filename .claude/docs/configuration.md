# Configuration System

Read this when adding, editing, or relabeling a device in `devices.yml`, or
writing a new device class that needs site-specific PVs.

Configuration is YAML-driven. The main file is `src/id4_common/configs/iconfig.yml`, which controls:
- RunEngine metadata (station, proposal, catalog)
- Enabled output formats (SPEC `.dat` files enabled by default, NeXus `.hdf` optional)
- APS Data Management (DM) integration paths
- Area detector defaults (Eiger 1M, Lambda, Vortex, LightField, Vimba)
- EPICS timeouts
- Bluesky session logging (`LOGGING.LOG_PATH` and friends — see `data-output-and-logging.md`)

Device definitions live in `src/id4_common/configs/devices.yml` — the single source of truth for all beamlines. Each device entry maps a Python class path to EPICS PV prefixes, labels, and any extra kwargs the class `__init__` requires.

Labels control which devices get connected at each beamline:
- `"core"` — loaded by all hutches (shared upstream/optics devices)
- Station labels (`"4idb"`, `"4idg"`, `"4idh"`) — hutch-specific devices
- `"baseline"` — included in supplemental data stream
- Functional labels (`"detector"`, `"motor"`, `"slit"`, etc.) — for filtering via `find_loadable_devices()`

To make a device available to an additional beamline, add that beamline's label to its entry in `devices.yml` — one edit, one file.

**PV-agnostic device pattern:** Device classes must not hardcode absolute EPICS PV strings. Instead, accept site-specific PV details as `__init__` kwargs and reference them in `FormattedComponent` templates. The kwarg name itself is not standardized — real devices use whatever fits (`motors_ioc` in `crl_device.py`, a computed `_slit_prefix` in `wb_slit.py`, etc.); `ioc_prefix` below is illustrative, not a convention to grep for:

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

**Factory-function patterns.** A device class is often generated at
module-load time by a function, rather than defined directly — two such
patterns are already mainstream in this codebase (not rare exceptions), plus
one you may need to reach for:

- `DynamicDeviceComponent` built inside a factory function, when the set of
  sub-signals depends on a runtime parameter (e.g. an IOC prefix or channel
  count). Used in 16+ device files — `crl_device.py`, the `vortex_*.py`
  family, `softgluezynq_*.py`, `scaler.py`, `magnet_911.py`, and others:

  ```python
  def make_mydevice_class(ioc="4idgSoft:"):
      class MyDevice(Base):
          ddc = DynamicDeviceComponent(_make_dict(ioc))
          ...
      return MyDevice

  MyDevice = make_mydevice_class()  # module-level default for devices.yml
  ```

- Building a class dynamically via `type(...)` with plain `Component`s
  generated from a PV-suffix mapping — see `kb_generic.py`'s `make_kb_class`
  (produces `GKBDevice`/`HKBDevice` from `v_motors`/`h_motors` suffix dicts).
  Reach for this when the components are plain motors/signals (no
  `DynamicDeviceComponent` needed) but the attribute names still depend on a
  runtime mapping.

Multiple devices sharing a class must all be listed under **one** class key in `devices.yml` (YAML sequences continue until the next mapping key — a misplaced `- name:` entry silently falls under the preceding class).

**Kinds on sub-Devices (#72, #100).** On a sub-Device (positioner, motor,
plugin, `DynamicDeviceComponent`), `kind` filters what is passed up; it does
not label the device:

- `normal` passes everything: its `normal` signals go into `read()` (event
  data, baseline, NeXus, SPEC) and its `config` signals into
  `read_configuration()`. ophyd turns a `normal` Device into `normal|config`
  by itself, so `Kind.normal | Kind.config` on a Device adds nothing.
- `config` passes **only** its `config` signals. A `normal`/`hinted`
  readback or setpoint inside is saved nowhere. This was the needle valve
  pressure bug, and the AD ROI bounds bug (ophyd's `min_xyz`/`size` are
  `normal` signals inside a `config` plugin).
- `omitted` passes nothing, not even the `config` signals.

So: leave a sub-Device `normal` when its readings should be saved, and
classify the leaf signals instead (readback/setpoint `normal`; gains,
limits, names `config`). Use `config` on a sub-Device only to deliberately
keep just its configuration, e.g. a deselected ROI, so its bounds stay in
the descriptor but its counts are not read. Descriptor configuration only
reaches the database: the NeXus and SPEC writers ignore it, so anything that
belongs in the files must be `normal` (and the device in the baseline).
Changing `.kind` at runtime does not update the parents. Check a device with
`audit_kinds("name")` in the session (`utils/kind_audit.py`); add new device
classes to `tests/test_kind_audit.py`.
