# 4IDG: Diffractometer Usage

4IDG is the diffraction hutch. The primary instrument is the Huber Euler
6-circle diffractometer (`huber_euler`), controlled through
[hklpy](https://blueskyproject.io/hklpy/) for reciprocal-space navigation.
An HP (high-pressure) diffractometer (`huber_hp`) is also available.

---

## Session Startup

```python
from id4_g.startup import *
```

This loads the `core` + `4idg` device set, which includes `huber_euler`,
`huber_hp`, `gkb`, `transfocator`, `gfilter`, `scaler1`, `scaler2`, `eiger`,
and temperature controllers.

---

## Selecting the Active Diffractometer

Two diffractometer geometries are available. Select the one you will use before
running any HKL calculations or moves:

```python
select_diffractometer(huber_euler)   # Cradle Euler (most common)
select_diffractometer(huber_hp)      # High-pressure cell
```

---

## Defining a Sample

Create a sample with its unit cell parameters (a, b, c in Å; α, β, γ in °):

```python
# Cubic Si, a = 5.4 Å
new_sample("Si", 5.4, 5.4, 5.4, 90, 90, 90)

# Tetragonal example
new_sample("MyOxide", 3.84, 3.84, 12.6, 90, 90, 90)
```

Verify the current sample and UB matrix:

```python
wh()    # print current reciprocal-space position and sample info
pa()    # print all engine parameters (UB matrix, reflections, mode)
```

---

## Orientation (UB Matrix)

Set orientation reflections one at a time. Move to the peak physically, then
call `setor0()` / `setor1()` to record the reflection:

```python
# Move to the first reflection physically, then:
setor0()    # record orientation reflection 0 at current motor positions

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

Move to an HKL position:

```python
RE(br(1, 0, 0))     # move to (1 0 0)
RE(br(2, 0, 0))     # move to (2 0 0)
RE(br(1, 1, 0))     # move to (1 1 0)
wh()                # confirm position after move
```

Move individual real-space axes:

```python
%mov huber_euler.phi 5        # move phi to 5°
%mov huber_euler.chi 0        # move chi to 0°
%mov huber_euler.delta 30     # move delta to 30°
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

Available modes include:

- `4-circles constant phi horizontal`
- `zaxis + alpha-fixed`
- `4-circles bissecting horizontal`
- `4-circles constant omega horizontal`
- `psi constant horizontal`
- `lifting detector mu/omega/chi/phi`

---

## Azimuth Reference and Constraints

Set the azimuth reference vector:

```python
setaz(0, 0, 1)   # [001] azimuth reference
setaz(0, 1, 0)   # [010] azimuth reference
```

Freeze an axis at a fixed value (e.g. fix phi):

```python
freeze(0)     # freeze phi at 0°
freeze(5)     # freeze phi at 5°
freeze(-90)   # freeze phi at -90°
```

Show and manage axis constraints:

```python
show_constraints()    # print current limits and frozen values
reset_constraints()   # reset all to defaults
set_constraints()     # interactive prompt to set low/high limits per axis
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

Scan along a real-space motor while monitoring intensity with the scalers:

```python
# Rock phi around current position
RE(lup(huber_euler.phi, -1, 1, 50, 1.0))

# Scan delta (2θ equivalent) through a Bragg peak
RE(lup(huber_euler.delta, -0.5, 0.5, 50, 0.5))

# Scan chi for polarization dependence
RE(lup(huber_euler.chi, -5, 5, 50, 0.5))
```

For the HP diffractometer, sample position motors are directly accessible:

```python
basex = huber_hp.basex
basey = huber_hp.basey
sx = huber_hp.x
sy = huber_hp.y

RE(lup(sx, -0.5, 0.5, 50, 0.1))    # sample X scan
RE(lup(sy, -0.5, 0.5, 50, 0.1))    # sample Y scan
```

---

## 2D Maps

Raster scan over two motors (useful for sample mapping or reciprocal-space maps):

```python
# Grid scan: motor1 outer, motor2 inner
RE(grid_scan(
    huber_euler.phi, -2, 2, 20,
    huber_euler.delta, -1, 1, 20,
    0.5,    # dwell time per point
))

# Sample position map with scaler
RE(grid_scan(
    huber_hp.x, -1, 1, 20,
    huber_hp.y, -1, 1, 20,
    0.2,
))
```

---

## Detector Selection

Set which detectors are read in scans:

```python
counters.plotselect()       # interactive — choose detector / monitor
counters.detectors          # show active detectors
counters.monitor            # show active monitor channel

# Add the Eiger area detector
load_device("eiger")
counters.detectors.append(eiger)
```

---

## Temperature Control

Temperature controllers are available at 4IDG:

```python
# LakeShore 336 (primary)
temp_336_4idg.input.A.temperature.get()   # read temperature sensor A
temp_336_4idg.output.one.setpoint.set(100)  # set setpoint to 100 K

# LakeShore 340
temp_340_4idg.input_A.get()
```

---

## Saving Data

SPEC files are enabled by default:

```python
newSpecFile("MyExperiment_Si_sample")   # creates 0410_MyExperiment_Si_sample.dat
spec_comment("Oriented Si (100), chi=0, phi frozen at 5 deg")
```

Access recent runs from the databroker catalog:

```python
run = cat[-1]                        # most recent run
run.primary.read()                   # read primary data stream as xarray
```
