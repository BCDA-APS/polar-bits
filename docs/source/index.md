# polar-bits

**Bluesky-based data acquisition for the POLAR beamline (4ID) at the Advanced Photon Source.**

polar-bits is built on the [BITS (Bluesky Instrument Toolkit Structure)](https://BCDA-APS.github.io/BITS/)
framework and provides a shared device library, scan plans, and data output callbacks
for four hutches: **4IDB**, **4IDG**, **4IDH**, and **Raman**.

```{toctree}
:maxdepth: 1
:hidden:

getting_started
architecture
configuration
devices_guide
devices_reference
plans
callbacks
queueserver
examples/4idg_diffractometer
examples/4idh_magnet
api/index
```

---

::::{grid} 2 2 3 3
:gutter: 3

:::{grid-item-card} Getting Started
:link: getting_started
:link-type: doc

Installation, first session, loading devices.
:::

:::{grid-item-card} Architecture
:link: architecture
:link-type: doc

Multi-beamline structure, startup flow, station labels.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc

`iconfig.yml` and `devices.yml` explained.
:::

:::{grid-item-card} Devices Guide
:link: devices_guide
:link-type: doc

PV-agnostic pattern, deferred connection, factory classes.
:::

:::{grid-item-card} Device Reference
:link: devices_reference
:link-type: doc

Lookup tables: all core, 4IDB, 4IDG, and 4IDH devices.
:::

:::{grid-item-card} Scan Plans
:link: plans
:link-type: doc

`lup`, `ascan`, `grid_scan`, DM workflow submission.
:::

:::{grid-item-card} Callbacks
:link: callbacks
:link-type: doc

SPEC, NeXus/HDF5, and dichroism stream output.
:::

:::{grid-item-card} QueueServer
:link: queueserver
:link-type: doc

Start/restart the QueueServer per beamline.
:::

:::{grid-item-card} 4IDG Examples
:link: examples/4idg_diffractometer
:link-type: doc

Diffractometer setup, HKL navigation, reciprocal-space scans.
:::

:::{grid-item-card} 4IDH Examples
:link: examples/4idh_magnet
:link-type: doc

Magnet 9-1-1 field sweeps, XMCD spectroscopy, temperature series.
:::

:::{grid-item-card} API Reference
:link: api/index
:link-type: doc

Full auto-generated API for all packages.
:::

::::
