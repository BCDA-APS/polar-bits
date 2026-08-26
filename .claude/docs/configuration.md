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
