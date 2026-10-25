"""Motor position display utilities (wm, wax, wa_scan, wa_new).

The live-EPICS helpers here walk every ``"motor"``-labelled entry in
``oregistry``, which at any station includes the *other* stations' motors:
``make_devices(..., connect=False)`` instantiates all of ``devices.yml`` and
only ``core`` plus the local station label is connected afterwards.  A motor
whose IOC is alive connects on demand in milliseconds, but one whose IOC is
down costs the full ``PV_CONNECTION`` timeout from ``iconfig.yml`` (60 s), and
serially over tens of devices that reads as a hang.

So every read goes through :func:`_motor_row`, which

1. skips the connection wait entirely for signals already connected,
2. probes the rest with a short ``PROBE_TIMEOUT`` instead of the session
   default, and
3. shares one ``PROBE_BUDGET`` across the whole call, after which the
   remaining unconnected devices are reported without any further I/O.

Consequence worth knowing: when many IOCs are down, *which* unconnected motors
get probed depends on registry iteration order.  Name filtering happens before
any read, so ``wax("ancillary")`` always probes its own small candidate set,
and ``wax("ancillary", timeout=5)`` probes it patiently.
"""

import time
import warnings

from apsbits.core.instrument_init import oregistry
from polartools.load_data import load_catalog
from pyRestTable import Table

cat = load_catalog("4id_polar")

#: Seconds allowed per signal that is not already connected.
PROBE_TIMEOUT = 0.2

#: Seconds of on-demand connecting allowed across one call, in total.
PROBE_BUDGET = 2.0

#: The EpicsMotor fields these helpers read.
MOTOR_FIELDS = ("user_readback", "low_limit_travel", "high_limit_travel")


def _is_motor(device):
    """Tell whether *device* exposes every field in :data:`MOTOR_FIELDS`.

    Some ``"motor"``-labelled entries are not motor records -- the 4IDH table
    pseudo-axes are ``PVPositionerSoftDoneWithStop`` with ``readback`` rather
    than ``user_readback``.  They are reported separately from motors that
    merely failed to read.
    """
    return all(hasattr(device, field) for field in MOTOR_FIELDS)


def _read_signal(signal, timeout, deadline):
    """Read one signal, bounding the connection wait when *timeout* is set.

    ``timeout=None`` means "use the session defaults from ``iconfig.yml``",
    which is what :func:`wm` wants.  Otherwise an already-connected signal is
    read straight from its monitor cache, and an unconnected one is probed
    only while *deadline* (``time.monotonic()``) has not passed.
    """
    if timeout is None:
        return signal.get()

    try:
        connected = bool(signal.connected)
    except Exception:
        # Lazy and area-detector components can raise on the property.
        connected = False

    if not connected:
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(
                f"{signal.name}: probe budget spent before connecting"
            )

    return signal.get(connection_timeout=timeout, timeout=timeout)


def _motor_row(device, timeout=PROBE_TIMEOUT, deadline=None, raise_error=False):
    """Return ``(name, position, limits)`` for *device*, or None if unreadable.

    Reads short-circuit on the first failure, so a motor whose IOC is down
    costs one timeout rather than three.  With *raise_error* the underlying
    exception propagates instead -- :func:`wm` names its devices explicitly
    and a ``ConnectionTimeoutError`` naming the PV is more use there than a
    dropped row.
    """
    try:
        values = []
        for field in MOTOR_FIELDS:
            signal = getattr(device, field)
            values.append(_read_signal(signal, timeout, deadline))
        pos, llm, hlm = values
        return (device.name, f"{pos:.5f}", f"[{llm:.5f},{hlm:.5f}]")
    except Exception:
        if raise_error:
            raise
        return None


def _motor_rows(devices, motor=None, timeout=PROBE_TIMEOUT):
    """Read *devices*, returning ``(rows, missed, skipped)``.

    *motor* filters on the device name **before** anything is read.
    """
    rows = []
    missed = []
    skipped = []
    deadline = None if timeout is None else time.monotonic() + PROBE_BUDGET

    for device in devices:
        name = getattr(device, "name", str(device))
        if motor and motor not in name:
            continue
        if not _is_motor(device):
            skipped.append(name)
            continue
        row = _motor_row(device, timeout=timeout, deadline=deadline)
        if row is None:
            missed.append(name)
        else:
            rows.append(row)

    return rows, missed, skipped


def _report_missed(
    missed,
    skipped=(),
    display_missed=False,
    reason="IOC down or not connected",
):
    """Say how many devices could not be read, and name them on request.

    The count prints unconditionally: a silent omission is what made a
    multi-minute ``wax()`` look like a hang rather than like dozens of
    timeouts.
    """
    if missed:
        noun = "motor" if len(missed) == 1 else "motors"
        print("")
        print(f"{len(missed)} {noun} could not be read ({reason}).")
        if display_missed:
            print(f"{sorted(missed)}")
        else:
            print("Use display_missed=True to list them.")

    if skipped and display_missed:
        noun = "entry" if len(skipped) == 1 else "entries"
        print("")
        print(
            f"{len(skipped)} registry {noun} labelled 'motor' are not "
            "motor records (no user_readback):"
        )
        print(f"{sorted(skipped)}")


def wm(*args):
    """
    Print a table of current position and travel limits for the given motors.
    """
    result = Table()
    result.labels = ("Motor", "Position", "Limits")
    for arg in args:
        # timeout=None keeps the session defaults, raise_error=True keeps the
        # ConnectionTimeoutError: these devices were named explicitly.
        result.rows.append(_motor_row(arg, timeout=None, raise_error=True))
    print("")
    print(result.reST(fmt="markdown"))


def wax(
    scan=None,
    motor=None,
    device="motor",
    display_missed=False,
    timeout=PROBE_TIMEOUT,
):
    """
    Display current and past motor values

    PARAMETERS
    ----------
        scan : int or str, optional
            Scan number of any scan.  A string is treated as a motor name
            filter on the current positions instead.
        motor : str, optional
            If None all motor positions will be displayed.
        device : str, optional
            Default is "motor", used to find devices in the registry.
            Other possibilities include "detector", "sensor", "actuator", etc.
        display_missed : bool, optional
            List the devices that could not be read, rather than only
            counting them.
        timeout : float, optional
            Seconds allowed per signal that is not already connected
            (default: :data:`PROBE_TIMEOUT`).  The call as a whole spends at
            most :data:`PROBE_BUDGET` seconds connecting on demand, so a
            station whose IOCs are down costs a couple of seconds, not a
            minute per motor.  ``None`` restores the session defaults from
            ``iconfig.yml`` and can block for a very long time.

    EXAMPLES
    ----------
        wax(): current position of all motors
        wax('motor'): current position of motors containing 'motor'
        wax(42, 'motor'): position of motors containing 'motor' in scan 42
        wax(42): position of all motors in scan 42

    """
    result = Table()
    # allow_none: Raman has no "motor"-labelled device at all, and findall
    # raises ComponentNotFound rather than returning an empty list.
    devices = oregistry.findall(device, allow_none=True) or []
    missed = []
    warnings.simplefilter(action="ignore", category=FutureWarning)
    if isinstance(scan, int):
        result.labels = ("Device name", "Position")
        for arg in devices:
            try:
                name = arg.name
                if motor:
                    pos = cat[scan].baseline.read()[name]

                    if motor in pos.name:
                        result.rows.append((name, f"{pos.values[0]}"))
                else:
                    pos = cat[scan].baseline.read()[name]
                    result.rows.append((name, f"{pos.values[0]}"))
            except Exception:
                missed.append(arg.name)
        print("")
        print(f"Values from scan #{scan}")
        print("")
        print(result.reST(fmt="markdown"))
        _report_missed(
            missed,
            display_missed=display_missed,
            reason="not in that scan's baseline",
        )
    else:
        # A string in the scan slot is a name filter, not a scan number.
        if isinstance(scan, str):
            motor = scan
        result.labels = ("Device name", "Position", "Limits")
        result.rows, missed, skipped = _motor_rows(
            devices, motor=motor, timeout=timeout
        )
        print("")
        print(result.reST(fmt="markdown"))
        _report_missed(missed, skipped, display_missed=display_missed)


def wa_scan(scan=None, motor=None):
    """Print motor positions recorded in the baseline stream of a past scan."""
    result = Table()
    result.labels = ("Motor", "Position")
    devices = oregistry.findall("motor", allow_none=True) or []
    missed = []
    if scan:
        for arg in devices:
            try:
                name = arg.name
                if motor:
                    pos = cat[scan].baseline.read()[name]

                    if motor in pos.name:
                        result.rows.append((name, f"{pos.values[0]}"))
                else:
                    pos = cat[scan].baseline.read()[name]
                    result.rows.append((name, f"{pos.values[0]}"))
            except Exception:
                missed.append(arg.name)
        print("")
        print(f"Motor positions from scan #{scan}")
        print("")
        print(result.reST(fmt="markdown"))
        print(f"{len(missed)} motors missed:")
        print(f"Motors missed {missed}")
    else:
        raise TypeError(
            "Wrong parameters. Expected: "
            "wapast(scan, part_of_motor_name), e.g. wa_past(1560,'huber_hp')"
        )


def wa_new(motor=None, display_missed=False, timeout=PROBE_TIMEOUT):
    """
    Print current position and limits for all motors, optionally filtered by
    name.
    """
    if not isinstance(motor, (str, type(None))):
        raise TypeError(
            "wa_new() filters on a motor name; for a past scan use "
            f"wax({motor!r})."
        )
    wax(motor=motor, display_missed=display_missed, timeout=timeout)
