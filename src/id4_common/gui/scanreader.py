"""Read a finished scan out of the catalog, in the GUI process.

The Scan plot tab used to ask the kernel for this, through a
``user_expressions`` helper.  That made it unusable during a scan: the poller
will not send a request while the kernel is busy
(``kernel.StatusPoller._poll_kernel``), and a request that did get through would
queue *inside* the kernel behind the running plan.  A scan is exactly when
someone wants to look back at the previous one.

So the GUI reads the catalog itself.  Nothing here touches the RunEngine, and a
load costs the acquisition nothing.  The same argument already applies elsewhere
in this package: ``tabs/flyscanplot.py`` reads its HDF5 directly, and
``tabs/status.py`` reads motor PVs directly to drive the move progress bar --
both because the kernel is busy precisely when the display is wanted.

Qt-free on purpose: the tab runs this on a worker thread, and keeping it plain
means it can be exercised without a GUI.

**The imports are deliberately inside the functions.**  ``import databroker``
costs 5.3 s and opening the catalog another 1.1 s, and the open drags in
``area_detector_handlers`` -> ``ophyd`` -> ``pyepics`` (8 daemon threads and a
Channel Access context) plus 4 pymongo monitor threads.  At module scope that
would be ~6.7 s added to every GUI start-up, including the sessions that never
open the tab.  Paid on the first load instead, off the Qt thread.
"""

import logging
import threading

logger = logging.getLogger(__name__)

#: The fields of ``dichro_monitor`` worth plotting.  ``positioner2`` is all-NaN
#: on a one-positioner scan and dropped below, but on a mesh it carries the
#: fast axis and is what makes an XMCD *map* possible.
DICHRO_FIELDS = (
    "dichro_positioner1",
    "dichro_positioner2",
    "dichro_xas",
    "dichro_xmcd",
)

#: Opened once and reused: 1.1 s a time is too much to pay per load.  Keyed by
#: (catalog name, instrument filter) so a station change reopens rather than
#: silently serving the wrong runs.  Private to this module -- the handle
#: carries a *readWrite* Mongo role, so nothing else should get hold of it.
_CATALOGS = {}
_LOCK = threading.Lock()


def _catalog(catalog_name, instrument_name):
    """Return the station's filtered catalog view, opening it once.

    The ``instrument_name`` filter is load-bearing, not cosmetic: the catalog
    holds 49,287 runs against 24,848 for this station, so roughly half belong to
    other beamlines and scan ids repeat across them.  Reading unfiltered would
    return 4-ID-H's scan 164 rather than an error -- the worst kind of wrong.
    The session's own ``cat`` is filtered the same way in ``id4_g/startup.py``.
    """
    key = (catalog_name, instrument_name)
    with _LOCK:
        catalog = _CATALOGS.get(key)
        if catalog is not None:
            return catalog

        import databroker

        catalog = databroker.catalog[catalog_name].v2
        if instrument_name:
            catalog = catalog.search({"instrument_name": instrument_name})
        _CATALOGS[key] = catalog
        return catalog


def is_connected(catalog_name, instrument_name):
    """Whether the catalog for this station is already open.

    Lets the caller say "connecting…" on the load that will take seven seconds
    and stay quiet on the ones that take a fifth of one.
    """
    with _LOCK:
        return (catalog_name, instrument_name) in _CATALOGS


def _table(catalog, scan_id, stream_name=None):
    """Read one stream as a DataFrame, without the pandas noise.

    v1's ``table()`` rather than the v2 dataset: 0.15 s against 4.8 s merely to
    *build* ``primary.to_dask()`` for a 400-point grid, because v1 leaves
    external data -- the Eiger frames -- as datum ids instead of fetching it.
    Every column read here is a scalar, so nothing is lost.

    ``table()`` also emits ``PerformanceWarning: DataFrame is highly
    fragmented`` dozens of times per call, on stderr, by default; that is
    pandas commenting on databroker's column-by-column assembly and there is
    nothing the caller can do about it.
    """
    import warnings

    from pandas.errors import PerformanceWarning

    run = catalog.v1[int(scan_id)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PerformanceWarning)
        if stream_name is None:
            return run.table()
        return run.table(stream_name=stream_name)


def _stream_names(catalog, scan_id):
    """Stream names of a run, or an empty tuple if they cannot be read."""
    try:
        return tuple(catalog.v1[int(scan_id)].stream_names)
    except Exception:  # noqa: BLE001 - absent streams are not an error here
        logger.debug("Could not list streams for scan %s.", scan_id)
        return ()


def _read_dichro(catalog, scan_id):
    """Return the reduced XAS/XMCD curves, when the scan has them.

    A dichro scan writes a second stream holding what the measurement is *for*:
    XAS and XMCD against the positioner, one point per energy where ``primary``
    has one per polarization.
    """
    if "dichro_monitor" not in _stream_names(catalog, scan_id):
        return None
    try:
        frame = _table(catalog, scan_id, stream_name="dichro_monitor")
    except Exception:  # noqa: BLE001 - a missing stream must not fail the load
        logger.debug("Could not read dichro_monitor for %s.", scan_id)
        return None

    columns = {}
    for name in DICHRO_FIELDS:
        if name not in frame:
            continue
        try:
            values = [float(v) for v in frame[name].values]
        except Exception:  # noqa: BLE001 - a non-numeric column is not ours
            continue
        # dichro_positioner2 is all-NaN on a one-positioner scan, and an
        # all-NaN column is nothing to plot.
        if any(v == v for v in values):
            columns[name] = values
    return columns if len(columns) > 1 else None


def read_scan(catalog_name, instrument_name, scan_id):
    """Return one past scan as a plain dict, or ``{"error": ...}``.

    The shape is what the Scan plot tab's renderers already consume, so the
    drawing code is unchanged by where the data came from.
    """
    try:
        catalog = _catalog(catalog_name, instrument_name)
        run = catalog[int(scan_id)]
        start = dict(run.metadata["start"])
        try:
            descriptors = run.primary.metadata["descriptors"]
        except AttributeError:
            return {"error": f"scan {scan_id} has no primary stream"}

        hinted = set(start.get("hints", {}).get("detectors") or [])
        if not hinted:
            # No detector hints in the start doc -- fall back to the
            # descriptor's own hints, which is where BEC looks.
            for desc in descriptors:
                for spec in (desc.get("hints") or {}).values():
                    hinted.update(spec.get("fields") or [])

        keys = {}
        for desc in descriptors:
            keys.update(desc.get("data_keys") or {})
        fields = sorted(
            key
            for key, spec in keys.items()
            if key in hinted and not spec.get("shape")
        )

        axes = []
        for entry in (start.get("hints") or {}).get("dimensions") or []:
            try:
                axes.append(entry[0][0])
            except Exception:  # noqa: BLE001 - a malformed hint is skippable
                continue

        frame = _table(catalog, scan_id)
        if frame is None or frame.empty:
            # A run with no primary data returns a (0, 0) frame rather than
            # raising -- scan 685 does exactly this.
            return {"error": f"scan {scan_id} has no primary stream"}

        # Every numeric column, not just the hinted ones: the Live plot tab
        # offers the whole descriptor and this tab should be no poorer -- any
        # channel plottable, any other channel usable as the divisor.  Cheap,
        # measured: 171 columns of a 400-point grid is 0.76 MB and about 10 ms,
        # against the 0.47 s read that has already happened.  A column that
        # will not convert is a string or a datum id, which cannot be plotted.
        columns = {}
        for name in frame.columns:
            try:
                columns[name] = [float(v) for v in frame[name].values]
            except Exception:  # noqa: BLE001 - not a numeric column
                continue

        return {
            "dichro": _read_dichro(catalog, scan_id),
            "scan_id": start.get("scan_id"),
            "uid": start.get("uid"),
            "plan_name": start.get("plan_name"),
            "time": start.get("time"),
            "hints": start.get("hints") or {},
            "shape": list(start.get("shape") or []),
            "extents": [list(e) for e in (start.get("extents") or [])],
            "axes": axes,
            "detectors": [f for f in fields if f in columns],
            "columns": columns,
        }
    except Exception as exc:  # noqa: BLE001 - reported in the tab, not raised
        logger.debug("Reading scan %s failed.", scan_id, exc_info=True)
        return {"error": f"{type(exc).__name__}: {exc}"}
