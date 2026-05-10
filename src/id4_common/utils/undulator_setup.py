"""Utility for configuring upstream and downstream undulator offsets.

The single public function, :func:`undulator_setup`, walks the user
through an interactive prompt for each undulator (DS = downstream, US =
upstream): what offset (in keV) to apply between mono energy and
undulator setpoint, and which harmonic to use.  Any value passed as a
kwarg short-circuits the matching prompt; ``None`` (the default) means
"ask interactively, with the current device state as the default
answer".

What this function does **not** do
----------------------------------

It does not toggle each undulator's ``.tracking`` flag.  Use
:func:`id4_common.devices.energy_device.EnergySignal.tracking_setup` for
that — it's the single source of truth for "which devices follow the
mono energy".

Typical workflow::

    undulator_setup(ds_off=-0.072, ds_harm=3)        # offset + harmonic
    energy.tracking_setup(["undulators_ds", "pr2"])  # turn tracking on

Both calls auto-save into ``RE.md["session_state"]``, so a bluesky
restart restores both halves via
:func:`id4_common.utils.session_state.restore_session_state`.
"""

from apsbits.core.instrument_init import oregistry

# Energy thresholds for the "[c]alculate" harmonic auto-pick.  Below the
# first cutoff use harmonic 1, below the second use 3, otherwise 5.
HARMONIC_BREAKPOINTS_KEV = ((8.6, 1), (18.0, 3))
_HARMONIC_FALLBACK = 5  # used when the energy is above every breakpoint
_VALID_HARMONICS = (1, 3, 5, 7, 9)


def _auto_harmonic(energy_keV: float) -> int:
    """Pick an undulator harmonic from the mono energy."""
    for cutoff, harm in HARMONIC_BREAKPOINTS_KEV:
        if energy_keV < cutoff:
            return harm
    return _HARMONIC_FALLBACK


def _resolve_offset(side: str, kwarg, side_dev, energy):
    """Decide on the offset for one undulator.

    - ``kwarg`` is what the caller passed (or ``None`` to prompt).
    - The prompt's default is the device's current offset, falling back
      to the calculated value (``undulator.energy.readback - energy``)
      when the offset is 0 (uninitialised).
    - Accepts the literal ``"c"`` to recompute from the live readback.
    """
    if kwarg is not None:
        return float(kwarg)

    current = side_dev.energy_offset.get()
    if current == 0:
        default = side_dev.energy.readback.get() - energy.get()
    else:
        default = current

    while True:
        answer = (
            input(
                f"   {side.upper()} undulator offset "
                f"(value/[c]alculate) [{default:.3f}]: "
            )
            or default
        )
        if answer == "c":
            return float(side_dev.energy.readback.get() - energy.get())
        try:
            return float(answer)
        except (TypeError, ValueError):
            print("     Offset must be a number or 'c'.")


def _resolve_harmonic(side: str, kwarg, side_dev, energy):
    """Decide on the harmonic for one undulator.

    - ``kwarg`` is what the caller passed (or ``None`` to prompt).
    - The prompt's default is the device's current harmonic value.
    - Accepts the literal ``"c"`` to auto-pick from the mono energy
      via :data:`HARMONIC_BREAKPOINTS_KEV`.
    """
    if kwarg is not None:
        return int(kwarg)

    default = side_dev.harmonic_value.get()

    while True:
        answer = (
            input(
                f"   {side.upper()} undulator harmonic "
                f"(1,3,5,../[c]alculate) [{default:.0f}]: "
            )
            or default
        )
        if answer == "c":
            return _auto_harmonic(energy.get())
        try:
            return int(answer)
        except (TypeError, ValueError):
            print("     Harmonic must be an odd integer or 'c'.")


def _setup_one_side(side: str, undulators, energy, off, harm):
    """Resolve and apply the offset + harmonic for one undulator side.

    Writes ``side.energy_offset`` and (when valid) ``side.harmonic_value``.
    Does **not** touch ``side.tracking``; tracking is configured by
    ``energy.tracking_setup`` (see module docstring).  Prints a
    one-line summary so interactive callers get feedback.
    """
    side_dev = getattr(undulators, side)

    resolved_off = _resolve_offset(side, off, side_dev, energy)
    resolved_harm = _resolve_harmonic(side, harm, side_dev, energy)

    side_dev.energy_offset.put(resolved_off)

    if resolved_harm in _VALID_HARMONICS:
        try:
            side_dev.harmonic_value.put(resolved_harm)
            print(
                f"{side.upper()} undulator: offset = {resolved_off:.3f}, "
                f"harmonic = {resolved_harm}"
            )
        except TimeoutError:
            # The harmonic_value PV is disconnected — typical when the
            # undulator IOC is down.  The offset write above may also
            # have failed silently; surface that to the user.
            print(
                f"     {side.upper()} harmonic_value PV unreachable — "
                "undulator currently disabled?"
            )
    else:
        print(
            f"     {side.upper()} harmonic must be one of "
            f"{_VALID_HARMONICS}; got {resolved_harm!r}.  Skipped."
        )


def undulator_setup(ds_off=None, ds_harm=None, us_off=None, us_harm=None):
    """
    Configure each undulator's offset and harmonic.

    Walks DS then US, asking two questions per undulator: "Offset?" →
    "Harmonic?".  Any kwarg supplied short-circuits the matching prompt.

    Parameters
    ----------
    ds_off, us_off : float, optional
        Offset in keV applied between the mono energy and the undulator
        setpoint.  ``None`` (default) triggers an interactive prompt
        that also accepts the literal string ``"c"`` to calculate the
        offset from ``undulator.energy.readback - energy``.  When the
        device's current ``energy_offset`` is 0 the prompt's default
        is the calculated value (assumed-uninitialised); otherwise the
        prompt's default is the current offset.
    ds_harm, us_harm : int, optional
        Undulator harmonic.  Must be an odd integer in
        ``{1, 3, 5, 7, 9}``.  ``None`` (default) triggers an interactive
        prompt that also accepts the literal string ``"c"`` to
        auto-pick from the mono energy via
        :data:`HARMONIC_BREAKPOINTS_KEV`.

    Side effects
    ------------
    Writes ``undulators.ds.energy_offset``, ``undulators.us.energy_offset``,
    and the corresponding ``harmonic_value`` PVs (when reachable and
    valid).  Auto-saves the new offsets / deadbands into
    ``RE.md["session_state"]`` so a bluesky restart can re-apply them
    via :func:`~id4_common.utils.session_state.restore_session_state`.

    Notes
    -----
    Does **not** touch ``.tracking``.  Use
    :func:`id4_common.devices.energy_device.EnergySignal.tracking_setup`
    to enable / disable per-device tracking.

    See Also
    --------
    :func:`id4_common.devices.energy_device.EnergySignal.tracking_setup`
    :func:`id4_common.utils.session_state.restore_session_state`
    """
    undulators = oregistry.find("undulators")
    energy = oregistry.find("energy")

    _setup_one_side("ds", undulators, energy, ds_off, ds_harm)
    _setup_one_side("us", undulators, energy, us_off, us_harm)

    # Auto-save the new offsets/deadbands so a bluesky restart can
    # re-apply them via session_state.restore_session_state().  Lazy
    # import keeps the module-load order safe.
    try:
        from .session_state import _save_undulator

        _save_undulator()
    except Exception:  # noqa: BLE001 — never break a setup function
        pass
