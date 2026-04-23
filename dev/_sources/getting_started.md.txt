# Getting Started

## Prerequisites

polar-bits is designed to operate in Linux with miniconda. The `hkl` package for
crystallography calculations and `pyepics` for EPICS communication are installed
via Conda because they depend on compiled C/Fortran libraries. The rest of the
packages are installed with `pip`.

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

## Starting polar-bits

Startup scripts are provided in `startup_scripts/`:
- `bluesky-4idb`
- `bluesky-4idg`
- `bluesky-4idh`
- `bluesky-core`

Note that these assume that the environment name is "polar-bits".

The "b", "g", and "h" scripts start the corresponding endstation support. The main difference in these is that it loads the station-specific database catalog, and it connects to the devices labeled "core" or the selected station in `src/id4_common/configs/devices.yml`.

The "core" startup will ask whether you want to connect all devices or none. See next section for more details on loading specific devices.

Note that all devices are always loaded, but not connected.

---

## Data Analysis

[polartools](https://github.com/APS-4ID-POLAR/polartools) is the companion
Python package for loading, processing, and plotting data collected at POLAR.
It provides routines for XAS/XMCD analysis, diffraction peak fitting, image
processing, and general data utilities. polartools functions are available in
the session namespace after startup.

---

## Loading Devices

In order to connect or reload a device you cna use the following utility functions:

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
