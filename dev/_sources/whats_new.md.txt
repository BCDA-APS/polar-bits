# What's New

A short summary of the user-visible changes since the previous APS run.
This page is updated once per APS run cycle (three runs per year);
older entries are kept for reference.

For the full commit history see [GitHub](https://github.com/BCDA-APS/polar-bits/commits/main).

---

## Run 2026-2 (Spring/Summer 2026)

Covers changes merged since [PR #30](https://github.com/BCDA-APS/polar-bits/pull/30)
("Update repository to match latest apsbits"), which was the baseline
for the 2026-1 run. Roughly 15 PRs landed during the shutdown — this
section groups them by user-visible theme.

Sections are ordered by how often a typical user is likely to notice
the change — restart workflow first, day-to-day scan helpers next,
then per-experiment setup, then the lower-level work that's mostly
transparent.

### Restarting a session — one line instead of a startup file

The setup helpers (`pr_setup`, `energy.tracking_setup`,
`counters.plotselect`, `undulator_setup`,
`qxscan_setup.load_params_json`) now auto-save their values into
`RE.md["session_state"]` every time you call them. After a bluesky
restart inside the same experiment, a single import re-applies
everything:

```python
import id4_common.macros.startup_common  # noqa: F401
```

That runs `experiment_resume()` followed by `restore_session_state()`
and prints a per-knob status. The hand-rolled startup file is now the
exception, not the rule. See
[Restarting a Session](examples/writing_macros.md#restarting-a-session).

A new curated star-import surface lives at `id4_common.macros.macros_api`
— one import line for every public scan plan, peak-finder, and session
singleton, kept stable across internal package reorgs. Three prebuilt
motor-shortcut modules (`shortcuts_4idg_euler`, `shortcuts_4idg_hp`,
`shortcuts_4idh_9T`) bind diffractometer / magnet sub-devices into
`__main__` under short names.

PRs: [#65](https://github.com/BCDA-APS/polar-bits/pull/65).

### New peak-finding plans

`cen` / `com` / `maxi` / `mini` are now plans you can call inside
macros — they read the most recent scan from the catalog, compute the
requested statistic (FWHM midpoint / centroid / max / min), and move
the positioner there:

```python
RE(cen())                                # FWHM midpoint of last scan
RE(com(positioner=tabx))                 # project a 2-D scan onto its axis
RE(maxi(scan_id=42, detector="hI2-apd"))
```

Backed by `apstools.utils.xy_statistics` + `scipy.signal` /
`scipy.ndimage`. Works for both 1-D scans and 2-D `grid_scan` /
`rel_grid_scan` (with noise-robust axis derivation that handles
encoder jitter). Diagnostic-only versions: `peak_pos`, `pmax`, `pmin`.

The earlier `apstools.lineup2`-backed implementations are still
available as `cen2` / `maxi2` / `mini2` from
`id4_common.plans.peak_position_legacy`.

See [Peak-Finding Plans](plans.md#peak-finding-plans).

PRs: [#62](https://github.com/BCDA-APS/polar-bits/pull/62).

### Temperature controllers — `tc` / `ts` / `te`

A new `temperature_setup(label)` helper picks the active controller
from a labelled lookup table and injects three names into the session:

```python
temperature_setup("g")        # 4IDG LakeShore 336
temperature_setup("g-340")    # 4IDG LakeShore 340
temperature_setup("h-9T")     # 4IDH 9 T magnet VTI
mv tc 295                     # write the setpoint
te(295)                       # equivalent shortcut
ts.get()                      # read the sample temperature
```

`ts` is added to the baseline so the sample temperature lands in every
scan automatically. Adding a new controller is a one-line edit to
`TEMPERATURE_CONTROLLERS` in `id4_common.utils.temperature_setup`.

PRs: [#57](https://github.com/BCDA-APS/polar-bits/pull/57),
[#61](https://github.com/BCDA-APS/polar-bits/pull/61).

### CRL focusing — new shortcuts and microns handle

- `crl_setup(hutch)` switches the CRL sample-position offset between
  4IDG and 4IDH (`"g"` / `"h"` / interactive).
- `crl_size(focal_size)` sets the focal size in µm (with `< 5 µm`
  triggering `crl.minimize_button` instead).
- `mov crl.beamsize 10` writes 10 µm directly to the underlying
  `focalSize` PV. The previous `EpicsSignal` with `write_pv` would
  hang waiting for `fSize_actual` to converge; the new `BeamsizeSignal`
  Device returns immediately. The raw meter-valued PVs are still
  reachable as `crl.beamsize.setpoint` / `crl.beamsize.readback`.

The internal device class was renamed `transfocator` → `crl` across
the codebase. The device is now `crl` in the registry; old `transfocator`
references should be updated.

PRs: [#58](https://github.com/BCDA-APS/polar-bits/pull/58),
[#61](https://github.com/BCDA-APS/polar-bits/pull/61).

### Reciprocal-space scans (4IDG)

Five new plans for the diffractometer (`huber_euler` / `huber_hp`):

```python
RE(hscan(start, stop, npts, time))
RE(kscan(start, stop, npts, time))
RE(lscan(start, stop, npts, time))
RE(hklscan(h0, h1, k0, k1, l0, l1, npts, time))
RE(psiscan(psi_start, psi_stop, npts, time))   # rotate around Bragg vector
```

All accept `dichro=True` / `lockin=True`. Together with `theta0`,
constraint cut points, and `setor0` / `setor1` / `or_swap` /
`Sync_UB_Matrix` updates, the 4IDG session migrated fully from hklpy
to hklpy2. The legacy hklpy code path was removed.

Two new devices were added to the 4IDG list: `ringlight` (sample
camera ring light) and `piezo_jena` (Piezo-Jena nanopositioner stage).

PRs: [#41](https://github.com/BCDA-APS/polar-bits/pull/41),
[#45](https://github.com/BCDA-APS/polar-bits/pull/45),
[#54](https://github.com/BCDA-APS/polar-bits/pull/54).

### Experiment lifecycle

`experiment_setup` was refactored: it now auto-detects whether DM is
reachable and falls back to `dserv` automatically with one warning
(no need to remember `skip_DM=True`); fixed the `reset_scan_id`
behaviour; added YAML persistence for restart; first unit-test suite
in the repo.

`experiment_resume()` and `experiment_load_from_scan(scan_id=-1)`
(renamed from the earlier `experiment_load_from_bluesky`) are the two
ways to pick up where you left off — one from the YAML snapshot, one
from a previous Bluesky run document.

PRs: [#52](https://github.com/BCDA-APS/polar-bits/pull/52).

### Devices — baseline cleanup + missing devices wired up

Several rarely-changed signals were demoted from `kind="hinted"` /
`kind="normal"` to `kind="config"` so the baseline stream is no longer
flooded with values that don't change over an experiment.

Devices that existed in code but weren't in `devices.yml` were added:
`srs810` (SRS-810 lock-in), `gslt` / `hslt` (4IDG/4IDH JJ slits),
`ringlight`, `piezo_jena`, `gmag` (Kepco PS), `comp` / `decomp` (HP
controllers), `laser` (Ventus laser).

PRs: [#64](https://github.com/BCDA-APS/polar-bits/pull/64).

### Bug fixes and infrastructure

- **SPEC writer** now produces files that `pymca` can parse for
  `qxscan` and other array-metadata scans (no more bare line wraps
  inside `#MD` blocks; `#S` lines collapse arrays to
  `<array len=N>`).
- **`load_device(name)`** is now the single canonical entry point for
  both first-load and reconnect (used to skip already-registered
  devices with a warning).
- **HDF1 priming** wired up for `Lambda250kDetector`, `VortexXspress34`,
  `VortexXspress37`, `VortexDante1`, `VortexDante4` — the first scan
  after a fresh IOC start no longer fails at staging.
- **Bluesky session logs** now go to the central log dir specified by
  `LOGGING.LOG_PATH` in `iconfig.yml` (with automatic fallback to
  `<cwd>/.logs/` when the central path is unwritable).
- **`load_vortex`** has parity with `load_device`: always assigns the
  device to `__main__`, runs `_post_connect_setup`, primes HDF1.
- **Energy tracking** prompt accepts `0` to disable tracking on every
  device.
- **`pr_setup`** memory leak fixed; `fixQ` reset on scan abort fixed;
  scan hints fixed; `predict_save_path` and `use_scalers` fixes.

PRs: [#37](https://github.com/BCDA-APS/polar-bits/pull/37),
[#53](https://github.com/BCDA-APS/polar-bits/pull/53).

### Plans module split (mostly transparent)

`id4_common.plans.local_scans` was split into focused modules so
imports inside macros are tidier:

| New module | Plans |
|------------|-------|
| `base_scans` | `lup`, `ascan`, `count`, `qxscan`, `th2th` |
| `grid_scans` | `grid_scan`, `rel_grid_scan` |
| `hkl_scans` | `hklscan`, `hscan`, `kscan`, `lscan`, `psiscan` |
| `move_plans` | `mv`, `mvr`, `abs_set` (with magnet911 staging) |
| `peak_position` | `cen`, `com`, `maxi`, `mini`, `peak`, `peak_pos`, `pmax`, `pmin` |
| `peak_position_legacy` | `cen2`, `maxi2`, `mini2` |

`id4_common.plans.local_scans` still exists as a back-compat shim that
re-exports from each of the above, so existing macros keep working
without changes. New macros should prefer
`from id4_common.macros.macros_api import *`, which is the curated
surface and is kept stable across internal reorgs.

PRs: [#56](https://github.com/BCDA-APS/polar-bits/pull/56),
[#65](https://github.com/BCDA-APS/polar-bits/pull/65).

### Documentation

The full documentation site was audited and refreshed:

- New [Useful Functions](useful_functions.md) reference page covering
  every session-level helper (`pr_setup`, `qxscan_setup`,
  `temperature_setup`, `restore_session_state`, device loaders, …).
- New "What's New" page (this one), updated each APS run.
- Several broken code snippets fixed (`experiment_load_from_bluesky`
  → `experiment_load_from_scan`, LakeShore `.input.A.temperature` /
  `.output.one.setpoint` → `loop1.readback` / `loop1.setpoint`, eight
  wrong device-class names in `devices_guide.md`).
- `peaks.cen` vs `peaks.com` documentation fixed (they are not the
  same — `peaks.cen` is the FWHM midpoint, `peaks.com` is the
  moment-based centroid).
- `devices_reference.md` filled in nine missing devices.
- The autogenerated API reference is no longer tracked in git
  (regenerated on every build, was producing ~140 noisy diffs after
  every local `sphinx-build`).

PRs: [#31](https://github.com/BCDA-APS/polar-bits/pull/31),
[#66](https://github.com/BCDA-APS/polar-bits/pull/66).
