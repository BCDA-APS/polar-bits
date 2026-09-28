"""Kernel-side helpers for the HKL tab.

These are installed in the kernel as part of the bootstrap cell.  They exist
here rather than in the GUI because ``user_expressions`` evaluates expressions
only -- it cannot run a ``try``/``except`` -- and almost every hklpy2 call can
raise on an unoriented or unreachable configuration.

The API mirrors ``id4_common.utils.hkl_utils``, which is the reference for the
call sequences.  Its console entry points are not called from here, because
almost all of them act on whichever diffractometer is *active* and prompt for
what they were not told, while the tab has to be able to show either device and
can never prompt.

Everything returned is plain Python (floats coerced off numpy) so the poller's
``ast.literal_eval`` round trip works.

**Three things differ from a Eulerian six-circle** and shape most of what
follows.  POLAR's ``APS POLAR`` geometry has six real axes ``tau, mu, chi, phi,
gamma, delta``; its mode names are **space-separated** (``"psi constant
horizontal"``, not ``psi_constant_horizontal``), so every test against a mode
name goes through :func:`_gui_hkl_mode_key`; and there is **no ``q``
engine** -- ``hkl-engine-list-error-quark: this engine list does not contain
this engine "q"`` -- so 2theta is computed here from ``UB`` rather than read off
a helper geometry.

The last one is worth stating precisely, because it is the sort of thing that
is right by luck or wrong by a factor of 2π.  hklpy2's ``UB`` is in the 2π
convention: ``|UB · (h, k, l)| = 2π/d``, checked against Bragg's law on a cubic
lattice for (100), (110) and (200).  So ``2θ = 2·asin(|UB·hkl|·λ/4π)``.
"""

from . import config

#: Diffractometers the tab may act on, in selector order.  The ``*_psi``
#: geometries are used internally for the psi readout only and are not offered.
DIFFRACTOMETERS = list(config.DIFFRACTOMETERS)

#: Diffractometer -> the psi-engine geometry on the same motors.  Per device,
#: because POLAR has two diffractometers and each has its own; ``hkl_utils``
#: finds it by the same convention, ``oregistry.find(name + "_psi")``.
PSI_GEOMETRY = dict(config.PSI_GEOMETRY)

#: Poller keys.
POSITION_KEY = "hkl_position"
STATE_KEY = "hkl_state"

#: Emitted ahead of the helpers so the map is a literal in the kernel rather
#: than something interpolated into every function that needs it.  Built with
#: ``repr`` for the same reason ``_gui_mcp`` sends its payload that way: a
#: device name reaches the kernel as data, never as code.
_PSI_PREAMBLE = f"_GUI_HKL_PSI = {PSI_GEOMETRY!r}\n\n\n"

_HELPERS_CODE = '''\
def _gui_hkl_f(value, default=None):
    """Coerce a possibly-numpy value to a plain float."""
    try:
        return float(value)
    except Exception:
        return default


def _gui_hkl_dev(name):
    """Return the named diffractometer from the registry."""
    return oregistry.find(name)


def _gui_hkl_psi_dev(name):
    """Return the psi-engine geometry that shares *name*'s motors."""
    return _gui_hkl_dev(_GUI_HKL_PSI[name])


def _gui_hkl_mode_key(mode):
    """Normalise a mode name for matching.

    POLAR's solver spells its modes with spaces -- ``"psi constant
    horizontal"``, ``"4-circles bissecting horizontal"`` -- where the Eulerian
    geometries use underscores.  Every test in this module compares against
    this form, so a mode is recognised whichever way its geometry writes it.
    Failing that test is silent in the worst way: a psi that reports "can only
    be fixed in a psi_constant mode" while sitting in exactly such a mode.
    """
    return str(mode).replace(" ", "_").replace("-", "_").lower()


def _gui_hkl_psi_modes(dev):
    """The device's psi_constant modes, whatever their spelling."""
    try:
        return [m for m in dev.core.modes if "psi_constant" in _gui_hkl_mode_key(m)]
    except Exception:
        return []


def _gui_hkl_active():
    """Name of the *active* diffractometer, the one the plans act on.

    POLAR keeps one selected device -- ``hklpy2.user``'s -- and the
    reciprocal-space plans (``hscan``, ``hklscan``, ``psiscan``, ``th2th``)
    find it themselves rather than taking it as an argument.  The tab can
    display either device, so it has to be able to say which one is live.
    """
    try:
        from hklpy2.user import get_diffractometer

        dev = get_diffractometer()
        return None if dev is None else dev.name
    except Exception:
        return None


def _gui_hkl_set_active(name):
    """Make *name* the active diffractometer.

    Deliberately a separate, explicit action rather than a side effect of the
    tab's selector: ``change_diffractometer`` also applies that device's axis
    constraints and pushes its aliases (``mu``, ``chi``, ``h``, ``cryox``, ...)
    into the session namespace, which is too much to happen because somebody
    wanted to *look* at the other diffractometer.
    """
    if name not in _GUI_HKL_PSI:
        return f"Unknown diffractometer {name!r}."
    try:
        change_diffractometer(name)
    except Exception as exc:
        return f"Could not switch diffractometer: {exc}"
    return f"Active diffractometer: {_gui_hkl_active()}"


def _gui_hkl_lattice(sample):
    """The six lattice constants of *sample*, as plain floats."""
    return {
        _p: _gui_hkl_f(getattr(sample.lattice, _p))
        for _p in ("a", "b", "c", "alpha", "beta", "gamma")
    }


def _gui_hkl_mirror_sample(src, dst):
    """Copy *src*'s lattice and UB onto *dst*, the psi helper geometry.

    Both halves are needed.  The psi engine solves against *dst*'s own
    sample, which starts life as a default cubic one, and hklpy2 pushes the
    whole sample -- lattice included -- to the solver; a UB copied onto a
    mismatched lattice gives a psi computed for the wrong crystal.

    **Lattice before UB.**  Assigning a lattice parameter flags
    ``_SolverDirty.SAMPLE | _SolverDirty.UB`` because some backends discard
    U/UB when the sample is re-pushed, so the other order can throw the
    matrix away again.

    Each half is skipped when it already matches: this runs on the 1 Hz
    position poll and every assignment flags the solver dirty, forcing a
    re-sync that is pure cost when nothing changed.

    The lattice is copied parameter by parameter rather than by assigning
    ``src.sample.lattice`` itself: ``Sample.lattice``'s setter rebinds
    ``_on_change`` on whatever object it is given, so sharing one Lattice
    would redirect the source sample's own change notification to *dst*.
    """
    want = _gui_hkl_lattice(src.sample)
    if _gui_hkl_lattice(dst.sample) != want:
        for _p, _v in want.items():
            if _v is not None:
                setattr(dst.sample.lattice, _p, _v)
    ub = [[_gui_hkl_f(_v) for _v in _row] for _row in src.sample.UB]
    if [[_gui_hkl_f(_v) for _v in _row] for _row in dst.sample.UB] != ub:
        dst.sample.UB = ub


def _gui_hkl_two_theta(dev):
    """Scattering angle at the current hkl, in degrees, from UB.

    The Eulerian geometries carry a ``q`` engine and this is one ``inverse()``
    call on it.  ``APS POLAR`` has no such engine -- libhkl answers *this
    engine list does not contain this engine "q"* -- so |Q| is taken from the
    orientation matrix instead:

        |Q| = |UB . (h, k, l)| = 2*pi/d        2*theta = 2 asin(|Q| lambda / 4 pi)

    The 2*pi is hklpy2's convention for UB, not an assumption: checked against
    Bragg's law on a 4 A cubic lattice for (100), (110) and (200).

    Written out rather than handed to numpy because the whole point of these
    helpers is that they return plain Python across a ``literal_eval`` round
    trip, and a 3x3 by 3 product is three lines.
    """
    import math

    try:
        _ub = [[_gui_hkl_f(_v) for _v in _row] for _row in dev.sample.UB]
        _hkl = [
            _gui_hkl_f(getattr(dev, _f).position)
            for _f in dev.pseudo_positioners._fields
        ]
        _lambda = _gui_hkl_f(dev.beam.wavelength.get())
    except Exception:
        return None
    if len(_ub) != 3 or len(_hkl) != 3 or not _lambda:
        return None
    if any(_v is None for _row in _ub for _v in _row) or any(
        _v is None for _v in _hkl
    ):
        return None
    _q = [sum(_ub[_i][_j] * _hkl[_j] for _j in range(3)) for _i in range(3)]
    _arg = math.sqrt(sum(_v * _v for _v in _q)) * _lambda / (4.0 * math.pi)
    if not -1.0 <= _arg <= 1.0:
        return None
    return math.degrees(2.0 * math.asin(_arg))


def _gui_hkl_derived(dev):
    """Return (two_theta, psi, psi_reference) for the current position.

    The psi half mirrors ``hkl_utils._wh()``: the psi geometry needs the main
    diffractometer's sample copied onto it before ``inverse()`` means
    anything.
    """
    psi = None
    reference = {}
    two_theta = _gui_hkl_two_theta(dev)
    try:
        _p = _gui_hkl_psi_dev(dev.name)
        _gui_hkl_mirror_sample(dev, _p)
        psi = _gui_hkl_f(_p.inverse(0).psi)
        reference = {k: _gui_hkl_f(v) for k, v in _p.core.extras.items()}
    except Exception:
        pass
    return two_theta, psi, reference


def _gui_hkl_position(name):
    """Cheap, frequently-polled readout: angles, hkl, 2theta, psi."""
    dev = _gui_hkl_dev(name)
    out = {"device": name}
    try:
        out["pseudos"] = {
            f: _gui_hkl_f(getattr(dev, f).position)
            for f in dev.pseudo_positioners._fields
        }
        out["reals"] = {
            f: _gui_hkl_f(getattr(dev, f).position)
            for f in dev.real_positioners._fields
        }
    except Exception as exc:
        out["error"] = str(exc)
        return out
    out["wavelength"] = _gui_hkl_f(dev.beam.wavelength.get())
    out["energy"] = _gui_hkl_f(dev.beam.energy.get())
    two_theta, psi, reference = _gui_hkl_derived(dev)
    out["two_theta"] = two_theta
    out["psi"] = psi
    out["psi_reference"] = reference
    out["mode"] = dev.core.mode
    return out


def _gui_hkl_state(name):
    """Full orientation state: samples, reflections, modes, UB."""
    dev = _gui_hkl_dev(name)
    state = {"device": name}
    # Which device the reciprocal-space plans will act on, which is not
    # necessarily the one being displayed -- see _gui_hkl_set_active.
    state["active"] = _gui_hkl_active()
    state["real_fields"] = list(dev.real_positioners._fields)
    state["pseudo_fields"] = list(dev.pseudo_positioners._fields)

    samples = {}
    for sname, sample in dev.samples.items():
        try:
            names = sample.lattice.system_parameter_names(0)
            samples[sname] = {
                p: _gui_hkl_f(getattr(sample.lattice, p)) for p in names
            }
        except Exception:
            samples[sname] = {}
    state["samples"] = samples
    state["sample"] = dev.sample.name
    state["lattice_names"] = list(
        dev.sample.lattice.system_parameter_names(0)
    )

    reflections = []
    try:
        order = list(dev.sample.reflections.order)
        for key, ref in dev.sample.reflections.items():
            tag = ""
            if order and key == order[0]:
                tag = "first"
            elif len(order) > 1 and key == order[1]:
                tag = "second"
            reflections.append({
                "key": str(key),
                "pseudos": {k: _gui_hkl_f(v) for k, v in ref.pseudos.items()},
                "reals": {k: _gui_hkl_f(v) for k, v in ref.reals.items()},
                "tag": tag,
            })
    except Exception:
        order = []
    state["reflections"] = reflections
    state["order"] = [str(k) for k in order]

    # Readback PV per real axis, so the GUI can follow a move over Channel
    # Access while the kernel's shell channel is blocked by the move itself.
    # None for a soft axis, which has no PV to watch.  POLAR has no
    # simulated diffractometer, so in practice every axis here has one.
    real_pvs = {}
    for _f in dev.real_positioners._fields:
        _ax = getattr(dev, _f, None)
        _pv = None
        for _attr in ("user_readback", "readback"):
            _sig = getattr(_ax, _attr, None)
            _pv = getattr(_sig, "pvname", None)
            if _pv:
                break
        real_pvs[_f] = _pv
    state["real_pvs"] = real_pvs

    state["mode"] = dev.core.mode
    state["modes"] = list(dev.core.modes)
    try:
        state["constant_axes"] = list(dev.core.constant_axis_names)
    except Exception:
        state["constant_axes"] = []
    try:
        state["presets"] = {k: _gui_hkl_f(v) for k, v in dev.core.presets.items()}
    except Exception:
        state["presets"] = {}
    try:
        state["extras"] = {k: _gui_hkl_f(v) for k, v in dev.core.extras.items()}
    except Exception:
        state["extras"] = {}
    # The mode's extra solver parameters, minus the psi reference vector,
    # which has its own boxes.  In a psi_constant mode this is ['psi'] -- a
    # value the mode holds constant just as surely as it holds mu and nu, but
    # one that never appears in ``constant_axis_names`` because it is not a
    # real axis.  The tab shows these alongside the fixed angles.
    state["extra_axes"] = [
        k for k in state["extras"] if k not in ("h2", "k2", "l2")
    ]
    try:
        state["ub"] = [[_gui_hkl_f(v) for v in row] for row in dev.sample.UB]
    except Exception:
        state["ub"] = []
    two_theta, psi, reference = _gui_hkl_derived(dev)
    state["two_theta"] = two_theta
    state["psi"] = psi
    state["psi_reference"] = reference
    return state


def _gui_hkl_recompute_ub(dev):
    """Recompute UB when two orienting reflections exist.

    ``forward(1, 0, 0)`` afterwards is the workaround documented in
    ``hkl_utils.compute_UB``: without one calculation, a later ``wh()``
    fails.
    """
    order = list(dev.sample.reflections.order)
    if len(order) < 2:
        return "UB not computed: needs two orienting reflections."
    dev.sample.core.calc_UB(order[0], order[1])
    dev.forward(1, 0, 0)
    return f"UB computed from {order[0]} and {order[1]}."


def _gui_hkl_select_sample(name, sample):
    try:
        _gui_hkl_dev(name).sample = sample
        return f"Current sample: {sample}"
    except Exception as exc:
        return f"Could not select sample: {exc}"


def _gui_hkl_add_sample(name, sample, a, b, c, alpha, beta, gamma):
    try:
        _gui_hkl_dev(name).add_sample(
            sample, a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma,
            replace=True,
        )
        return f"Added sample {sample}."
    except Exception as exc:
        return f"Could not add sample: {exc}"


def _gui_hkl_remove_sample(name, sample):
    dev = _gui_hkl_dev(name)
    if sample == dev.sample.name:
        return "The current sample cannot be removed."
    try:
        dev.core.remove_sample(sample)
        return f"Removed sample {sample}."
    except Exception as exc:
        return f"Could not remove sample: {exc}"


def _gui_hkl_set_lattice(name, values):
    """values: {parameter: number}."""
    dev = _gui_hkl_dev(name)
    try:
        for key, value in values.items():
            setattr(dev.sample.lattice, key, float(value))
    except Exception as exc:
        return f"Could not set lattice: {exc}"
    return "Lattice updated. " + _gui_hkl_recompute_ub(dev)


def _gui_hkl_add_reflection(name, pseudos, reals):
    """pseudos/reals are dicts; reals=None uses the current angles."""
    dev = _gui_hkl_dev(name)
    try:
        if reals is None:
            reals = {
                f: getattr(dev, f).position for f in dev.real_positioners._fields
            }
        ordered = [float(reals[f]) for f in dev.real_positioners._fields]
        hkl = tuple(float(pseudos[f]) for f in dev.pseudo_positioners._fields)
        ref = dev.add_reflection(hkl, ordered)
        return f"Added reflection {ref.name}."
    except Exception as exc:
        return f"Could not add reflection: {exc}"


def _gui_hkl_edit_reflection(name, key, pseudos, reals):
    """Reflection.pseudos/.reals are settable, so this edits in place."""
    dev = _gui_hkl_dev(name)
    try:
        ref = dev.sample.reflections[key]
        if pseudos:
            ref.pseudos = {k: float(v) for k, v in pseudos.items()}
        if reals:
            ref.reals = {k: float(v) for k, v in reals.items()}
    except Exception as exc:
        return f"Could not edit reflection: {exc}"
    message = f"Reflection {key} updated."
    if key in list(dev.sample.reflections.order)[:2]:
        message += " " + _gui_hkl_recompute_ub(dev)
    return message


def _gui_hkl_remove_reflection(name, key):
    dev = _gui_hkl_dev(name)
    try:
        if key in list(dev.sample.reflections.order)[:2]:
            return "Cannot remove an orienting reflection; reassign it first."
        dev.sample.reflections.pop(key)
        return f"Removed reflection {key}."
    except Exception as exc:
        return f"Could not remove reflection: {exc}"


def _gui_hkl_set_orienting(name, first, second):
    dev = _gui_hkl_dev(name)
    try:
        refs = dev.sample.reflections
        order = list(refs.order)
        keys = list(refs.keys())
        if first not in keys or second not in keys:
            return "Unknown reflection key."
        if first == second:
            return "The two orienting reflections must differ."
        order[0:1] = [first]
        if len(order) > 1:
            order[1:2] = [second]
        else:
            order.append(second)
        refs.order = order
    except Exception as exc:
        return f"Could not set orienting reflections: {exc}"
    return f"Orienting: {first}, {second}. " + _gui_hkl_recompute_ub(dev)


def _gui_hkl_compute_ub(name):
    try:
        return _gui_hkl_recompute_ub(_gui_hkl_dev(name))
    except Exception as exc:
        return f"Could not compute UB: {exc}"


def _gui_hkl_presets_text(dev):
    """Render the current mode's presets the way the tab shows them."""
    try:
        items = dict(dev.core.presets)
    except Exception:
        return "unavailable"
    return ", ".join(f"{k}={v:g}" for k, v in items.items()) or "none"


def _gui_hkl_set_presets(name, values):
    """Fix (preset) the angles the current mode holds constant.

    ``values`` is ``{axis: number}``; an axis left out has no preset, so
    ``forward()`` falls back to that motor's live position.  Presets change
    *computed* solutions only -- nothing moves.

    hklpy2's ``presets`` setter silently drops any axis that is not constant
    in the current mode, so the names it would have dropped are checked here
    and reported back rather than disappearing without a word.
    """
    dev = _gui_hkl_dev(name)
    try:
        constant = list(dev.core.constant_axis_names)
    except Exception as exc:
        return f"Could not read the constant axes: {exc}"
    try:
        wanted = {k: float(v) for k, v in (values or {}).items()}
    except Exception as exc:
        return f"Fixed angles must be numbers: {exc}"
    ignored = [k for k in wanted if k not in constant]
    try:
        dev.core.presets = {k: v for k, v in wanted.items() if k in constant}
    except Exception as exc:
        return f"Could not set the fixed angles: {exc}"
    message = f"Fixed angles ({dev.core.mode}): {_gui_hkl_presets_text(dev)}"
    if ignored:
        message += (
            " -- ignored " + ", ".join(sorted(ignored))
            + ", not held constant in this mode"
        )
    return message


def _gui_hkl_set_extras(name, values):
    """Set the current mode's extra solver parameters, e.g. psi.

    An extra is not a preset.  A preset is optional -- an axis left out of
    ``core.presets`` follows its motor -- whereas a mode that defines an
    extra always uses it, so there is nothing to leave out and no checkbox
    to untick.

    hklpy2 *raises* ``ConfigurationError`` on an extra the current mode does
    not define, so the names are filtered against ``core.extras`` first: a
    psi sent in the wrong mode is reported rather than taking the whole
    write down with it.
    """
    dev = _gui_hkl_dev(name)
    try:
        known = list(dev.core.extras)
    except Exception as exc:
        return f"Could not read the extra parameters: {exc}"
    try:
        wanted = {k: float(v) for k, v in (values or {}).items()}
    except Exception as exc:
        return f"Extra parameters must be numbers: {exc}"
    ignored = sorted(k for k in wanted if k not in known)
    accepted = {k: v for k, v in wanted.items() if k in known}
    if accepted:
        try:
            dev.core.extras = accepted
        except Exception as exc:
            return f"Could not set the extra parameters: {exc}"
    message = "Fixed " + (
        ", ".join(f"{k}={v:g}" for k, v in accepted.items()) or "nothing"
    )
    if ignored:
        message += (
            " -- ignored " + ", ".join(ignored)
            + f", not used by mode {dev.core.mode}"
        )
    return message


def _gui_hkl_set_fixed(name, presets, extras):
    """Write the mode's fixed angles and its extra parameters together.

    Two different things, written in one call because the tab shows them in
    one block and applies them from one debounce timer -- two separate calls
    would race for the same reply slot and only one message would survive.
    """
    messages = [_gui_hkl_set_presets(name, presets)]
    if extras:
        messages.append(_gui_hkl_set_extras(name, extras))
    return "  ".join(messages)


def _gui_hkl_set_mode(name, mode):
    """Set the mode and freeze the unused detector angle.

    The preset logic follows ``hkl_utils.setmode``: a 'vertical' mode
    holds the horizontal detector (solver 'gamma') at 0 and vice versa,
    translated from solver axis names to this diffractometer's own.

    The detector angle is only defaulted when it has no preset yet.  hklpy2
    keeps presets *per mode* and restores them when a mode is re-selected, so
    assigning a fresh dict here would throw away an angle the user had fixed
    in this mode earlier -- re-picking the mode in the tab would silently undo
    their setting.
    """
    dev = _gui_hkl_dev(name)
    try:
        dev.core.mode = mode
    except Exception as exc:
        return f"Could not set mode: {exc}"

    # POLAR's constant axes agree with this rule: 'psi constant horizontal'
    # holds tau and delta, 'psi constant vertical' holds mu and gamma.  An
    # axis the mode does not hold constant would be dropped silently anyway.
    key = _gui_hkl_mode_key(mode)
    solver_det = None
    if "vertical" in key:
        solver_det = "gamma"
    elif "horizontal" in key:
        solver_det = "delta"

    try:
        axis = None
        if solver_det is not None:
            mapping = dict(
                zip(dev.core.solver_real_axis_names, list(dev.real_positioners._fields))
            )
            axis = mapping.get(solver_det)
        presets = dict(dev.core.presets)
        if axis is not None and axis not in presets:
            presets[axis] = 0
            dev.core.presets = presets
        return f"Mode: {mode} (fixed: {_gui_hkl_presets_text(dev)})"
    except Exception as exc:
        return f"Mode set to {mode}, but presets failed: {exc}"


def _gui_hkl_set_azimuth(name, h2, k2, l2):
    """Write the psi reference vector.

    ``core.extras`` only exists in a psi_constant mode, so this switches into
    each of them, writes, mirrors onto the psi geometry, and restores the
    original mode -- the same dance as ``hkl_utils.setaz``.  Written in every
    such mode because extras are stored *per mode*: a reference set only in
    the horizontal one would be missing the moment the operator picked the
    vertical one.

    The modes are found by matching rather than named, since POLAR spells them
    with spaces and the Eulerian geometries with underscores.
    """
    dev = _gui_hkl_dev(name)
    original = dev.core.mode
    extras = {"h2": float(h2), "k2": float(k2), "l2": float(l2)}
    try:
        candidates = _gui_hkl_psi_modes(dev)
        if not candidates:
            return f"{name} has no psi_constant mode to hold a reference."
        for candidate in candidates:
            dev.core.mode = candidate
            dev.core.extras = extras
        try:
            _gui_hkl_psi_dev(name).core.extras = extras
        except Exception:
            pass
        return f"Psi reference = {h2} {k2} {l2}"
    except Exception as exc:
        return f"Could not set psi reference: {exc}"
    finally:
        try:
            dev.core.mode = original
        except Exception:
            pass


def _gui_hkl_set_psi(name, psi):
    """Freeze psi for the psi_constant modes (``hkl_utils.freeze``)."""
    dev = _gui_hkl_dev(name)
    if "psi_constant" not in _gui_hkl_mode_key(dev.core.mode):
        return f"Psi can only be fixed in a psi_constant mode (now {dev.core.mode})."
    try:
        dev.core.extras = {"psi": float(psi)}
        return f"Psi fixed at {psi}"
    except Exception as exc:
        return f"Could not fix psi: {exc}"


def _gui_hkl_calc(name, h, k, l, psi=None, presets=None):
    """Compute real angles for an hkl, optionally fixing psi and angles first.

    ``presets`` is re-sent with every calculation rather than relied upon from
    an earlier write: the tab applies fixed angles on a debounce timer, so
    pressing Calculate straight after typing could otherwise solve against the
    previous value.
    """
    dev = _gui_hkl_dev(name)
    out = {"device": name, "h": h, "k": k, "l": l}
    if presets is not None:
        try:
            constant = list(dev.core.constant_axis_names)
            dev.core.presets = {
                _k: float(_v) for _k, _v in presets.items() if _k in constant
            }
            out["presets"] = {_k: _gui_hkl_f(_v) for _k, _v in dev.core.presets.items()}
        except Exception as exc:
            out["error"] = f"Could not fix the angles: {exc}"
            return out
    if psi is not None and "psi_constant" in _gui_hkl_mode_key(dev.core.mode):
        try:
            dev.core.extras = {"psi": float(psi)}
            out["psi"] = float(psi)
        except Exception as exc:
            out["error"] = f"Could not fix psi: {exc}"
            return out
    try:
        pos = dev.forward(float(h), float(k), float(l))
        out["reals"] = {
            f: _gui_hkl_f(getattr(pos, f)) for f in dev.real_positioners._fields
        }
    except Exception as exc:
        out["error"] = str(exc)
    return out
'''

#: Installed in the kernel by the bootstrap cell.  Plain concatenation, not
#: ``%``-formatting: the body is several hundred lines of Python and a single
#: literal ``%`` anywhere in it -- a format string, a modulo -- would break the
#: whole thing at import time.
HKL_HELPERS_CODE = _PSI_PREAMBLE + _HELPERS_CODE
