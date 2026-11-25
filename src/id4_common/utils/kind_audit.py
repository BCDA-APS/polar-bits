"""
Find signals that a device's ``kind`` settings silently drop from the data
(issues #72, #100).

In ophyd, ``kind`` on a sub-Device filters what it passes up to its parent:

- ``read()`` only recurses into children with the ``normal`` bit.
- ``read_configuration()`` only recurses into children with the ``config``
  bit, and only picks up leaf signals that are themselves ``config``.

So a ``normal``/``hinted`` signal inside a ``config`` sub-Device (e.g. a
positioner readback) is in neither. These helpers list such signals by
walking the kinds the same way ``Device.read()`` and
``Device.read_configuration()`` do, so they need no EPICS connection and
work on disconnected or fake devices.

Typical use in the interactive session::

    audit_kinds("magnet911", "mono_feedback")
"""

from ophyd import Device
from ophyd import Kind

__all__ = [
    "audit_kinds",
    "find_unrecorded_signals",
]


def _reached_signals(device, kind):
    """
    Yield the leaf signals reached by recursing through children of ``kind``.

    With ``Kind.normal`` this mirrors ``Device.read()``, with ``Kind.config``
    ``Device.read_configuration()``, and with both every non-omitted path.
    """
    for attr in device.component_names:
        child = getattr(device, attr)
        if child is None:
            continue
        if not child.kind & kind:
            continue
        if isinstance(child, Device):
            yield from _reached_signals(child, kind)
        else:
            yield child


def find_unrecorded_signals(device):
    """
    Return names of non-omitted signals missing from read and configuration.

    A signal is reported when it and all its parents are not ``omitted``,
    but neither ``device.read()`` nor ``device.read_configuration()``
    reaches it, i.e. a ``config`` parent is hiding a ``normal`` signal.
    Everything below an ``omitted`` parent counts as deliberately dropped.

    Parameters
    ----------
    device : ophyd.Device
        Top-level device to audit.

    Returns
    -------
    list of str
        Signal names (as used in the data), sorted.
    """
    recorded = {
        id(sig)
        for kind in (Kind.normal, Kind.config)
        for sig in _reached_signals(device, kind)
    }
    return sorted(
        sig.name
        for sig in _reached_signals(device, Kind.normal | Kind.config)
        if id(sig) not in recorded
    )


def audit_kinds(*devices):
    """
    Print the signals each device's kinds drop from the data.

    Parameters
    ----------
    *devices : ophyd.Device or str
        Devices, or names to look up in ``oregistry``.

    Returns
    -------
    dict
        ``{device_name: [lost signal names]}`` for devices with losses.
    """
    from apsbits.core.instrument_init import oregistry

    result = {}
    for dev in devices:
        if isinstance(dev, str):
            dev = oregistry.find(dev)
        lost = find_unrecorded_signals(dev)
        if lost:
            result[dev.name] = lost
            print(f"{dev.name}: {len(lost)} signal(s) not recorded")
            for name in lost:
                print(f"    {name}")
        else:
            print(f"{dev.name}: OK")
    return result
