"""MCP tools for setting up and driving the POLAR diffractometer.

Run as ``polar-mcp`` over stdio, next to a running ``polar-gui``.  Every tool is
one call into :meth:`id4_common.mcp_server.session.HklSession.call`; the work is in
the descriptions, which carry the ordering rules that make hklpy2 setup
succeed -- a mode before the angles it holds constant, two orienting
reflections before a UB, a "psi constant" mode before a fixed psi.

**Motion is requested, never performed.**  A move tool validates, then parks a
proposal for the operator to approve in the GUI's Agent tab, and returns
*before* anything happens.  The kernel-side dispatcher has no path to ``RE``
at all (:mod:`id4_common.mcp_server.motion`), so this is a property of the code
rather than a promise in a docstring.

Orientation tools take ``device``, defaulting to
:data:`~id4_common.mcp_server.bridge.DEFAULT_DEVICE`.  **That default is a real
machine.**  6-ID-B could default to a simulator, so touching hardware was
always an explicit act; POLAR has no simulated diffractometer, so that layer
does not exist here and the approval gate is the only thing in front of the
motors.  The allow-list and the per-op scope are checked again in the kernel,
so a bug here cannot address an op to a device it was not written for.

Every tool returns ``{"ok", "message", "data"}``.  ``message`` is written to be
read: when hklpy2 declines something -- a preset for an axis this mode does not
hold constant, say -- it says which and why, so the next call can be corrected
without a round trip to the human.

Needs the ``mcp`` SDK::

    conda activate polar-bits && pip install mcp

Nothing else in this package imports it, so the rest works without it.  Both
SDK generations are accepted: 2.0 calls the decorator-style server
``mcp.server.MCPServer``, 1.x called it ``mcp.server.fastmcp.FastMCP``, and
``@server.tool()`` and ``run()`` behave the same on either.
"""

import argparse
import sys

from .bridge import ALLOWED_DEVICES
from .bridge import DEFAULT_DEVICE
from .bridge import SESSION_DEVICE
from .session import HklSession

#: "huber_euler, huber_hp", for the instructions -- built from the allow-list
#: rather than typed out, so adding a machine in ``gui/config.py`` reaches the
#: text a client reads without a second edit here.
_DEVICE_LIST = ", ".join(sorted(ALLOWED_DEVICES))

_INSTRUCTIONS = """\
Drive a POLAR diffractometer in a live Bluesky session: set up an orientation,
propose moves, run scans, read what came back.

Two diffractometers, {devices}, and **both are real** -- there is no
simulator here, so there is nowhere to try something out first. `{default}` is
the default; name the other one explicitly. Each has its own sample list,
reflections, UB and mode, so read hkl_get_state for the device you mean rather
than assuming the two agree.

The reciprocal-space scan plans (hscan, kscan, lscan, hklscan, th2th, psiscan)
take no device argument: they act on whichever diffractometer the session has
made active. hkl_get_state reports that in its `active` field -- check it
before asking for one of those scans. You cannot change it: switching also
re-applies the axis constraints and rebinds the console's axis names, so it is
the operator's to do from the HKL tab. Ask them if you need the other one.

**You cannot change anything by yourself.** move_hkl, move_axes, set_signals
and run_scan validate the request and then park it for the human operator, who
approves or rejects it in the GUI. They return immediately, saying "awaiting
approval"; that is success, not completion. After one:

  - Poll get_request_status. Do NOT send the request again -- a second one
    while the first is pending is refused, and re-asking is how a queue of
    unwanted moves gets built.
  - The operator may have armed an auto-approve window, in which case it runs
    without a click. You cannot tell in advance, and should not assume it.
  - If a guard refuses (a soft limit, or too far in one move), that is a
    reason to tell the operator what you wanted and why, not to retry with
    allow_large_move. Only use allow_large_move when the human has said the
    long move is intended.

Orientation setup, in this order -- each step depends on the one before:

1. hkl_get_state -- always start here. It reports the current sample, lattice,
   reflections, mode, constant axes and UB, so nothing below is guesswork.
2. hkl_add_sample + hkl_select_sample, or hkl_set_lattice on the current one.
3. hkl_add_reflection twice. Omit `angles` to use the diffractometer's live
   position -- that is the normal case: the operator drives to the peak, you
   record it.
4. hkl_set_orienting (or hkl_compute_ub) to get an orientation matrix.
5. hkl_set_mode, then hkl_set_fixed_angles for the axes that mode holds
   constant. The order matters: which axes can be fixed depends on the mode.
   POLAR's mode names contain spaces -- "psi constant vertical", not
   "psi_constant_vertical". Copy them from hkl_get_state rather than typing
   them.
6. hkl_calc_angles to solve an hkl into angles. Nothing moves.

Two kinds of thing can be changed, and they do not overlap:

  - Axes are *moved*: list_axes, then move_axes (or move_hkl, or run_scan).
  - Everything else writable is *set*: list_signals, then set_signals. That is
    where a filter attenuation, a lock-in sensitivity, a temperature setpoint
    or a mode enum lives. Ask list_signals with no argument for the
    devices that have any, then again with device_name for one device's
    signals and what each accepts.

Reading is free and leaves no trace in the operator's console: list_axes,
read_axes, list_signals, get_counters, get_last_scan, get_session_status.

If a call reports the session is busy, a scan or an approved move is running.
get_session_status still answers -- it reads the motors over Channel Access
rather than through the session -- so use it to follow progress, and wait.
""".format(devices=_DEVICE_LIST, default=DEFAULT_DEVICE)


def _add_tools(mcp, session):
    """Declare every tool against *session*."""

    def call(op, **args):
        return session.call(op, **args)

    def session_call(op, **args):
        """An op that acts on the session rather than on a diffractometer."""
        return session.call(op, device=SESSION_DEVICE, **args)

    # -- reading -----------------------------------------------------------

    @mcp.tool()
    def hkl_get_state(device: str = DEFAULT_DEVICE) -> dict:
        """Report the full orientation state of a diffractometer.

        *device* names one of the diffractometers listed in the server
        instructions -- all of them real machines, each with its own samples,
        reflections, UB and mode, so state read for one says nothing about the
        other.  Returns the sample list and their lattices, the current
        sample, its reflections (with keys, hkl, angles, and which two are orienting), the
        UB matrix, the current mode and the modes available, the axes this mode
        holds constant, the fixed angles (presets) in force, psi and the psi
        reference vector -- plus ``active``, the diffractometer the
        reciprocal-space scan plans act on, which need not be this one.

        Call this first, and again after anything unexpected: it is the only
        way to know which reflection keys and mode names exist.  It also
        teaches this server the axes' PV names, which is what lets
        get_session_status follow a move while the session is busy.
        """
        return call("get_state", device=device)

    @mcp.tool()
    def hkl_get_position(device: str = DEFAULT_DEVICE) -> dict:
        """Report where a diffractometer is now: hkl, the six angles, 2theta, psi.

        Also the wavelength and energy the solver is using.  This is a
        position, not a setting -- use hkl_calc_angles to find the angles for
        an hkl without going there.
        """
        return call("get_position", device=device)

    # -- sample and lattice ------------------------------------------------

    @mcp.tool()
    def hkl_add_sample(
        name: str,
        a: float,
        b: float,
        c: float,
        alpha: float = 90.0,
        beta: float = 90.0,
        gamma: float = 90.0,
        device: str = DEFAULT_DEVICE,
    ) -> dict:
        """Add a sample with a lattice, replacing one of the same name.

        Lengths in angstroms, angles in degrees.  Adding does not select:
        follow with hkl_select_sample.  A new sample has no reflections and no
        UB of its own.
        """
        return call(
            "add_sample",
            device=device,
            sample=name,
            a=a,
            b=b,
            c=c,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )

    @mcp.tool()
    def hkl_select_sample(name: str, device: str = DEFAULT_DEVICE) -> dict:
        """Make *name* the current sample.

        Reflections, UB and lattice all belong to the current sample, so every
        other tool acts on whichever one this selected.
        """
        return call("select_sample", device=device, sample=name)

    @mcp.tool()
    def hkl_set_lattice(values: dict, device: str = DEFAULT_DEVICE) -> dict:
        """Change lattice parameters of the current sample.

        *values* maps parameter name to number, e.g. ``{"a": 5.431}``; only the
        ones given change.  The valid names are in ``lattice_names`` from
        hkl_get_state -- a cubic sample exposes only ``a``.

        UB is recomputed afterwards if two orienting reflections exist, so the
        orientation follows the lattice rather than going quietly stale.
        """
        return call("set_lattice", device=device, values=values)

    @mcp.tool()
    def hkl_remove_sample(name: str, device: str = DEFAULT_DEVICE) -> dict:
        """Delete a sample.  The current one cannot be removed; select another
        first."""
        return call("remove_sample", device=device, sample=name)

    # -- reflections and UB -------------------------------------------------

    @mcp.tool()
    def hkl_add_reflection(
        h: float,
        k: float,
        l: float,  # noqa: E741 - the Miller index is called l
        angles: dict = None,
        device: str = DEFAULT_DEVICE,
    ) -> dict:
        """Record a reflection: an hkl observed at a set of angles.

        Omit *angles* to use the diffractometer's **live position**, which is
        the usual case -- the operator drives to the peak and you record it.
        Given explicitly, it must name every real axis (see ``real_fields``
        from hkl_get_state), in degrees.

        Two reflections are needed for a UB.  The first two added become the
        orienting pair automatically; hkl_set_orienting changes which.
        """
        return call(
            "add_reflection",
            device=device,
            pseudos={"h": h, "k": k, "l": l},
            reals=angles,
        )

    @mcp.tool()
    def hkl_edit_reflection(
        key: str,
        hkl: dict = None,
        angles: dict = None,
        device: str = DEFAULT_DEVICE,
    ) -> dict:
        """Change an existing reflection in place.

        *key* is from hkl_get_state.  Pass *hkl* (``{"h":…,"k":…,"l":…}``),
        *angles*, or both; what is left out is kept.  Editing one of the two
        orienting reflections recomputes UB.
        """
        return call(
            "edit_reflection", device=device, key=key, pseudos=hkl, reals=angles
        )

    @mcp.tool()
    def hkl_remove_reflection(key: str, device: str = DEFAULT_DEVICE) -> dict:
        """Delete a reflection.

        An orienting reflection is refused -- point hkl_set_orienting at a
        different pair first, or the sample would be left without an
        orientation.
        """
        return call("remove_reflection", device=device, key=key)

    @mcp.tool()
    def hkl_set_orienting(
        first: str, second: str, device: str = DEFAULT_DEVICE
    ) -> dict:
        """Choose which two reflections define the orientation, and compute UB.

        Both keys come from hkl_get_state and must differ.  They should be
        non-parallel: two reflections along the same direction cannot fix a
        rotation about it, and the UB that comes back will be unusable.
        """
        return call("set_orienting", device=device, first=first, second=second)

    @mcp.tool()
    def hkl_compute_ub(device: str = DEFAULT_DEVICE) -> dict:
        """Recompute UB from the current orienting pair.

        Needed after changing a reflection's angles by other means; the tools
        above already do it themselves.
        """
        return call("compute_ub", device=device)

    @mcp.tool()
    def hkl_restore_ub(device: str = DEFAULT_DEVICE) -> dict:
        """Put back the UB from before the last change.

        One level of undo, for UB only -- a computation on a mistyped
        reflection would otherwise destroy a working orientation.  Lattice,
        mode and reflections are *not* restored.
        """
        return call("restore_ub", device=device)

    # -- mode, fixed angles, psi -------------------------------------------

    @mcp.tool()
    def hkl_set_mode(mode: str, device: str = DEFAULT_DEVICE) -> dict:
        """Choose the geometry mode, i.e. how the solver picks among solutions.

        Valid names are in ``modes`` from hkl_get_state.  Each mode solves some
        axes and holds the rest constant, so **set the mode before fixing
        angles** -- which axes can be fixed changes with it.

        POLAR's names contain **spaces**, e.g. ``"psi constant vertical"``,
        ``"4-circles bissecting horizontal"``.  Copy one out of ``modes``
        rather than typing it; an underscored guess is not a mode.

        A 'vertical' mode also defaults the unused horizontal detector angle
        (solver ``gamma``) to 0, and a 'horizontal' one the vertical detector
        (``delta``) -- but only where that axis has no fixed value in this mode
        already, since presets are kept per mode.
        """
        return call("set_mode", device=device, mode=mode)

    @mcp.tool()
    def hkl_set_fixed_angles(
        values: dict, device: str = DEFAULT_DEVICE
    ) -> dict:
        """Fix (preset) the angles the current mode holds constant.

        *values* maps axis name to degrees, e.g. ``{"phi": 30}``.  An axis left
        out has no preset, so the solver uses that motor's live position
        instead -- omitting is not the same as passing its current value.

        Only axes in ``constant_axes`` from hkl_get_state can be fixed; hklpy2
        silently drops the others, so any that were ignored are named in the
        reply.  This changes *computed* solutions only.  Nothing moves.
        """
        return call("set_fixed_angles", device=device, values=values)

    @mcp.tool()
    def hkl_set_psi_reference(
        h2: float, k2: float, l2: float, device: str = DEFAULT_DEVICE
    ) -> dict:
        """Set the reciprocal-space vector psi is measured against.

        Works from any mode -- it switches into a "psi constant" mode to write
        the value and restores the mode afterwards, because those are the only
        modes in which hklpy2 keeps the reference.
        """
        return call("set_psi_reference", device=device, h2=h2, k2=k2, l2=l2)

    @mcp.tool()
    def hkl_set_psi(psi: float, device: str = DEFAULT_DEVICE) -> dict:
        """Fix the azimuthal angle psi, in degrees.

        Only meaningful in a "psi constant horizontal" or "psi constant
        vertical" mode -- POLAR's only two with a psi extra.  Call hkl_set_mode
        first, and hkl_set_psi_reference to say which vector psi is measured
        against.
        """
        return call("set_psi", device=device, psi=psi)

    # -- solving -------------------------------------------------------------

    @mcp.tool()
    def hkl_calc_angles(
        h: float,
        k: float,
        l: float,  # noqa: E741 - the Miller index is called l
        psi: float = None,
        fixed_angles: dict = None,
        device: str = DEFAULT_DEVICE,
    ) -> dict:
        """Compute the angles that would reach a given hkl.  Nothing moves.

        *fixed_angles* and *psi*, if given, are applied first and persist
        afterwards, exactly as the separate tools would leave them.

        A failure here usually means the reflection is unreachable in this mode
        with these fixed angles, not that the hkl is wrong: try relaxing a
        fixed angle or changing mode.  Use move_hkl to ask to go there.
        """
        return call(
            "calc_angles",
            device=device,
            h=h,
            k=k,
            l=l,
            psi=psi,
            presets=fixed_angles,
        )

    # -- motion: requested here, approved by the operator -------------------

    @mcp.tool()
    def move_hkl(
        h: float,
        k: float,
        l: float,  # noqa: E741 - the Miller index is called l
        device: str = DEFAULT_DEVICE,
        allow_large_move: bool = False,
    ) -> dict:
        """Ask the operator to move a diffractometer to an hkl.

        **Returns before anything moves.**  The hkl is solved into six angles
        first, so the request the operator sees is a list of angles, not three
        Miller indices; then the angles are checked against the soft limits and
        the per-move travel cap, and the request is parked for approval.

        A success here means *requested*.  Poll get_request_status; do not send
        it again while one is pending.

        The solution depends on the mode and the fixed angles in force, so set
        those first -- the same hkl in two modes is two different sets of
        angles, and only one of them may be the one wanted.

        *allow_large_move* lifts the travel cap only.  Soft limits are never
        lifted.  Use it when the human has said a long move is intended, not to
        get past a refusal on your own initiative.
        """
        return call(
            "request_hkl",
            device=device,
            h=h,
            k=k,
            l=l,
            allow_large_move=allow_large_move,
        )

    @mcp.tool()
    def move_axes(targets: dict, allow_large_move: bool = False) -> dict:
        """Ask the operator to move one or more axes to absolute positions.

        *targets* maps a dotted axis path to a number, e.g.
        ``{"gslt.hcen": 0.0, "gslt.hsize": 0.5}``.  Use list_axes for the paths;
        anything not in that list is refused by name.  Positions are absolute
        and in each axis's own units -- degrees, mm, keV.

        **Returns before anything moves**, exactly like move_hkl.  Every axis
        is checked before anything is parked, and one bad axis refuses the
        whole request, so a partial move is not possible.
        """
        return session_call(
            "request_axes", targets=targets, allow_large_move=allow_large_move
        )

    @mcp.tool()
    def set_signals(targets: dict, allow_large_move: bool = False) -> dict:
        """Ask the operator to set writable EPICS signals to absolute values.

        This is the counterpart of move_axes for the things that are *set*
        rather than moved -- a filter attenuation, a lock-in sensitivity, a
        temperature setpoint, an enum that picks a mode.  *targets* maps a
        dotted signal path to a value, e.g.
        ``{"gfilter.attenuation_setpoint": 10.0}``.  Use list_signals for the
        paths and for what each one accepts; anything not in that list is
        refused by name, and a path that is really a motor is refused with a
        pointer to move_axes.

        A signal with named settings takes the name, not the number:
        ``{"gfilter.energy_select": "Local"}``.  A name that is not one of its
        choices comes back with the choices listed.

        **Returns before anything is written**, exactly like move_hkl -- a
        filter that goes in changes what the next scan measures as surely as a
        motor does, so it goes through the same approval gate.  Every target is
        checked before anything is parked, and one bad target refuses the whole
        request.
        """
        return session_call(
            "request_signals",
            targets=targets,
            allow_large_move=allow_large_move,
        )

    @mcp.tool()
    def run_scan(
        plan: str,
        points: float,
        time: float,
        axes: list = None,
        detectors: list = None,
        fixq: bool = False,
        allow_large_move: bool = False,
    ) -> dict:
        """Ask the operator to run a scan.

        Twelve plans, in three shapes -- and *axes* means something different
        in each, so pick the shape before writing the call:

        **You choose the axes.**  ``ascan`` (absolute) and ``lup`` (relative to
        where the axes are now) share one point count across their axes;
        ``grid_scan`` and ``rel_grid_scan`` walk a mesh and give each axis its
        own.  *axes* is a list of
        ``{"axis": path, "start": number, "stop": number}``, with a per-axis
        ``"points"`` for the two grid plans.  Paths come from list_axes.

        **The axis is in the plan's name.**  ``th2th`` (2theta), ``hscan``,
        ``kscan``, ``lscan``, ``hklscan`` (h, k and l together, one row each,
        in that order) and ``psiscan``.  These take *axes* rows carrying
        ``"start"`` and ``"stop"`` **only** -- no ``"axis"`` key, since there
        is nothing to choose -- and one row per implicit axis, so ``hklscan``
        needs exactly three and the others exactly one.  They act on the
        diffractometer named by hkl_get_state's ``active`` field, which is
        not necessarily the one you have been reading state for and is not
        yours to change.

        **No axes at all.**  ``count`` repeats readings, *points* times.
        ``qxscan`` walks an absorption edge: its *points* is the **edge energy
        in keV**, not a count, and the energy points themselves come from
        ``qxscan_params()``, which the operator runs in the console first.

        *time* is seconds per point; a negative value means monitor counts
        instead.  Omit *detectors* to use whatever the operator has selected in
        the GUI -- the normal case, and the one that keeps their counters
        configuration intact.

        *fixq* holds hkl constant during the scan, which is what makes an
        energy scan at a fixed reflection possible.  It is dropped for the
        reciprocal-space plans, where the scan *is* the trajectory.

        **Returns before anything runs.**  For a plan that names its motors,
        both ends of every axis are checked against the soft limits, since a
        scan that starts inside them and ends outside is a scan that stops half
        way.  **The reciprocal-space plans get no such check** -- which motors
        move, and how far, is only known once each point is solved against the
        UB and the mode -- so there the operator reading the approval banner is
        the whole of the protection.
        """
        return session_call(
            "request_scan",
            plan=plan,
            axes=axes,
            points=points,
            time=time,
            detectors=detectors,
            fixq=fixq,
            allow_large_move=allow_large_move,
        )

    @mcp.tool()
    def get_request_status() -> dict:
        """Report the pending move or scan request, and recent outcomes.

        ``pending`` is the request waiting for the operator, or null.  ``last``
        is what became of the previous one: approved and done, rejected,
        refused by a guard, or failed.  ``blocked`` means the operator has
        switched motion requests off entirely.

        This is the tool to poll after a move request.  It reads only, so it
        leaves nothing in the operator's console.  If the session reports busy,
        the approved move or scan is running: use get_session_status instead,
        which answers anyway.
        """
        return session_call("get_request")

    @mcp.tool()
    def cancel_request(reason: str = "withdrawn by the client") -> dict:
        """Withdraw the pending request.

        Use this when what was asked for is no longer wanted -- a change of
        plan, a correction after reading the state again.  It does not stop a
        move that has already been approved; only Ctrl-C in the session or the
        operator can do that.
        """
        return session_call("cancel_request", reason=reason)

    # -- reading the session ------------------------------------------------

    @mcp.tool()
    def list_axes() -> dict:
        """List every axis that can be moved, with its position and soft limits.

        The dotted paths here are exactly what move_axes and run_scan accept.
        Limits are ``null`` for an axis that has none configured, which means
        the travel cap is the only guard on it.
        """
        return session_call("list_axes")

    @mcp.tool()
    def read_axes(axes: list = None) -> dict:
        """Read named axes.  With no argument, reads the diffractometer angles.

        Cheaper and quieter than list_axes when the positions are all that is
        wanted.
        """
        return session_call("read_axes", axes=axes)

    @mcp.tool()
    def list_signals(device_name: str = None) -> dict:
        """List the writable EPICS signals that set_signals can set.

        Everything that is *set* rather than moved: a filter attenuation, a
        lock-in sensitivity, a temperature setpoint, an enum that picks a
        mode.  Motor-like axes are deliberately absent -- they are in
        list_axes, and are moved with move_axes.

        With no argument, the devices that have any and how many, which is
        short.  With *device_name* -- ``"gfilter"``, ``"temp_336_4idg"``,
        ``"srs810"`` -- that device's signals in full: the dotted path
        set_signals accepts, the
        current value, the soft limits where the IOC publishes them, the units,
        and the ``choices`` of a signal that is set by name.  A device at a
        time, because reading each value is a channel-access round trip.
        """
        return session_call("list_signals", name=device_name)

    @mcp.tool()
    def get_counters() -> dict:
        """Report what the next scan will count.

        The selected detectors, their channels, the monitor channel and any
        extra devices recorded at each point.  This is the operator's
        selection; changing it is not something this server can do.
        """
        return session_call("get_counters")

    @mcp.tool()
    def get_last_scan() -> dict:
        """Report the last scan and the peak of each of its detectors.

        Scan id, plan, the axis scanned, and for every hinted detector the
        centre, centre of mass, maximum, minimum and FWHM -- computed by the
        same ``plans.peak_position`` code ``cen()`` moves on, so the numbers
        here, the ones in the console table and the ones an alignment plan
        would use cannot disagree.

        A grid scan is answered too, with a peak per axis.

        Use this to decide the next move after a scan: read the peak, then ask
        for a move to it.
        """
        return session_call("get_last_scan")

    @mcp.tool()
    def get_session_status() -> dict:
        """Report motor positions and scan id **while the session is busy**.

        Every other tool is refused during a scan or an approved move, because
        a request sent to a busy session would queue and run much later.  This
        one does not go through the session at all: it reads the motors over
        Channel Access and the run metadata straight out of the RunEngine's
        metadata store on disk, so it keeps answering throughout.

        ``busy`` says whether the session is running something.  ``positions``
        covers the axes whose PV names this server has learnt -- call
        hkl_get_state once on the device of interest first, or it has none to
        read.  ``scan_id``, ``sample``, ``proposal_id`` and ``beamline_id``
        need one call made while the session was idle, which is when this
        server learns where that store is; from then on they are reported
        during scans too.
        """
        return session.status()


def _server_class():
    """The SDK's decorator-style server class, under either of its names.

    ``mcp`` 2.0 renamed ``mcp.server.fastmcp.FastMCP`` to
    ``mcp.server.MCPServer``.  Everything used here -- ``@server.tool()``,
    ``run()`` -- is the same on both, so which one is installed does not reach
    the rest of this module.
    """
    try:
        from mcp.server import MCPServer

        return MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP

        return FastMCP


def build(connection_file=None):
    """Build the MCP server and the session it talks to."""
    import inspect

    server_class = _server_class()
    options = {"instructions": _INSTRUCTIONS}
    # ``version`` reaches ``serverInfo``, which clients display.  Only 2.0 takes
    # it as a constructor argument; on 1.x an unknown keyword lands in the
    # settings object and raises.
    if "version" in inspect.signature(server_class.__init__).parameters:
        options["version"] = _package_version()

    session = HklSession(connection_file=connection_file)
    mcp = server_class("POLAR HKL", **options)
    _add_tools(mcp, session)
    return mcp, session


def _package_version():
    """The installed version of this package, or an empty string."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version

    try:
        return version("polar-bits")
    except PackageNotFoundError:
        return ""


def main(argv=None):
    """Entry point for the ``polar-mcp`` console script."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--connection-file",
        help=(
            "Kernel connection file, or the GUI's .polar-gui-kernel.json. "
            "Found automatically when this runs inside the session's "
            "directory tree."
        ),
    )
    options = parser.parse_args(argv)

    try:
        mcp, _ = build(options.connection_file)
    except ImportError:
        # stderr, not stdout: stdout is the protocol channel.
        print(
            "The MCP SDK is not installed. Run:\n"
            "    conda activate polar-bits && pip install mcp",
            file=sys.stderr,
        )
        return 1
    # Not connecting here: a GUI started after this server is still usable,
    # because HklSession.call attaches on first use and reports in words when
    # there is nothing to attach to.
    mcp.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
