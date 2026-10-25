"""wax() must stay bounded when a station's IOCs are down.

The regression these pin: ``wax()`` walked every ``"motor"``-labelled entry in
oregistry and called ``.get()`` with the session default 60 s connection
timeout, so a few dozen unreachable motors meant the call never returned.
"""

from __future__ import annotations

import inspect
import time

import pytest
from id4_common.utils.wax import MOTOR_FIELDS
from id4_common.utils.wax import PROBE_BUDGET
from id4_common.utils.wax import PROBE_TIMEOUT
from id4_common.utils.wax import _is_motor
from id4_common.utils.wax import _motor_row
from id4_common.utils.wax import _motor_rows
from id4_common.utils.wax import _report_missed
from id4_common.utils.wax import wax

#: Stand-in for the session default, long enough that a test which forgets to
#: pass a short timeout blows its wall-clock budget instead of passing.
SESSION_DEFAULT_TIMEOUT = 60.0


class FakeSignal:
    """Minimal EpicsSignal stand-in that records the timeouts handed to get."""

    def __init__(
        self, value=1.0, connected=True, fails=False, connected_raises=False
    ):
        self.name = "fake"
        self._value = value
        self._connected = connected
        self._fails = fails
        self._connected_raises = connected_raises
        self.calls = []

    @property
    def connected(self):
        if self._connected_raises:
            raise RuntimeError("lazy component")
        return self._connected

    def get(self, connection_timeout=None, timeout=None):
        self.calls.append(
            {"connection_timeout": connection_timeout, "timeout": timeout}
        )
        if self._fails:
            # Sleep exactly as long as the caller said it would wait, so a
            # caller that omits the short timeout pays the session default.
            delay = timeout if timeout is not None else SESSION_DEFAULT_TIMEOUT
            time.sleep(delay)
            raise TimeoutError("not connected")
        return self._value


class FakeMotor:
    """EpicsMotor-shaped object built from three FakeSignals."""

    def __init__(self, name="m1", **kwargs):
        self.name = name
        self.user_readback = FakeSignal(value=1.0, **kwargs)
        self.low_limit_travel = FakeSignal(value=-5.0, **kwargs)
        self.high_limit_travel = FakeSignal(value=5.0, **kwargs)


class FakePositioner:
    """A "motor"-labelled entry that is not a motor record (4IDH tables)."""

    def __init__(self, name="table_4idh_x"):
        self.name = name
        self.readback = FakeSignal()


def test_connected_motor_reads() -> None:
    row = _motor_row(FakeMotor())
    assert row == ("m1", "1.00000", "[-5.00000,5.00000]")


def test_dead_motor_is_probed_with_the_short_timeout() -> None:
    """The core guard: never hand a dead PV the 60 s session default."""
    motor = FakeMotor(connected=False, fails=True)

    t0 = time.monotonic()
    assert _motor_row(motor, timeout=PROBE_TIMEOUT) is None
    elapsed = time.monotonic() - t0

    assert motor.user_readback.calls == [
        {"connection_timeout": PROBE_TIMEOUT, "timeout": PROBE_TIMEOUT}
    ]
    assert elapsed < 1.0


def test_unconnected_but_live_motor_still_appears() -> None:
    """An IOC that is up connects on demand even without connect_device()."""
    motor = FakeMotor(connected=False, fails=False)
    assert _motor_row(motor) == ("m1", "1.00000", "[-5.00000,5.00000]")


def test_connected_property_raising_does_not_propagate() -> None:
    motor = FakeMotor(connected_raises=True)
    assert _motor_row(motor) == ("m1", "1.00000", "[-5.00000,5.00000]")


def test_read_short_circuits_on_first_failure() -> None:
    motor = FakeMotor()
    motor.user_readback = FakeSignal(connected=False, fails=True)

    assert _motor_row(motor) is None
    assert motor.low_limit_travel.calls == []
    assert motor.high_limit_travel.calls == []


def test_raise_error_propagates() -> None:
    """The wm() contract: an explicitly named dead motor still raises."""
    motor = FakeMotor(connected=False, fails=True)
    with pytest.raises(TimeoutError):
        _motor_row(motor, raise_error=True)


def test_non_motor_entry_is_skipped_not_missed() -> None:
    assert _is_motor(FakeMotor()) is True
    assert _is_motor(FakePositioner()) is False

    rows, missed, skipped = _motor_rows([FakeMotor(), FakePositioner()])
    assert len(rows) == 1
    assert missed == []
    assert skipped == ["table_4idh_x"]


def test_fifty_dead_motors_return_quickly() -> None:
    """The bug itself: 50 dead motors used to cost 50 minutes."""
    motors = [
        FakeMotor(name=f"m{i}", connected=False, fails=True) for i in range(50)
    ]

    t0 = time.monotonic()
    rows, missed, skipped = _motor_rows(motors)
    elapsed = time.monotonic() - t0

    assert rows == []
    assert len(missed) == 50
    assert elapsed < PROBE_BUDGET + 1.0


def test_probe_budget_caps_how_many_dead_motors_are_probed() -> None:
    motors = [
        FakeMotor(name=f"m{i}", connected=False, fails=True) for i in range(50)
    ]
    _motor_rows(motors)

    probed = sum(1 for m in motors if m.user_readback.calls)
    assert probed <= PROBE_BUDGET / PROBE_TIMEOUT + 2


def test_name_filter_runs_before_any_read() -> None:
    wanted = FakeMotor(name="huber_tth")
    other = FakeMotor(name="ancillary_x", connected=False, fails=True)

    rows, missed, skipped = _motor_rows([wanted, other], motor="huber")

    assert [row[0] for row in rows] == ["huber_tth"]
    assert other.user_readback.calls == []


def test_count_prints_without_display_missed(capsys) -> None:
    _report_missed(["a", "b"], display_missed=False)
    out = capsys.readouterr().out
    assert "2 motors could not be read" in out
    assert "display_missed=True" in out
    assert "['a', 'b']" not in out


def test_display_missed_lists_names(capsys) -> None:
    _report_missed(["b", "a"], skipped=["t"], display_missed=True)
    out = capsys.readouterr().out
    assert "['a', 'b']" in out
    assert "not\nmotor records" in out or "motor records" in out
    assert "['t']" in out


def test_wax_signature_is_backward_compatible() -> None:
    params = list(inspect.signature(wax).parameters.items())
    names = [name for name, _ in params[:4]]
    assert names == ["scan", "motor", "device", "display_missed"]

    defaults = {name: p.default for name, p in params}
    assert defaults["scan"] is None
    assert defaults["motor"] is None
    assert defaults["device"] == "motor"
    assert defaults["display_missed"] is False
    assert defaults["timeout"] == PROBE_TIMEOUT


def test_motor_fields_match_epics_motor() -> None:
    assert MOTOR_FIELDS == (
        "user_readback",
        "low_limit_travel",
        "high_limit_travel",
    )
