"""Everything the GUI and MCP layer knows about *this* beamline.

The rest of the package is written against the names in here, so porting to
another station is editing this file rather than grepping for motor names.
At 6-ID-B these values were scattered as module constants across
``hkl_bridge``, ``tabs/hkl``, ``mcp_server/bridge`` and ``mcp_server/session``;
collecting them is what makes the layer shareable between id4_b, id4_g, id4_h
and id4_raman.

Nothing here imports ophyd, Qt or bluesky — the GUI process, the MCP client
process and the kernel all read it.
"""

# --- identity --------------------------------------------------------------

#: Instrument package whose ``startup`` the kernel runs.
INSTRUMENT_PACKAGE = "id4_common"

#: Beamline package actually imported.  Overridden per station by the
#: ``ID4_STATION`` environment variable, since one checkout serves four.
DEFAULT_STATION = "id4_g"

#: Shown in the window title.  ``{station}`` is filled in at runtime.
WINDOW_TITLE = "POLAR {station} — Bluesky session"

#: Qt settings scope, so the four stations keep separate font/log preferences.
QSETTINGS_ORG = "APS"
QSETTINGS_APP = "polar-gui"


def station() -> str:
    """Return the station package name for this session."""
    import os

    return os.environ.get("ID4_STATION", DEFAULT_STATION)


def pointer_filename(station_name: str | None = None) -> str:
    """Name of the kernel pointer file the MCP server discovers.

    Station-scoped on purpose.  6-ID-B could use a fixed
    ``.id6b-gui-kernel.json`` because there is one session; four POLAR
    stations on one filesystem would collide, and cross-attaching an MCP
    client to the wrong beamline's kernel is the one failure this must not
    have.
    """
    return f".polar-gui-kernel-{station_name or station()}.json"


# --- diffractometers -------------------------------------------------------

#: Diffractometers the HKL tab offers, in the order shown.
#:
#: The POLAR geometry is ``APS POLAR`` under ``hkl_soleil`` with six real
#: axes -- ``tau mu chi phi gamma delta`` -- and there are *two* machines on
#: the same solver, the Euler cradle and the high-pressure press.  6-ID-B had
#: one machine (``psic``) plus its simulator; here the pairing is by role, not
#: by real-versus-simulated.
DIFFRACTOMETERS = ["huber_euler", "huber_hp"]

#: ``device -> psi-engine partner``.  hklpy2 keeps psi in a separate engine on
#: the same motors, and the HKL tab reads the live psi off it.  At 6-ID-B this
#: was a single module constant because there was a single machine.
PSI_GEOMETRY = {
    "huber_euler": "huber_euler_psi",
    "huber_hp": "huber_hp_psi",
}

#: ``device -> q-engine partner``.
#:
#: **POLAR has none.**  6-ID-B read 2theta off a ``q`` engine (``psic_q``);
#: there is no such device here, so the tab computes 2theta from the angles
#: instead (see ``hkl_bridge._gui_hkl_derived``).  Left as an empty mapping
#: rather than deleted, so a station that adds one only edits this file.
Q_GEOMETRY: dict[str, str] = {}

#: Devices that drive real motors.  Everything in ``DIFFRACTOMETERS`` that is
#: listed here gets the red "REAL MOTORS WILL MOVE" banner and the extra line
#: in the Move confirmation.
#:
#: At POLAR **both** machines are real -- there is no simulator in
#: ``devices.yml`` -- so this is the whole list.  Add a simulated twin here by
#: leaving it *out*.
REAL_MOTOR_DEVICES = {"huber_euler", "huber_hp"}

#: Devices an MCP client may address.  Checked in the *kernel*, so a bug in
#: the server -- or a second client that found the connection file -- is still
#: bounded by it.  The psi/q partners stay out: separate engines on the same
#: motors, and nothing in the tool set needs them.
MCP_ALLOWED_DEVICES = frozenset(DIFFRACTOMETERS)

#: Device an MCP tool call defaults to when it does not name one.
#:
#: 6-ID-B defaulted to the *simulator*, so reaching the real machine was
#: always an explicit act.  POLAR has no simulator, so that protection is not
#: available and the default is a real machine -- which is precisely why the
#: approval gate is the load-bearing control here, not the default.
MCP_DEFAULT_DEVICE = "huber_euler"


# --- the 3D model ----------------------------------------------------------

#: ``3D model angle -> device real-axis name``.
#:
#: The model in ``diffract3d`` is built from
#: ``jwkim/python/diffract/diffractometer_polar.py`` and names the horizontal
#: detector rotation ``nu``; the hklpy2 APS POLAR geometry calls it ``gamma``.
#: ``tau`` is a real axis with no counterpart in the model -- it moves the
#: whole instrument, not a part of it -- so it is absent here and simply not
#: drawn.
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
