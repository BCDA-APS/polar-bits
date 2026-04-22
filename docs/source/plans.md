# Scan Plans

All scan plans are available in the session namespace after
`from id4_common.startup import *`. They wrap or extend standard
[Bluesky](https://blueskyproject.io/bluesky/) plans with POLAR-specific
defaults (counters, monitor selection, DM integration).

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
RE(lup(motor, start, stop, npts))
RE(lup(motor, start, stop, npts, md={"sample": "Fe3O4"}))
```

### `ascan` — absolute scan

Scan `motor` from `start` to `stop` in absolute coordinates.

```python
RE(ascan(motor, start, stop, npts))
```

---

## 2-D / N-D Scans

### `grid_scan` — absolute grid

```python
RE(grid_scan(
    [detector],
    motor1, start1, stop1, npts1,
    motor2, start2, stop2, npts2,
))
```

### `rel_grid_scan` — relative grid

Same as `grid_scan` but offsets are relative to current motor positions.

---

## Simple Count

```python
RE(count(num=1, delay=None))    # count once, or num times with optional delay
```

---

## Energy Scan with Q steps.

`qxscan` scans the energy using a non-constant step size.

```python
RE(qxscan(q_start, q_stop, npts))
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

---

## Scan Metadata

Persistent metadata is stored in `RE.md`:

```python
RE.md["proposal_id"] = "GUP-12345"
RE.md["sample"] = "Fe3O4 thin film"
RE.md["user"] = "J. Smith"
```

Values set here are attached to every subsequent run document.

---

## Plan Preprocessors

`id4_common.plans.local_preprocessors` provides plan decorators that inject
standard behavior (e.g. automatic shutter open/close, baseline snapshots)
around user plans.
