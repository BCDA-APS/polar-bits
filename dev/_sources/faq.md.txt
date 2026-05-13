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

After any scan the `peaks` object is updated with statistics from the last
scan:

```python
peaks.cen    # center-of-mass position of the peak
peaks.com    # alias for center-of-mass
peaks.max    # position of the maximum value
peaks.min    # position of the minimum value
```

`peaks` reports results per detector signal. If more than one detector was
active, index by signal name:

```python
peaks.cen["scaler1_ch9"]    # center-of-mass for channel 9
peaks.max["scaler1_ch9"]    # position of maximum for channel 9
```

Move a motor to the peak center:

```python
%mov tabx peaks.cen["scaler1_ch9"]
```

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
