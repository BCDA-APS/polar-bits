"""Utility for configuring upstream and downstream undulator setpoints.

The single public function, :func:`undulator_setup`, walks the user
through an interactive prompt for each undulator (DS = downstream, US =
upstream): whether to track the mono energy, what offset (in keV) to
apply between mono energy and undulator setpoint, and which harmonic to
use.  Any value passed as a kwarg short-circuits the matching prompt;
sentinel kwarg defaults mean "ask interactively, with the current
device state as the default answer".

Sentinel values used in the kwargs (legacy API; see the module-level
TODO at the bottom of this file for a proposed cleanup):

==========  =============  ============================================
kwarg       sentinel       meaning
==========  =============  ============================================
``ds``      ``"N"``        ask, defaulting to "yes" if already tracking
``us``      ``"N"``        same
``ds_off``  ``999``        ask, defaulting to current offset (or
                           calculated from mono if the offset is 0)
``us_off``  ``999``        same
``ds_harm`` ``0``          ask, defaulting to the device's current value
``us_harm`` ``0``          same
==========  =============  ============================================

A value of ``"c"`` for an offset (only valid when prompted) means
"calculate from ``undulator.energy.readback - energy``"; a value of
``"c"`` for a harmonic picks 1 / 3 / 5 from the energy thresholds in
:data:`HARMONIC_BREAKPOINTS_KEV`.
"""

from apsbits.core.instrument_init import oregistry

# Sentinel for "kwarg not supplied"; the legacy API uses these literal
# values instead of None.  See the cleanup TODO at the bottom of this
# file for the proposed migration.
_OFFSET_SENTINEL = 999  # ds_off / us_off "ask interactively" default
_HARM_SENTINEL = 0  # ds_harm / us_harm "ask interactively" default

# Energy thresholds for the "[c]alculate" harmonic auto-pick.  Below the
# first cutoff use harmonic 1, below the second use 3, otherwise 5.
HARMONIC_BREAKPOINTS_KEV = ((8.6, 1), (18.0, 3))
_HARMONIC_FALLBACK = 5  # used when the energy is above every breakpoint


def _auto_harmonic(energy_keV: float) -> int:
    """Pick an undulator harmonic from the mono energy."""
    for cutoff, harm in HARMONIC_BREAKPOINTS_KEV:
        if energy_keV < cutoff:
            return harm
    return _HARMONIC_FALLBACK


def undulator_setup(
    ds="N", ds_off=999, ds_harm=0, us="N", us_off=999, us_harm=0
):
    """
    Configure each undulator's tracking, offset, and harmonic.

    Walks DS then US, asking three questions per undulator:
    "Use it?" → "Offset?" → "Harmonic?".  Any kwarg whose value differs
    from its sentinel skips the matching prompt.

    Parameters
    ----------
    ds, us : {"Y", "y", "yes", "Yes", "N", "n", "no", "No"}, optional
        Whether the undulator should track the mono energy.  ``"N"`` is
        the sentinel that triggers an interactive prompt (default).
        Default answer at the prompt: "yes" if the device is currently
        tracking, else "no".
    ds_off, us_off : float, optional
        Offset in keV applied between the mono energy and the undulator
        setpoint.  Sentinel ``999`` triggers an interactive prompt that
        also accepts the literal string ``"c"`` to calculate the offset
        from ``undulator.energy.readback - energy``.  When the
        device's current ``energy_offset`` is 0 the prompt's default
        is the calculated value (assumed-uninitialised); otherwise the
        prompt's default is the current offset.
    ds_harm, us_harm : int, optional
        Undulator harmonic.  Must be an odd integer in {1, 3, 5, 7, 9}.
        Sentinel ``0`` triggers an interactive prompt that also accepts
        the literal string ``"c"`` to auto-pick from the mono energy
        via :data:`HARMONIC_BREAKPOINTS_KEV`.

    Side effects
    ------------
    Writes ``undulators.{ds,us}.energy_offset``,
    ``…tracking``, and ``…harmonic_value`` for whichever undulators
    are turned on.  Prints a one-line summary per undulator.

    The auto-save hook at the end of the function mirrors the new
    offsets / deadbands into ``RE.md["session_state"]`` so a bluesky
    restart can re-apply them via
    :func:`id4_common.utils.session_state.restore_session_state`.

    See Also
    --------
    :func:`id4_common.devices.energy_device.EnergySignal.tracking_setup`
        Higher-level "which devices follow energy" selector — typically
        called *with* this function (after this sets per-undulator
        offsets/harmonics, ``tracking_setup`` flips the tracking flags
        in one go).
    :func:`id4_common.utils.session_state.restore_session_state`
        Replays the saved offsets / harmonics / tracking flags after a
        bluesky restart.
    """

    undulators = oregistry.find("undulators")
    energy = oregistry.find("energy")

    # The flag dance below answers, for each kwarg, "did the caller
    # supply a value, or should we prompt?"  When a sentinel matches we
    # also seed the prompt's default with a sensible value pulled from
    # the live device state.
    ds_inq = False
    us_inq = False
    ds_off_inq = False
    us_off_inq = False
    if ds != "N":
        ds_inq = True
    elif ds == "N" and undulators.ds.tracking.get():
        # No kwarg given but the device is already tracking → default the
        # prompt to "yes" so the user just hits enter to keep tracking.
        ds = "Y"
        ds_inq = False
    else:
        ds_inq = False

    if us != "N":
        us_inq = True
    elif us == "N" and undulators.us.tracking.get():
        us = "Y"
        us_inq = False
    else:
        us_inq = False

    # Offset defaults: if the device's current offset is 0 (probably
    # uninitialised) and the caller didn't pass a value, default the
    # prompt to the *calculated* offset (mono - undulator readback).
    # Otherwise default to the device's current offset.  When the
    # caller supplies a value via kwarg, skip the prompt entirely.
    if undulators.ds.energy_offset.get() == 0 and ds_off == _OFFSET_SENTINEL:
        ds_off = undulators.ds.energy.readback.get() - energy.get()
    elif ds_off == _OFFSET_SENTINEL:
        ds_off = undulators.ds.energy_offset.get()
    else:
        ds_off_inq = True
    if undulators.us.energy_offset.get() == 0 and us_off == _OFFSET_SENTINEL:
        us_off = undulators.us.energy.readback.get() - energy.get()
    elif us_off == _OFFSET_SENTINEL:
        us_off = undulators.us.energy_offset.get()
    else:
        us_off_inq = True

    # Harmonic defaults: pull from the device unless a kwarg was passed.
    if ds_harm == _HARM_SENTINEL:
        ds_harm = undulators.ds.harmonic_value.get()
        ds_harm_inq = False
    else:
        ds_harm_inq = True

    if us_harm == _HARM_SENTINEL:
        us_harm = undulators.us.harmonic_value.get()
        us_harm_inq = False
    else:
        us_harm_inq = True

    # ----------------------------------------------------------------
    # DS undulator  (the US branch below is byte-identical except for
    # the side prefix — see the cleanup TODO at the end of the file).
    # ----------------------------------------------------------------
    ds = ds if ds_inq else input(f"Use DS undulator [{ds}]: ") or ds
    if ds in ["Yes", "Y", "y", "yes"]:
        ds_off = (
            ds_off
            if ds_off_inq
            else input(
                f"   DS undulator offset (value/[c]alculate) [{ds_off:.3f}]: "
            )
            or ds_off
        )
        if ds_off == "c":
            ds_off = undulators.ds.energy.readback.get() - energy.get()
        ds_harm = (
            ds_harm
            if ds_harm_inq
            else input(
                f"   DS undulator harmonics (1,3,5,../[c]alculate) [{ds_harm:.0f}]: "
            )
            or ds_harm
        )
        if ds_harm == "c":
            ds_harm = _auto_harmonic(energy.get())

        undulators.ds.energy_offset.put(float(ds_off))
        undulators.ds.tracking.put(True)
        try:
            if ds_harm in [1, 3, 5, 7, 9]:
                undulators.ds.harmonic_value.put(int(ds_harm))
                print(f"Undulator uses harmonic {ds_harm:.0f}")
            else:
                print("     Harmonics needs to be an odd integer!")
        except Exception:
            print("     Undulator currently disabled")
        print(f"DS undulator tracking with offset = {float(ds_off):.3f}\n")
    else:
        undulators.ds.tracking.put(False)
        print("DS undulator tracking OFF\n")

    # ----------------------------------------------------------------
    # US undulator  (duplicate of DS branch above — see cleanup TODO).
    # ----------------------------------------------------------------
    us = us if us_inq else input(f"Use US undulator [{us}]: ") or us
    if us in ["Yes", "Y", "y", "yes"]:
        us_off = (
            us_off
            if us_off_inq
            else input(
                f"   US undulator offset (value/[c]alculate) [{us_off:.3f}]: "
            )
            or us_off
        )
        if us_off == "c":
            us_off = undulators.us.energy.readback.get() - energy.get()
        us_harm = (
            us_harm
            if us_harm_inq
            else input(
                f"   US undulator harmonics (1,3,5,../[c]alculate) [{us_harm:.0f}]: "
            )
            or us_harm
        )
        # NOTE: previously this branch wrote to ``ds_harm`` instead of
        # ``us_harm`` — a copy-paste bug from the duplicated DS/US logic.
        # Fixed here to write to the correct US variable.
        if us_harm == "c":
            us_harm = _auto_harmonic(energy.get())
        undulators.us.energy_offset.put(float(us_off))
        undulators.us.tracking.put(True)
        try:
            if us_harm in [1, 3, 5, 7, 9]:
                undulators.us.harmonic_value.put(int(us_harm))
                print(f"Undulator uses harmonic {us_harm:.0f}")
            else:
                print("     Harmonics needs to be an odd integer!")
        except Exception:
            print("     Undulator currently disabled")
        print(f"US undulator tracking with offset = {float(us_off):.3f}")
    else:
        undulators.us.tracking.put(False)
        print("US undulator tracking OFF")

    # Auto-save the new offsets/deadbands so a bluesky restart can
    # re-apply them via session_state.restore_session_state().  Lazy
    # import keeps the module-load order safe.
    try:
        from .session_state import _save_undulator

        _save_undulator()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# TODO(undulator_setup cleanup) — see the chat thread that introduced this
# block.  Keeping the function as-is for now to avoid behaviour change in
# the same PR as session_state; revisit as a focused refactor.
#
# Concrete items:
#
# 1. Replace the magic sentinels (999 / 0 / "N") with ``None`` so the
#    "kwarg supplied vs not" check is just ``if value is None:``.  Drops
#    the six ``*_inq`` flags entirely.
#
# 2. Extract the per-side block (lines under "DS undulator" / "US
#    undulator" banners) into a private ``_setup_one_side(side, …)``
#    helper called twice.  Halves the function length and removes the
#    class of bugs that produced the harmonic copy-paste mistake just
#    fixed in this commit.
#
# 3. Catch a specific exception in the harmonic ``try`` blocks instead of
#    bare ``Exception``.  Today's ``except Exception:`` swallows real
#    bugs along with "undulator disabled" timeouts.
#
# 4. Decide whether ``undulator_setup`` should still toggle each
#    undulator's ``.tracking`` flag at all, given that
#    ``energy.tracking_setup([...])`` is the canonical "which devices
#    follow energy" selector.  Two paths to the same state are confusing.
#    Likely outcome: keep the offset/harmonic prompts here, drop the
#    on/off prompt and document that users go through
#    ``energy.tracking_setup`` for that toggle.
#
# 5. Once 1–4 are done the function shrinks to ~50 lines with one
#    docstring per public symbol; the current block-comment scaffolding
#    (the "DS undulator" / "US undulator" banners) becomes redundant.
# ---------------------------------------------------------------------------
