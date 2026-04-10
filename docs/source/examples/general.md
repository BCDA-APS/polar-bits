# General Examples

This page covers session setup and common operations that apply to all beamlines.

---

## Experiment Setup

`experiment_setup()` collects the metadata needed to organize data into the
correct folders and associate it with an APS proposal and ESAF. It can be run
**interactively** (prompts at the command line) or **non-interactively** by
passing all arguments as keyword parameters.

### Interactive mode

Call with no arguments — the function prompts for each field in sequence:

```python
experiment_setup()
```

The prompts walk through:

1. **ESAF ID** — enter the APS ESAF number (or `dev` to skip for development sessions)
2. **Proposal ID** — the APS proposal number (or `dev`)
3. **Server** — choose between `dserv` (local storage) and data management (`dm`)
4. **Experiment name** — must match an existing experiment in the DM system if using DM
5. **Sample name** — free text; creates a sub-folder under the experiment path
6. **Scan ID reset** — optionally reset the Bluesky `scan_id` counter
7. **File base name** — prefix for SPEC file names (e.g. `scan` → `scan_0001`)

After completing setup, the SPEC writer is configured, `RE.md` is populated,
and data will be written to the correct experiment path automatically.

### Non-interactive mode

Pass all values as keyword arguments — useful for startup scripts:

```python
experiment_setup(
    esaf_id       = 281924,
    proposal_id   = "dev",
    base_name     = "scan",
    sample        = "EuAl4",
    server        = "dserv",
    experiment_name = "Miao_25-3",
    reset_scan_id = -1,     # -1 = do not reset
)
```

### Resuming from the last run

If the session was interrupted, reload the experiment state from the most
recent Bluesky run rather than re-entering all values:

```python
experiment_load_from_bluesky()    # reads metadata from cat[-1]
```

### Changing sample mid-experiment

```python
experiment_change_sample(sample_name="Fe3O4", base_name="scan")
```

---

(detector-selection)=
## Detector Selection

`counters.plotselect()` configures which scaler channels are used as
detectors and monitor in all scan plans. Called without arguments, it prints
a table of available channels and prompts interactively:

```
counters.plotselect()
```

```
+---+-------------------+----------+
| # | Detector          | Monitor? |
+---+-------------------+----------+
| 0 | scaler1_ch1 (I0)  |    *     |
| 1 | scaler1_ch2 (I1)  |          |
| 2 | scaler1_ch3 (I2)  |          |
...
Enter detector number(s) [0]: 2
Enter monitor number [0]: 0

counters:
  detectors : [scaler1_ch3]
  monitor   : scaler1_ch1
```

Alternatively, pass indices directly (no prompt):

```python
# Single detector (index 9), monitor at index 8
counters.plotselect(9, 8)

# Multiple detectors, same monitor
counters.plotselect([6, 9], 8)
counters.plotselect([14, 19], 5)
```

Inspect the current selection at any time:

```python
print(counters)           # prints selection table
counters.detectors        # list of active detector objects
counters.monitor          # active monitor channel name
```

---

## IPython Magics

Several IPython magic commands provide convenient shortcuts for motor control:

```python
# Move a motor to an absolute position (blocking)
%mov motor_name 10.5
%mov energy 7.245
%mov phi 45

# Multiple motors at once
%mov energy 7.245 phi 45

# Relative move
%movr motor_name 0.1
%movr phi -5

# Show positions of all named motors
%wa

# Show positions and software limits for specific motors
%wm motor1 motor2
```

These are equivalent to running `RE(mv(...))` but more concise for interactive use.

---

## Basic Scan Workflow

A typical scan sequence:

```python
# 1. Set up the experiment (once per session or sample change)
experiment_setup()

# 2. Select detectors
counters.plotselect(9, 8)

# 3. Set energy
%mov energy 7.514

# 4. Align sample
RE(lup(tabx, -1, 1, 50, 0.2))

# 5. Start new SPEC file
newSpecFile("TbFe_300K")

# 6. Add a comment
spec_comment("Sample: TbFe, T = 300 K, field = 0 T")

# 7. Scan
RE(ascan(energy, 7.4, 7.7, 150, 1.0))
```

---

## Finding and Loading Devices

```python
# List all available devices from devices.yml
find_loadable_devices()

# Filter by hutch or function
find_loadable_devices(label="4idg")
find_loadable_devices(label="detector")
find_loadable_devices(name="kb")       # substring match

# Connect a device not loaded at startup
load_device("eiger")

# Disconnect and remove from baseline
remove_device("eiger")

# Access a device by name using the registry
from apsbits.core.instrument_init import oregistry
dev = oregistry.find("huber_euler")
```

---

## Accessing Data

Runs are stored in the databroker catalog (`cat`):

```python
run = cat[-1]            # most recent run
run = cat[-2]            # second-to-last run
run = cat[42]            # by scan_id

# Read primary data stream
ds = run.primary.read()  # returns xarray Dataset
ds["energy"]             # energy axis
ds["scaler1_ch9"]        # detector channel

# Quick plot
import matplotlib.pyplot as plt
plt.plot(ds["energy"], ds["scaler1_ch9"] / ds["scaler1_ch8"])
```

Peak finding from the last scan:

```python
peaks.cen    # center-of-mass position of the peak
peaks.max    # position of maximum
peaks.com    # alias for center-of-mass
```

---

## Energy Tracking

Configure which devices follow the monochromator when energy changes:

```python
energy.tracking_setup(["undulators_ds", "pr2"])

# Check which devices are currently tracked
energy.tracking

# Fine-tune the undulator offset relative to the mono
undulators.ds.energy_offset.put(-0.063)
undulators.ds.energy_deadband.put(0.002)
```

---

## RunEngine Status

```python
RE.md                     # view all persistent metadata
RE.md["scan_id"]          # current scan counter
RE.md["proposal_id"] = "GUP-12345"   # set metadata

RE.abort()    # abort current plan (cleanup may not run)
RE.stop()     # graceful stop (cleanup runs)
RE.pause()    # pause mid-scan (can resume)
RE.resume()   # resume after pause or RE.request_pause()
```
