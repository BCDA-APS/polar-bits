"""
Keep pseudo-axis targets in step with where the real motors are.

ophyd's ``PseudoSingle.move()`` goes through
``PseudoPositioner.move_single()``, which solves for the new value of that
axis together with the *target* of every other axis.  A target is the last
value commanded on that axis, and nothing clears it when the real motors move
on their own (an alignment scan, ``cen()``, ``th2th``, ``mvr(chi, ...)``).
So after ``ubr(1, 1, 0)`` and a chi alignment that leaves the diffractometer
at (1.003, 0.997, 0.020), ``mov huber_euler.h 1.01`` solved for
(1.01, 1, 0) and moved all six angles back, undoing the alignment.  The same
went for ``hscan``/``kscan``/``lscan``, ``mvr(h, ...)`` and ``cen()`` after an
hkl scan.

Imports only ophyd, so it can be tested where libhkl is not installed.
"""

from ophyd import Device


class _TargetsFollowMotorsMixin(Device):
    """Clear pseudo-axis targets when the real motors move on their own.

    After every real-motor readback (``_real_pos_update``, on ophyd's monitor
    thread), if no pseudo move is in progress and any target is further than
    ``_target_tolerance`` from the current position, all targets are cleared
    with ``PseudoSingle.sync()``.  A single-axis move then keeps the other
    axes where the diffractometer *is*.  The exact commanded values survive
    as long as the motors sit where they were sent.

    "A pseudo move is in progress" is a flag set synchronously in ``move()``
    and cleared in ``_done_moving()``.  ophyd's own state cannot be used:
    ``PseudoPositioner.moving`` turns true only once DMOV drops (late, and
    never for a zero-length move), and ``_real_waiting`` is emptied at the
    start of every ``_setup_move``.  bluesky ``mv(h, 1, k, 1, l, 0)`` sends
    three single-axis moves in a row, and clearing the targets between them
    would make the last one solve with a stale h.

    A move that is stopped or fails still ends in ``_done_moving()``, after
    which the targets follow wherever it stopped.

    Relies on ophyd private attributes: ``PseudoSingle._target``,
    ``PseudoPositioner._pseudo`` and ``PositionerBase._position``.  Check
    them when upgrading ophyd.

    How to apply: list it before the ``PseudoPositioner`` base.
    """

    #: Largest |target - position|, per axis, still treated as "where it was
    #: sent".  About 60x the hkl change from 0.0001 deg of motor resolution at
    #: the (110), so normal settling and readback jitter keep the commanded
    #: values.
    _target_tolerance = 1e-4

    def __init__(self, *args, **kwargs):
        """Construct, with no pseudo move in progress."""
        # Before super(): real-motor subscriptions may fire during it.
        self._pseudo_move_pending = False
        super().__init__(*args, **kwargs)

    def move(self, *args, **kwargs):
        """Move the pseudo axes, marking the move as in progress first."""
        self._pseudo_move_pending = True
        try:
            return super().move(*args, **kwargs)
        except Exception:
            self._pseudo_move_pending = False
            raise

    def _done_moving(self, *args, **kwargs):
        """The pseudo move finished (or stopped): targets may follow again."""
        self._pseudo_move_pending = False
        super()._done_moving(*args, **kwargs)

    def _real_pos_update(self, *args, **kwargs):
        """A real motor moved: update the position, then the targets."""
        super()._real_pos_update(*args, **kwargs)
        self._follow_real_motors()

    def _follow_real_motors(self):
        """Clear all targets if the motors moved away from them."""
        if self._pseudo_move_pending:
            return
        position = self._position
        if position is None:
            return
        tolerance = self._target_tolerance
        if any(
            axis._target is not None and abs(axis._target - value) > tolerance
            for axis, value in zip(self._pseudo, position, strict=False)
        ):
            # All together, so the targets stay one consistent point.
            for axis in self._pseudo:
                axis.sync()
