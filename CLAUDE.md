# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`polar-bits` is a Bluesky-based data acquisition instrument package for the POLAR beamline (4ID sector) at the Advanced Photon Source (APS). It is built on the [BITS (Bluesky Instrument Toolkit Structure)](https://BCDA-APS.github.io/BITS/) framework from the `apsbits` package.

## Development Setup

```bash
conda create -y -n polar-bits python=3.11 hkl pyepics
conda activate polar-bits
pip install -e ".[dev]"
```

## Commands

**Linting:**
```bash
pre-commit run --all-files
```

**Testing:**
```bash
pytest
pytest path/to/test_file.py::test_name  # single test
```

**QueueServer (per beamline):**
```bash
./src/id4_b_qserver/qs_host.sh restart   # start/restart
./src/id4_b_qserver/qs_host.sh status
queue-monitor &                           # GUI client
```
Each beamline has a `qs-config.yml` and `qs_host.sh`. The QS uses Redis (localhost:6379) for communication and an IPython kernel backend. `startup.py` detects QueueServer context via `running_in_queueserver()` and adjusts imports accordingly (e.g., no interactive prompts, no shutter suspenders).

**Start interactive session (IPython):**
```bash
ipython
# Combined session (prompts to load all stations' devices):
from id4_common.startup import *
# Or per-beamline (loads only that station's devices, no prompt):
from id4_b.startup import *      # 4IDB
from id4_g.startup import *      # 4IDG
from id4_h.startup import *      # 4IDH
from id4_raman.startup import *  # Raman
```

## Architecture

All beamlines share `id4_common` and have beamline-specific packages:

- `id4_common/` — shared devices, plans, callbacks, utils for all beamlines
- `id4_b/`, `id4_g/`, `id4_h/`, `id4_raman/` — beamline-specific overrides and startup
- `id4_{b,g,h,raman}_qserver/` — QueueServer configs and launch scripts per beamline
- `id4_common_qserver/` — shared QueueServer components

Configuration is YAML-driven: `src/id4_common/configs/iconfig.yml` (RunEngine
metadata, output formats, DM paths, detector defaults, logging) and
`src/id4_common/configs/devices.yml` (single source of truth for every
device, its EPICS prefixes, and its beamline labels). See
`.claude/docs/configuration.md` before adding/editing a device or writing a
new device class — it covers the required PV-agnostic `__init__` pattern and
the `DynamicDeviceComponent` factory pattern.

Startup connects devices in two phases (instantiate-without-connect, then
connect by label) so a dead IOC doesn't block the whole session — see
`.claude/docs/startup-flow.md` for the entry points and the `_common_startup`
sequence, and `.claude/docs/device-loading.md` for `oregistry`,
`load_device`/`reload_all_devices`, the `_post_connect_setup()` contract, HDF1
plugin priming, and the detector plotting (`CountersMixin`) API.

Data output (SPEC/NeXus/dichro), session logging, and temperature-controller
setup are covered in `.claude/docs/data-output-and-logging.md`.

## Implementing New Devices & Code

When new code needs to read or write hardware/EPICS state, follow this
priority order — **do not start with raw `pyepics`**:

1. **Use a signal on an existing ophyd device.** Find it via
   `oregistry.find(name)` / `oregistry.findall(...)` (imported as
   `from apsbits.core.instrument_init import oregistry`), then read/write the
   ophyd `Signal`/`Component` on it (`.get()`, `.put()`, `.set()`). This is
   the default whenever a device in `devices.yml` already models the PV.
   Example pattern already in the codebase:
   `sgz_vortex = oregistry.find("sgz_vortex"); sgz_vortex.div_by_n.n.get()`
   (`src/id4_common/plans/_local_scan_utils.py`).
2. **Reach for an apstools or ophyd building block**
   ([apstools](https://github.com/BCDA-APS/apstools),
   [ophyd](https://github.com/bluesky/ophyd)) — e.g. `EpicsSignal`,
   `EpicsSignalRO`, `EpicsSignalWithRBV`, apstools mixins/utilities — when no
   existing device exposes the needed PV but it still deserves to be modeled
   as a signal rather than poked ad hoc.
3. **Add the signal to an existing device class, or create a new device
   class** ([guarneri](https://github.com/BCDA-APS/guarneri) registers it via
   `oregistry`) when the PV represents real, reusable device behavior. Follow
   the PV-agnostic pattern in `.claude/docs/configuration.md` and the
   `_post_connect_setup()` rule in `.claude/docs/device-loading.md`. This is
   the right home for anything read/written more than once.
4. **Only as a last resort, use direct `pyepics` `caget`/`caput`** — for a
   truly one-off, throwaway PV poke that doesn't warrant modeling.
   **Whenever this path is taken, explicitly tell the user** which PV and why
   none of steps 1-3 fit; never use pyepics silently.

Existing raw `caget`/`caput` calls in `hkl_utils.py` and
`attenuator_utils.py` are known tech debt, not a pattern to imitate — don't
add more of them when touching that code; migrate opportunistically if a
change already touches it, but don't scope-creep an unrelated task into a
refactor.

## Documentation

The docs site (Sphinx + PyData theme + sphinx-autoapi, hosted on GitHub
Pages) is built from `docs/source/`. See `.claude/docs/documentation-site.md`
for the local build command, deploy workflow, and page structure.

## Code Style

- Line length: 80 (both ruff and black configs in `pyproject.toml`)
- Python 3.11+
- Linting: ruff (replaces flake8/isort/black in pre-commit)
- Docstrings required for all public classes/functions/methods/modules (ruff rules D100-D107)

## Detailed References

Read these only when the task at hand touches that area:

- `.claude/docs/configuration.md` — `iconfig.yml`/`devices.yml`, PV-agnostic device pattern, `DynamicDeviceComponent` factory pattern
- `.claude/docs/startup-flow.md` — the two startup entry points, `_common_startup` sequence, per-beamline `stations` table
- `.claude/docs/device-loading.md` — `id4_common/` module map, `oregistry`/`load_device`/`reload_all_devices`, deferred EPICS connection pattern, HDF1 priming, `CountersMixin` detector plotting API
- `.claude/docs/data-output-and-logging.md` — SPEC/NeXus/dichro output, session logging config, temperature controllers
- `.claude/docs/documentation-site.md` — Sphinx build/deploy commands and doc-page structure
