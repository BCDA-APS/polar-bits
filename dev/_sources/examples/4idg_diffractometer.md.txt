# 4IDG: Diffractometer Usage

4IDG is the diffraction hutch. The primary instrument is the Huber Euler
6-circle diffractometer (`huber_euler`), controlled through
[hklpy](https://blueskyproject.io/hklpy/) for reciprocal-space navigation.
An HP (high-pressure) diffractometer (`huber_hp`) is also available.

---

## Starting the Session

Use the beamline startup script from a terminal:

```bash
bluesky-4idg
```

This activates the `polar-bits` conda environment and launches IPython with all
4IDG devices pre-loaded (equivalent to `from id4_g.startup import *`).

---

## Motor Shortcuts

After the main startup, users typically run a per-session startup file
(e.g. `startup_4idg.py`) that assigns convenient short names to frequently
used motors:

```python
from apsbits.core.instrument_init import oregistry

huber_euler = oregistry.find("huber_euler")
huber_hp    = oregistry.find("huber_hp")
energy      = oregistry.find("energy")
gkb         = oregistry.find("gkb")

# Motor shortcuts for huber_euler
sx  = huber_euler.x
sy  = huber_euler.y
sz  = huber_euler.z
mu  = huber_euler.mu
delta = huber_euler.delta
chi   = huber_euler.chi
phi   = huber_euler.phi
gamma = huber_euler.gamma

# Motor shortcuts for huber_hp (nanofocusing stage)
nanox = huber_hp.nanox
nanoy = huber_hp.nanoy
sx_hp = huber_hp.x
sy_hp = huber_hp.y
```

Run this file at the start of each session:

```python
%run startup_4idg.py
```

---

## Selecting the Active Diffractometer

Two diffractometer geometries are available. Select the one in use before
running any HKL calculations or moves:

```python
select_diffractometer(huber_euler)   # Cradle Euler (most common)
select_diffractometer(huber_hp)      # High-pressure cell
```

---

## Defining a Sample

Create a sample with its unit cell parameters (a, b, c in Å; α, β, γ in °).
`sampleNew` prompts interactively if called without arguments, or accepts
positional arguments:

```python
# Interactive (prompts for name and lattice constants)
sampleNew()

# Non-interactive
sampleNew("Si", 5.4, 5.4, 5.4, 90, 90, 90)          # cubic Si
sampleNew("MyOxide", 3.84, 3.84, 12.6, 90, 90, 90)   # tetragonal
```

Verify the current sample and orientation matrix:

```python
wh     # print current reciprocal-space position and sample info (no parentheses needed)
pa()   # print full engine parameters: UB matrix, reflections, mode
```

---

## Orientation (UB Matrix)

Set orientation reflections one at a time. Move to the peak physically, then
call `setor0()` / `setor1()` to record the reflection at the current motor
positions:

```python
# Move to the first reflection physically, then:
setor0()    # record orientation reflection 0 — prompts for H K L if not at peak

# Move to the second reflection, then:
setor1()    # record orientation reflection 1 — UB matrix is now calculated
```

List stored reflections:

```python
list_reflections()
```

---

## Checking Angles and Moving in Reciprocal Space

Calculate motor angles for any HKL without moving:

```python
ca(1, 0, 0)     # angles for (1 0 0)
ca(1, 1, 0)     # angles for (1 1 0)
ca(0, 0, 2)     # angles for (0 0 2)
```

Move to an HKL position (executes as a plan):

```python
RE(br(1, 0, 0))     # move to (1 0 0)
RE(br(2, 0, 0))     # move to (2 0 0)
RE(br(1, 1, 0))     # move to (1 1 0)
wh                  # confirm position after move
```

Move individual real-space axes with the `%mov` magic:

```python
%mov huber_euler.phi 5        # move phi to 5°
%mov huber_euler.chi 0        # move chi to 0°
%mov huber_euler.delta 30     # move delta to 30°

# Or using shortcuts:
%mov phi 5
%mov chi 0
```

---

## Diffractometer Modes

`setmode()` opens an interactive prompt listing all available modes.
Pass a mode number to set it directly:

```python
setmode()      # interactive selection
setmode(7)     # e.g. "4-circles bissecting horizontal"
setmode(12)    # e.g. "psi constant horizontal"
```

Available modes include (geometry-dependent):

- `4-circles constant phi horizontal`
- `zaxis + alpha-fixed`, `zaxis + beta-fixed`, `zaxis + alpha=beta`
- `4-circles bissecting horizontal`
- `4-circles constant omega horizontal`
- `psi constant horizontal`
- `lifting detector mu/omega/chi/phi`

---

## Azimuth Reference and Constraints

Set the azimuth reference vector (interactive if called without arguments):

```python
setaz(0, 0, 1)   # [001] azimuth reference
setaz(0, 1, 0)   # [010] azimuth reference
```

Freeze an axis at a fixed value (freezes phi by default; interactive if no
argument given):

```python
freeze(0)     # freeze phi at 0°
freeze(5)     # freeze phi at 5°
freeze(-90)   # freeze phi at -90°
```

Show and manage axis constraints:

```python
show_constraints()    # print current limits and frozen values
reset_constraints()   # reset all to defaults
set_constraints()     # interactive loop — set low/high limits per axis
```

---

## Inverse Calculation

Convert real-space motor positions to reciprocal-space coordinates:

```python
# (mu, delta, gamma, chi, phi, omega) → (h, k, l)
sol = huber_euler.inverse((0, 30, 0, 0, 0, 69.0966))
print(sol.h, sol.k, sol.l)

sol = huber_euler.inverse((0, 92, 33.2, -139, 33.1, 0))
print(sol)
```

---

## Scanning in Reciprocal Space

Scan along real-space motors while monitoring intensity with the scalers.
All plans use `counters.detectors` and `counters.monitor` by default
(see [General Examples](general.md) for detector selection):

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

For the HP diffractometer sample stage:

```python
RE(lup(sx_hp, -0.5, 0.5, 50, 0.1))    # sample X scan
RE(lup(sy_hp, -0.5, 0.5, 50, 0.1))    # sample Y scan
```

Center on a peak after a scan:

```python
RE(lup(phi, -1, 1, 50, 0.5))
RE(cen(phi))     # moves phi to the center-of-mass of the last scan
```

---

## 2D Maps

Raster scan over two motors:

```python
# Grid scan over sample position (useful for mapping or alignment)
RE(grid_scan(
    sx, -1, 1, 20,
    sy, -1, 1, 20,
    0.2,    # dwell time per point
))

# Relative grid scan with snake trajectory
RE(rel_grid_scan(
    nanoy, -3.5, 3.5, 45,
    nanox, -2, 2, 31,
    0.05,
    snake_axes=True,
))
```

---

## Detector Selection

See [General Examples → Detector Selection](general.md#detector-selection) for
the full `counters.plotselect()` walkthrough.

```python
# Quick selection: detector index 14, monitor index 5
counters.plotselect(14, 5)

# Multiple detectors
counters.plotselect([14, 19], 5)
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
