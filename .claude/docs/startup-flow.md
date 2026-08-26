# Startup Flow

Read this when debugging why a device didn't connect at startup, or changing
what `_common_startup.py` sets up.

There are two startup entry points:

1. `id4_{b,g,h,raman}/startup.py` — per-beamline. Loads station-specific config, then `from id4_common._common_startup import *`, then `make_devices(..., connect=False)`, then `connect_device(...)` for devices matching that beamline's stations list. No interactive prompt.
2. `id4_common/startup.py` — combined. Loads the shared config and prompts the user `"Do you want to load all devices?"`. If yes, loads every station (`["core", "4idb", "4idg", "4idh"]`).

**Exception: `id4_raman/startup.py` does not follow pattern 1.** It does not
import `_common_startup` at all — it reimplements the sequence inline, and
that copy has already drifted from `_common_startup.py` (missing several of
the imports listed below, and importing the now-nonexistent
`id4_common.utils.polartools_hklpy_imports` instead of
`polartools_hklpy2_imports` — this looks like a real bug, not just doc
staleness; verify before relying on Raman startup). Treat `id4_raman/startup.py`
as its own source of truth rather than assuming it mirrors the other three
beamlines.

`id4_b`, `id4_g`, and `id4_h`'s `startup.py` share `id4_common/_common_startup.py`, which in order:
1. Calls `init_instrument("guarneri")` and clears `oregistry`
2. Sets up APS DM integration (`aps_dm_setup`)
3. Registers Bluesky and POLAR-local IPython magics
4. Imports `RE`, `bec`, `cat_full`, `cat_legacy`, `peaks`, `sd` (each beamline's `startup.py` then derives its own `cat` from `cat_full` via `db_query(...)`)
5. Conditionally loads NeXus and SPEC callbacks based on `iconfig.yml`
6. Loads dichro stream callbacks
7. In non-QueueServer sessions, imports plans, suspenders, counters, attenuators, etc.
8. Installs the A-shutter suspender on the RunEngine

Each beamline startup connects only the devices whose labels match its `stations` list:

| Beamline | stations list |
|----------|--------------|
| 4IDB | `["core", "4idb"]` |
| 4IDG | `["core", "4idg"]` |
| 4IDH | `["core", "4idh"]` |
| Raman | `["4idb"]` |

A device shared between beamlines lists each station's label directly rather
than a single `"core"` label — e.g. `crl` in `devices.yml` carries
`["4idg", "4idh", ...]`. `"core"` is reserved for devices loaded by every
hutch (shared upstream/optics equipment); a device scoped to one beamline
only (e.g. `gslt`, which is 4IDG-only) carries just that one station label.
