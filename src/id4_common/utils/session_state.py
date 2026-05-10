"""
Auto-saved per-experiment session state in ``RE.md['session_state']``.

Each setup helper in this package — ``pr_setup``, ``energy.tracking_setup``,
``counters.plotselect``, ``undulator_setup``, ``qxscan_setup`` — calls the
matching ``_save_*`` helper at the tail of its body.  The snapshot is
mirrored into the apsbits ``RE.md`` ``PersistentDict`` so it survives
bluesky restarts.

To re-apply every saved knob after a restart::

    from id4_common.utils.session_state import restore_session_state
    status = restore_session_state()
    for knob, s in status.items():
        print(f"  {knob:18}  {s}")

Each restore step reports ``"applied"`` / ``"skipped: <reason>"`` /
``"failed: <Exception>"``.  ``restore_session_state`` never raises — a
missing device or a single failed put is logged and the rest of the
restore continues.

The schema under ``RE.md['session_state']`` is a nested dict with one
sub-key per knob group:

- ``saved_at``         (str, ISO timestamp; refreshed on every save)
- ``undulators``       (``{us|ds: {energy_offset, energy_deadband}}``)
- ``energy_tracking``  (``{devices: [name, ...]}``)
- ``pr_setup``         (``{positioner, offset, oscillate_pzt}``)
- ``counters``         (``{detectors, monitor, extra_read}`` — by
  ``(device, channel)`` pairs to survive index shifts)
- ``qxscan``           (``{source}`` (json filename) or ``{params}``)
"""

from __future__ import annotations

import logging
from datetime import datetime

from apsbits.core.instrument_init import oregistry

from .run_engine import RE

logger = logging.getLogger(__name__)

__all__ = [
    "restore_session_state",
    "save_session_state",
]

_TOP_KEY = "session_state"


# ---------------------------------------------------------------------------
# Snapshot read / commit primitives
# ---------------------------------------------------------------------------


def _state() -> dict:
    """Return the current session_state dict (empty if absent or RE.md is
    not yet ready).
    """
    try:
        existing = RE.md.get(_TOP_KEY)
    except Exception:  # noqa: BLE001 — RE may be absent very early at startup
        return {}
    if not isinstance(existing, dict):
        return {}
    return dict(existing)


def _commit(state: dict) -> None:
    """Write the snapshot back, refreshing ``saved_at``."""
    state["saved_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        RE.md[_TOP_KEY] = state
    except Exception as exc:  # noqa: BLE001 — never break a setup function
        logger.warning("Could not persist session_state to RE.md: %s", exc)


# ---------------------------------------------------------------------------
# Per-knob save helpers — called from each setup function's tail
# ---------------------------------------------------------------------------


def _save_undulator() -> None:
    """Snapshot ``energy_offset`` and ``energy_deadband`` for both undulators."""
    undulators = oregistry.find("undulators", allow_none=True)
    if undulators is None:
        return
    snapshot: dict = {}
    for side in ("us", "ds"):
        dev = getattr(undulators, side, None)
        if dev is None:
            continue
        try:
            snapshot[side] = {
                "energy_offset": float(dev.energy_offset.get()),
                "energy_deadband": float(dev.energy_deadband.get()),
            }
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "session_state: could not read %s undulator offset: %s",
                side,
                exc,
            )
    if not snapshot:
        return
    state = _state()
    state["undulators"] = snapshot
    _commit(state)


def _save_energy_tracking() -> None:
    """Snapshot the names of every device currently flagged as tracking."""
    energy = oregistry.find("energy", allow_none=True)
    if energy is None:
        return
    try:
        active = [d.name for d in energy.trackable_devices if d.tracking.get()]
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "session_state: could not read energy tracking state: %s", exc
        )
        return
    state = _state()
    state["energy_tracking"] = {"devices": active}
    _commit(state)


def _save_pr_setup() -> None:
    """Snapshot the active ``pr_setup`` positioner / offset / oscillate flag."""
    try:
        from .pr_setup import pr_setup as _pr
    except Exception as exc:  # noqa: BLE001
        logger.info("session_state: pr_setup not importable: %s", exc)
        return
    snapshot = {
        "positioner": getattr(_pr.positioner, "name", None),
        "offset": getattr(_pr.offset, "name", None),
        "oscillate_pzt": bool(_pr.oscillate_pzt),
    }
    state = _state()
    state["pr_setup"] = snapshot
    _commit(state)


def _save_counters() -> None:
    """Snapshot ``counters.plotselect`` dets/mon/extra_read by (dev, channel)."""
    try:
        from .counters_class import counters as _c
    except Exception as exc:  # noqa: BLE001
        logger.info("session_state: counters not importable: %s", exc)
        return
    snapshot = {
        "detectors": [list(t) for t in _c._selected_dets],
        "monitor": list(_c._selected_mon) if _c._selected_mon else None,
        "extra_read": [list(t) for t in _c._selected_extra_read],
    }
    state = _state()
    state["counters"] = snapshot
    _commit(state)


def _save_qxscan(*, source: str | None = None) -> None:
    """Snapshot the qxscan setup — by file pointer when available, else inline."""
    qx = oregistry.find("qxscan_setup", allow_none=True)
    if qx is None:
        return
    snapshot: dict = {}
    if source is not None:
        snapshot["source"] = str(source)
    else:
        try:
            snapshot["params"] = qx._make_params_dict()
        except Exception as exc:  # noqa: BLE001
            logger.info("session_state: could not read qxscan params: %s", exc)
            return
    state = _state()
    state["qxscan"] = snapshot
    _commit(state)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_session_state() -> dict:
    """Snapshot every supported knob (escape hatch — normal flow is the
    auto-save hooks).
    """
    _save_undulator()
    _save_energy_tracking()
    _save_pr_setup()
    _save_counters()
    _save_qxscan()
    return _state()


def restore_session_state(state: dict | None = None) -> dict:
    """Re-apply every knob from ``RE.md['session_state']`` (or ``state``).

    Returns ``{knob_group: status_str}`` so callers can print a summary.
    Never raises.
    """
    if state is None:
        state = _state()
    status: dict = {}
    if not state:
        status["session_state"] = "skipped: no snapshot in RE.md"
        return status

    if "undulators" in state:
        status["undulators"] = _restore_undulator(state["undulators"])
    if "energy_tracking" in state:
        status["energy_tracking"] = _restore_energy_tracking(
            state["energy_tracking"]
        )
    if "pr_setup" in state:
        status["pr_setup"] = _restore_pr_setup(state["pr_setup"])
    if "counters" in state:
        status["counters"] = _restore_counters(state["counters"])
    if "qxscan" in state:
        status["qxscan"] = _restore_qxscan(state["qxscan"])

    return status


# ---------------------------------------------------------------------------
# Per-knob restore helpers — never raise
# ---------------------------------------------------------------------------


def _restore_undulator(snapshot: dict) -> str:
    undulators = oregistry.find("undulators", allow_none=True)
    if undulators is None:
        return "skipped: undulators not loaded"
    try:
        for side, knobs in snapshot.items():
            dev = getattr(undulators, side, None)
            if dev is None:
                continue
            if "energy_offset" in knobs:
                dev.energy_offset.put(float(knobs["energy_offset"]))
            if "energy_deadband" in knobs:
                dev.energy_deadband.put(float(knobs["energy_deadband"]))
        return "applied"
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"


def _restore_energy_tracking(snapshot: dict) -> str:
    energy = oregistry.find("energy", allow_none=True)
    if energy is None:
        return "skipped: energy not loaded"
    try:
        energy.tracking_setup(snapshot.get("devices", []))
        return "applied"
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"


def _restore_pr_setup(snapshot: dict) -> str:
    try:
        from .pr_setup import pr_setup as _pr
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"
    try:
        positioner_name = snapshot.get("positioner")
        offset_name = snapshot.get("offset")
        positioner = (
            oregistry.find(positioner_name, allow_none=True)
            if positioner_name
            else None
        )
        offset = (
            oregistry.find(offset_name, allow_none=True)
            if offset_name
            else None
        )
        if positioner_name and positioner is None:
            return f"skipped: positioner {positioner_name!r} not loaded"
        if offset_name and offset is None:
            return f"skipped: offset {offset_name!r} not loaded"
        _pr.positioner = positioner
        _pr.offset = offset
        _pr.oscillate_pzt = bool(snapshot.get("oscillate_pzt", True))
        return "applied"
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"


def _restore_counters(snapshot: dict) -> str:
    try:
        from .counters_class import counters as _c
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"
    try:
        options = _c.detectors_plot_options

        def _index(pair):
            if not pair:
                return None
            dev, chan = pair
            mask = (options["detectors"] == dev) & (options["channels"] == chan)
            if not mask.any():
                return None
            return int(options.index[mask][0])

        det_idx = [
            i
            for i in (_index(p) for p in snapshot.get("detectors", []))
            if i is not None
        ]
        mon_idx = _index(snapshot.get("monitor"))
        extra_idx = [
            i
            for i in (_index(p) for p in snapshot.get("extra_read", []))
            if i is not None
        ]
        if not det_idx or mon_idx is None:
            return "skipped: saved channels not in current options"
        _c.plotselect(dets=det_idx, mon=mon_idx, extra_read=extra_idx)
        return "applied"
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"


def _restore_qxscan(snapshot: dict) -> str:
    qx = oregistry.find("qxscan_setup", allow_none=True)
    if qx is None:
        return "skipped: qxscan_setup not loaded"
    try:
        if "source" in snapshot:
            qx.load_params_json(snapshot["source"])
            return f"applied (from {snapshot['source']})"
        if "params" in snapshot:
            qx._read_params_dict(snapshot["params"])
            return "applied (from inline params)"
        return "skipped: no qxscan source/params in snapshot"
    except Exception as exc:  # noqa: BLE001
        return f"failed: {type(exc).__name__}: {exc}"
