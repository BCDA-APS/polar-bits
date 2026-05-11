"""
Overnight field-dependent XMCD sequence on the 9-T magnet (4-ID-H).

Pattern: ramp the magnet to a target, settle, re-align (the field
ramp shifts the sample), measure XMCD at L2 and L3, then ramp the
field through the negative polarity and repeat.  Designed to be
``RE(overnight_field_sweep([3.0, -3.0]))``-able.
"""

from bluesky.plan_stubs import sleep
from id4_common.macros.macros_api import *  # noqa: F401, F403

# Adjust if you split align_routine / xmcd_at_two_edges into your own
# files; pulling them in by name keeps this script self-documenting.
from .align_routine import align_xy, check_position  # noqa: F401
from .xmcd_at_two_edges import measure_xmcd, move_to_edge  # noqa: F401

magnet = oregistry.find("magnet911")  # noqa: F405


def settle_at_field(target, settle_seconds=300):
    """Ramp to ``target`` Tesla and wait for the field to stabilise."""
    yield from mv(magnet.ps.field, target)  # noqa: F405
    print(f"Field at {target} T; settling for {settle_seconds} s.")
    yield from sleep(settle_seconds)


def field_point(field, num_per_edge=5, dwell=5, edges=("L2", "L3")):
    """One field point: settle, re-align, measure at every edge in ``edges``."""
    yield from settle_at_field(field)
    yield from align_xy(-0.2, 0.2)
    yield from check_position(tolerance=0.0005, wait_time=60, max_tries=20)

    for name in edges:
        yield from move_to_edge(name)
        yield from measure_xmcd(
            name,
            num=num_per_edge,
            time=dwell,
            align_first=True,
            align_plan=align_xy,
        )


def overnight_field_sweep(targets, num_per_edge=9, dwell=5):
    """Visit every field in ``targets``; finish back at zero field."""
    for f in targets:
        yield from field_point(f, num_per_edge=num_per_edge, dwell=dwell)
    yield from mv(magnet.ps.field, 0)  # noqa: F405
