id4_common.utils.session_state
==============================

.. py:module:: id4_common.utils.session_state

.. autoapi-nested-parse::

   Auto-saved per-experiment session state in ``RE.md['session_state']``.

   Each setup helper in this package — ``pr_setup``, ``energy.tracking_setup``,
   ``counters.plotselect``, ``undulator_setup``, ``qxscan_setup`` — calls the
   matching ``_save_*`` helper at the tail of its body.  The snapshot is
   mirrored into the apsbits ``RE.md`` ``PersistentDict`` so it survives
   bluesky restarts.

   To re-apply every saved knob after a restart::

       from id4_common.utils.session_state import restore_session_state
       status = restore_session_state()
       for knob, s in status.items():
           print(f"  {knob:18}  {s}")

   Each restore step reports ``"applied"`` / ``"skipped: <reason>"`` /
   ``"failed: <Exception>"``.  ``restore_session_state`` never raises — a
   missing device or a single failed put is logged and the rest of the
   restore continues.

   The schema under ``RE.md['session_state']`` is a nested dict with one
   sub-key per knob group:

   - ``saved_at``         (str, ISO timestamp; refreshed on every save)
   - ``undulators``       (``{us|ds: {energy_offset, energy_deadband}}``)
   - ``energy_tracking``  (``{devices: [name, ...]}``)
   - ``pr_setup``         (``{positioner, offset, oscillate_pzt}``)
   - ``counters``         (``{detectors, monitor, extra_read}`` — by
     ``(device, channel)`` pairs to survive index shifts)
   - ``qxscan``           (``{source}`` (json filename) or ``{params}``)





Module Contents
---------------

.. py:function:: save_session_state() -> dict

   Snapshot every supported knob (escape hatch — normal flow is the
   auto-save hooks).


.. py:function:: restore_session_state(state: dict | None = None) -> dict

   Re-apply every knob from ``RE.md['session_state']`` (or ``state``).

   Returns ``{knob_group: status_str}`` so callers can print a summary.
   Never raises.
