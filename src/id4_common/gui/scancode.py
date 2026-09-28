"""Build a scan-plan call from form values.

Shared by the Scan tab, which runs one scan now, and the Macro tab, which
writes one into a plan.  The rule worth keeping in one place is the argument
order, which differs between the plans and is silent when got wrong::

    ascan(motor, start, stop, ..., num_points, time)     # len % 3 == 2
    grid_scan(motor, start, stop, num, ..., time)        # len % 4 == 1
    hscan(start, stop, num_points, time)                 # axis is implicit
    hklscan(h1, h2, k1, k2, l1, l2, num_points, time)    # three implicit axes

Every numeric slot is a **string**.  The Scan tab formats its spin-box floats
before calling; the Macro tab passes its free-text fields straight through, so
a loop variable (``start`` = ``centre - 0.1``) survives into the generated code.

POLAR's reciprocal-space plans are the reason this module grew a third shape.
``hscan``/``kscan``/``lscan``/``th2th``/``psiscan``/``hklscan`` take **no axis
argument** -- the axis is in the plan's name, and the plan finds the active
diffractometer itself.  Modelling them as "an axis row whose axis is fixed"
keeps one code path in both tabs; the alternative, a special case per plan,
is exactly the kind of silent argument-order bug this module exists to
prevent.
"""


class Plan:
    """How one scan plan's positional arguments are laid out.

    ``takes_axes``
        Whether the caller chooses the axes.  False for ``count``/``qxscan``,
        which take no trajectory at all, and for the fixed-axis plans, whose
        axes are in their names.
    ``per_axis_points``
        Whether each axis carries its own point count (a mesh) or they share
        one (a trajectory).
    ``fixed_axes``
        Labels for rows whose axis is implicit.  These emit ``start, stop``
        only -- no axis name -- and the labels are shown in the form so the
        operator can see which is which.
    ``scalar_label``
        For a plan with no rows, what its single leading number is.
    ``scalar_points``
        Whether that leading number *is* a point count.  ``qxscan``'s is an
        edge energy in keV: a float, and no basis for a duration estimate,
        since how many points it visits comes from ``qxscan_params()``.
    ``note``
        Shown under the form.  Only where a plan has a precondition the
        argument list does not express.
    """

    def __init__(
        self,
        takes_axes=True,
        per_axis_points=False,
        fixed_axes=(),
        scalar_label="Points",
        scalar_points=True,
        note=None,
    ):
        """Record one plan's argument layout."""
        self.takes_axes = takes_axes
        self.per_axis_points = per_axis_points
        self.fixed_axes = tuple(fixed_axes)
        self.scalar_label = scalar_label
        self.scalar_points = scalar_points
        self.note = note

    @property
    def has_rows(self):
        """Whether the form shows start/stop rows for this plan."""
        return self.takes_axes or bool(self.fixed_axes)


#: Plan name -> layout.  The order is the order the plan chooser shows.
#:
#: ``dichro``, ``lockin``, ``vortex_sgz`` and ``per_step`` are deliberately not
#: offered here.  They change what a point *is* rather than where the points
#: are, they interact with each other, and getting one wrong costs a scan --
#: they belong in the console or in a macro's Code component, with a person
#: who knows why they are on.
PLANS = {
    "count": Plan(takes_axes=False, scalar_label="Readings"),
    "ascan": Plan(),
    "lup": Plan(),
    "grid_scan": Plan(per_axis_points=True),
    "rel_grid_scan": Plan(per_axis_points=True),
    "th2th": Plan(takes_axes=False, fixed_axes=("2theta",)),
    "hscan": Plan(takes_axes=False, fixed_axes=("h",)),
    "kscan": Plan(takes_axes=False, fixed_axes=("k",)),
    "lscan": Plan(takes_axes=False, fixed_axes=("l",)),
    "hklscan": Plan(takes_axes=False, fixed_axes=("h", "k", "l")),
    "psiscan": Plan(
        takes_axes=False,
        fixed_axes=("psi",),
        note=(
            "Runs at the current (h, k, l) in a psi_constant mode. Set the "
            "mode and the psi reference in the HKL tab first."
        ),
    ),
    "qxscan": Plan(
        takes_axes=False,
        scalar_label="Edge energy (keV)",
        scalar_points=False,
        note="Run qxscan_params() in the console first — it sets the energy points.",
    ),
}

#: Plans whose points lie in reciprocal space, so ``fixq`` is meaningless (the
#: scan *is* the trajectory) and the checkbox is hidden.
NO_FIXQ = frozenset({"hscan", "kscan", "lscan", "hklscan", "psiscan", "count"})


#: ``ascan``/``lup`` hand their arguments to bluesky's ``scan()``, which takes
#: any number of motors, so a third axis is a real trajectory.  The grid plans
#: accept more dimensions too, but the Scan plot's live image is 2D
#: (``rows, columns = shape``), so a third grid axis would be silently
#: collapsed onto the first two -- worse than not offering it.
MAX_TRAJECTORY_AXES = 3
MAX_GRID_AXES = 2

#: Label for the checkbox that reveals each axis row after the first.
AXIS_ORDINALS = ("", "Second axis", "Third axis")


def plan(name):
    """Return the :class:`Plan` for *name*, defaulting to the ``ascan`` shape."""
    return PLANS.get(name) or Plan()


def plan_shape(name):
    """Return ``(takes_axes, per_axis_points)`` for *name*."""
    spec = plan(name)
    return spec.takes_axes, spec.per_axis_points


def fixed_axes(name):
    """Return the implicit axis labels for *name*, or an empty tuple."""
    return plan(name).fixed_axes


def takes_fixq(name):
    """Whether the ``fixq`` checkbox applies to *name*."""
    spec = plan(name)
    return spec.has_rows and name not in NO_FIXQ


def axis_limit(name):
    """Return how many axis rows *name* may be given in the GUI."""
    spec = plan(name)
    if spec.fixed_axes:
        return len(spec.fixed_axes)
    if not spec.takes_axes:
        return 0
    return MAX_GRID_AXES if spec.per_axis_points else MAX_TRAJECTORY_AXES


def active_axes(name, enabled):
    """Return how many axis rows are in play.

    *enabled* is the checked state of the boxes that add rows 2, 3, ...  Each
    extra row needs the one before it, so the count stops at the first
    unchecked box -- and at the plan's own ceiling.  A fixed-axis plan has no
    boxes: every one of its rows is always in play.
    """
    limit = axis_limit(name)
    if not limit:
        return 0
    if fixed_axes(name):
        return limit
    count = 1
    for index, checked in enumerate(enabled, start=1):
        if index >= limit or not checked:
            break
        count += 1
    return count


def format_number(value):
    """Format a float for generated code, without trailing noise."""
    value = round(float(value), 6)
    if value == int(value):
        return str(int(value))
    return repr(value)


def scan_arguments(name, rows, shared_points, time_text):
    """Return ``(args, problem)`` -- the positional arguments, as strings.

    *rows* is a sequence of ``(axis, start, stop, points)`` string tuples; the
    ``points`` entry is ignored for the plans that share one point count, and
    the ``axis`` entry for the fixed-axis plans, where it is a label rather
    than something to pass.  *problem* is a message when the form cannot make a
    valid call, in which case *args* is None.
    """
    spec = plan(name)
    time_text = str(time_text).strip()
    if not time_text:
        return None, "Give a time per point."

    if not spec.has_rows:
        points = str(shared_points).strip()
        if not points:
            return None, f"Give a value for {spec.scalar_label.lower()}."
        return [points, time_text], None

    if not rows:
        return None, "Choose an axis."

    args = []
    for axis, start, stop, points in rows:
        axis = str(axis).strip()
        start = str(start).strip()
        stop = str(stop).strip()
        if not axis:
            return None, "Choose an axis."
        if not start or not stop:
            return None, f"{axis}: give a start and a stop."
        # A single-row scan with start == stop moves nothing, which is a
        # mistake.  A multi-row *fixed*-axis plan is different: hklscan sweeps
        # one line through reciprocal space, and holding h and k while l runs
        # is the ordinary case, not an error.  The whole trajectory is checked
        # after the loop instead.
        if start == stop and len(rows) == 1:
            return None, f"{axis}: start and stop are the same."
        # A fixed-axis plan names its axis in the plan name, so the label is
        # for the operator only -- passing it would be a positional argument
        # the plan does not have.
        if not spec.fixed_axes:
            args.append(axis)
        args += [start, stop]
        if spec.per_axis_points:
            points = str(points).strip()
            if not points:
                return None, f"{axis}: give a number of points."
            args.append(points)

    axes = [str(row[0]).strip() for row in rows]
    if not spec.fixed_axes and len(axes) != len(set(axes)):
        return None, "Each axis must be a different one."
    if len(rows) > 1 and all(
        str(start).strip() == str(stop).strip() for _a, start, stop, _p in rows
    ):
        return None, "Nothing moves — every start equals its stop."

    if not spec.per_axis_points:
        points = str(shared_points).strip()
        if not points:
            return None, "Give a number of points."
        args.append(points)
    args.append(time_text)
    return args, None


def format_scan_call(
    name, rows, shared_points, time_text, fixq=False, detectors=None
):
    """Return ``(call_text, problem)`` for a bare ``plan(...)`` call.

    The caller decides what to do with it: the Scan tab wraps it in ``RE(...)``,
    the Macro tab prefixes ``yield from``.

    *detectors* is a list of device names, or None to leave the argument out.
    Omitting it matters -- passing an explicit list makes the plan skip
    ``_setup_detectors()``, which is where the negative-time validation lives.
    """
    args, problem = scan_arguments(name, rows, shared_points, time_text)
    if problem:
        return None, problem

    keywords = []
    if detectors:
        keywords.append(f"detectors=[{', '.join(detectors)}]")
    if fixq and takes_fixq(name):
        keywords.append("fixq=True")
    return f"{name}({', '.join(args + keywords)})", None
