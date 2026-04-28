# Scan Plans

All scan plans are available in the session namespace after
`from id4_common.startup import *`. They wrap or extend standard
[Bluesky](https://blueskyproject.io/bluesky/) plans with POLAR-specific
defaults (counters, monitor selection, DM integration).

---

## Common Scan Flags

Most scan plans (`lup`, `ascan`, `th2th`, `qxscan`, `grid_scan`) share three
optional boolean flags that enable advanced measurement modes.

The `dichro` and `lockin` flags require running `pr_setup` first to configure
the scan (see [Phase Retarder setup](examples/4idh_magnet.md)).

### `dichro` — circular dichroism

Switches the X-ray helicity at every point using the phase retarder (PR2) in a
user defined sequence (usually `+, −, −, +`). The readings are accumulated
by the dichro data stream into XAS and XMCD signals.

```python
RE(lup(energy, -0.05, 0.05, 50, 1.0, dichro=True))
RE(ascan(field, -3, 3, 60, 2.0, dichro=True))
```

### `lockin` — lock-in detection

Oscillates the phase retarder continuously and reads the lock-in amplifier
signal instead of the scaler. Use for high-sensitivity dichroism measurements.

```python
RE(lup(energy, -0.05, 0.05, 50, 1.0, lockin=True))
```

### `fixq` — fixed reciprocal-space position

Keeps the diffractometer at a fixed HKL position throughout the scan by
adjusting the real-space angles after each motor move. Useful for energy scans
where you want to track a specific Bragg reflection as the energy changes.
The HKL correction is applied *after* all other motors have moved.

```python
RE(qxscan(7.514, 1.0, fixq=True))
RE(lup(energy, -0.05, 0.05, 50, 1.0, fixq=True))
```

---

## Positioner Motions

Motions are an exception in that it can be done using both the RE wrapper and through the `mov` and `movr` python magics.

Note that a positioner can be motor, temperature, magnetic field, energy, etc.

```python
# Absolute move
mov positioner position
mov positioner1 pos1 positioner2 pos2 # simultaneous multi-motor move

# Relative move
movr positioner delta
```

These are the same as:

```python
# Absolute move
RE(mv(motor, position))
RE(mv(motor1, pos1, motor2, pos2))

# Relative move
RE(mvr(motor, delta))
```
The move options above will wait until the motion is done. If you want to start a motion and gain back command line control use `abs_set`:

```
RE(abs_set(motor, position))
```

---

## 1-D Scans

### `lup` — relative scan

Scan `motor` from `start` to `stop` relative to its current position, collecting `npts` points.

```python
RE(lup(motor, start, stop, npts, time))
RE(lup(motor, start, stop, npts, time, md={"sample": "Fe3O4"}))
```

### `ascan` — absolute scan

Scan `motor` from `start` to `stop` in absolute coordinates.

```python
RE(ascan(motor, start, stop, npts, time))
```

### `th2th` — relative theta/2theta scan

Coupled scan of `mu` and `gamma` (theta and 2theta) relative to their current
positions. `tth_start`/`tth_end` set the 2theta range; theta moves at half that
rate.

```python
RE(th2th(tth_start, tth_end, npts, time_per_point))
```

Optional flags:

```python
RE(th2th(tth_start, tth_end, npts, time_per_point, dichro=True))
RE(th2th(tth_start, tth_end, npts, time_per_point, lockin=True))
RE(th2th(tth_start, tth_end, npts, time_per_point, fixq=True))
```

---

## 2-D / N-D Scans

### `grid_scan` — absolute grid

```python
RE(grid_scan(
    motor1, start1, stop1, npts1,
    motor2, start2, stop2, npts2,
    time,
))
```

### `rel_grid_scan` — relative grid

Same as `grid_scan` but offsets are relative to current motor positions.

---

## Simple Count

```python
RE(count(num, time))              # count num times with time per point
RE(count(num, time, delay=1.0))   # add delay (seconds) between readings
```

---

## XAFS Energy Scan (`qxscan`)

`qxscan` is an XAFS-style energy scan covering pre-edge, edge, and post-edge
regions. The post-edge step size is defined in k-space (Å⁻¹) and converted to
energy internally, so the energy step increases with energy above the edge.

All energies in `qxscan_params` are **relative to the absorption edge**.

### Step 1 — Configure `qxscan_params`

Call the device to enter the interactive setup wizard:

```python
qxscan_params()
```

This prompts for pre-edge regions (energy start, step, time factor), the edge
region (energy start/end, step, time factor), and post-edge regions (k end, k
step, time factor). It then computes and stores the full energy list.

Parameters can also be saved and reloaded:

```python
qxscan_params.save_params_json("my_scan.json")
qxscan_params.load_params_json("my_scan.json")
qxscan_params.load_from_scan(scan_id)   # restore from a previous run
```

Print the current setup:

```python
print(qxscan_params)
```

### Step 2 — Run the scan

```python
RE(qxscan(edge_energy, time))
```

- `edge_energy`: absorption edge energy in eV (absolute)
- `time`: counting time factor applied to all detectors

Optional flags:

```python
RE(qxscan(edge_energy, time, dichro=True))   # switch polarization at each point
RE(qxscan(edge_energy, time, lockin=True))   # lock-in detection mode
RE(qxscan(edge_energy, time, fixq=True))     # fix diffractometer hkl during scan
```

---

## APS Data Management Plans

Plans in `id4_common.plans.dm_plans` submit workflow jobs to the APS DM
system after data collection:

```python
# Submit a workflow to DM after a scan completes
RE(dm_workflow_plan(
    workflow_name="4id-xmcd",
    scan_plan=ascan(motor, 0, 1, 10),
))
```

See the [API reference](api/id4_common/plans/index.rst) for full parameter
documentation of `dm_plans`.

---

## RunEngine

The RunEngine is available as `RE` after startup:

```python
RE(lup(m1, -1, 1, 21))                       # run a plan
RE(lup(m1, -1, 1, 21), md={"note": "test"})  # add metadata
RE.abort()                                     # abort current plan
RE.stop()                                      # graceful stop
RE.pause()                                     # pause (resume with RE.resume())
RE.resume()
```
