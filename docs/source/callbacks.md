# Callbacks and Data Output

polar-bits supports three data output streams, all configured through
`iconfig.yml` and loaded automatically during startup.

---

## SPEC Data Files

**Status:** Enabled by default.

SPEC `.dat` files are written by `id4_common.callbacks.spec_data_file_writer`.
After startup, three helpers are available:

```python
# Create a new SPEC file for this session
newSpecFile("my_experiment")
# → creates a file like: 0409_my_experiment.dat

# Add a free-form comment to the current SPEC file
spec_comment("Sample aligned, beam 50x50 µm")

# The callback instance (subscribes to the RunEngine)
specwriter
```

`newSpecFile` prepends the current month+day, appends the `.dat` extension, and
resets `RE.md["scan_id"]` to the last scan number in the file if the file
already exists.

### `iconfig.yml` settings

```yaml
SPEC_DATA_FILES:
  ENABLE: true
  FILE_EXTENSION: dat
```

Set `ENABLE: false` to disable SPEC output entirely.

---

## NeXus / HDF5 Data Files

**Status:** Opt-in (disabled by default).

NeXus output is written by `id4_common.callbacks.nexus_data_file_writer`.
Enable it in `iconfig.yml`:

```yaml
NEXUS_DATA_FILES:
  ENABLE: true
  FILE_EXTENSION: hdf
```

After enabling, `nxwriter` is available in the session:

```python
nxwriter   # NeXus callback instance
```

Files are written in the NeXus/HDF5 format with standard
`/entry/instrument/...` hierarchy.

---

## Dichroism Stream

The dichroism stream callback (`id4_common.callbacks.dichro_stream`) is always
loaded at startup. It processes circular dichroism data in real time:

```python
dichro                    # DichroStream device
dichro_bec                # Best Effort Callback for the dichro stream
plot_dichro_settings()    # configure dichro plots
```

The dichro callback subscribes to the RunEngine and accumulates
positive/negative helicity readings for on-the-fly XMCD calculation.

---

## Best Effort Callback (BEC)

The standard Bluesky BEC is configured by the `BEC` block in `iconfig.yml`:

```yaml
BEC:
  BASELINE: true    # print baseline readings at scan start
  HEADING: true     # print column headers
  PLOTS: false      # disable live plots (useful in non-GUI sessions)
  TABLE: true       # print scan data as a table
```

`bec` and `peaks` are available in the session:

```python
bec           # BestEffortCallback instance
peaks         # peak-finding helper (populated after each scan)

# After a scan:
peaks.com     # center-of-mass position
peaks.max     # position of maximum
peaks.cen     # centroid position
```

---

## Baseline Supplemental Stream

Devices labelled `"baseline"` in `devices.yml` are read at the start and end
of every scan and stored in the `baseline` stream of the run document:

```yaml
# devices.yml
- name: some_device
  labels: ["core", "baseline"]
```

Enable the baseline label collection in `iconfig.yml`:

```yaml
BASELINE_LABEL:
  ENABLE: true
```
