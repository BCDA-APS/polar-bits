"""
HKL map + center on a Bragg peak.

For a known peak around (h0, k0, l0), runs a small ``hklscan`` sweep
along H, then ``cen(h)`` to refine the H position.  Repeats for K and L
to lock down the orientation in three quick scans.
"""

from id4_common.macros.macros_api import *  # noqa: F401, F403


def refine_hkl(h0, k0, l0, half_window=0.05, npts=51, dwell=0.5):
    """Scan h/k/l one at a time around (h0, k0, l0) and center on each."""
    yield from hscan(  # noqa: F405
        h0 - half_window, h0 + half_window, npts, dwell
    )
    yield from cen(positioner=oregistry.find("h"))  # noqa: F405

    yield from kscan(  # noqa: F405
        k0 - half_window, k0 + half_window, npts, dwell
    )
    yield from cen(positioner=oregistry.find("k"))  # noqa: F405

    yield from lscan(  # noqa: F405
        l0 - half_window, l0 + half_window, npts, dwell
    )
    yield from cen(positioner=oregistry.find("l"))  # noqa: F405


def hkl_grid_map(h0, k0, l0, span=0.05, npts=21, dwell=0.5):
    """2-D ``hklscan`` from (h-span, k0, l0) to (h+span, k+span, l0).

    Uses :func:`hklscan` which sweeps the three pseudo axes along a
    straight line in reciprocal space.  After the scan, run
    ``RE(cen())`` from the prompt to move to the FWHM midpoint of the
    largest-range axis.
    """
    yield from hklscan(  # noqa: F405
        h0 - span,
        h0 + span,
        k0,
        k0 + span,
        l0,
        l0,
        npts,
        dwell,
    )
