"""One-line session-restart helper.

Importing this module runs the canonical post-restart sequence:
``experiment_resume()`` (auto-discovers the experiment snapshot from
the cwd or the most recent run in the catalog) followed by
``restore_session_state()`` (re-applies every auto-saved setup knob —
PR setup, energy tracking, undulator offsets, counters, qxscan
params). The per-knob status dict is printed so the user can see what
was applied / skipped / failed.
"""

from id4_common.utils.experiment_utils import experiment_resume
from id4_common.utils.session_state import restore_session_state

experiment_resume()
status = restore_session_state()
for knob, msg in status.items():
    print(f"  {knob:18}  {msg}")
