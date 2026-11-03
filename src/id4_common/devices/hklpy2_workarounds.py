"""
Temporary workarounds for hklpy2 solver problems.

TEMPORARY: everything in this module is expected to be removed after an
hklpy2 update. See the comment above ``_ThreadSafeSolverMixin`` for what to
remove and when, and the "Temporary hklpy2 workarounds" section of
CLAUDE.md.

Kept apart from ``polar_diffractometer`` (which builds ``hkl_soleil``
classes at import time and so needs libhkl) so it can be tested anywhere.
"""

import functools
import threading

# Private hklpy2 API, used only by the temporary _ThreadSafeSolverMixin.
from hklpy2.utils import _SolverDirty
from ophyd import Device


# TEMPORARY (hklpy2 workaround). The whole class below is a stopgap for two
# hklpy2 problems and is expected to be removed after an hklpy2 update:
#   (a) _on_wavelength_change and its assignment in __init__: remove once
#       hklpy2's beam callback (incident.py ``_wavelength_changed``) flags
#       only ``_SolverDirty.WAVELENGTH`` instead of calling
#       ``request_solver_update(True)``.
#   (b) the lock (_solver_lock, _locked, _solver_methods, the restore
#       override): remove once hklpy2 serializes ``Core`` itself.
# When both are gone, delete this module and
# tests/test_solver_thread_safety.py, drop the mixin from the bases of the
# six diffractometer classes (polar_diffractometer.py and
# sim_diffractometer.py), and remove the CLAUDE.md section "Temporary
# hklpy2 workarounds".
class _ThreadSafeSolverMixin(Device):
    """Serialize hklpy2 solver access; re-push only the wavelength on change.

    Why: ophyd runs ``inverse()`` on the CA monitor thread for every
    real-motor readback while plans and the console call ``forward()`` /
    ``calc_UB()`` on other threads, and hklpy2 has no locking. hklpy2's beam
    callback also marks every solver domain dirty, so each wavelength change
    rebuilds the solver sample and replays the reflections (each one swaps
    the solver wavelength). Together these can leave the solver at an
    orienting reflection's wavelength or solve from the wrong start geometry.

    How to apply: list it first among the bases so its ``__init__`` runs
    after hklpy2 has built ``self.core``.

    TODO: remove once hklpy2 narrows the callback and serializes ``Core``
    (https://github.com/bluesky/hklpy2/issues/436).
    """

    #: Core methods that read or write the solver, or its dirty flags.
    _solver_methods = (
        "forward",
        "inverse",
        "calc_UB",
        "update_solver",
        "request_solver_update",
        "add_reflection",
        "add_sample",
        "refine_lattice",
    )

    def __init__(self, *args, **kwargs):
        """Construct the diffractometer, then wrap its solver entry points."""
        super().__init__(*args, **kwargs)
        self._solver_lock = threading.RLock()
        # Instance attributes shadow the Core methods, so hklpy2's internal
        # self.update_solver() / self.request_solver_update() calls are
        # locked too.
        for name in self._solver_methods:
            setattr(self.core, name, self._locked(getattr(self.core, name)))
        # DiffractometerBase.__init__ bound core.request_solver_update.
        self.beam.wavelength_updated_func = self._on_wavelength_change

    def _locked(self, method):
        """Return ``method`` wrapped in the solver lock."""

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            with self._solver_lock:
                return method(*args, **kwargs)

        return wrapper

    def _on_wavelength_change(self, *_):
        """Beam callback: only the wavelength needs re-pushing."""
        self.core.request_solver_update(_SolverDirty.WAVELENGTH)

    def restore(self, *args, **kwargs):
        """Restore a configuration while holding the solver lock."""
        with self._solver_lock:
            return super().restore(*args, **kwargs)
