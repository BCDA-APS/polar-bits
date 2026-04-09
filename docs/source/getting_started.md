# Getting Started

## Prerequisites

polar-bits requires Linux (or macOS) with Conda. The `hkl` package for
crystallography calculations and `pyepics` for EPICS communication are installed
via Conda because they depend on compiled C/Fortran libraries.

## Installation

```bash
export ENV_NAME=polar-bits
conda create -y -n $ENV_NAME python=3.11 hkl pyepics aps-dm-api
conda activate $ENV_NAME
pip install -e ".[dev]"
```

### hklpy LD_LIBRARY_PATH

After creating the environment, set the library path so hklpy can find its
compiled dependencies:

```bash
conda env config vars set LD_LIBRARY_PATH="$HOME/.conda/envs/$ENV_NAME/lib:$LD_LIBRARY_PATH"
```

### Documentation dependencies

To build the documentation locally, install the `doc` extras:

```bash
pip install -e ".[doc]"
```

---

## Starting an Interactive Session

Launch IPython from your terminal:

```bash
ipython
```

Then import everything from the beamline startup module:

```python
from id4_common.startup import *
```

The startup module will:

1. Load `iconfig.yml` configuration
2. Set up APS Data Management integration
3. Initialize the RunEngine (`RE`), databroker catalog (`cat`), and BEC
4. Load SPEC / NeXus callbacks (based on `iconfig.yml` settings)
5. Prompt you to load devices
6. Connect devices for your beamline
7. Install shutter suspenders on the RunEngine

---

## Loading Devices

After startup, use these helpers to manage device connections:

```python
# List all available devices
find_loadable_devices()

# Filter by label
find_loadable_devices(label="4idg")

# Connect a specific device
load_device("transfocator")

# Disconnect and remove from baseline
remove_device("transfocator")

# Reload all devices (useful after devices.yml changes)
reload_all_devices()
reload_all_devices(stations=["core", "4idh"])  # for a specific beamline
```

---

## Running Simulated Plans

To verify that the installation works without requiring EPICS connections,
run the built-in simulation plans:

```python
RE(sim_print_plan())
RE(sim_count_plan())
RE(sim_rel_scan_plan())
```

---

## Jupyter Notebook

You can also start a session inside JupyterLab:

```bash
jupyter lab
```

Then in a notebook cell:

```python
from id4_common.startup import *
```

---

## Beamline-Specific Startup

Each beamline has its own startup module that loads its specific devices:

| Beamline | Import |
|----------|--------|
| 4IDB | `from id4_b.startup import *` |
| 4IDG | `from id4_g.startup import *` |
| 4IDH | `from id4_h.startup import *` |
| Raman | `from id4_raman.startup import *` |
