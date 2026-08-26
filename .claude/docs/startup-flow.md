# Startup Flow

Read this when debugging why a device didn't connect at startup, or changing
what `_common_startup.py` sets up.

There are two startup entry points:

1. `id4_{b,g,h,raman}/startup.py` — per-beamline. Loads station-specific config, then `from id4_common._common_startup import *`, then `make_devices(..., connect=False)`, then `connect_device(...)` for devices matching that beamline's stations list. No interactive prompt.
2. `id4_common/startup.py` — combined. Loads the shared config and prompts the user `"Do you want to load all devices?"`. If yes, loads every station (`["core", "4idb", "4idg", "4idh"]`).

Both paths share `id4_common/_common_startup.py`, which in order:
1. Calls `init_instrument("guarneri")` and clears `oregistry`
2. Sets up APS DM integration (`aps_dm_setup`)
3. Registers Bluesky and POLAR-local IPython magics
4. Imports `RE`, `bec`, `cat`, `cat_legacy`, `peaks`, `sd`
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

Devices shared between beamlines (e.g. `crl`, `gslt`) carry the `"core"` label in `devices.yml`.
