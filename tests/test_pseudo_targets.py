"""Single-axis hkl moves must keep the other axes where the motors are.

Report item 4.3 (huber_euler wrong positions, 2026-10-31): ophyd solves a
single pseudo-axis move with the other axes' *last commanded* values, and
nothing cleared those when the real motors moved on their own.  After an
alignment, ``mov h ...`` drove k and l back to the old command.

A toy pseudo-positioner on soft motors (h, k, l = a, b, c) stands in for the
diffractometer, so none of this needs libhkl or EPICS.
"""

from __future__ import annotations

import pytest
from id4_common.devices.pseudo_targets import _TargetsFollowMotorsMixin
from ophyd import Component
from ophyd import PseudoPositioner
from ophyd import PseudoSingle
from ophyd import SoftPositioner
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument


class Toy(_TargetsFollowMotorsMixin, PseudoPositioner):
    """h, k, l mapped one to one onto three soft motors."""

    h = Component(PseudoSingle)
    k = Component(PseudoSingle)
    l = Component(PseudoSingle)  # noqa: E741 - the Miller index
    a = Component(SoftPositioner, init_pos=0.0)
    b = Component(SoftPositioner, init_pos=0.0)
    c = Component(SoftPositioner, init_pos=0.0)

    fail_forward = False

    @pseudo_position_argument
    def forward(self, pseudo):
        if self.fail_forward:
            raise ValueError("no solution")
        return self.RealPosition(a=pseudo.h, b=pseudo.k, c=pseudo.l)

    @real_position_argument
    def inverse(self, real):
        return self.PseudoPosition(h=real.a, k=real.b, l=real.c)


@pytest.fixture
def toy():
    device = Toy(name="toy")
    device.wait_for_connection()
    return device


def _mv_hkl(toy, h, k, l):  # noqa: E741
    """What bluesky mv(h, .., k, .., l, ..) does: three single-axis moves."""
    for axis, value in ((toy.h, h), (toy.k, k), (toy.l, l)):
        axis.move(value, wait=True)


def test_sequential_single_axis_moves_land_on_the_command(toy):
    _mv_hkl(toy, 1.0, 1.0, 0.0)

    assert tuple(toy.position) == (1.0, 1.0, 0.0)
    assert tuple(toy.target) == (1.0, 1.0, 0.0)


def test_a_real_motor_move_makes_the_targets_follow(toy):
    _mv_hkl(toy, 1.0, 1.0, 0.0)

    toy.b.move(1.3)  # an alignment move on a real motor

    assert tuple(toy.target) == pytest.approx(tuple(toy.position))
    assert toy.k.target == pytest.approx(1.3)


def test_mov_h_keeps_k_and_l_where_the_motors_are(toy):
    """The user's case: ``mov h`` after an alignment."""
    _mv_hkl(toy, 1.0, 1.0, 0.0)
    toy.b.move(1.3)
    toy.c.move(0.02)

    toy.h.move(1.01, wait=True)

    assert tuple(toy.position) == pytest.approx((1.01, 1.3, 0.02))


def test_jitter_below_the_tolerance_keeps_the_commanded_values(toy):
    _mv_hkl(toy, 1.0, 1.0, 0.0)

    toy.b.move(1.0 + toy._target_tolerance / 2)

    assert toy.k._target == 1.0


def test_no_follow_while_a_pseudo_move_is_in_progress(toy):
    """A readback in the middle of mv(h, k, l) must not clear the targets."""
    _mv_hkl(toy, 1.0, 1.0, 0.0)
    toy.h._target = 2.0  # h commanded, k and l not yet issued
    toy._pseudo_move_pending = True

    toy.b.move(1.3)

    assert toy.h._target == 2.0


def test_a_failed_move_clears_the_in_progress_flag(toy):
    _mv_hkl(toy, 1.0, 1.0, 0.0)
    toy.fail_forward = True

    with pytest.raises(ValueError):
        toy.h.move(2.0, wait=True)
    assert toy._pseudo_move_pending is False

    toy.fail_forward = False
    toy.b.move(1.3)
    assert tuple(toy.target) == pytest.approx(tuple(toy.position))


def test_nothing_commanded_means_nothing_to_follow(toy):
    """Targets start as None and simply read the position."""
    toy.a.move(0.5)

    assert all(axis._target is None for axis in (toy.h, toy.k, toy.l))
    assert tuple(toy.target) == pytest.approx((0.5, 0.0, 0.0))
