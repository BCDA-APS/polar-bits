# Writing Macros

Macros are Python files (or functions) that extend a session with reusable
procedures. They range from simple motor shortcuts to complex multi-step
Bluesky plans. The files in `.usage_logs/` provide real examples from
production sessions.

---

## Startup Scripts (Shell)

The `startup_scripts/` folder contains shell scripts that launch a session
for each beamline. Each one activates the conda environment and starts IPython
with the appropriate import:

```bash
# startup_scripts/bluesky-4idh
#!/bin/bash
source /APSshare/miniconda/x86_64/bin/activate polar-bits
ipython -i -c "from id4_h.startup import *"
```

Run from a terminal:

```bash
bluesky-4idg    # 4IDG session
bluesky-4idh    # 4IDH session
bluesky-4idb    # 4IDB session
bluesky-core    # shared core only
```

---

## Per-Session Startup Files

After the main shell startup, users typically run a Python file that handles
session-specific setup: loading extra devices, setting energy tracking,
configuring detectors, and defining motor shortcuts. This is run inside IPython
with `%run`:

```python
%run startup_4idh.py
```

A typical session startup file looks like this:

```python
# startup_4idh.py
from apsbits.core.instrument_init import oregistry
from id4_common.utils.experiment_utils import experiment_resume
from id4_common.utils.counters_class import counters
from id4_common.utils.pr_setup import pr_setup
import matplotlib.pyplot as plt

plt.ion()    # enable interactive plots

# Restore the previous session from its YAML snapshot.
# experiment_resume() auto-discovers the snapshot in the current working
# directory or via cat[-1] (whichever it finds first). If neither is
# available — first run of an experiment — fall back to the full
# experiment_setup() prompt, or to experiment_load_from_bluesky() to
# re-derive from a Bluesky run document.
experiment_resume()

# Energy tracking
energy = oregistry.find("energy")
energy.tracking_setup(["undulators_ds", "pr2"])

# Undulator offset
undulators = oregistry.find("undulators")
undulators.ds.energy_offset.put(-0.063)
undulators.ds.energy_deadband.put(0.002)

# Default detector/monitor selection
counters.plotselect(9, 8)

# PR2 setup for helicity switching
pr_setup.positioner    = oregistry.find("pr2_pzt_localdc")
pr_setup.offset        = oregistry.find("pr2_pzt_offset_microns")
pr_setup.oscillate_pzt = True

# Load motor shortcuts and macros
from motor_shortcuts import *
from macros import *
```

---

## Motor Shortcuts

Create short variable names for frequently used motors by retrieving them
from the device registry. Put these in a `motor_shortcuts.py` file:

```python
# motor_shortcuts.py — 4IDH example
from apsbits.core.instrument_init import oregistry

_mag = oregistry.find("magnet911")

tabx  = _mag.tab.x       # sample table X
taby  = _mag.tab.y       # sample table Y
tabth = _mag.tab.srot    # sample table rotation
samy  = _mag.samp.y      # sample Y
samth = _mag.samp.th     # sample rotation
field = _mag.ps.field    # magnetic field (Tesla)
```

```python
# motor_shortcuts.py — 4IDG example
from apsbits.core.instrument_init import oregistry

huber_euler = oregistry.find("huber_euler")
huber_hp    = oregistry.find("huber_hp")
energy      = oregistry.find("energy")

sx  = huber_euler.x
sy  = huber_euler.y
phi = huber_euler.phi
chi = huber_euler.chi
delta = huber_euler.delta

nanox = huber_hp.nanox
nanoy = huber_hp.nanoy
```

Import with a wildcard so shortcuts land in the session namespace:

```python
from motor_shortcuts import *
# now: tabx, field, phi, etc. are directly usable
```

---

## Writing Bluesky Plans

Bluesky plans are Python generator functions. They use `yield from` to compose
built-in plan stubs, which allows the RunEngine to track, pause, and replay
them. Any sequence of moves and scans can be wrapped in a plan:

```python
# macros.py
from bluesky.plan_stubs import abs_set, sleep
from id4_common.plans.local_scans import lup, ascan, mv, grid_scan, rel_grid_scan
from id4_common.plans.center_maximum import cen
from id4_common.utils.counters_class import counters
from apsbits.core.instrument_init import oregistry

huber_hp = oregistry.find("huber_hp")
energy   = oregistry.find("energy")


def align_sample():
    """Align sample in X and Y by scanning to the transmission peak."""
    tabx  = oregistry.find("magnet911").tab.x
    taby  = oregistry.find("magnet911").tab.y
    yield from lup(tabx, -0.5, 0.5, 30, 0.2)
    yield from cen(tabx)
    yield from lup(taby, -0.5, 0.5, 30, 0.2)
    yield from cen(taby)


def energy_map(energies, dwell=0.5):
    """Take a 2D nano-scan at each energy in the list."""
    for en in energies:
        yield from mv(energy, en)
        yield from rel_grid_scan(
            huber_hp.nanoy, -3, 3, 31,
            huber_hp.nanox, -2, 2, 21,
            dwell,
            snake_axes=True,
        )
```

Run a plan:

```python
RE(align_sample())
RE(energy_map([6.205, 6.208, 6.211]))
```

Chain plans sequentially:

```python
RE(align_sample())
RE(energy_map([6.205, 6.208, 6.211], dwell=0.1))
```

Or within a single plan:

```python
def overnight_run(energies):
    """Full overnight sequence."""
    yield from align_sample()
    yield from energy_map(energies)

RE(overnight_run([6.205, 6.208, 6.210, 6.212]))
```

---

## Accessing Devices Inside Plans

Use `oregistry.find()` at the top of the macro file to get device references.
Avoid accessing the registry inside a running plan — resolve names at import
time instead:

```python
# Good — resolve at import time
_magnet = oregistry.find("magnet911")
field   = _magnet.ps.field

def field_sweep():
    yield from ascan(field, -1, 1, 50, 2.0, dichro=True)
```

---

## Non-Interactive Experiment Setup in Scripts

When running from a script (not interactive), pass all arguments to
`experiment_setup()` as keywords so it does not prompt:

```python
from id4_common.utils.experiment_utils import experiment_setup, experiment
from apsbits.utils.config_loaders import get_config
from pathlib import Path

experiment_setup(
    esaf_id         = 281924,
    proposal_id     = "1014446",
    base_name       = "scan",
    sample          = "EuAl4",
    server          = "dserv",
    experiment_name = "Frontini_26-1",
    reset_scan_id   = 0,        # last scan_id = 0 → next scan = 1
)

# Override the data path if needed
iconfig = get_config()
experiment.base_experiment_path = (
    Path(iconfig["DM_ROOT_PATH"]) / "2026-1/Frontini_26-1/data"
)
```

`reset_scan_id` is the **last completed** scan number, not the next one
— `0` means "fresh start, next scan will be `1`"; `47` means "continue
from where we left off, next scan will be `48`". `-1` is the no-op
sentinel.

If you do not want `experiment_setup()` to talk to Data Management at
all (e.g. DM is down), nothing special is needed: the function probes
DM at the start and falls back to `dserv` automatically with a single
warning. To force the bypass even when DM is up, pass
`server="dserv"` or `esaf_id="dev"`/`proposal_id="dev"`.

---

## Logging Notes Within a Session

Use `spec_comment` to annotate the SPEC logbook with free-form text at any
point during a session:

```python
spec_comment("Sample: EuAl4 single crystal, (001) face")
spec_comment("PR2 theta = 22.302 deg, field = +3 T, T = 100 K")
spec_comment("Starting overnight field-dependent XMCD run")
```

Comments appear in the SPEC `.dat` file prefixed with `#C` and are visible
in any SPEC data viewer.

For Python-side logging within a macro, use the standard `logging` module:

```python
import logging
logger = logging.getLogger(__name__)

def my_plan():
    logger.info("Starting field sweep")
    yield from ascan(field, -1, 1, 50, 2.0)
    logger.info("Field sweep complete")
```

---

## Importing Macros

Load macros into the session namespace:

```python
%run macros_4idh.py          # executes the file; all names land in session
from macros_4idh import *    # explicit wildcard import
```

To share macros across sessions, keep them in a dedicated directory and use
`%run` from anywhere:

```python
%run /home/beams/POLAR/macros/macros_4idh.py
```
