"""
Sample-alignment routine modelled after a real beamline macro.

Scans the table x and y motors of the 9-T magnet stage, centers on the
absorption peak via :func:`cen`, and offers a ``check_position`` retry
loop that re-runs the alignment until the position settles within a
tolerance.  Lift the patterns straight into your own macro.
"""

from bluesky.plan_stubs import sleep
from id4_common.macros.macros_api import *  # noqa: F401, F403

magnet = oregistry.find("magnet911")  # noqa: F405
energy = oregistry.find("energy")  # noqa: F405


def align_x(start=-0.015, end=0.015, npts=60, dwell=0.2):
    """Scan tab.x and move to the FWHM midpoint."""
    yield from lup(magnet.tab.x, start, end, npts, dwell)  # noqa: F405
    yield from cen(magnet.tab.x)  # noqa: F405


def align_y(start=-0.015, end=0.015, npts=60, dwell=0.2):
    """Scan tab.y and move to the FWHM midpoint."""
    yield from lup(magnet.tab.y, start, end, npts, dwell)  # noqa: F405
    yield from cen(magnet.tab.y)  # noqa: F405


def align_xy(start=-0.015, end=0.015):
    """Run align_x then align_y at the current energy."""
    yield from align_x(start, end)
    yield from align_y(start, end)


def check_position(tolerance=0.001, wait_time=30, max_tries=10):
    """Re-align until x and y stop moving by more than ``tolerance``.

    Useful when the sample is drifting (e.g. after a field ramp).  Sleeps
    ``wait_time`` between attempts and gives up after ``max_tries``.
    """
    xi = magnet.tab.x.position
    yi = magnet.tab.y.position

    for i in range(max_tries):
        yield from align_xy()
        xn = magnet.tab.x.position
        yn = magnet.tab.y.position

        print(f"\n attempt #{i + 1}")
        print(f"   x: {xi:.5f} -> {xn:.5f}  (dx = {xn - xi:+.5f})")
        print(f"   y: {yi:.5f} -> {yn:.5f}  (dy = {yn - yi:+.5f})")

        if abs(xn - xi) < tolerance and abs(yn - yi) < tolerance:
            print("   settled.")
            return

        xi, yi = xn, yn
        print(f"   sleeping {wait_time} s before re-trying...")
        yield from sleep(wait_time)

    print(f"max_tries={max_tries} hit without settling.")
