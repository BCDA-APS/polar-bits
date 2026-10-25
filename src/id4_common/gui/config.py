"""Everything the GUI and MCP layer knows about *this* beamline.

The rest of the package is written against the names in here, so porting to
another station is editing this file rather than grepping for motor names.
At 6-ID-B these values were scattered as module constants across
``hkl_bridge``, ``tabs/hkl``, ``mcp_server/bridge`` and ``mcp_server/session``;
collecting them is what makes the layer shareable between id4_b, id4_g, id4_h
and id4_raman.

What differs *between* those stations lives in :data:`STATIONS`, one
:class:`StationProfile` each, resolved at call time by :func:`profile`.  What
is the same everywhere -- the POLAR geometry's axis names, the peak plans --
stays a flat constant below.

Nothing here imports ophyd, Qt or bluesky — the GUI process, the MCP client
process and the kernel all read it.
"""

import logging
import os
from dataclasses import dataclass
from dataclasses import field
from types import MappingProxyType
from typing import Mapping

logger = logging.getLogger(__name__)

# --- identity --------------------------------------------------------------

#: Instrument package whose ``startup`` the kernel runs.
INSTRUMENT_PACKAGE = "id4_common"

#: Beamline package actually imported.  Overridden per station by the
#: ``ID4_STATION`` environment variable, since one checkout serves four.
DEFAULT_STATION = "id4_g"

#: Shown in the window title.  ``{station}`` is filled in at runtime with the
#: profile's display name, so the bar reads "POLAR 4IDB", not "POLAR id4_b".
WINDOW_TITLE = "POLAR {station} — Bluesky session"

#: Qt settings scope.  Read through :func:`qsettings_app`, which scopes the
#: application half per station -- these are the org half and the base name.
QSETTINGS_ORG = "APS"
QSETTINGS_APP = "polar-gui"


def station() -> str:
    """Return the station package name for this session."""
    return os.environ.get("ID4_STATION", DEFAULT_STATION)


def qsettings_app() -> str:
    """Return the Qt settings application scope for this station.

    Scoped per station because the settings are not all cosmetic: alongside
    the font size and console background sit the transcript's log path and
    its auto-enable flag, which ``app.MainWindow`` reads at start-up.  Shared,
    a 4IDB session would open the GUI and start appending its console traffic
    to whatever file the 4IDG session last wrote.

    ``id4_g`` keeps the unscoped name it has been writing since before this
    was scoped, so the station that already has a GUI does not lose its font,
    log path and macro folder the first time it starts a station-aware build.
    """
    name = station()
    if name == "id4_g":
        return QSETTINGS_APP
    return f"{QSETTINGS_APP}-{name}"


def pointer_filename(station_name: str | None = None) -> str:
    """Name of the kernel pointer file the MCP server discovers.

    Station-scoped on purpose.  6-ID-B could use a fixed
    ``.id6b-gui-kernel.json`` because there is one session; four POLAR
    stations on one filesystem would collide, and cross-attaching an MCP
    client to the wrong beamline's kernel is the one failure this must not
    have.
    """
    return f".polar-gui-kernel-{station_name or station()}.json"


# --- the station profile ---------------------------------------------------


@dataclass(frozen=True)
class StationProfile:
    """What the GUI and MCP layer may offer at one station.

    **Declared, not discovered.**  Every station's ``startup`` calls
    ``make_devices(file="devices.yml")`` with no ``path``, and apsbits
    resolves that against ``INSTRUMENT_PATH`` -- always
    ``id4_common/configs``.  So every station instantiates the same devices
    and the station label only decides which ones get ``connect_device()``
    called: ``oregistry.find("huber_euler")`` succeeds at 4IDB and hands back
    a disconnected object.  The one honest runtime signal is
    ``get_diffractometer()``, and that needs a live kernel -- far too late for
    a window that must draw its tabs before the session exists.

    It is not in YAML either.  ``apsbits.update_config`` is a top-level
    ``dict.update``, so a station overriding one nested key drops the rest of
    that block; the four ``iconfig_extras.yml`` already lose
    ``RUN_ENGINE.DEFAULT_METADATA.proposal_id`` that way.

    Only fields with a consumer belong here.  A declaration this layer never
    reads goes stale unnoticed -- see the note at the foot of this file.
    """

    #: Station package name, matching the key in :data:`STATIONS`.
    package: str

    #: Hutch name as people say it.  Used in the window title and in the
    #: reason a disabled tab gives for being disabled.
    display: str

    #: Diffractometers the HKL tab offers, in the order shown.  Empty at a
    #: station that never calls ``set_diffractometer()``.
    #:
    #: The POLAR geometry is ``APS POLAR`` under ``hkl_soleil`` with six real
    #: axes -- ``tau mu chi phi gamma delta`` -- and there are *two* machines
    #: on the same solver, the Euler cradle and the high-pressure press.
    #: 6-ID-B had one machine (``psic``) plus its simulator; here the pairing
    #: is by role, not by real-versus-simulated.
    diffractometers: tuple[str, ...] = ()

    #: ``device -> psi-engine partner``.  hklpy2 keeps psi in a separate
    #: engine on the same motors, and the HKL tab reads the live psi off it.
    #:
    #: A factory rather than a literal default because ``dataclasses`` refuses
    #: an unhashable one, and ``MappingProxyType`` is unhashable.  The
    #: populated entries below still use a proxy: the default is the only
    #: thing checked, and a shared mutable default is what the rule is for.
    psi_geometry: Mapping[str, str] = field(default_factory=dict)

    #: Devices that drive real motors.  Everything in
    #: :attr:`diffractometers` listed here gets the red "REAL MOTORS WILL
    #: MOVE" banner and the extra line in the Move confirmation.
    #:
    #: At POLAR **both** machines are real -- there is no simulator in
    #: ``devices.yml`` -- so this is the whole list.  Add a simulated twin by
    #: leaving it *out*.
    real_motor_devices: frozenset[str] = frozenset()

    #: Device an MCP tool call defaults to when it does not name one.
    #:
    #: 6-ID-B defaulted to the *simulator*, so reaching the real machine was
    #: always an explicit act.  POLAR has no simulator, so that protection is
    #: not available and the default is a real machine -- which is precisely
    #: why the approval gate is the load-bearing control here, not the
    #: default.
    mcp_default_device: str | None = None

    #: Station has the softglue and piezo hardware the flyscan viewer reads.
    #: Both ``gsgz_isn`` and ``piezo_jena`` are labelled ``4idg`` only.
    has_flyscan: bool = False

    #: Why the GUI refuses to launch here at all, or None.  Set for a station
    #: whose ``startup`` cannot be imported, and for a name that is not a
    #: station; ``app.main`` prints it and exits rather than starting a window
    #: whose kernel then dies on the bootstrap.
    unsupported_reason: str | None = None

    @property
    def has_diffractometer(self) -> bool:
        """Whether an hkl-aware session runs at this station."""
        return bool(self.diffractometers)

    @property
    def mcp_allowed_devices(self) -> frozenset[str]:
        """Devices an MCP client may address.

        Derived rather than declared, so a station cannot allow a device it
        does not offer.  Checked in the *kernel*, so a bug in the server -- or
        a second client that found the connection file -- is still bounded by
        it.  The psi partners stay out: separate engines on the same motors,
        and nothing in the tool set needs them.
        """
        return frozenset(self.diffractometers)


#: Every station this GUI knows, keyed by package name.
#:
#: Adding a station is an entry here.  Adding a *capability* to one is a field
#: on that entry -- not a branch somewhere in ``gui/``.
STATIONS: dict[str, StationProfile] = {
    "id4_b": StationProfile(
        package="id4_b",
        display="4IDB",
    ),
    "id4_g": StationProfile(
        package="id4_g",
        display="4IDG",
        diffractometers=("huber_euler", "huber_hp"),
        psi_geometry=MappingProxyType(
            {
                "huber_euler": "huber_euler_psi",
                "huber_hp": "huber_hp_psi",
            }
        ),
        real_motor_devices=frozenset({"huber_euler", "huber_hp"}),
        mcp_default_device="huber_euler",
        has_flyscan=True,
    ),
    "id4_h": StationProfile(
        package="id4_h",
        display="4IDH",
    ),
    "id4_raman": StationProfile(
        package="id4_raman",
        display="Raman",
        unsupported_reason=(
            "id4_raman cannot start a session: id4_raman/startup.py imports "
            "polartools_hklpy_imports, which was deleted in 329651ef.  Fix "
            "that import before launching the GUI there."
        ),
    ),
}


def profile(station_name: str | None = None) -> StationProfile:
    """Return the capability profile for *station_name*, or this session's.

    Resolved at **call time**, never at import: ``app.main`` does not set
    ``ID4_STATION`` until it has parsed ``--station``, and by then this module
    has long been imported by way of ``gui.kernel``.  Anything that caches a
    profile in a module constant re-freezes the bug this exists to fix.

    An unrecognised name is reported and answered with a capability-free
    profile rather than an exception.  The MCP server reads ``ID4_STATION``
    from an environment it does not control, and a station it cannot place is
    a station it should offer nothing for.
    """
    name = station_name or station()
    known = STATIONS.get(name)
    if known is not None:
        return known

    logger.warning(
        "Unknown station %r; offering no station-specific capabilities. "
        "Known stations: %s",
        name,
        ", ".join(sorted(STATIONS)),
    )
    return StationProfile(
        package=name,
        display=name,
        unsupported_reason=(
            f"{name!r} is not a POLAR station.  Known stations: "
            + ", ".join(sorted(STATIONS))
        ),
    )


#: ``device -> q-engine partner``.
#:
#: **POLAR has none.**  6-ID-B read 2theta off a ``q`` engine (``psic_q``);
#: there is no such device here, so the tab computes 2theta from the angles
#: instead (see ``hkl_bridge._gui_hkl_derived``).  Left as an empty mapping
#: rather than deleted, so a station that adds one only edits this file.  It
#: stays a flat constant rather than a profile field until something reads it:
#: an unread field on the profile is exactly the drift the profile docstring
#: warns about.
Q_GEOMETRY: dict[str, str] = {}


# --- the 3D model ----------------------------------------------------------

#: ``3D model angle -> device real-axis name``.
#:
#: The model in ``diffract3d`` is built from
#: ``jwkim/python/diffract/diffractometer_polar.py`` and names the horizontal
#: detector rotation ``nu``; the hklpy2 APS POLAR geometry calls it ``gamma``.
#: ``tau`` is a real axis with no counterpart in the model -- it moves the
#: whole instrument, not a part of it -- so it is absent here and simply not
#: drawn.
#:
#: Not per station: this describes the POLAR geometry, and the one station
#: that drives it is the only one that draws the model.
MODEL_AXIS_MAP = {
    "mu": "mu",
    "chi": "chi",
    "phi": "phi",
    "nu": "gamma",
    "delta": "delta",
}

#: Real axes the 3D model does not draw.
#:
#: Named rather than left implicit because the panel says so on screen: an
#: axis that moves and changes nothing in the view looks like a view that has
#: stopped updating, and the operator has no way to tell the two apart.
UNMODELLED_AXES = ("tau",)


# --- scan plans ------------------------------------------------------------

#: Peak-finding plans offered by the Macro tab's "Go to peak" component.
PEAK_PLANS = ["cen", "com", "maxi", "mini"]

#: What each of those is called on screen.
#:
#: A plan missing from here is offered under its own name, so adding one to
#: ``PEAK_PLANS`` is enough to make it appear.
PEAK_PLAN_LABELS = {
    "cen": "center of the peak",
    "com": "center of mass",
    "maxi": "maximum",
    "mini": "minimum",
}

#: The keyword the positioner is passed under, or ``None`` to pass it first
#: and positionally.
#:
#: POLAR's signature is ``cen(scan_id=-1, positioner=None, detector=None,
#: confirm=True)``, so the **first positional is the catalog index**: an axis
#: passed there would be read as a scan number rather than as the motor to
#: move -- either a ``TypeError`` deep inside the catalog or, for a bare
#: integer, a lookup of the wrong scan.  Named, it cannot be mistaken.
PEAK_AXIS_KEYWORD = "positioner"

#: Extra keyword every peak plan call carries.
#:
#: ``id4_common.plans.peak_position.cen`` defaults to ``confirm=True``, which
#: calls ``input()``.  **stdin is closed in the GUI kernel**, so the default
#: would hang the plan rather than raise -- the same failure mode as
#: ``counters.plotselect()`` on a bad argument.  Emitting it explicitly is a
#: one-line fix that needs no change in ``id4_common``.
PEAK_PLAN_KWARGS = {"confirm": "False"}

#: Peak plans take ``monitor=``.  POLAR's do not -- theirs normalise inside
#: ``peak_position`` -- so the Macro tab hides that field.
PEAK_PLANS_TAKE_MONITOR = False


# --- detectors -------------------------------------------------------------
#
# There is deliberately no detector-priority list here.  6-ID-B's config
# carried one to mirror ``counters_class.IDEAL_ORDER``, but nothing in the GUI
# reads it -- ``counters`` applies its own order and the Detectors tab groups
# by whatever ``detectors_plot_options`` returns.  A second copy of a list this
# layer never consults is a statement that can go stale unnoticed, and it had:
# it read ``["scaler", "eiger", "vortex"]`` while POLAR's actual order begins
# ``scaler1, scaler2`` and ends with three flag cameras.  Priority belongs in
# ``id4_common/utils/counters_class.py``, once.
