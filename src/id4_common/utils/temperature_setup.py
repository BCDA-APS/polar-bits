"""
Label-keyed setup helper for the active temperature controller (issue #57).

Picks one entry from :data:`TEMPERATURE_CONTROLLERS`, resolves its setpoint
and readback signals on the registered device, and injects the result into
the interactive session as three names:

- ``tc`` — the temperature **control** signal (movable, the setpoint)
- ``ts`` — the temperature **sample** signal (readable, the readback)
- ``TEMPERATURE_CONTROLLER`` — the active label (or ``None``)

After ``temperature_setup("g-336-loop1")`` the user can ``mv tc 295`` /
``RE(count(1, 1))`` and the sample temperature will land in the data and
(by default) the baseline stream every scan.

Adding a new controller is a one-line edit to the ``TEMPERATURE_CONTROLLERS``
dict below — no class changes, no devices.yml edits.
"""

import logging
import sys

from apsbits.core.instrument_init import oregistry

from .run_engine import sd

__all__ = [
    "TEMPERATURE_CONTROLLERS",
    "temperature_setup",
    "get_active_label",
    "get_active_tc",
    "get_active_ts",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config: label -> (device_name, setpoint_attr_path, readback_attr_path)
#
# `device_name` is looked up via `oregistry.find(...)` so it must match a
# `devices.yml` entry (or anything else registered at startup).  The two
# attribute paths are dotted strings resolved with `getattr`-walk (mirrors
# `CountersMixin._preset_monitor_attr`).
# ---------------------------------------------------------------------------
TEMPERATURE_CONTROLLERS = {
    # 4-ID-G LakeShore controllers (already in devices.yml)
    "g-336-loop1": ("temp_336_4idg", "loop1.setpoint", "loop1.readback"),
    "g-336-loop2": ("temp_336_4idg", "loop2.setpoint", "loop2.readback"),
    "g-340-loop1": ("temp_340_4idg", "loop1.setpoint", "loop1.readback"),
    # 4-ID-H 9-Tesla magnet (sub-components of `magnet911`)
    "h-9T-vti-a": ("magnet911", "temps.setpoint_1", "temps.sensor_a"),
    "h-9T-vti-b": ("magnet911", "temps.setpoint_2", "temps.sensor_b"),
    "h-9T-vti-c": ("magnet911", "temps.setpoint_3", "temps.sensor_c"),
    "h-9T-vti-d": ("magnet911", "temps.setpoint_4", "temps.sensor_d"),
    "h-9T-nv": (
        "magnet911",
        "needle_valve.temp.setpoint",
        "needle_valve.temp.readback",
    ),
}


# Module-level cache so re-running `temperature_setup()` keeps the previous
# choice as the prompt default and `te()` (in shorts.py) can find the active
# `tc` without going through `sys.modules["__main__"]`.
_active_label: str | None = None
_active_tc = None
_active_ts = None


def get_active_label():
    """Return the currently-active controller label, or ``None``."""
    return _active_label


def get_active_tc():
    """Return the currently-active setpoint signal, or ``None``."""
    return _active_tc


def get_active_ts():
    """Return the currently-active readback signal, or ``None``."""
    return _active_ts


def _resolve_path(device, dotted):
    """Walk a dotted attribute path on ``device`` and return the final attr."""
    obj = device
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


def _prompt_for_label(default):
    """Interactive prompt: list known labels and accept one."""
    print("Available temperature-controller labels:")
    for key in sorted(TEMPERATURE_CONTROLLERS):
        device, setpoint, readback = TEMPERATURE_CONTROLLERS[key]
        print(f"  {key:18}  ({device}.{setpoint} / {device}.{readback})")
    suffix = f" [{default}]" if default else ""
    answer = input(f"\nLabel{suffix}: ").strip() or default
    return answer


def temperature_setup(label=None, *, add_to_baseline=True):
    """
    Bind ``tc`` (setpoint) and ``ts`` (readback) to the requested controller.

    Parameters
    ----------
    label : str, optional
        Key into :data:`TEMPERATURE_CONTROLLERS`.  If ``None`` (default),
        prompt interactively, defaulting to the previously-active label
        (or no default on the first call of the session).
    add_to_baseline : bool, optional
        If ``True`` (default), append ``ts`` to ``sd.baseline`` so the
        sample temperature is recorded in every scan's baseline stream.
        Removes any previously-active ``ts`` from the baseline first so
        re-running ``temperature_setup`` swaps cleanly.

    Side effects
    ------------
    On success, sets the following attributes on ``__main__``:

    - ``tc`` — the resolved setpoint signal (movable).
    - ``ts`` — the resolved readback signal (readable).
    - ``TEMPERATURE_CONTROLLER`` — the active label string.

    Raises
    ------
    KeyError
        ``label`` is not in :data:`TEMPERATURE_CONTROLLERS`.
    LookupError
        The mapped device is not in ``oregistry``.
    AttributeError
        One of the dotted attribute paths does not resolve on the device.
    """
    global _active_label, _active_tc, _active_ts

    if label is None:
        label = _prompt_for_label(_active_label)

    if not label:
        print("No label given; temperature_setup() aborted.")
        return

    if label not in TEMPERATURE_CONTROLLERS:
        raise KeyError(
            f"Unknown temperature controller label {label!r}. "
            f"Known labels: {sorted(TEMPERATURE_CONTROLLERS)}.  Add a new "
            "row to TEMPERATURE_CONTROLLERS in "
            "id4_common.utils.temperature_setup."
        )

    device_name, setpoint_path, readback_path = TEMPERATURE_CONTROLLERS[label]

    device = oregistry.find(device_name, allow_none=True)
    if device is None:
        raise LookupError(
            f"Temperature controller {label!r} maps to device "
            f"{device_name!r}, which is not in oregistry.  Either load it "
            "(`load_device('...')`) or fix the TEMPERATURE_CONTROLLERS entry."
        )

    new_tc = _resolve_path(device, setpoint_path)
    new_ts = _resolve_path(device, readback_path)

    # Swap baseline membership: remove the previous ts (if any), append the new.
    if add_to_baseline:
        if _active_ts is not None and _active_ts in sd.baseline:
            sd.baseline.remove(_active_ts)
        if new_ts not in sd.baseline:
            sd.baseline.append(new_ts)

    _active_label = label
    _active_tc = new_tc
    _active_ts = new_ts

    main = sys.modules["__main__"]
    main.tc = new_tc
    main.ts = new_ts
    main.TEMPERATURE_CONTROLLER = label

    print(
        f"Active temperature controller: {label}  "
        f"(tc={device_name}.{setpoint_path}, "
        f"ts={device_name}.{readback_path})"
    )
