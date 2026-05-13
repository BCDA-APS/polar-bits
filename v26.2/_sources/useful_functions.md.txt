# Useful Functions

A reference of the session-level helpers — the functions and singletons
you call interactively to configure per-experiment state, restore a
session after a restart, manage devices, and annotate data. Most of the
setup helpers in the first section auto-snapshot their values into
`RE.md["session_state"]`, so a later restart can re-apply everything via
[`restore_session_state()`](#session-restore).

Scan plans (`lup`, `ascan`, `grid_scan`, `cen`, `com`, `maxi`, `mini`,
…) live in [Scan Plans](plans.md). Device classes are in the
[Device Reference](devices_reference.md) and [Devices Guide](devices_guide.md).

---

## Per-session setup helpers

Calling each of these once per experiment configures a session-level
knob and auto-saves the resulting state into `RE.md["session_state"]`.
After a bluesky restart, `restore_session_state()` re-applies them.

### `temperature_setup(label)` — active temperature controller

Resolves the requested controller from
`id4_common.utils.temperature_setup.TEMPERATURE_CONTROLLERS` and
injects three names into the session: `tc` (setpoint, movable), `ts`
(sample readback), and `TEMPERATURE_CONTROLLER` (the active label).
Adds `ts` to the baseline so the sample temperature lands in every
scan.

```python
temperature_setup("g")        # 4IDG LakeShore 336 (default loop)
temperature_setup("g-340")    # 4IDG LakeShore 340
temperature_setup("h-9T")     # 4IDH 9 T magnet VTI
temperature_setup()           # interactive prompt — shows known labels

mv tc 295                     # set the setpoint to 295 K
te(295)                       # equivalent shortcut
ts.get()                      # current readback
```

To add a new controller, edit `TEMPERATURE_CONTROLLERS` (a single
`label → (device_name, setpoint_attr_path, readback_attr_path)`
tuple). No class changes, no `devices.yml` edits.

### `pr_setup()` — phase retarders for XMCD

Interactive setup for the phase-retarder stack used in helicity
switching: which PR to track, which PR to oscillate, the offset
positioner and value, and the PZT center. Call with no arguments to
walk through every PR in the registry:

```python
pr_setup()
```

Or set the three exposed attributes directly when you already know
what you want:

```python
pr_setup.positioner    = oregistry.find("pr2_pzt_localdc")
pr_setup.offset        = oregistry.find("pr2_pzt_offset_microns")
pr_setup.oscillate_pzt = True
```

Each assignment auto-saves into `RE.md["session_state"]`. Print the
current configuration with `print(pr_setup)`.

### `qxscan_setup()` — XAFS-style energy scans

Interactive wizard that configures the pre-edge / edge / post-edge
regions for the `qxscan` plan. Energies are stored relative to the
absorption edge.

```python
qxscan_setup()                              # interactive
qxscan_setup.save_params_json("my.json")    # snapshot to disk
qxscan_setup.load_params_json("my.json")    # restore from disk
qxscan_setup.load_from_scan(scan_id)        # restore from a previous run

print(qxscan_setup)                         # show current setup
```

Both `qxscan_setup()` and `load_params_json()` auto-save into
`RE.md["session_state"]`. See [the qxscan section in
plans.md](plans.md#xafs-energy-scan-qxscan) for the scan plan itself.

### `undulator_setup(...)` — undulator offsets and harmonics

Sets the upstream (us) / downstream (ds) undulator energy offset
relative to the monochromator and picks the harmonic. Pass nothing for
an interactive prompt; pass keyword args for a non-interactive setup:

```python
undulator_setup()                                          # prompts
undulator_setup(ds_off=-0.063)                             # ds offset only
undulator_setup(ds_off=-0.063, ds_harm=3, us_off=-0.063)   # both sides
```

Auto-saves into `RE.md["session_state"]`. Tracking on/off is managed
separately via `energy.tracking_setup` (below).

### `energy.tracking_setup([names])` — which devices follow the mono

Picks the energy-trackable devices that should move when the
monochromator energy changes (typically the undulators and one phase
retarder).

```python
energy.tracking_setup()                              # interactive table
energy.tracking_setup(["undulators_ds", "pr2"])      # explicit list
energy.tracking_setup([])                            # disable all
energy.tracking                                      # print current state
```

Auto-saves into `RE.md["session_state"]`.

### `counters.plotselect(...)` — active detectors and monitor

Configures which scaler channels every scan plan plots, monitors, and
reads. Accepts indices, single device objects, or lists of either.

```python
counters.plotselect()                  # interactive prompt
counters.plotselect(0, 1)              # detector index 0, monitor index 1
counters.plotselect(dets=0, mon=1)     # equivalent named-arg form
counters.plotselect(
    dets=[0, 2], mon=1, extra_read=[3]
)                                      # multi-detector + extra readout
print(counters)                        # show current selection
```

Auto-saves into `RE.md["session_state"]`.

### `crl_setup(hutch)` and `crl_size(focal_size)` — CRL focusing

```python
crl_setup("g")           # apply the 4IDG sample-position offset
crl_setup("h")           # apply the 4IDH offset
crl_setup()              # interactive prompt

crl_size(50)             # focal size in µm; < 5 triggers crl.minimize_button
mov crl.beamsize 10      # write 10 µm directly to focalSize
                         # (returns immediately; no setpoint <-> readback wait)
```

`crl.beamsize` is a microns handle (PR #61) — the underlying meter
PVs are still reachable as `crl.beamsize.setpoint` / `crl.beamsize.readback`.

---

## Session restore

The recommended path after a bluesky restart inside the same
experiment is the prebuilt one-liner:

```python
import id4_common.macros.startup_common  # noqa: F401
```

That import runs `experiment_resume()` followed by
`restore_session_state()` and prints a per-knob status summary.

### `restore_session_state(state=None)` — re-apply auto-saved knobs

Reads `RE.md["session_state"]` (or the `state` dict you pass) and
re-applies every saved sub-key. Returns a `{knob_group: status}` dict;
restore never raises — a missing device or single failed `.put()` is
logged and the rest of the restore continues.

```python
status = restore_session_state()
for knob, msg in status.items():
    print(f"  {knob:18}  {msg}")
# "applied" / "skipped: <reason>" / "failed: <Exception>"
```

`restore_session_state` is imported into the interactive namespace by
`_common_startup.py`, so no extra `from … import` is needed.

### `save_session_state()` — manual snapshot (escape hatch)

You normally don't need this — every supported setup helper auto-saves
when you call it. `save_session_state()` is the explicit API if you
want to force a snapshot without re-running the helpers:

```python
save_session_state()
```

Same return shape as `restore_session_state()`.

---

## Experiment lifecycle

### `experiment_setup(...)` — start or re-configure an experiment

Collects the metadata that organizes data into the right folders and
associates it with an APS proposal and ESAF. Run interactively (no
args) or non-interactively (all kwargs):

```python
experiment_setup()                          # prompts
experiment_setup(
    esaf_id=281924,
    proposal_id="1014446",
    base_name="scan",
    sample="EuAl4",
    server="dserv",
    experiment_name="Frontini_26-1",
    reset_scan_id=0,
)
```

Writes a `.polar_experiment.yml` snapshot to the experiment directory.
See [General Examples](examples/general.md#experiment-setup) for the
full parameter description and the `reset_scan_id` table.

### `experiment_resume(path=None)` — restore from the YAML snapshot

```python
experiment_resume()              # auto-discover (cwd or cat[-1])
experiment_resume("/path/to/dir")  # explicit base path or .yml file
```

Does not contact DM; works even when DM is down.

### `experiment_load_from_scan(scan_id=-1)` — restore from a Bluesky run

Re-derives the metadata from a specific run document; restores
`RE.md["scan_id"]` so numbering continues from the loaded run.

```python
experiment_load_from_scan()       # last scan (cat[-1])
experiment_load_from_scan(1234)   # specific scan id
```

### `experiment_change_sample(sample_name=...)` — rotate sample mid-experiment

```python
experiment_change_sample(sample_name="Fe3O4", base_name="scan")
```

Rotates the SPEC file and writes a fresh snapshot to disk.

---

## Device loading

These helpers operate on the runtime device registry (`oregistry`).
See [Devices Guide](devices_guide.md) for the full pattern and the
deferred-EPICS-connection rule.

```python
find_loadable_devices()                      # all entries from devices.yml
find_loadable_devices(label="4idg")          # filter by label
find_loadable_devices(name="kb")             # substring match on name
find_loadable_devices(name="crl", exact_name=True)

load_device("crl")                           # connect (or reconnect) one device
remove_device("crl")                         # disconnect + drop from baseline
reload_all_devices()                         # everything in devices.yml
reload_all_devices(stations=["core", "4idh"])  # one beamline only
```

### `load_vortex(electronics, ...)` — pick the vortex electronics at runtime

Vortex electronics (xspress3 vs dante, 1-element vs 4/7-element) are
chosen per session rather than hardcoded in `devices.yml`. After
loading, the device is added to `__main__` regardless of whether the
EPICS connection succeeded so the user can still call configuration
methods.

```python
load_vortex("xspress4")             # 4-element xspress3
load_vortex("xspress7")             # 7-element xspress3
load_vortex("dante1")               # 1-element dante
load_vortex("dante4")               # 4-element dante
```

---

## SPEC files and annotations

```python
newSpecFile("my_experiment")        # creates 04_09_my_experiment.dat
                                    # (mm_dd_<title>.dat; resets scan_id
                                    # to last in file if file already exists)

spec_comment("Sample aligned, beam 50x50 µm")
                                    # writes a #C line to the active SPEC file
```

`specwriter` (the callback instance) is also available in the session
if you need to introspect or rotate it manually.

---

## Quick shortcuts (`shorts.py`)

A handful of one-liners for very common operations.

```python
te(295)              # set active temperature controller setpoint to 295
                     # (equivalent to: mv tc 295)

opt()                # move positioner of last scan to its center-of-mass
opt("max")           # … or to its maximum

crl_setup("g")      # see "CRL focusing" above
crl_size(50)        # see "CRL focusing" above
```

---

## IPython magics (`local_magics.py`)

Available without parentheses at the prompt:

```
%mov motor position             # absolute move (waits for completion)
%mov motor1 pos1 motor2 pos2    # multi-motor parallel move
%movr motor delta               # relative move
%wm motor [motor2 ...]          # show motor positions
%wa                             # show all positioners
```

---

## Listing what's available

```
list_functions()                 # print every callable in __main__
list_functions("scan")           # filter by substring
%whos                            # IPython: list all variables with types

ascan?                           # show ascan() docstring
ascan??                          # show ascan() source
counters?                        # show CountersClass docstring
```
