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
| `change_diffractometer(name)` | Select active diffractometer; injects motor aliases |
| `set_detector()` | Select Eiger or point detector/analyzer arm |

### Moving

| Command | Description |
|---------|-------------|
| `wh` | Current H K L, motor positions, energy, PSI (no parentheses) |
| `ca(h, k, l)` | Calculate motor angles for HKL without moving |
| `ubr(h, k, l)` | Move to HKL (runs own RunEngine) |
| `RE(br(h, k, l))` | Move to HKL as a Bluesky plan |
| `uan(gamma, mu)` | Move gamma and mu together |

### Sample management

| Command | Description |
|---------|-------------|
| `newsample()` | Add sample interactively; seeds default UB and azimuthal reference |
| `sampleList()` | List all samples; mark current one |
| `sampleChange(name)` | Switch active sample |
| `sampleRemove(name)` | Remove a sample |
| `setlat(a,b,c,α,β,γ)` | Set lattice constants (no args = interactive) |
| `update_lattice(par)` | Refine one lattice constant from current HKL position |

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
| `compute_UB()` | Force UB recomputation (normally automatic) |

### Modes, azimuth and constraints

| Command | Description |
|---------|-------------|
| `setmode(n)` | Set diffractometer mode by number (no args = interactive list) |
| `setaz(h, k, l)` | Set azimuthal reference vector |
| `freeze(val)` | Freeze constant axis for current mode (no args = use current position) |
| `freeze_general()` | Interactively freeze all constant axes |
| `show_constraints()` | Show angle limits for each axis |
| `set_constraints(…)` | Set angle limits (no args = interactive per axis) |
| `reset_constraints()` | Reset all limits to defaults |

### Analyzer

| Command | Description |
|---------|-------------|
| `analyzer_configuration(energy)` | Select crystal and set d-spacing |
| `analyzer_set()` | Move analyzer to Bragg angles for current energy |

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
| `x`, `y`, `z` | Sample stage |
| `nanox`, `nanoy`, `nanoz` | Nano-focusing stage |
| `basex`, `basey`, `basez` | Base stage |
| `ath`, `atth`, `eta`, `achi` | Analyzer arm |

The reciprocal-space pseudo-axes `h`, `k`, `l` are **not** injected automatically.
Assign them once per session (see [Per-Session Startup](#per-session-startup)):

```python
h = huber_euler.h
k = huber_euler.k
l = huber_euler.l
```

---

## Per-Session Startup

Users typically run a per-session startup file to set additional shortcuts and
load experiment-specific settings:

```python
%run startup_4idg.py
```

This file should also alias the reciprocal-space pseudo-axes so they can be
used directly in scans:

```python
change_diffractometer("huber_euler")

h = huber_euler.h
k = huber_euler.k
l = huber_euler.l
```

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
`update_lattice()`. There is no need to call `compute_UB()` manually in normal
use.

### Recompute the UB matrix

```python
compute_UB()    # force recomputation — only needed in exceptional cases
```

### Inspect and manage reflections

```python
list_reflections()         # list all reflections for the current sample
list_orienting()           # list only the two orienting reflections
set_orienting()            # interactively pick which reflections are orienting
or_swap()                  # swap first and second orienting reflections; recomputes UB
del_reflection()           # interactively delete a non-orienting reflection
```

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

Show and manage axis constraints (angle limits):

```python
show_constraints()          # print low/high limits for each axis
reset_constraints()         # reset all limits to defaults
set_constraints()           # interactive: set limits for each axis
set_constraints("phi", -180, 180)   # set limits for one axis
set_constraints(-1,1, 0,90, -20,200, -180,180, -2,140, -5,50)  # set all 6 axes
```

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

With `h`, `k`, `l` aliased (see [Per-Session Startup](#per-session-startup)),
scan directly along a reciprocal-space direction. The diffractometer moves all
required angular axes simultaneously to follow the path:

```python
# L-scan through (0 0 2)
RE(lup(l, 1.8, 2.2, 40, 0.5))

# H-scan through (2 0 0)
RE(lup(h, 1.8, 2.2, 40, 0.5))

# Absolute scan along K
RE(ascan(k, -0.1, 0.1, 40, 0.5))
```

Center on a peak after a scan:

```python
RE(lup(l, 1.8, 2.2, 40, 0.5))
RE(cen(l))     # moves to the center-of-mass of the last scan
```

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

Configure and move the analyzer arm. `analyzer_configuration()` prompts
for the analyzer crystal and sets its d-spacing. `analyzer_set()` moves
the analyzer to the correct angles for the current energy:

```python
analyzer_configuration()      # select crystal, set d-spacing; optionally pass energy (keV)
analyzer_configuration(7.0)   # configure for 7.0 keV
analyzer_set()                # move ath/atth to correct Bragg angles
```

---

## Detector Selection

Switch between the Eiger area detector and the point detector/analyzer arm
(motors are 25° apart in delta):

```python
set_detector()    # interactive: (E)iger or (P)oint Detector/Analyzer
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
to overwrite or append the current configuration:

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
