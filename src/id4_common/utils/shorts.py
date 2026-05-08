"""Short convenience wrappers for common session operations."""

from datetime import datetime

from apsbits.core.instrument_init import oregistry
from epics import caput
from polartools.load_data import load_catalog

from id4_common.plans.center_maximum import cen
from id4_common.plans.center_maximum import maxi

_CRL_OFFSET_PV = "4idPyCRL:CRL4ID:1:oePosOffset.DOL"
_CRL_OFFSETS = {"diffractometer": 0.0, "magnet": 6.5}


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


def crl_setup():
    """
    Set the CRL sample-position offset for the active instrument.

    Prompts for the instrument (Diffractometer or Magnet) and writes
    the corresponding offset to ``4idPyCRL:CRL4ID:samplePositionOffset_RBV``:

    - Diffractometer  → 0
    - Magnet    → 6.5
    """
    answer = input(
        "Instrument (Diffractometer / Magnet) [Diffractometer]: "
    ).strip().lower() or "diffractometer"

    if answer.startswith("d"):
        offset = _CRL_OFFSETS["diffractometer"]
        label = "Diffractometer"
    elif answer.startswith("9") or "magnet" in answer or answer.startswith("m"):
        offset = _CRL_OFFSETS["magnet"]
        label = "Magnet"
    else:
        print(
            f"Unknown instrument '{answer}'. "
            "Choose 'Diffractometer' or 'Magnet'."
        )
        return

    caput(_CRL_OFFSET_PV, str(offset))
    print(f"{label}: {_CRL_OFFSET_PV} = {offset}")


def crl(focal_size):
    """
    Set the CRL focus size on the transfocator.

    Parameters
    ----------
    focal_size : float
        Target focal size in microns. If < 5 µm, the transfocator's
        ``minimize_button`` is triggered instead of writing a setpoint.
        Otherwise the value is converted to meters and written to
        ``transfocator.focal_size_setpoint``.
    """
    focal_size = float(focal_size)
    transfocator = oregistry.find("transfocator")
    if focal_size < 5:
        transfocator.minimize_button.put(1)
    else:
        transfocator.focal_size_setpoint.put(focal_size * 1e-6)


def te(temperature):
    """
    Set the temperature setpoint on ``temp_336_4idg`` (loop 1).

    Writes the setpoint and returns immediately; the controller continues
    ramping toward the target on its own.

    Parameters
    ----------
    temperature : float
        Target temperature setpoint.
    """
    controller = oregistry.find("temp_336_4idg")
    controller.loop1.setpoint.put(float(temperature))
