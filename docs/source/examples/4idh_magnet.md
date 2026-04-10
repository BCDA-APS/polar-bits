# 4IDH: Magnet 9-1-1 Usage

4IDH is the magnet hutch, centered around the 9T-1T-1T superconducting vector
magnet (`magnet911`). Typical experiments include XMCD (X-ray Magnetic Circular
Dichroism), field-dependent absorption spectroscopy, and magneto-optical Kerr
measurements, all using the circular dichroism data stream.

---

## Session Startup

```python
from id4_h.startup import *
```

This loads the `core` + `4idh` device set: `magnet911`, `hkb`, `transfocator`,
`hfilter`, `scaler1`, `scaler2`, `hxbpm`, `hsydor`, `table_4idh`, and
pre-amplifiers.

Load the magnet explicitly if not connected at startup:

```python
load_device("magnet911")
magnet911     # inspect device
```

---

## Beam Alignment

After startup, align the sample in the beam using the table motors:

```python
# X/Y table scan — find peak transmission (I / I0)
RE(lup(table_4idh.x, -1, 1, 50, 0.2))
RE(lup(table_4idh.y, -1, 1, 50, 0.2))

# Sample Y axis (independent from table)
RE(lup(magnet911.tab.y, -0.5, 0.5, 30, 0.2))

# Fine-tune X and Y alternately
RE(lup(table_4idh.x, -0.5, 0.5, 30, 0.2))
RE(lup(table_4idh.y, -0.5, 0.5, 30, 0.2))

# 2D map to find sample
RE(grid_scan(
    table_4idh.x, -3, 2, 50,
    table_4idh.y,  1.8, 6.2, 50,
    0.2,
))
```

---

## Energy and Phase Retarder Setup

Set the photon energy and configure the phase retarders for circular
polarization:

```python
# Set energy (moves monochromator)
%mov energy 7.245    # Gd L3 edge
%mov energy 7.936    # Tb L3 edge
%mov energy 8.255    # Tb L2 edge

# Setup experiment parameters (experiment-specific macro)
experiment_setup()

# Configure phase retarder tracking with energy
energy.tracking_setup()

# Align PR1 (diamond phase retarder 1) theta
RE(lup(pr1.th, -0.02, 0.02, 100, 0.2))
%mov pr1.th 22.303          # move to Bragg peak
pr1.set_energy(energy.get())  # sync energy to current value

# Check and adjust PZT feedback offset
pr1.pzt.offset_microns.get()         # read current PZT offset
%mov pr1.pzt.localdc 20              # set local DC voltage
%mov pr1.pzt.localdc 25.1477         # fine-adjust

# Same for PR2
RE(lup(pr2.th, -0.02, 0.02, 100, 0.2))
%mov pr2.th 22.302
pr2.set_energy(energy.get())
%mov pr2.pzt.localdc 25.5
```

---

## Dichroism Data Stream

The dichro stream accumulates intensity at alternating helicities (positive and
negative circular polarization):

```python
# The dichro callback is always loaded at startup:
dichro        # DichroStream callback instance
dichro_bec    # BestEffortCallback for dichro stream

# Configure dichro plot settings
plot_dichro_settings()
```

Scans with `dichro=True` read the scaler at each helicity state automatically.

---

## Field Operations

The field motor exposes the magnet current as a pseudo-motor in Tesla:

```python
# Check current field
field.get()

# Move to a fixed field value (blocking)
%mov field 3.0      # apply +3 T
%mov field 0        # zero field
%mov field -3.0     # apply -3 T (reverse polarity)
```

:::{warning}
Always ramp to zero before reversing field direction. Confirm with the magnet
operator before exceeding safe ramp rates.
:::

---

## Field-Dependent Scans (XMCD)

Scan the magnetic field while recording XAS signal with helicity switching:

```python
# Field sweep +0.5 T → -0.5 T with dichroism (50 points, 2.5 s dwell)
RE(ascan(field, -0.5, 0.5, 50, 2.5, dichro=True))

# Reverse direction scan
RE(ascan(field, 0.5, -0.5, 50, 2.5, dichro=True))
```

---

## XMCD Spectroscopy Macros

High-level experiment macros are available for common measurement protocols.
They handle energy positioning, field switching, and data averaging:

```python
# Tb L3 edge XMCD: 6 helicity cycles, 5 s dwell, with alignment before each
RE(measure_TbL3_xmcd(6, 5, align=True))

# Tb L2 edge XMCD
RE(measure_TbL2_xmcd(6, 5, align=True))

# Gd L3 with lock-in detection
RE(measure_GdL3_lockin(6, 5))

# Single-cycle quick measurement (no alignment)
RE(measure_TbL3_xmcd(1, 5))
```

Sequential edge measurements in one call:

```python
RE(measure_TbL3_xmcd(6, 5, align=True))
RE(move_TbL2())                            # change energy to Tb L2
RE(measure_TbL2_xmcd(4, 5, align=True))
```

---

## Q-Space Scans with Dichroism

The `qxscan` plan scans in reciprocal space (requires the crystal analyzer setup):

```python
# Load scan parameters from JSON
qxscan_setup.load_params_json("tb.json")

# Run a Q-space scan at 8.252 keV, 0.5 Å⁻¹ range, with helicity switching
RE(qxscan(8.252, 0.5, dichro=True))

# Without dichroism
RE(qxscan(11.215, 1))
```

---

## Temperature-Dependent Measurements

Control the cryostat temperature and record temperature series:

```python
# Move to a temperature setpoint (blocking)
RE(move_temp(300))    # 300 K
RE(move_temp(250))    # 250 K
RE(move_temp(200))    # 200 K

# Temperature series (example sequence)
for T in [300, 250, 230, 210, 200]:
    RE(move_temp(T))
    RE(measure_TbL3_xmcd(6, 5, align=True))
```

Predefined temperature macros:

```python
RE(measure_210())   # measurement routine at 210 K
RE(measure_230())   # measurement routine at 230 K
RE(measure_250())   # measurement routine at 250 K
```

---

## Beam Position Monitoring

Check beam stability between long scans:

```python
# Check beam position (waits for stabilization before reading)
RE(check_position(wait_time=30))    # 30 s settle time
RE(check_position(wait_time=60))    # 60 s settle time for thermal drifts
```

---

## Alignment Utilities

```python
RE(align_xy())     # scan and center both X and Y
RE(align_y())      # scan and center Y only

# Center on peak using the peak-finding helper
RE(lup(table_4idh.y, -0.5, 0.5, 30, 0.2))
cen(table_4idh.y)    # move to center-of-mass of last scan
cen(table_4idh.x)    # center X
```

---

## Reading XAS Data

Load and plot a recent scan:

```python
# Read last run from catalog
en, xas = load_absorption(
    -1, cat,
    positioner="energy",
    detector="4idhI1",
    monitor="4idhI0",
)
import matplotlib.pyplot as plt
plt.figure()
plt.plot(en, xas)
plt.xlabel("Energy (keV)")
plt.ylabel("XAS (I/I0)")
plt.title("XAS at Tb L3 edge")
```

---

## RunEngine Metadata

Tag each experiment for later retrieval:

```python
RE.md["proposal_id"] = "GUP-12345"
RE.md["sample"]      = "TbFe thin film / MgO substrate"
RE.md["experiment_name"] = "XMCD commissioning Jan 2026"
RE.md["scan_id"] = 1    # reset counter for new SPEC file
```

---

## Saving Data

```python
# Create a new SPEC file for this session
newSpecFile("TbFe_100K_XMCD")
# → writes to e.g. 0110_TbFe_100K_XMCD.dat

# Add a free-form comment
spec_comment("field +3 T, T = 100 K, 6 dichro cycles")
```
