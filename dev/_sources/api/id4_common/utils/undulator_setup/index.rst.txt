id4_common.utils.undulator_setup
================================

.. py:module:: id4_common.utils.undulator_setup

.. autoapi-nested-parse::

   Utility for configuring upstream and downstream undulator offsets.

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







Module Contents
---------------

.. py:data:: HARMONIC_BREAKPOINTS_KEV
   :value: ((8.6, 1), (18.0, 3))


.. py:function:: undulator_setup(ds_off=None, ds_harm=None, us_off=None, us_harm=None)

   Configure each undulator's offset and harmonic.

   Walks DS then US, asking two questions per undulator: "Offset?" →
   "Harmonic?".  Any kwarg supplied short-circuits the matching prompt.

   :param ds_off: Offset in keV applied between the mono energy and the undulator
                  setpoint.  ``None`` (default) triggers an interactive prompt
                  that also accepts the literal string ``"c"`` to calculate the
                  offset from ``undulator.energy.readback - energy``.  When the
                  device's current ``energy_offset`` is 0 the prompt's default
                  is the calculated value (assumed-uninitialised); otherwise the
                  prompt's default is the current offset.
   :type ds_off: float, optional
   :param us_off: Offset in keV applied between the mono energy and the undulator
                  setpoint.  ``None`` (default) triggers an interactive prompt
                  that also accepts the literal string ``"c"`` to calculate the
                  offset from ``undulator.energy.readback - energy``.  When the
                  device's current ``energy_offset`` is 0 the prompt's default
                  is the calculated value (assumed-uninitialised); otherwise the
                  prompt's default is the current offset.
   :type us_off: float, optional
   :param ds_harm: Undulator harmonic.  Must be an odd integer in
                   ``{1, 3, 5, 7, 9}``.  ``None`` (default) triggers an interactive
                   prompt that also accepts the literal string ``"c"`` to
                   auto-pick from the mono energy via
                   :data:`HARMONIC_BREAKPOINTS_KEV`.
   :type ds_harm: int, optional
   :param us_harm: Undulator harmonic.  Must be an odd integer in
                   ``{1, 3, 5, 7, 9}``.  ``None`` (default) triggers an interactive
                   prompt that also accepts the literal string ``"c"`` to
                   auto-pick from the mono energy via
                   :data:`HARMONIC_BREAKPOINTS_KEV`.
   :type us_harm: int, optional
   :param Side effects:
   :param ------------:
   :param Writes ``undulators.ds.energy_offset``:
   :param ``undulators.us.energy_offset``:
   :param :
   :param and the corresponding ``harmonic_value`` PVs (when reachable and:
   :param valid).  Auto-saves the new offsets / deadbands into:
   :param ``RE.md["session_state"]`` so a bluesky restart can re-apply them:
   :param via :func:`~id4_common.utils.session_state.restore_session_state`.:

   .. rubric:: Notes

   Does **not** touch ``.tracking``.  Use
   :func:`id4_common.devices.energy_device.EnergySignal.tracking_setup`
   to enable / disable per-device tracking.

   .. seealso:: :func:`id4_common.devices.energy_device.EnergySignal.tracking_setup`, :func:`id4_common.utils.session_state.restore_session_state`


