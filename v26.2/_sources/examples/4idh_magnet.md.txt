# 4IDH: Magnet 9-1-1 Usage

4IDH is the magnet hutch, centered around the 9T-1T-1T superconducting vector
magnet (`magnet911`). Typical experiments include XMCD (X-ray Magnetic Circular
Dichroism), field-dependent absorption spectroscopy, and field-sweep measurements,
all using the circular dichroism data stream.

---

## Starting the Session

Use the beamline startup script from a terminal:

```bash
bluesky-4idh
```

This activates the `polar-bits` conda environment and launches IPython with all
4IDH devices pre-loaded (equivalent to `from id4_h.startup import *`).

---

## Motor Shortcuts

The package ships a prebuilt shortcut module that binds the magnet's
sub-devices into the interactive session. Importing it once after
startup makes `field`, `tabx`, `taby`, `tabz`, `tabsx`, `tabsz`,
`tabrot`, `sy`, `sth` directly usable:

```python
import id4_common.macros.shortcuts_4idh_9T  # noqa: F401
```

For names that aren't covered, write your own in a per-session file:

```python
# extra_shortcuts.py
from apsbits.core.instrument_init import oregistry

_mag = oregistry.find("magnet911")

samz  = _mag.samp.z       # sample Z (not in the prebuilt set)
energy = oregistry.find("energy")
```

Run with `%run extra_shortcuts.py` or `from extra_shortcuts import *`.

---

## Beam Alignment

Find the sample in the beam using the table motors. Use relative scans
centered on the current position:

```python
# Scan table X and Y to find peak transmission (I / I0)
RE(lup(tabx, -1, 1, 50, 0.2))
RE(lup(taby, -1, 1, 50, 0.2))

# Fine-tune
RE(lup(tabx, -0.5, 0.5, 30, 0.2))
RE(lup(taby, -0.5, 0.5, 30, 0.2))

# 2D map to locate the sample
RE(grid_scan(
    tabx, -3, 2, 50,
    taby, -2, 2, 40,
    0.2,
))

# Center on peak using the peak finder
RE(lup(tabx, -0.5, 0.5, 30, 0.2))
RE(cen(tabx))   # moves tabx to center-of-mass of the last scan
RE(lup(taby, -0.5, 0.5, 30, 0.2))
RE(cen(taby))
```

---

## Energy and Phase Retarder Setup

Set the photon energy (moves the monochromator):

```python
%mov energy 7.245    # Gd L3 edge (~7.245 keV)
%mov energy 7.514    # Tb L3 edge (~7.514 keV)
%mov energy 8.255    # Tb L2 edge (~8.255 keV)
```

Configure which devices track the energy (call once per session):

```python
energy.tracking_setup(["undulators_ds", "pr2"])
```

Set the undulator offset relative to the mono energy:

```python
undulators = oregistry.find("undulators")
undulators.ds.energy_offset.put(-0.063)
undulators.ds.energy_deadband.put(0.002)
```

---

## Phase Retarder (PR2) Setup

The `pr_setup` object controls the PR2 piezo and helicity switching:

```python
from id4_common.utils.pr_setup import pr_setup

pr_setup.positioner   = oregistry.find("pr2_pzt_localdc")
pr_setup.offset       = oregistry.find("pr2_pzt_offset_microns")
pr_setup.oscillate_pzt = True
```

Each assignment auto-snapshots into `RE.md["session_state"]`, and the
energy-tracking + undulator-offset blocks above do the same. After a
bluesky restart, `restore_session_state()` (or
`import id4_common.macros.startup_common`) re-applies all of them in
one step — see [Recoverable session
state](writing_macros.md#recoverable-session-state).

Align PR2 theta:

```python
RE(lup(pr2.th, -0.02, 0.02, 100, 0.2))
%mov pr2.th 22.302          # move to Bragg reflection
```

---

## Temperature Control (VTI)

The 9 T magnet's variable-temperature insert (VTI) is exposed through
the standard `temperature_setup(label)` helper. Pick the `"h-9T"`
controller and the session globals `tc` (setpoint) and `ts` (readback)
become the VTI handles:

```python
temperature_setup("h-9T")
mv tc 5.0                # set the VTI setpoint to 5 K
te(5.0)                  # equivalent shortcut
ts.get()                 # current sample-temperature readback
```

`ts` is added to the baseline so the temperature lands in every scan
automatically.

---

## CRL Focusing

The compound refractive lens (`crl`) is shared between 4IDG and 4IDH;
switch its sample-position offset to the 4IDH value before using:

```python
crl_setup("h")           # apply the 4IDH offset (or pass nothing for a prompt)
crl_size(50)             # set the focal size to 50 µm (the < 5 µm path
                         # triggers crl.minimize_button instead)
mov crl.beamsize 10      # write 10 µm directly to the focalSize PV
                         # (returns immediately; the readback in fSize_actual
                         # may not converge to the same value)
```

---

## Dichroism Data Stream

The dichro callback accumulates intensity at alternating helicities.
It is loaded automatically at startup:

```python
dichro              # DichroStream callback instance
dichro_bec          # BestEffortCallback for the dichro stream
plot_dichro_settings()   # configure dichro plots
```

Scans with `dichro=True` read the scaler at each helicity state
automatically.

---

## Field Operations

The `field` shortcut (from `motor_shortcuts.py`) exposes the magnet
field as a pseudo-motor in Tesla:

```python
field.get()       # read current field value

# Move to a fixed field (use %mov for blocking interactive moves)
%mov field 3.0    # apply +3 T
%mov field 0      # zero field
%mov field -3.0   # apply -3 T (reverse polarity)
```

---

## Field-Dependent Scans

Scan the magnetic field while recording XAS intensity with helicity switching:

```python
# Field sweep with dichroism (50 points, 2.5 s dwell per point)
RE(ascan(field, -0.5, 0.5, 50, 2.5, dichro=True))

# Reverse direction scan
RE(ascan(field, 0.5, -0.5, 50, 2.5, dichro=True))
```

---

## Q-Space Scans with Dichroism

The `qxscan` plan scans across an absorption edge in reciprocal space.
Parameters are loaded from a JSON file:

```python
qxscan_setup = oregistry.find("qxscan_setup")
qxscan_setup.load_params_json("tb.json")   # load scan range / energy list

# Run a Q-space scan at Tb L3 edge, 1.0 s dwell, with helicity switching
RE(qxscan(7.514, 1.0, dichro=True))

# Without dichroism
RE(qxscan(7.514, 0.5))
```

---

## Detector Selection

Select which scaler channels to plot and use as the monitor
(see [General Examples → Detector Selection](general.md)):

```python
counters.plotselect(9, 8)     # detector ch 9, monitor ch 8
counters.plotselect([6, 9], 8)   # two detectors, same monitor
```

In scripts this is typically called once at the top:

```python
counters.plotselect(9, 8)
```

---

## Reading XAS/XMCD Data

The functions below are from [polartools](https://github.com/APS-4ID-POLAR/polartools)
and are available in the session namespace after startup.

Load a single XAS scan and plot it:

```python
import matplotlib.pyplot as plt

en, xas = load_absorption(
    -1, cat,
    positioner="energy",
    detector="4idhI1",
    monitor="4idhI0",
)
plt.figure()
plt.plot(en, xas)
plt.xlabel("Energy (keV)")
plt.ylabel("XAS (I/I₀)")
```

Load XMCD from a single dichro scan (returns positioner, XAS, and XMCD arrays):

```python
en, xas, xmcd = load_dichro(
    -1, cat,
    positioner="energy",
    detector="4idhI1",
    monitor="4idhI0",
)
```

Process and plot XMCD from scans collected at opposing magnetic fields.
`scans_plus` and `scans_minus` are lists of scan IDs at +field and −field:

```python
plus, minus = process_xmcd(
    scans_plus=[10, 12, 14],
    scans_minus=[11, 13, 15],
    source=cat,
)
plot_xmcd(plus, minus)
```

Average XAS over multiple scans:

```python
en, xas = load_multi_xas(
    [10, 11, 12], cat,
    positioner="energy",
    detector="4idhI1",
    monitor="4idhI0",
)
```

---

## RunEngine Control

```python
RE(count(5, 1.0))   # 5 counts of 1 s each

RE.abort()          # abort current plan
RE.stop()           # graceful stop (runs cleanup)
RE.pause()          # pause (resume with RE.resume())
RE.resume()
```

---

## Session Metadata

Tag experiments for later retrieval:

```python
RE.md["proposal_id"]     = "GUP-12345"
RE.md["sample"]          = "TbFe thin film / MgO substrate"
RE.md["experiment_name"] = "XMCD commissioning Jan 2026"
```

---

## Saving Data

```python
# Start a new SPEC file for this session
newSpecFile("TbFe_100K_XMCD")
# → creates e.g. 0110_TbFe_100K_XMCD.dat

# Add free-form logbook comments
spec_comment("field +3 T → -3 T sweep, T = 100 K, dichro=True")
spec_comment("PR2 aligned at 22.302 deg, offset = 25.5 V")
```
