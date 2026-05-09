# General Examples

This page covers session setup and common operations that apply to all beamlines.

---

## Experiment Setup

`experiment_setup()` collects the metadata needed to organize data into the
correct folders and associate it with an APS proposal and ESAF. It can be run
**interactively** (prompts at the command line) or **non-interactively** by
passing all arguments as keyword parameters.

After every successful setup, the resulting state is also saved to a small
YAML snapshot at `<base_experiment_path>/.polar_experiment.yml`, so a later
session can pick up where you left off — see [Resuming](#resuming-an-experiment)
below.

### Interactive mode

Call with no arguments — the function prompts for each field in sequence:

```python
experiment_setup()
```

The prompts walk through:

1. **ESAF ID** — enter the APS ESAF number (or `dev` to skip for development sessions)
2. **Proposal ID** — the APS proposal number (or `dev`)
3. **Server** — choose between `dserv` (local storage) and data management (`data management`)
4. **Experiment name** — must match an existing experiment in the DM system if using DM
5. **Sample name** — free text; creates a sub-folder under the experiment path
6. **Scan ID reset** — optionally reset the Bluesky `scan_id` counter
7. **File base name** — prefix for SPEC file names (e.g. `scan` → `scan_0001`)

After completing setup, the SPEC writer is configured, `RE.md` is populated,
and data will be written to the correct experiment path automatically.

### Data Management auto-detect

`experiment_setup()` probes the DM system at the start of every call. If DM
is unreachable (server down, bad config, missing env file), it logs a single
warning and falls back to `server="dserv"` automatically — ESAF / proposal
prompts are skipped and metadata is stamped as `dev`. **You no longer need a
`skip_DM` flag.** To force the bypass even when DM is reachable, use any of:

- `experiment_setup(server="dserv", ...)` — pick the dserv path explicitly
- `experiment_setup(esaf_id="dev", proposal_id="dev", ...)` — record-only bypass
- Type `dev` at any prompt during interactive setup

The DM voyager DAQ start (which can change file permissions) is now
**off by default**. Set `experiment.start_daq = True` in your startup
script if you need it.

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

### `reset_scan_id` semantics

`RE.md["scan_id"]` stores the **last completed** scan number; the next
scan is `scan_id + 1`. So:

| Value | Effect |
|-------|--------|
| `-1` (default) | Leave `RE.md["scan_id"]` untouched. Used by `experiment_resume()` and `experiment_load_from_bluesky()`. |
| `0` | Fresh start: next scan will be `1`. |
| `47` | Continue numbering: next scan will be `48`. |
| `None` | Interactive prompt ("Reset last scan_id to 0? [no]"). |
| any other negative int | Logs a warning, leaves `RE.md["scan_id"]` untouched. |

If `RE.md["scan_id"]` is still missing after `experiment_setup()` runs
(e.g. fresh session and `reset_scan_id=-1`), `setup()` defaults it to `0`
and emits a visible warning so you know the value was invented rather
than inherited.

(resuming-an-experiment)=
### Resuming an experiment

Two complementary ways to pick up where you left off:

**`experiment_resume()`** — restore everything from the YAML snapshot saved
during the previous `experiment_setup()`. Does **not** contact DM, so it
works even when DM is down.

```python
experiment_resume()              # auto-discover the snapshot
experiment_resume("/path/to/dir") # explicit base path or .yml file
```

With no arguments, `resume()` looks first in the current working
directory (`setup_path()` `chdir`s into the experiment dir during normal
setup, so this almost always succeeds), then falls back to the
`base_experiment_path` recorded in the last scan in `cat[-1]`. If both
snapshots exist and point at *different* experiments, you'll be asked
which one to use.

**`experiment_load_from_bluesky()`** — re-derive the metadata from a
specific Bluesky run document. Restores `RE.md["scan_id"]` so numbering
continues from the loaded run.

```python
experiment_load_from_bluesky()    # uses cat[-1]
```

### Changing sample mid-experiment

```python
experiment_change_sample(sample_name="Fe3O4", base_name="scan")
```

This rotates the SPEC file and writes a fresh snapshot to disk.

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

### polartools

[polartools](https://github.com/APS-4ID-POLAR/polartools) provides higher-level
data loading and inspection utilities available in the session namespace:

```python
# Print metadata summary for recent runs
show_meta(last=-1, db=cat)      # most recent run
show_meta(db=cat)               # all runs in catalog

# Query runs matching metadata fields
db_query(cat, {"sample": "Fe3O4", "proposal_id": "GUP-12345"})

# Load a scan as a pandas DataFrame
df = load_table(-1, cat)
```

---

## Energy Tracking

Configure which devices follow the monochromator when energy changes:

```python
# Iterative. Displays the available devices and you enter their corresponding numbers
energy.tracking_setup()
# Or not interactive:
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
