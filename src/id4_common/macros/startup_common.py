from id4_common.utils.session_state import restore_session_state
from id4_common.utils.experiment_utils import experiment_resume

experiment_resume()
status = restore_session_state()
for knob, msg in status.items():
    print(f"  {knob:18}  {msg}")
