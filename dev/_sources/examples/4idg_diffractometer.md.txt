!# 4IDG: Diffractometer Usage

4IDG is the diffraction hutch. The 6-circle diffractometer is controlled through
[hklpy2](https://blueskyproject.io/hklpy2/) for reciprocal-space navigation.
Two configurations are available depending on which insert is mounted:

- `huber_euler` — Huber Eulerian cradle
- `huber_hp` — high-precision goniometer

The HKL utility functions are provided by `hkl_utils_hklpy2.py` and cover
sample management, orientation, forward/inverse calculations, mode selection,
constraint management, and configuration save/restore.

---

## Command Reference

### Diffractometer and status

| Command | Description |
|---------|-------------|
| `change_diffractometer(name)` | Select active diffractometer; update motor aliases, h/k/l aliases, and axis constraints |
| `set_detector()` | Select Eiger or point detector/analyzer arm |

### Moving

| Command | Description |
|---------|-------------|
| `wh` | Current H K L, motor positions, energy, PSI (no parentheses) |
| `ca(h, k, l)` | Calculate motor angles for HKL without moving |
| `ubr(h, k, l)` | Move to HKL (runs own RunEngine) |
| `RE(br(h, k, l))` | Move to HKL as a Bluesky plan |
| `uan(gamma, mu)` | Move gamma and mu together |

### Reciprocal-space scans

| Command | Description |
|---------|-------------|
| `hscan(start, stop, num, time, …)` | Sweep `h` only (k, l held fixed by the engine) |
| `kscan(start, stop, num, time, …)` | Sweep `k` only |
| `lscan(start, stop, num, time, …)` | Sweep `l` only |
| `hklscan(h1, h2, k1, k2, l1, l2, num, time, …)` | Linear (h, k, l) trajectory |

### Peak finding from a previous scan

| Command | Description |
|---------|-------------|
| `peak_pos(scan_id=-1)` | Print peak statistics (com, cen, max, min, fwhm) for the scan's detectors; supports 1D **and** 2D `grid_scan` |
| `RE(cen())` | Move scan motor(s) to the FWHM midpoint |
| `RE(com())` | Move scan motor(s) to the centroid (center-of-mass) |
| `RE(maxi())` | Move scan motor(s) to the x at peak maximum |
| `RE(mini())` | Move scan motor(s) to the x at peak minimum |
| `RE(cen2())` / `RE(maxi2())` / `RE(mini2())` | Legacy fallback that reads from the live `BestEffortCallback().peaks` (1D only); use when the new plans can't read your scan |

### Sample management

| Command | Description |
|---------|-------------|
| `newsample()` | Add sample interactively |
| `sampleList()` | List all samples; mark current one |
| `sampleChange(name)` | Switch active sample |
| `sampleRemove(name)` | Remove a sample |
| `setlat(a,b,c,α,β,γ)` | Set lattice constants (no args = interactive) |
| `update_lattice(par)` | Refine one lattice constant from current HKL position |
| `theta0()` | Cubic-sample 2θ zero-shift and `a0` from two reflections |

### Orientation / UB matrix

| Command | Description |
|---------|-------------|
| `or0(h, k, l)` | Set primary reflection at current motor positions |
| `or1(h, k, l)` | Set secondary reflection at current motor positions |
| `setor0()` | Set primary reflection — prompts for motor positions and HKL |
| `setor1()` | Set secondary reflection — prompts for motor positions and HKL |
| `list_reflections()` | List all reflections for current sample |
| `list_orienting()` | List only the two orienting reflections |
| `set_orienting()` | Interactively pick which reflections are orienting |
| `or_swap()` | Swap first and second orienting reflections |
| `del_reflection()` | Delete a non-orienting reflection |

### Modes, azimuth and constraints

| Command | Description |
|---------|-------------|
| `setmode(n)` | Set diffractometer mode by number (no args = interactive list) |
| `setaz(h, k, l)` | Set azimuthal reference vector |
| `freeze(val)` | Freeze constant axis for current mode (no args = use current position) |
| `freeze_general()` | Interactively freeze all constant axes |
| `show_constraints()` | Show angle limits and cut point for each axis |
| `set_constraints(…)` | Set angle limits and optional cut point (no args = interactive per axis) |
| `reset_constraints()` | Reset all limits to defaults |

### Analyzer

| Command | Description |
|---------|-------------|
| `analyzer_configuration(energy)` | Select crystal and set d-spacing |
| `analyzer_set()` | Calibrate current motor position to calculated Bragg angle |

### Configuration save/restore

| Command | Description |
|---------|-------------|
| `write_config(name)` | Save sample, UB, reflections, constraints to YAML |
| `read_config()` | Load configuration from YAML (overwrite or append) |
| `restore_huber_from_scan(id)` | Restore orientation from a previous scan |

---

## Starting the Session

Use the beamline startup script from a terminal:

```bash
bluesky-4idg
```

This activates the `polar-bits` conda environment and launches IPython with all
4IDG devices pre-loaded (equivalent to `from id4_g.startup import *`).

---

## Selecting the Active Diffractometer

Two diffractometers are available. Call `change_diffractometer()` to select one.
This sets the active diffractometer for all HKL utility functions, applies the
appropriate axis constraints, and injects motor aliases into the session
namespace:

```python
change_diffractometer("huber_euler")   # Eulerian cradle
change_diffractometer("huber_hp")      # High-precision goniometer
change_diffractometer()                # interactive prompt
```

### Motor aliases created automatically

After `change_diffractometer("huber_euler")`:

| Alias | Motor |
|-------|-------|
| `mu`, `gamma`, `delta`, `chi`, `phi`, `tau` | Diffractometer circles (angular space) |
| `cryox`, `cryoy`, `cryoz` | Sample stage |
| `ath`, `atth`, `eta`, `achi` | Analyzer arm |

After `change_diffractometer("huber_hp")`:

| Alias | Motor |
|-------|-------|
| `mu`, `gamma`, `delta`, `chi`, `phi`, `tau` | Diffractometer circles (angular space) |
| `xeryon` | Xeryon piezo rotation |
| `x`, `y`, `z` | Sample stage |
| `nanox`, `nanoy`, `nanoz` | Nano-focusing stage |
| `basex`, `basey`, `basez` | Base stage |
| `ath`, `atth`, `eta`, `achi` | Analyzer arm |

The reciprocal-space pseudo-axes `h`, `k`, `l` are also injected automatically
into the session namespace by `change_diffractometer()`. They behave like
ophyd positioners — anywhere a real motor is accepted you can pass `h`, `k`,
or `l` instead, e.g. `mv(l, 2.0)`, `lup(l, -0.05, 0.05, 21, 0.5)`,
`ascan(k, -0.1, 0.1, 40, 0.5)`, or `cen(l)` after a scan.

---

## Per-Session Startup

Users typically run a per-session startup file to set additional shortcuts and
load experiment-specific settings:

```python
%run startup_4idg.py
```

```python
change_diffractometer("huber_euler")
```

`change_diffractometer()` injects motor aliases and the reciprocal-space
pseudo-axes `h`, `k`, `l` into the session namespace automatically.

---

## Sample Management

### Add a new sample

`newsample()` prompts interactively for the sample name and lattice constants.
It also seeds two default reflections — `(0 0 2)` and `(2 0 0)` — computes an
initial UB matrix from them, and sets `(1 0 0)` as the azimuthal reference
vector. These defaults get the diffractometer into a working state immediately;
replace them with measured reflections using `or0()`/`or1()` or
`setor0()`/`setor1()`, and update the azimuthal reference with `setaz()` as
needed.

```python
newsample()
```

### List, switch, and remove samples

```python
sampleList()                  # list all defined samples; mark current one
sampleChange("Si")            # switch to sample named "Si"
sampleChange()                # interactive selection
sampleRemove("old_sample")    # remove a sample by name
sampleRemove()                # interactive selection
```

### Update lattice constants

Set lattice constants directly or interactively:

```python
setlat(5.43, 5.43, 5.43, 90, 90, 90)   # direct: a, b, c, alpha, beta, gamma
setlat()                                 # interactive with current values as defaults
```

Refine a single lattice constant from the current HKL position
(auto-detects which parameter to refine based on position):

```python
update_lattice()        # auto: refines a, b, or c depending on current HKL
update_lattice("c")     # refine only c
```

---

## Checking the Current Position

```python
wh     # print H K L, energy, motor positions, PSI — no parentheses
ca(1, 0, 0)     # calculate motor angles for (1 0 0) without moving
ca(1, 1, 0)     # calculate motor angles for (1 1 0) without moving
```

`wh` also snapshots the current reciprocal-space position into uppercase
globals `H`, `K`, `L` so you can reuse them at the prompt:

```python
wh
ubr(H, K, L + 0.01)     # step L by +0.01 from the position just printed
```

---

## Orientation (UB Matrix)

### Setting orientation reflections

Two workflows exist depending on whether you are at the peak or not.

**If you are physically at the peak** — use `or0()` / `or1()`, which capture
the current motor positions and only ask for H K L:

```python
# Move to the first reflection physically, then:
or0()             # record primary reflection at current motors — prompts for H K L
or0(0, 0, 2)      # record primary reflection — no prompt

# Move to the second reflection, then:
or1()             # record secondary reflection at current motors — prompts for H K L
or1(2, 0, 0)      # record secondary reflection — no prompt
```

**To enter motor positions manually** — use `setor0()` / `setor1()`, which
prompt for both motor positions and H K L:

```python
setor0()    # enter angles + H K L for primary reflection
setor1()    # enter angles + H K L for secondary reflection
```

The UB matrix is recalculated automatically whenever the orienting reflections
or lattice parameters are updated — including after `or0()`, `or1()`,
`setor0()`, `setor1()`, `or_swap()`, `set_orienting()`, `setlat()`, and
`update_lattice()`.

### Inspect and manage reflections

```python
list_reflections()         # list all reflections for the current sample
list_orienting()           # list only the two orienting reflections
set_orienting()            # interactively pick which reflections are orienting
or_swap()                  # swap first and second orienting reflections; recomputes UB
del_reflection()           # interactively delete a non-orienting reflection
```

---

## Cubic 2θ Zero-Shift and Lattice Constant

For a cubic sample, `theta0()` computes the 2θ zero-shift and the lattice
constant `a0` from any two stored reflections (Brueckel 1994). It assumes
horizontal scattering geometry (`gamma = 2θ`, `delta = 0`).

```python
theta0()
```

Workflow:

1. Measure two reflections (e.g. with `or0()` / `or1()` after centering on
   each Bragg peak).
2. Run `theta0()` — it lists all stored reflections, marks the two
   orienting ones as `first` / `second`, and prompts for the indices of the
   two reflections to use (defaults to the orienting pair).
3. The function prints the 2θ zero-shift, two estimates of `a0` (one from
   each reflection), and the corrected 2θ values.

Use the printed zero-shift to update the `gamma` motor offset, and the
`a0` value with `setlat()` or `update_lattice()`.

---

## Moving in Reciprocal Space

Move to an HKL position (executes as a Bluesky plan):

```python
RE(br(1, 0, 0))     # move to (1 0 0)
RE(br(2, 0, 0))     # move to (2 0 0)
```

Move directly without wrapping in `RE` (runs its own RunEngine):

```python
ubr(1, 0, 0)        # move to (1 0 0)
ubr(2, 0, 0)        # move to (2 0 0)
```

Move gamma and mu together (for detector arm alignment):

```python
uan(40, 20)         # move to gamma=40, mu=20
```

Move individual real-space axes with the `%mov` magic:

```python
%mov phi 5          # move phi to 5°
%mov chi 0
%mov delta 30
```

The `h`, `k`, `l` pseudo-axes also work with `mv`, `mvr`, `lup`, `ascan`,
`cen`, etc. — anywhere a real motor is accepted:

```python
RE(mv(l, 2.0))                         # move l to 2.0 (h, k held fixed)
RE(mvr(l, 0.01))                       # step l by +0.01
RE(lup(l, -0.05, 0.05, 21, 0.5))       # relative L-scan
RE(ascan(k, -0.1, 0.1, 40, 0.5))       # absolute K-scan
RE(cen(l))                             # center l on the last scan's COM
```

See [Scans in reciprocal space](#scans-in-reciprocal-space) for the
dedicated `hscan` / `kscan` / `lscan` / `hklscan` plans.

---

## Diffractometer Modes

`setmode()` lists all available modes (1-indexed). Selecting a mode
automatically freezes the unused detector angle at 0:

```python
setmode()       # interactive selection (shows numbered list)
setmode(1)      # e.g. "4-circles constant phi horizontal" → freezes delta=0
setmode(7)      # e.g. "4-circles bissecting horizontal"
setmode(12)     # e.g. "psi constant horizontal"
```

Available modes include (geometry-dependent):

- `4-circles constant phi horizontal`
- `4-circles constant mu horizontal`
- `4-circles constant chi horizontal`
- `4-circles bissecting horizontal`
- `4-circles constant omega horizontal`
- `psi constant horizontal`, `psi constant vertical`
- `zaxis + alpha-fixed`, `zaxis + beta-fixed`, `zaxis + alpha=beta`
- `lifting detector mu/omega/chi/phi`

---

## Azimuth Reference and Constraints

Set the azimuthal reference vector. This updates the psi-engine counterpart
diffractometer and reports the resulting PSI value:

```python
setaz(0, 0, 1)   # [001] azimuth reference
setaz(0, 1, 0)   # [010] azimuth reference
setaz()          # interactive prompt
```

Freeze the constant axis for the current mode. Behavior depends on mode:

- **Psi constant modes**: freezes psi (uses current psi if no argument)
- **Single-axis modes** (`constant phi/mu/chi`): freezes that axis (uses current
  motor position if no argument)
- **Other modes**: interactive prompt for each constant axis

```python
freeze()        # auto-detect from current mode; prompt or use current position
freeze(0)       # freeze axis at 0 (mode-dependent)
freeze(5)       # freeze axis at 5 (mode-dependent)
freeze_general()  # always prompts interactively for all constant axes
```

Show and manage axis constraints (angle limits and cut point). The cut point
defines the wrap-around for the axis: solutions are reported in the interval
`[cut, cut + 360)`.

```python
show_constraints()          # print low/high limits and cut point for each axis
reset_constraints()         # reset all limits to defaults
set_constraints()           # interactive: set limits/cut for each axis
set_constraints("phi")      # interactive: set limits/cut for one axis
set_constraints("phi", -180, 180)         # set limits only
set_constraints("phi", -180, 180, -180)   # set limits and cut point

# Set all 6 axes at once (limits only — 12 args):
set_constraints(-1,1, 0,90, -20,200, -180,180, -2,140, -5,50)

# Set all 6 axes with cut points (limits + cut — 18 args):
set_constraints(
    -1, 1, 0,
    0, 90, 0,
    -20, 200, -180,
    -180, 180, -180,
    -2, 140, 0,
    -5, 50, 0,
)
```

Interactive prompts accept either two numbers (`low high`) or three numbers
(`low high cut`), separated by spaces or commas. Press Enter to keep the
current values.

---

## Inverse Calculation

Convert real-space motor positions to reciprocal-space coordinates.
Motor order for 6-circle is `(gamma, mu, chi, phi, delta, tau)`:

```python
sol = huber_euler.inverse((40, 20, 90, 0, 0, 0))
print(sol.h, sol.k, sol.l)
```

---

## Scans

All plans use `counters.detectors` and `counters.monitor` by default
(see [General Examples](general.md) for detector selection).

### Scans in angular space

Scan individual diffractometer circles directly:

```python
# Rock phi around current position (relative scan, 50 pts, 1.0 s dwell)
RE(lup(phi, -1, 1, 50, 1.0))

# Scan delta (2θ) through a Bragg peak
RE(lup(delta, -0.5, 0.5, 50, 0.5))

# Scan chi for polarization dependence
RE(lup(chi, -5, 5, 50, 0.5))

# Absolute scan
RE(ascan(delta, 28, 32, 40, 0.5))
```

#### th-2th scan

`th2th` is a local plan that scans `mu` and `gamma` simultaneously with the
coupled 1:2 ratio. Arguments give the relative 2-theta (gamma) range; mu
moves at half that rate. Positions are restored after the scan (same as `lup`).

```python
RE(th2th(tth_start, tth_end, number_of_points, time_per_point))

# Examples
RE(th2th(-1, 1, 50, 0.5))    # ±1° in 2θ, 50 pts, 0.5 s/pt
RE(th2th(-2, 2, 100, 0.5))   # ±2° in 2θ, 100 pts
```

### Scans in reciprocal space

Two equivalent ways to scan a reciprocal-space axis:

1. **Generic plans with the `h`, `k`, `l` aliases** (set by
   `change_diffractometer()`) — `lup`, `ascan`, etc. work on the pseudo
   axes the same way they work on real motors:

   ```python
   RE(lup(l, 1.8, 2.2, 40, 0.5))      # relative L-scan through (0 0 2)
   RE(ascan(k, -0.1, 0.1, 40, 0.5))   # absolute K-scan
   ```

2. **Dedicated single-axis plans** `hscan` / `kscan` / `lscan` — thin
   wrappers around `ascan` on the matching pseudo axis. They take only
   `(start, stop, num, time)` and tag the run with their own `plan_name`,
   which makes them easier to identify in the catalog and works
   automatically with `peak()`'s positioner detection:

   ```python
   RE(lscan(1.8, 2.2, 40, 0.5))        # absolute L-scan
   RE(hscan(1.95, 2.05, 21, 0.5))      # absolute H-scan
   RE(kscan(-0.05, 0.05, 21, 0.5))     # absolute K-scan
   ```

   They forward `detectors`, `lockin`, `dichro`, `fixq`, `vortex_sgz`,
   `g_sgz`, `per_step`, and `md` to `ascan`:

   ```python
   RE(lscan(1.8, 2.2, 40, 0.5, dichro=True))
   ```

#### Linear (h, k, l) trajectory — `hklscan`

`hklscan` sweeps a straight line in reciprocal space from
`(h1, k1, l1)` to `(h2, k2, l2)` in `num` points. All three pseudo axes
move together; the diffractometer solves the angles at each point.

```python
RE(hklscan(h1, h2, k1, k2, l1, l2, num, time))

# Diagonal scan from (1, 0, 0) to (1, 0, 0.2):
RE(hklscan(1, 1, 0, 0, 0, 0.2, 21, 0.5))

# Off-axis cut crossing (2, 0, 0):
RE(hklscan(1.95, 2.05, -0.02, 0.02, 0, 0, 21, 0.5))
```

The `dichro`, `lockin`, `vortex_sgz`, `g_sgz`, `per_step`, and `md`
kwargs are forwarded to `ascan`. `fixq` is forced off (the scan *is* the
trajectory).

Center on a peak after a scan:

```python
RE(lup(l, 1.8, 2.2, 40, 0.5))
RE(cen(l))     # moves to the center-of-mass of the last scan
```

#### Peak position from a previous scan

`peak_pos`, `cen`, `com`, `maxi`, and `mini` (and the PR-#54 aliases
`peak` / `pmax` / `pmin`) compute peak statistics from a stored scan.
They work on any past run from the `4id_polar` catalog — useful for
revisiting a peak later in the session or for picking a specific
detector channel.

Backend: `apstools.utils.xy_statistics` for the 1D `com` / `max` / `min`
/ `fwhm`, `scipy.signal.find_peaks` for the FWHM-midpoint `cen`, and
`scipy.ndimage` for true 2D peak detection on `grid_scan` runs.

Print statistics for the last scan for every detector hinted in the
scan:

```python
peak_pos()                          # last scan, all hinted detectors
peak_pos(-3)                        # 3 scans back
peak_pos(1234, y="scaler1_ch14")    # specific scan, single detector
```

Move to a peak feature. Wrap in `RE()`:

```python
RE(lup(delta, -0.5, 0.5, 50, 0.5))
RE(cen())                           # move delta to the FWHM midpoint
RE(com())                           # move delta to the centroid
RE(maxi())                          # move delta to x at peak maximum
RE(mini())                          # move delta to x at peak minimum

# Pick a specific detector channel:
RE(cen(detector="scaler1_ch14"))

# Operate on an older scan:
RE(cen(scan_id=1234))

# Move a different positioner than the scan axis:
RE(cen(positioner=phi))
```

`cen` and `com` differ only for asymmetric peaks: `cen` is the midpoint
of the half-max crossings (matches bluesky's `PeakStats.cen`), `com`
is the moment-based centroid `Σx·y / Σy`.

For multi-motor 1D scans (`hklscan`, …) the move plans default to the
fastest-changing axis and prompt to confirm; pass `confirm=False` to
skip every interactive prompt. `th2th` always uses 2θ (`gamma`) — no
prompt. `psiscan` is rejected because the scan axis is a virtual extra,
not a movable positioner.

For 2D `grid_scan` runs the move plans default to moving **both** scan
motors in parallel to the 2D feature (issue #59):

```python
RE(grid_scan(cryox, -1, 1, 20, cryoy, -1, 1, 20, 0.2))
RE(cen())                           # one mv() moves cryox + cryoy together
RE(maxi(positioner=cryox))          # project to cryox, move only that axis
```

`peak_pos()` on a `grid_scan` returns motor-coordinate tuples
(`(cryox_val, cryoy_val)`) instead of scalars; per-axis `fwhm` is a
two-element tuple computed from 1D projections along each motor.

If the new plans can't read a scan (e.g. catalog isn't reachable),
fall back to the legacy `cen2` / `maxi2` / `mini2`. They read from
`BestEffortCallback().peaks` and only work on `cat[-1]` (the most
recently plotted run) — but require no catalog access.

For the HP diffractometer sample stage:

```python
RE(lup(x, -0.5, 0.5, 50, 0.1))        # sample X scan
RE(lup(y, -0.5, 0.5, 50, 0.1))        # sample Y scan
RE(lup(nanox, -0.05, 0.05, 50, 0.1))  # nanofocusing X
```

---

## 2D Maps

Raster scan over two motors:

```python
RE(grid_scan(
    cryox, -1, 1, 20,
    cryoy, -1, 1, 20,
    0.2,
))

RE(rel_grid_scan(
    nanoy, -3.5, 3.5, 45,
    nanox, -2, 2, 31,
    0.05,
    snake_axes=True,
))
```

---

## Analyzer

Configure and calibrate the analyzer arm. `analyzer_configuration()` prompts
for the analyzer crystal and sets its d-spacing. `analyzer_set()` calibrates
the motor position — use it when the analyzer is physically on peak to set the
motor offset so the reported position matches the calculated Bragg angles for
the current energy. Pass `"r"` to release (clear) the calibration offset:

```python
analyzer_configuration()      # select crystal, set d-spacing; optionally pass energy (keV)
analyzer_configuration(7.0)   # configure for 7.0 keV
analyzer_set()                # calibrate ath/atth offset to calculated Bragg angles (must be on peak)
analyzer_set("r")             # release calibration; restore raw motor positions
```

---

## Detector Selection

Switch between the Eiger area detector and the point detector/analyzer arm
(motors are 25° apart in delta):

```python
set_detector()    # interactive: (E)iger or (P)oint Detector/Analyzer
```

---

## Sample-Area Ringlight

The sample illuminator is exposed as `ringlight` and is read into the
baseline stream every scan. The IOC enum has six choices controlled
through convenience methods or `set_state`:

```python
ringlight.off()         # OFF
ringlight.full()        # 100%
ringlight.half()        # 50%
ringlight.quarter()     # 25%
ringlight.eighth()      # 12.5%
ringlight.rainbow()     # RAINBOW

ringlight.set_state(0)        # by index (0-5)
ringlight.set_state("half")   # by short name
ringlight.set_state("100%")   # by raw IOC label

ringlight.state.get()         # read current state ("OFF", "100", "50", ...)
```

---

## Saving and Restoring Configuration

### Write to file

Save the current diffractometer state (sample, reflections, UB matrix,
constraints, mode) to a YAML file in the current directory:

```python
write_config()              # saves to default_polar_config.yml
write_config("EuAl4_run1")  # saves to EuAl4_run1_polar_config.yml
write_config("EuAl4_run1", overwrite=True)  # skip confirmation prompt
```

### Read from file

Lists all `*_polar_config.yml` files in the current directory and prompts
to overwrite or append the current configuration. Restores samples,
azimuthal-reference extras (`h2`, `k2`, `l2` for psi-constant modes), and
constraints, then recomputes the UB matrix from the orienting reflections.
Wavelength and current mode are intentionally left untouched to avoid
silently retargeting motors.

```python
read_config()    # interactive file selection; choose overwrite or append
```

### Restore from a previous scan

Restore diffractometer orientation from the supplemental data stored in a
databroker scan:

```python
restore_huber_from_scan(-1)                           # most recent scan
restore_huber_from_scan(1234)                         # scan ID 1234
restore_huber_from_scan(1234, sample_name="EuAl4")    # override sample name
restore_huber_from_scan(1234, force=True)             # use first available info
```

---

## Detector Selection

See [General Examples → Detector Selection](general.md) for
the full `counters.plotselect()` walkthrough.

```python
counters.plotselect(14, 5)        # detector index 14, monitor index 5
counters.plotselect([14, 19], 5)  # multiple detectors
```

---

## Temperature Control

Temperature controllers are available at 4IDG:

```python
# LakeShore 336 (primary)
temp_336_4idg.input.A.temperature.get()     # read sensor A
temp_336_4idg.output.one.setpoint.put(100)  # set to 100 K

# LakeShore 340
temp_340_4idg.input_A.get()

# Convenient shortcut (from per-session startup)
temp = oregistry.find("temp_340_4idg").control
```

---

## Saving Data

SPEC files are enabled by default. Use `newSpecFile` to start a new file and
`spec_comment` to annotate the logbook:

```python
newSpecFile("EuAl4_experiment")
# → creates e.g. 0410_EuAl4_experiment.dat

spec_comment("Sample: EuAl4, oriented (001), T = 300 K")
spec_comment("Aligned at (2 0 0), phi frozen at 5 deg")
```

Access recent runs from the databroker catalog:

```python
run = cat[-1]              # most recent run
run.primary.read()         # read as xarray Dataset
```

[polartools](https://github.com/APS-4ID-POLAR/polartools) provides higher-level
routines for diffraction data analysis, available in the session namespace:

```python
df = load_table(-1, cat)
fit = fit_peak(df["delta"], df["scaler1_ch14"])

plot_fit([10, 20, 1], cat, positioner="delta", detector="scaler1_ch14")
fit_series([10, 20, 1], cat, positioner="delta", detector="scaler1_ch14")

mesh = load_mesh(-1, cat, xmotor="cryox", ymotor="cryoy", detector="scaler1_ch14")
plot_2d(mesh)
```
