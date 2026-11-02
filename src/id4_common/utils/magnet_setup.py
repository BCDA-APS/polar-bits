"""
Label-keyed setup helper for the 4-ID-G superconducting magnet.

Asks whether each registered magnet is the one to select and, on a yes,
injects two positioners into the interactive session:

- ``mfield`` — the magnet field positioner (use ``set_field()`` to move it)
- ``mcurrent`` — the magnet current positioner
- ``MAGNET`` — the active magnet label (or ``None``)

Only ``hts110`` (``gmag``, 2 T superconducting magnet, 4-ID-G) is listed in
:data:`MAGNETS` for now. Adding another magnet later is a one-line edit to
that dict — no class changes, no devices.yml edits.
"""

import logging
import sys

from apsbits.core.instrument_init import oregistry

from .device_loader import connect_device

__all__ = [
    "MAGNETS",
    "magnet_setup",
    "get_active_label",
    "get_active_field",
    "get_active_current",
    "set_field",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config: label -> (device_name, field_attr_path, current_attr_path)
#
# `device_name` is looked up via `oregistry.find(...)` so it must match a
# `devices.yml` entry (or anything else registered at startup).  The two
# attribute paths are dotted strings resolved with `getattr`.
# ---------------------------------------------------------------------------
MAGNETS = {
    # 4-ID-G 2 T superconducting magnet (KepcoDevice power supply)
    "g-hts110": ("gmag", "field", "current"),
}

_DESCRIPTIONS = {
    "g-hts110": "2 T superconducting magnet, 4-ID-G",
}

# Supply settings written to the device when the label is selected.  Keys are
# dotted attribute paths on the device; values are written with `.set()`.
# The voltage entries use the writable protection signals because the
# `voltage_limit_*` signals on KepcoDevice are read-only.
MAGNET_SETTINGS = {
    "g-hts110": {
        # "mode": not written here. setfuncmode is an enum index PV and
        # writing the string "CURR" fails with ValueError. KepcoDevice's
        # auto-mode callback already keeps the supply in current mode.
        "current_limit_positive": 115,
        "current_limit_negative": 115,
        "voltage_protection_positive": 1.1,
        "voltage_protection_negative": 1.1,
    },
}


# Module-level cache so `magnet_setup()` can report the current selection
# and the getters below work without touching `sys.modules["__main__"]`.
_active_label: str | None = None
_active_field = None
_active_current = None


def get_active_label():
    """Return the currently-active magnet label, or ``None``."""
    return _active_label


def get_active_field():
    """Return the currently-active field positioner, or ``None``."""
    return _active_field


def get_active_current():
    """Return the currently-active current positioner, or ``None``."""
    return _active_current


def set_field(value=None, *, wait=True):
    """
    Move the active magnet to a field setpoint, or report the current field.

    Parameters
    ----------
    value : float, optional
        Field setpoint, in the units of the ``gmag.field`` positioner.  If
        ``None`` (default), nothing is moved and the current field readback
        is returned.
    wait : bool, optional
        If ``True`` (default), block until the move finishes.  If ``False``,
        return immediately and leave the move running in the background.

    Returns
    -------
    float or None
        The field readback when ``value`` is ``None``, otherwise ``None``.

    Raises
    ------
    RuntimeError
        No magnet has been selected yet; run :func:`magnet_setup` first.
    """
    if _active_field is None:
        raise RuntimeError(
            "No magnet selected. Run magnet_setup() before set_field()."
        )

    if value is None:
        return _active_field.readback.get()

    logger.info("Setting %s field to %s", _active_label, value)
    status = _active_field.set(value)
    if wait:
        status.wait()


def _resolve_path(device, dotted):
    """Walk a dotted attribute path on ``device`` and return the final attr."""
    obj = device
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


def _confirm(label):
    """Interactive yes/no prompt asking whether to select ``label``."""
    device_name = MAGNETS[label][0]
    description = _DESCRIPTIONS.get(label, label)
    answer = (
        input(f"Select {device_name} ({description})? [Y/n]: ").strip().lower()
    )
    return answer in ("", "y", "yes")


def magnet_setup(label=None):
    """
    Bind ``mfield`` and ``mcurrent`` to the selected magnet.

    Parameters
    ----------
    label : str, optional
        Key into :data:`MAGNETS`.  If ``None`` (default), ask yes/no for
        each magnet in turn and select the first one confirmed.

    Side effects
    ------------
    On success, sets the following attributes on ``__main__``:

    - ``mfield`` — the resolved field positioner (movable).
    - ``mcurrent`` — the resolved current positioner (movable).
    - ``MAGNET`` — the active magnet label string.

    Raises
    ------
    KeyError
        ``label`` is not in :data:`MAGNETS`.
    LookupError
        The mapped device is not in ``oregistry``.
    AttributeError
        One of the dotted attribute paths does not resolve on the device.
    """
    global _active_label, _active_field, _active_current

    if label is None:
        for candidate in MAGNETS:
            if _confirm(candidate):
                label = candidate
                break
        else:
            print("No magnet selected; magnet_setup() made no changes.")
            return

    if label not in MAGNETS:
        raise KeyError(
            f"Unknown magnet label {label!r}. "
            f"Known labels: {sorted(MAGNETS)}.  Add a new row to MAGNETS "
            "in id4_common.utils.magnet_setup."
        )

    device_name, field_path, current_path = MAGNETS[label]

    device = oregistry.find(device_name, allow_none=True)
    if device is None:
        raise LookupError(
            f"Magnet {label!r} maps to device {device_name!r}, which is not "
            "in oregistry.  Either load it (`load_device('...')`) or fix the "
            "MAGNETS entry."
        )

    # gmag is not loaded at startup (rarely used), so connect it on demand.
    if not device.connected:
        logger.info("%s is not connected; connecting now.", device_name)
        connect_device(device, raise_error=False)
        if not device.connected:
            raise ConnectionError(
                f"Could not connect {device_name!r} for magnet {label!r}. "
                "Check the IOC, then run magnet_setup() again."
            )

    # Configure the supply before binding, so a failed write leaves the
    # previous selection untouched.
    # Each write is bounded so a stalled PV reports which setting hung
    # instead of blocking the session.
    for attr, value in MAGNET_SETTINGS.get(label, {}).items():
        logger.info("Writing %s.%s = %s", device_name, attr, value)
        try:
            _resolve_path(device, attr).set(value, timeout=10).wait(timeout=10)
        except TimeoutError as exc:
            raise TimeoutError(
                f"Timed out writing {device_name}.{attr} = {value}. Selection "
                f"of {label!r} was not completed; check the supply, then run "
                "magnet_setup() again."
            ) from exc
        logger.info("%s.%s -> %s", device_name, attr, value)

    new_field = _resolve_path(device, field_path)
    new_current = _resolve_path(device, current_path)

    _active_label = label
    _active_field = new_field
    _active_current = new_current

    main = sys.modules["__main__"]
    main.mfield = new_field
    main.mcurrent = new_current
    main.MAGNET = label

    logger.info(
        "Active magnet: %s  (mfield=%s.%s, mcurrent=%s.%s)",
        label,
        device_name,
        field_path,
        device_name,
        current_path,
    )
