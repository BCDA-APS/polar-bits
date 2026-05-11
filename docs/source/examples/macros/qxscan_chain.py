"""
Chain ``qxscan`` over a list of edges.

The qxscan plan handles one absorption edge at a time.  This script
shows two related patterns:

- ``qxscan_chain`` — iterate over an explicit list of (label, energy)
  pairs.  Pass ``lockin=True`` for XMCD-style scans.
- ``qxscan_setup_then_run`` — interactively reconfigure the
  ``qxscan_setup`` device's pre/edge/post regions before running.
"""

from id4_common.macros.macros_api import *  # noqa: F401, F403

qxscan_setup = oregistry.find("qxscan_setup")  # noqa: F405

EDGES = [
    ("Tb_L3", 7.515),
    ("Tb_L2", 8.253),
]


def qxscan_chain(time=5, lockin=False, edges=EDGES, num=1):
    """Run ``num`` qxscans at every (label, energy) pair in ``edges``."""
    for label, energy_keV in edges:
        for _ in range(num):
            print(f"\n=== qxscan @ {label} ({energy_keV} keV) ===")
            yield from qxscan(  # noqa: F405
                energy_keV, time, lockin=lockin
            )


def qxscan_setup_then_run(label, energy_keV, time=5, lockin=False):
    """Re-prompt ``qxscan_setup`` then run one qxscan at the given edge.

    The interactive call regenerates ``qxscan_setup.energy_list`` /
    ``factor_list`` from the current pre/edge/post regions, so this is
    the right entry point when you want to change the scan grid before
    measuring.
    """
    qxscan_setup()
    print(f"\n=== qxscan @ {label} ({energy_keV} keV) ===")
    yield from qxscan(energy_keV, time, lockin=lockin)  # noqa: F405
