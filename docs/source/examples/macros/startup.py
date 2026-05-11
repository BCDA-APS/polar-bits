"""
Session-restart template — recoverable startup macro.

Use this when bluesky needs to be restarted mid-experiment::

    %run startup.py

Restores the per-experiment knobs (undulator offsets / deadbands,
energy tracking selection, ``pr_setup``, ``counters.plotselect``,
qxscan setup) that were auto-saved into ``RE.md["session_state"]`` by
the regular setup helpers (``pr_setup``, ``energy.tracking_setup``,
``counters.plotselect``, ``undulator_setup``,
``qxscan_setup.load_params_json``).

Anything not auto-saved (vortex electronics choice, custom motor
shortcuts, …) goes below the ``# --- hand-set after this line ---``
marker so a future restart still picks it up.
"""

from matplotlib import pyplot as plt

from id4_common.macros.macros_api import *  # noqa: F401, F403
from id4_common.utils.experiment_utils import experiment_load_from_scan
from id4_common.utils.session_state import restore_session_state

plt.ion()  # interactive plots

experiment_load_from_scan()  # restores experiment metadata from cat[-1]

status = restore_session_state()
print("\nSession-state restore:")
for knob, msg in status.items():
    print(f"  {knob:18}  {msg}")


# --- hand-set after this line --------------------------------------------
#
# Things that aren't (yet) auto-saved into RE.md.  Edit per experiment.

# vortex = load_vortex("xspress4")
# vortex.auto_save_on()
# vortex._sleep_after_trigger = 0.1

# from motor_shortcuts import *
