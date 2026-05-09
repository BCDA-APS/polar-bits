"""Short convenience wrappers for common session operations."""

from datetime import datetime

from apsbits.core.instrument_init import oregistry
from polartools.load_data import load_catalog

from id4_common.plans.center_maximum import cen
from id4_common.plans.center_maximum import maxi


def opt(method="cen"):
    """
    Move positioner of last scan to center of last scan

    usage: RE(opt())
        optional argument: 	method = 'cen' (default)
                                                method = 'max'


    """
    cat = load_catalog("4id_polar")
    motor = cat[-1].metadata["start"]
    rmotor = ".".join(motor["motors"][0].rsplit("_", 1))
    positioner = oregistry.find(motor["motors"][0])
    time = datetime.now() - datetime.fromtimestamp(motor["time"])

    if time.seconds < 60:
        if method == "cen":
            yield from cen(positioner)
        elif method == "max":
            yield from maxi(positioner)

    else:
        inp = input(f"Move {rmotor} to center (Y/[N])? ")
        if inp in ["Y", "y", "yes"]:
            if method == "cen":
                yield from cen(positioner)
            elif method == "max":
                yield from maxi(positioner)


def crl_setup(hutch=None):
    """
    Switch the CRL sample-position offset to the active hutch.

    Delegates to :meth:`CRLClass.select_g` / ``select_h``, which
    write to the IOC's ``ZOffsetToggle`` PV.  The per-hutch offset values
    themselves live on the device as ``crl.offset_g`` / ``offset_h`` and
    are not changed here.

    Parameters
    ----------
    hutch : {'g', 'h'}, optional
        Hutch to switch to.  Case-insensitive, accepts ``"G"`` / ``"H"``
        and the longer aliases ``"diffractometer"`` (= G) /
        ``"magnet"`` (= H) for backwards compatibility.  When ``None``
        (default), prompt interactively.
    """
    if hutch is None:
        hutch = input("Hutch (G / H) [G]: ").strip().lower() or "g"
    else:
        hutch = str(hutch).strip().lower()

    crl_dev = oregistry.find("crl")

    if hutch in ("g", "diffractometer") or hutch.startswith("d"):
        crl_dev.select_g()
        label = "G (diffractometer)"
    elif (
        hutch in ("h", "magnet")
        or hutch.startswith("m")
        or hutch.startswith("9")
    ):
        crl_dev.select_h()
        label = "H (magnet)"
    else:
        print(f"Unknown hutch '{hutch}'.  Choose 'G' or 'H'.")
        return

    print(f"CRL sample-position offset set for {label}.")


def crl_size(focal_size):
    """
    Set the CRL focal size.

    Renamed from ``crl`` so the function does not shadow the ``crl``
    device that ``load_device("crl")`` injects into the session
    namespace.

    Parameters
    ----------
    focal_size : float
        Target focal size in microns. If < 5 µm, the device's
        ``minimize_button`` is triggered instead of writing a setpoint.
        Otherwise the value is converted to meters and written to
        ``crl.focal_size_setpoint``.
    """
    focal_size = float(focal_size)
    crl_dev = oregistry.find("crl")
    if focal_size < 5:
        crl_dev.minimize_button.put(1)
    else:
        crl_dev.focal_size_setpoint.put(focal_size * 1e-6)


def te(temperature):
    """
    Set the active temperature controller's setpoint.

    Thin shortcut over the ``tc`` signal installed by
    :func:`id4_common.utils.temperature_setup.temperature_setup`.  Writes
    the setpoint and returns immediately; the controller continues ramping
    toward the target on its own.

    Parameters
    ----------
    temperature : float
        Target temperature setpoint.

    Raises
    ------
    RuntimeError
        ``temperature_setup()`` has not been run, so there is no active
        controller to talk to.
    """
    from .temperature_setup import get_active_label
    from .temperature_setup import get_active_tc

    tc = get_active_tc()
    if tc is None:
        raise RuntimeError(
            "No active temperature controller.  Run "
            "`temperature_setup('<label>')` first (see "
            "id4_common.utils.temperature_setup.TEMPERATURE_CONTROLLERS "
            "for the available labels)."
        )
    tc.put(float(temperature))
    print(f"{get_active_label()}: setpoint -> {float(temperature)}")
