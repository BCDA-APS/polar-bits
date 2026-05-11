"""
Setup and initialize the Bluesky RunEngine.
===========================================

Local copy of ``apsbits.core.run_engine_init.init_RE`` that fixes the
broken ``handler_name`` selector. Upstream apsbits 2.0.1 hard-codes
``handler_name = StoredDict`` (the class object) and then compares it to
the string ``"PersistentDict"`` / ``"StoredDict"`` — both branches are
always False, so ``RE.md`` is never wired up to the on-disk
PersistentDict and `scan_id` (etc.) never restore on startup.

Drop this shim once apsbits ships a release that picks the handler from
the path layout instead of pinning it to a class.

.. autosummary::
    ~init_RE
"""

import collections
import logging
from pathlib import Path
from typing import Any
from typing import Optional

import bluesky
import databroker._drivers.mongo_normalized
import databroker._drivers.msgpack
import tiled
from apsbits.utils.controls_setup import connect_scan_id_pv
from apsbits.utils.controls_setup import set_control_layer
from apsbits.utils.controls_setup import set_timeouts
from apsbits.utils.metadata import get_md_path
from apsbits.utils.metadata import re_metadata
from apsbits.utils.stored_dict import StoredDict
from bluesky.utils import ProgressBarManager
from bluesky_tiled_plugins import TiledWriter

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


def init_RE(
    iconfig: collections.abc.Mapping[str, Any],
    subscribers: Optional[list[Any]] = None,
    **kwargs: Any,
) -> tuple[bluesky.RunEngine, bluesky.SupplementalData]:
    """Initialize and configure a Bluesky RunEngine instance.

    Mirrors :func:`apsbits.core.run_engine_init.init_RE`. The only
    behavioural difference is :data:`handler_name`, which here selects
    ``"StoredDict"`` for a file ``MD_PATH`` and ``"PersistentDict"``
    otherwise — the upstream version hard-codes the class and never
    actually restores from disk.
    """
    re_config = iconfig.get("RUN_ENGINE", {})

    # Steps that must occur before any EpicsSignalBase (or subclass) is created.
    control_layer = iconfig.get("OPHYD", {}).get("CONTROL_LAYER", "PyEpics")
    set_control_layer(control_layer=control_layer)
    set_timeouts(timeouts=iconfig.get("OPHYD", {}).get("TIMEOUTS", {}))

    RE = bluesky.RunEngine(**kwargs)
    """The Bluesky RunEngine object."""

    sd = bluesky.SupplementalData()
    """Supplemental data providing baselines and monitors for the RunEngine."""
    RE.preprocessors.append(sd)

    MD_PATH = get_md_path(iconfig)
    # Save/restore RE.md dictionary in the specified order.
    if MD_PATH is not None:
        # The upstream apsbits bug: this line was `handler_name = StoredDict`
        # (the class), which never compares equal to the string literals
        # below — so `RE.md` was never wired to the on-disk PersistentDict.
        handler_name = (
            "StoredDict" if Path(MD_PATH).is_file() else "PersistentDict"
        )
        logger.debug(
            "Selected %r to store 'RE.md' dictionary in %s.",
            handler_name,
            MD_PATH,
        )
        try:
            if handler_name == "PersistentDict":
                RE.md = bluesky.utils.PersistentDict(MD_PATH)
            elif handler_name == "StoredDict":
                RE.md = StoredDict(MD_PATH)
        except Exception as error:
            print(
                "\n"
                f"Could not create {handler_name} for RE metadata. Continuing "
                f"without saving metadata to disk. {error=}\n"
            )

    RE.md.update(re_config.get("DEFAULT_METADATA", {}))
    RE.md.update(re_metadata(iconfig))  # programmatic metadata

    if subscribers:
        for instance in subscribers:
            if instance is None:
                continue

            # Check if it's a tiled client
            if isinstance(instance, tiled.client.container.Container):
                try:
                    tiled_writer = TiledWriter(instance, batch_size=1)
                    RE.subscribe(tiled_writer)
                except Exception:
                    logger.exception(
                        "Failed to subscribe TiledWriter for tiled client %r "
                        "(type=%s)",
                        instance,
                        type(instance).__name__,
                    )
                    raise

            # Check if it's a databroker catalog
            elif isinstance(
                instance,
                (
                    databroker._drivers.msgpack.BlueskyMsgpackCatalog,
                    databroker._drivers.mongo_normalized.BlueskyMongoCatalog,
                ),
            ):
                try:
                    RE.subscribe(instance.v1.insert)
                except Exception:
                    logger.exception(
                        "Failed to subscribe databroker catalog insert for %r "
                        "(type=%s)",
                        instance,
                        type(instance).__name__,
                    )
                    raise

            # Default: subscribe directly (handles BEC and other callbacks)
            else:
                try:
                    RE.subscribe(instance)
                except Exception:
                    logger.exception(
                        "Failed to subscribe callback %r (type=%s)",
                        instance,
                        type(instance).__name__,
                    )
                    raise

    scan_id_pv = iconfig.get("RUN_ENGINE", {}).get("SCAN_ID_PV")
    connect_scan_id_pv(RE, pv=scan_id_pv)

    if re_config.get("USE_PROGRESS_BAR", True):
        # Add a progress bar.
        pbar_manager = ProgressBarManager()
        RE.waiting_hook = pbar_manager

    return RE, sd
