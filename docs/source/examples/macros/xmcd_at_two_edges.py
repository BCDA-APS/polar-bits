"""
XMCD measurement at two absorption edges (e.g. Tb L3 / L2).

Shows two patterns:

- ``move_to_edge`` — group the energy + analyzer + preamp moves needed
  to switch between two edges in one yield-from.
- ``measure_xmcd`` — wrap a small sequence (optional alignment + N
  averaged ``qxscan`` runs) so callers can do
  ``RE(measure_xmcd("L3", num=5))`` or chain it from a longer plan.
"""

from id4_common.macros.macros_api import *  # noqa: F401, F403

energy = oregistry.find("energy")  # noqa: F405
pr2 = oregistry.find("pr2")  # noqa: F405
preamp_i = oregistry.find("preamp_4idhI1")  # noqa: F405


# Each entry: (energy in keV, pr2 PZT offset in deg, qxscan edge in keV,
# preamp sensitivity value, preamp sensitivity unit).
EDGES = {
    "L3": (7.520, 0.012, 7.515, "2", "uA/V"),
    "L2": (8.255, 0.009, 8.253, "5", "uA/V"),
}


def move_to_edge(name):
    """Move energy + PR2 phase + preamp gain to one of the named edges."""
    e, pzt_offset, _, sens_value, sens_unit = EDGES[name]
    yield from mv(  # noqa: F405
        energy,
        e,
        pr2.pzt.offset_degrees,
        pzt_offset,
    )
    yield from mv(  # noqa: F405
        preamp_i.sensitivity_value,
        sens_value,
        preamp_i.sensitivity_unit,
        sens_unit,
    )
    yield from mv(preamp_i.set_all, 1)  # noqa: F405


def measure_xmcd(edge, num=1, time=1, align_first=False, align_plan=None):
    """Measure ``num`` averaged qxscans at ``edge``.

    If ``align_first`` is True, calls ``align_plan`` (defaults to your
    own ``align_xy()`` from align_routine.py) before each scan.
    """
    _, _, edge_energy, _, _ = EDGES[edge]
    for _ in range(num):
        if align_first and align_plan is not None:
            yield from align_plan()
        yield from qxscan(  # noqa: F405
            edge_energy, time, lockin=True
        )


def xmcd_l2_l3(num=5, time=1, align_first=False, align_plan=None):
    """Convenience: measure num scans at L2 then num scans at L3."""
    yield from move_to_edge("L2")
    yield from measure_xmcd(
        "L2", num=num, time=time, align_first=align_first, align_plan=align_plan
    )
    yield from move_to_edge("L3")
    yield from measure_xmcd(
        "L3", num=num, time=time, align_first=align_first, align_plan=align_plan
    )
