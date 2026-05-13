# Frequently Asked Questions

---

## How do I enable or disable live plots during scans?

Live plots are controlled by the `BEC.PLOTS` setting in `iconfig.yml`:

```yaml
BEC:
  PLOTS: false   # set to true to enable live plots
```

This setting applies at startup. For non-GUI sessions (e.g. SSH without X
forwarding) keep it `false`.

You can also toggle plots **within a running session** without restarting:

```python
bec.enable_plots()    # turn on live plots for subsequent scans
bec.disable_plots()   # turn off live plots
```

Similarly, you can control the printed table and baseline report:

```python
bec.enable_table()      # show scan data as a table in the terminal
bec.disable_table()
bec.enable_baseline()   # print baseline readings at the start of each scan
bec.disable_baseline()
```

---

## How do I add or remove a device from the baseline?

The **baseline stream** records all tagged devices once before and once after
every scan, providing a passive log of instrument state.

### Persistent change (recommended)

Add or remove the `"baseline"` label from the device entry in `devices.yml`,
then reload devices:

```yaml
# devices.yml — add "baseline" to make a device part of the baseline
id4_common.devices.my_device.MyDevice:
  - name: mydev
    labels: ["core", "4idb", "baseline"]   # <-- add "baseline" here
```

```python
reload_all_devices()   # re-reads devices.yml and reconnects everything
```

### Runtime change (current session only)

Load a device and it will be added to the baseline automatically if its
`devices.yml` entry carries the `"baseline"` label:

```python
load_device("mydev")      # connects device; adds to baseline if labelled
```

Remove a device from both the registry and the baseline:

```python
remove_device("mydev")    # disconnects and removes from baseline
```

To inspect which devices are currently in the baseline:

```python
[d.name for d in sd.baseline]
```

---

## How do I pause, resume, or abort a running scan?

Press **Ctrl-C** once during a scan to request a deferred pause — the
RunEngine finishes the current step before stopping. Then:

```python
RE.resume()   # continue from where the scan paused
RE.stop()     # end the scan cleanly; data collected so far is saved
RE.abort()    # end the scan; run is marked exit_status='aborted'
RE.halt()     # emergency stop — no cleanup, use as a last resort
```

**Key differences:**

| Command | Cleanup runs? | Exit status |
|---------|--------------|-------------|
| `RE.resume()` | — (continues) | — |
| `RE.stop()` | Yes | `success` |
| `RE.abort()` | Yes | `aborted` |
| `RE.halt()` | No | `fail` |

Data from stopped or aborted scans is still saved to the catalog and SPEC
file. `RE.halt()` may leave hardware in an undefined state — prefer
`RE.stop()` or `RE.abort()` unless there is an emergency.

---

## Why did my scan pause automatically?

The RunEngine installs **shutter suspenders** at startup. If the photon
shutter closes mid-scan (e.g. due to a beam dump, interlock trip, or manual
close), the RunEngine automatically suspends rather than continuing with no
beam. It will resume automatically once the shutter re-opens.

If you need to check the current RunEngine state:

```python
RE.state      # 'running', 'paused', 'idle', etc.
```

If the beam has returned but the scan has not resumed after a minute, you
can resume manually:

```python
RE.resume()
```

If you want to abort instead of waiting:

```python
RE.abort()
```

---

## How do I find the peak center after a scan?

The recommended path is the peak-finding plans in
`id4_common.plans.peak_position` — they read the last scan from the
catalog, compute the requested statistic, and **move the positioner
there in one step**:

```python
RE(cen())     # move to the FWHM midpoint of the last scan
RE(com())     # move to the center-of-mass (centroid)
RE(maxi())    # move to x at maximum y
RE(mini())    # move to x at minimum y
```

These work for both 1-D scans and 2-D `grid_scan` / `rel_grid_scan`.
Pass `confirm=False` to skip the >5-min interactive confirmation, or
`positioner=`/`detector=` to override the defaults. See
[Peak-Finding Plans](plans.md#peak-finding-plans) for the full API.

If you only want the values without moving, the BEC `peaks` object is
updated after every scan:

```python
peaks.com    # x at center-of-mass (centroid)
peaks.cen    # x at FWHM midpoint  ← NOT the same as peaks.com
peaks.max    # x at maximum y
peaks.min    # x at minimum y
peaks.fwhm   # full-width at half-max
```

`peaks` reports results per detector signal — index by signal name:

```python
peaks.com["scaler1_ch9"]    # centroid for channel 9
peaks.cen["scaler1_ch9"]    # FWHM midpoint for channel 9
```

Or use the diagnostic helpers (`peak_pos()`, `pmax()`, `pmin()`) which
print + return the same statistics for the last scan without moving
anything.

---

## How do I get help on a scan plan or function?

In IPython, append `?` to any function name to see its docstring, or `??`
to see its full source code:

```python
lup?          # show the lup() docstring (arguments, description, examples)
ascan?        # show the ascan() docstring
grid_scan?    # show grid_scan() help
counters?     # show the counters object docstring

lup??         # show lup() full source code
```

To see all plans and functions currently in the session namespace:

```python
%whos         # list all variables, their types and sizes
```

To list available scan plans specifically, filter by type:

```python
# Plans are generator functions — search by name pattern
[k for k in dir() if "scan" in k]
```

To explore devices available for loading:

```python
find_loadable_devices()              # all devices in devices.yml
find_loadable_devices(label="4idg")  # filter by label
find_loadable_devices(name="kb")     # substring match on name
```

---

## How do I switch the active temperature controller?

Call `temperature_setup(label)` once. It resolves the requested
controller from `id4_common.utils.temperature_setup.TEMPERATURE_CONTROLLERS`
and injects three names into the session: `tc` (setpoint, movable),
`ts` (sample readback), and `TEMPERATURE_CONTROLLER` (the active
label string). `ts` is added to the baseline so the sample
temperature lands in every scan automatically.

```python
temperature_setup("g")        # 4IDG LakeShore 336 (default loop)
temperature_setup("g-340")    # 4IDG LakeShore 340
temperature_setup("h-9T")     # 4IDH 9 T magnet VTI

mv tc 295                     # set the setpoint to 295 K
te(295)                       # equivalent shortcut

ts.get()                      # current sample-temperature readback
```

To add a new controller, edit `TEMPERATURE_CONTROLLERS` (a single
`label → (device_name, setpoint_attr_path, readback_attr_path)`
tuple). No class changes, no devices.yml edits.

---

## How do I restore my session after a bluesky restart?

Each setup helper (`pr_setup`, `energy.tracking_setup`,
`counters.plotselect`, `undulator_setup`,
`qxscan_setup.load_params_json`) auto-saves its current values into
`RE.md["session_state"]` — apsbits' `PersistentDict` survives a
restart. After restarting bluesky, call `restore_session_state()` to
re-apply every saved knob in one go:

```python
status = restore_session_state()
for knob, msg in status.items():
    print(f"  {knob:18}  {msg}")
```

`status` reports `applied` / `skipped: <reason>` / `failed: <Exception>`
per knob group — restore never raises, a missing device or single
failed put is logged and the rest of the restore continues.

A one-line wrapper that calls `experiment_resume()` first and prints
the status summary itself ships with the package:

```python
import id4_common.macros.startup_common  # noqa: F401
```

See [Writing Macros](examples/writing_macros.md#recoverable-session-state)
for the full restart template.

---

## How do I set the CRL focal size?

The recommended path is the `crl_size` shortcut, which handles the
`< 5 µm` "minimize" path and the µm → m conversion:

```python
crl_setup("h")          # switch the offset to the active hutch (g or h)
crl_size(50)            # 50 µm focal size
crl_size(2)             # < 5 µm triggers crl.minimize_button
```

For direct `mov`-style control, `crl.beamsize` is now a microns
handle (PR #61) — `mov crl.beamsize 10` writes 10 µm to the
underlying `focalSize` PV and returns immediately without waiting
for `fSize_actual` to converge (the two PVs do not always agree, and
the previous `EpicsSignal` with `write_pv` would hang). The raw
meter-valued PVs are still reachable as `crl.beamsize.setpoint` /
`crl.beamsize.readback`.
