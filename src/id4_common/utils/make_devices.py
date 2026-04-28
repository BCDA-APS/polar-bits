"""Local overrides of ``apsbits`` ``make_devices`` and
``guarneri_namespace_loader`` that add a ``connect`` flag.

When ``connect=False``, devices are instantiated and registered in
``__main__`` / the ``oregistry`` but no EPICS connections are attempted.
This restores the documented "deferred connection" pattern so that explicit
``connect_device(...)`` calls own all EPICS I/O — avoiding the
``DEFAULT_TIMEOUT`` wait and ``NotConnectedError`` log spam for devices
whose IOCs are intentionally off.

These are line-for-line copies of the upstream functions in
``apsbits.core.instrument_init`` with the single addition of the
``connect`` parameter. Drop these helpers once apsbits exposes the same
flag upstream.
"""

import asyncio
import pathlib
import sys
import time
from logging import getLogger

import guarneri
from apsbits.utils.config_loaders import get_config
from ophyd_async.core import NotConnected

logger = getLogger(__name__)
logger.bsdev(__file__)

MAIN_NAMESPACE = "__main__"


def make_devices(
    *,
    pause: float = 1,
    clear: bool = True,
    file: str,
    path: str | pathlib.Path | None = None,
    device_manager=None,
    connect: bool = True,
):
    """
    Initialize ophyd-style devices using a device manager, optionally
    connect them, then make them part of the main namespace.

    Local override of ``apsbits.core.instrument_init.make_devices`` that
    adds the ``connect`` flag.

    PARAMETERS

    pause : float
        Wait 'pause' seconds (default: 1) for slow objects to connect.
    clear : bool
        Clear 'oregistry' first if True (the default).
    file : str | pathlib.Path | None
        Path to a YAML/TOML file containing device configurations.
    path : str | pathlib.Path | None
        Optional alternative configs directory.
    device_manager :
        The device manager to use. Currently only 'guarneri' is supported.
    connect : bool
        If True (default), eagerly try to connect every device after
        loading. If False, skip the connect step entirely — devices are
        instantiated and registered, but no EPICS I/O is performed. Use
        this when later ``connect_device(...)`` calls handle connections.
    """
    logger.debug("(Re)Loading local control objects.")
    if file is None:
        logger.error("No custom device file provided.")
        return

    if path is None:
        iconfig = get_config()
        instrument_path_config = iconfig.get("INSTRUMENT_PATH")
        instrument_path = pathlib.Path(instrument_path_config).parent
        configs_path = instrument_path / "configs"
        logger.info(
            f"No custom path provided.\n\n"
            f"Using default configs path: {configs_path}"
        )

    else:
        logger.info(f"Using custom path for device files: {path}")
        configs_path = pathlib.Path(path)

    if clear and isinstance(device_manager, guarneri.Instrument):
        main_namespace = sys.modules[MAIN_NAMESPACE]

        # Clear the oregistry and remove any devices registered previously.
        for dev_name in device_manager.devices.device_names:
            # Remove from __main__ namespace any devices registered previously.
            if hasattr(main_namespace, dev_name):
                logger.info("Removing %r from %r", dev_name, MAIN_NAMESPACE)

                delattr(main_namespace, dev_name)

        device_manager.devices.clear()

    logger.debug("Loading device files: %r", file)

    # Load each device file
    device_path = configs_path / file
    if not device_path.exists():
        logger.error("Device file not found: %s", device_path)

    else:
        logger.info("Loading device file: %s", device_path)
        if isinstance(device_manager, guarneri.Instrument):
            try:
                asyncio.run(
                    guarneri_namespace_loader(
                        yaml_device_file=device_path,
                        instrument=device_manager,
                        oregistry=device_manager.devices,
                        main=True,
                        connect=connect,
                    )
                )
            except Exception as e:
                logger.error(
                    "Error loading device file %s: %s", device_path, str(e)
                )
                logger.error("Full exception:", exc_info=True)
        elif device_manager == "happi":
            pass
        elif device_manager is None:
            logger.error("No device_manager provided.")
            return
    if pause > 0:
        logger.debug(
            "Waiting %s seconds for slow objects to connect.",
            pause,
        )
        time.sleep(pause)


async def guarneri_namespace_loader(
    yaml_device_file,
    instrument=None,
    oregistry=None,
    main=True,
    connect: bool = True,
):
    """
    Load our ophyd-style controls as described in a YAML file into the
    main namespace.

    Local override of
    ``apsbits.core.instrument_init.guarneri_namespace_loader`` that adds
    the ``connect`` flag. When ``connect=False`` the eager
    ``await instrument.connect()`` call is skipped.

    PARAMETERS

    yaml_device_file : str or pathlib.Path
        YAML file describing ophyd-style controls to be created.
    main : bool
        If ``True`` add these devices to the ``__main__`` namespace.
    connect : bool
        If True (default), eagerly try to connect every device. If False,
        only load and register them.

    """
    logger.debug("Devices file %r.", str(yaml_device_file))
    t0 = time.time()

    current_devices = oregistry.device_names
    instrument.load(yaml_device_file)

    if connect:
        try:
            await instrument.connect()
        except NotConnected as exc:
            logger.exception(exc)

    logger.info("Devices loaded in %.3f s.", time.time() - t0)
    if main:
        main_namespace = sys.modules[MAIN_NAMESPACE]
        for label in sorted(oregistry.device_names):
            if label in current_devices:
                continue
            logger.info("Adding ophyd device %r to main namespace", label)
            setattr(main_namespace, label, oregistry[label])
