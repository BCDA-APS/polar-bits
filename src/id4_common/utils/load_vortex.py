"""Utilities for loading and connecting Vortex detector devices."""

import sys
from logging import getLogger

from apsbits.core.instrument_init import oregistry

from ..devices.vortex_dante_me1 import VortexDante1
from ..devices.vortex_dante_me4 import VortexDante4
from ..devices.vortex_xmap import VortexXMAP
from ..devices.vortex_xspress3_me4 import VortexXspress34
from ..devices.vortex_xspress3_me7 import VortexXspress37
from .run_engine import sd

logger = getLogger(__name__)

# TODO: Get this from a YAML file?
DETECTORS = {
    "dante1": (VortexDante1, "dp_dante1_xrd12:"),
    "dante4": (VortexDante4, "dp_dante8_xrd4:"),
    "xmap": (VortexXMAP, "dpxXMAPDP2:"),
    "xspress4": (VortexXspress34, "S4QX4:"),
    "xspress7": (VortexXspress37, "s4XSP3ME7:"),
}


def load_vortex(
    electronic: str,
    pv: str = None,
    name: str = "vortex",
    labels: list = None,
    baseline: bool = False,
    **kwargs,
):
    """
    Load Vortex detector. kwargs are passed to the detector class.

    If a device named ``name`` already exists in the registry it is removed
    first. A warning is issued, and the warning is more prominent when the
    existing device is a different electronics type than the one being loaded.

    The device is added to the ``__main__`` namespace under ``name`` so it is
    available in the interactive session without capturing the return value.

    PARAMETERS
    ----------
        electronic : string
            Name of the electronic. Must be one of the keys in DETECTORS:
            "dante1", "dante4", "xmap", "xspress4", "xspress7".
        pv : string, optional
            PV prefix of detector. If None it will use the default.
        name : str, optional
            Bluesky name of the detector. Defaults to 'vortex'.
        labels : list of strings, optional
            Bluesky labels. Defaults to ["detector"].
        baseline : bool, optional
            Flag to add the device to the baseline. Defaults to False.
    RETURNS
    -------
        vortex_detector : Ophyd device
    """

    if labels is None:
        labels = ["detector"]

    if electronic not in DETECTORS.keys():
        raise ValueError(
            f"Available electronics are {list(DETECTORS.keys())}, "
            f"but {electronic!r} was entered."
        )

    vortexclass, _pv = DETECTORS[electronic]
    pv = _pv if pv is None else pv

    # Replace any existing device registered under the same name.
    existing = oregistry.find(name, allow_none=True)
    if existing is not None:
        if not isinstance(existing, vortexclass):
            logger.warning(
                "Replacing %r (%s) with a different electronics type (%s).",
                name,
                existing.__class__.__name__,
                vortexclass.__name__,
            )
        else:
            logger.warning("Reloading %r (%s).", name, vortexclass.__name__)
        oregistry.pop(existing)
        if existing in sd.baseline:
            sd.baseline.remove(existing)

    device = vortexclass(pv, name=name, labels=labels, **kwargs)

    try:
        logger.info("Connecting to %s...", device.name)
        device.wait_for_connection()
        if baseline:
            sd.baseline.append(device)
        if hasattr(device, "default_settings"):
            device.default_settings()
        oregistry.register(device)
        logger.info("Adding %r to the main namespace.", name)
        setattr(sys.modules["__main__"], name, device)
        if "dante" in electronic.lower():
            message = (
                "\n To prime, hdf, Acq.Mode needs to be in MCA mapping mode."
            )
            message += "\n with IOC with dpuser, vortex._local_folder = /local/home/dpuser/sector4/"
            message += "\n with IOC with polar, vortex._local_folder = /net/s4data/export/sector4/4idd/bluesky_images/vortex"
        logger.warning(message)
    except TimeoutError:
        message = f"Device {device.name} is disconnected."
        if baseline:
            message += " This device was not added to the baseline."

    return device
