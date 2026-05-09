"""
Diffractometer scan plans: ``th2th``, ``hklscan``, ``hscan``, ``kscan``,
``lscan``, ``psiscan``.

These all run on the active hklpy2 diffractometer (see
:func:`hklpy2.user.set_diffractometer`).  Most are thin wrappers over
:func:`ascan` / :func:`lup` from :mod:`base_scans`; ``psiscan`` wraps
:func:`hklpy2.scan_psi` because it owns its own inner loop.
"""

__all__ = [
    "th2th",
    "hklscan",
    "hscan",
    "kscan",
    "lscan",
    "psiscan",
]

from logging import getLogger

from bluesky.preprocessors import subs_decorator
from hklpy2 import scan_psi as hklpy2_scan_psi
from hklpy2.user import get_diffractometer

from ..callbacks.nexus_data_file_writer import nxwriter
from ._local_scan_utils import _build_scan_md
from ._local_scan_utils import _collect_extras
from ._local_scan_utils import _configure_dichro
from ._local_scan_utils import _configure_fixq
from ._local_scan_utils import _setup_detectors
from ._local_scan_utils import _setup_file_io
from ._local_scan_utils import flag
from .base_scans import ascan
from .base_scans import lup
from .local_preprocessors import configure_counts_decorator
from .local_preprocessors import extra_devices_decorator

logger = getLogger(__name__)
logger.info(__file__)


def th2th(
    tth_start,
    tth_end,
    number_of_points,
    time_per_point,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Relative horizontal theta/2theta scan. It will scan the mu and gamma motors.

    Parameters
    ----------
    tth_start : float
            Relative 2theta start. The relative theta will be half of
            the 2theta.
    tth_end : float
            Relative 2theta end. The relative theta will be half of the 2theta.
    number_of_points : int
            Number of points to be measured.
    time_per_point : float
            Measurement time per point.
    detectors : list, optional
            List of detectors to be used in the scan. If None, will use the
            detectors defined in `counters.detectors`.
    lockin : boolean, optional
            Flag to do a lock-in scan. Please run pr_setup.config() prior do a
            lock-in scan.
    dichro : boolean, optional
            Flag to do a dichro scan. Please run pr_setup.config() prior do a
            dichro scan. Note that this will switch the x-ray
            polarization at every point using the +, -, -, + sequence,
            thus increasing the number of
            points by a factor of 4
    fixq : boolean, optional
            Flag for fixQ scans. If True, it will fix the diffractometer hkl
            position during the scan. This is particularly useful for
            energy scan.
            Note that hkl is moved ~after~ the other motors!
    vortex_sgz : boolean, optional
            Measures the Vortex detector using the softgluezynq
            triggers. This is a special mode that requires the 'vortex'
            and 'sgz_vortex' devices to
            exist otherwise an error will be thrown.
    per_step: callable, optional
            hook for customizing action of inner loop (messages per step).
            See docstring of
            :func:`bluesky.plan_stubs.one_nd_step` (the default)
            for details.
    md : dictionary, optional
            Metadata to be added to the run start.

    See Also
    --------
    :func:`lup`
    :func:`ascan`
    """

    diffract = get_diffractometer()
    if diffract is None:
        raise ValueError(
            "There is no diffractometer setup. Please use "
            "`select_diffractometer` to setup the diffractometer."
        )

    _md = {"plan_name": "th2th"}
    _md.update(md or {})

    yield from lup(
        diffract.gamma,
        tth_start,
        tth_end,
        diffract.mu,
        tth_start / 2,
        tth_end / 2,
        number_of_points,
        time_per_point,
        detectors=detectors,
        lockin=lockin,
        dichro=dichro,
        fixq=fixq,
        vortex_sgz=vortex_sgz,
        g_sgz=g_sgz,
        per_step=per_step,
        md=_md,
    )


def hklscan(
    h1,
    h2,
    k1,
    k2,
    l1,
    l2,
    number_of_points,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Linear hkl trajectory scan.

    Sweeps the active diffractometer's (h, k, l) pseudo axes along a straight
    line in reciprocal space from (h1, k1, l1) to (h2, k2, l2) in
    ``number_of_points`` points. Delegates to :func:`ascan`; ``fixq`` is
    forced off because the scan *is* the trajectory.

    Parameters
    ----------
    h1, h2 : float
        Initial and final ``h`` of the trajectory.
    k1, k2 : float
        Initial and final ``k`` of the trajectory.
    l1, l2 : float
        Initial and final ``l`` of the trajectory.
    number_of_points : int
        Number of points (inclusive of endpoints).
    time : float
        Count time per point (seconds).
    detectors : list, optional
        Detectors to read. If None, uses ``counters.detectors``.
    lockin : bool, optional
        Run as a lock-in scan. Requires ``pr_setup.config()`` to have
        been run beforehand.
    dichro : bool, optional
        Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
        Switches the x-ray polarization at every point using the
        ``+ - - +`` sequence, multiplying the point count by 4.
    vortex_sgz : bool, optional
        Trigger the Vortex detector via softgluezynq.  Requires both
        the ``vortex`` and ``sgz_vortex`` devices to exist.
    g_sgz : bool, optional
        Add the ``pos_stream`` position-stream device to the scan so
        motor positions are captured through the softgluezynq pipeline.
    per_step : callable, optional
        Hook for customizing the inner-loop messages.  See
        :func:`bluesky.plan_stubs.one_nd_step` (the default).
    md : dict, optional
        Metadata to add to the run start.

    See Also
    --------
    :func:`ascan`
    :func:`psiscan`
    """

    diff = get_diffractometer()
    if diff is None:
        raise ValueError(
            "There is no diffractometer setup. Please use "
            "`change_diffractometer` to setup the diffractometer."
        )

    _md = {"plan_name": "hklscan"}
    _md.update(md or {})

    yield from ascan(
        diff.h,
        h1,
        h2,
        diff.k,
        k1,
        k2,
        diff.l,
        l1,
        l2,
        number_of_points,
        time,
        detectors=detectors,
        lockin=lockin,
        dichro=dichro,
        fixq=False,
        vortex_sgz=vortex_sgz,
        g_sgz=g_sgz,
        per_step=per_step,
        md=_md,
    )


def _single_axis_scan(
    axis_name, plan_label, start, stop, number_of_points, time, **kwargs
):
    """Helper: ascan over a single (h/k/l) pseudo axis of the active diffractometer."""
    diff = get_diffractometer()
    if diff is None:
        raise ValueError(
            "There is no diffractometer setup. Please use "
            "`change_diffractometer` to setup the diffractometer."
        )
    md = kwargs.pop("md", None) or {}
    md = {"plan_name": plan_label, **md}
    yield from ascan(
        getattr(diff, axis_name),
        start,
        stop,
        number_of_points,
        time,
        md=md,
        **kwargs,
    )


def hscan(
    start,
    stop,
    number_of_points,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Sweep the active diffractometer's ``h`` pseudo axis.

    Thin wrapper around :func:`ascan(diff.h, start, stop, number_of_points,
    time, ...)` that tags the run with ``plan_name="hscan"`` so
    :func:`peak` can identify the scan axis.

    Parameters
    ----------
    start, stop : float
        Initial and final ``h`` value.
    number_of_points : int
        Number of points (inclusive of endpoints).
    time : float
        Count time per point (seconds).
    detectors : list, optional
        Detectors to read. If None, uses ``counters.detectors``.
    lockin : bool, optional
        Run as a lock-in scan. Requires ``pr_setup.config()`` to have
        been run beforehand.
    dichro : bool, optional
        Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
        Switches the x-ray polarization at every point using the
        ``+ - - +`` sequence, multiplying the point count by 4.
    fixq : bool, optional
        Fix the diffractometer hkl during the scan.  Note: hkl is moved
        *after* the other motors.
    vortex_sgz : bool, optional
        Trigger the Vortex detector via softgluezynq.  Requires both
        the ``vortex`` and ``sgz_vortex`` devices to exist.
    g_sgz : bool, optional
        Add the ``pos_stream`` position-stream device to the scan so
        motor positions are captured through the softgluezynq pipeline.
    per_step : callable, optional
        Hook for customizing the inner-loop messages.  See
        :func:`bluesky.plan_stubs.one_nd_step` (the default).
    md : dict, optional
        Metadata to add to the run start.

    See Also
    --------
    :func:`ascan`
    :func:`hklscan`
    :func:`kscan`
    :func:`lscan`
    """
    yield from _single_axis_scan(
        "h",
        "hscan",
        start,
        stop,
        number_of_points,
        time,
        detectors=detectors,
        lockin=lockin,
        dichro=dichro,
        fixq=fixq,
        vortex_sgz=vortex_sgz,
        g_sgz=g_sgz,
        per_step=per_step,
        md=md,
    )


def kscan(
    start,
    stop,
    number_of_points,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Sweep the active diffractometer's ``k`` pseudo axis.

    Thin wrapper around :func:`ascan(diff.k, start, stop, number_of_points,
    time, ...)` that tags the run with ``plan_name="kscan"`` so
    :func:`peak` can identify the scan axis.

    Parameters
    ----------
    start, stop : float
        Initial and final ``k`` value.
    number_of_points : int
        Number of points (inclusive of endpoints).
    time : float
        Count time per point (seconds).
    detectors : list, optional
        Detectors to read. If None, uses ``counters.detectors``.
    lockin : bool, optional
        Run as a lock-in scan. Requires ``pr_setup.config()`` to have
        been run beforehand.
    dichro : bool, optional
        Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
        Switches the x-ray polarization at every point using the
        ``+ - - +`` sequence, multiplying the point count by 4.
    fixq : bool, optional
        Fix the diffractometer hkl during the scan.  Note: hkl is moved
        *after* the other motors.
    vortex_sgz : bool, optional
        Trigger the Vortex detector via softgluezynq.  Requires both
        the ``vortex`` and ``sgz_vortex`` devices to exist.
    g_sgz : bool, optional
        Add the ``pos_stream`` position-stream device to the scan so
        motor positions are captured through the softgluezynq pipeline.
    per_step : callable, optional
        Hook for customizing the inner-loop messages.  See
        :func:`bluesky.plan_stubs.one_nd_step` (the default).
    md : dict, optional
        Metadata to add to the run start.

    See Also
    --------
    :func:`ascan`
    :func:`hklscan`
    :func:`hscan`
    :func:`lscan`
    """
    yield from _single_axis_scan(
        "k",
        "kscan",
        start,
        stop,
        number_of_points,
        time,
        detectors=detectors,
        lockin=lockin,
        dichro=dichro,
        fixq=fixq,
        vortex_sgz=vortex_sgz,
        g_sgz=g_sgz,
        per_step=per_step,
        md=md,
    )


def lscan(
    start,
    stop,
    number_of_points,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Sweep the active diffractometer's ``l`` pseudo axis.

    Thin wrapper around :func:`ascan(diff.l, start, stop, number_of_points,
    time, ...)` that tags the run with ``plan_name="lscan"`` so
    :func:`peak` can identify the scan axis.

    Parameters
    ----------
    start, stop : float
        Initial and final ``l`` value.
    number_of_points : int
        Number of points (inclusive of endpoints).
    time : float
        Count time per point (seconds).
    detectors : list, optional
        Detectors to read. If None, uses ``counters.detectors``.
    lockin : bool, optional
        Run as a lock-in scan. Requires ``pr_setup.config()`` to have
        been run beforehand.
    dichro : bool, optional
        Run as a dichro scan. Requires ``pr_setup.config()`` beforehand.
        Switches the x-ray polarization at every point using the
        ``+ - - +`` sequence, multiplying the point count by 4.
    fixq : bool, optional
        Fix the diffractometer hkl during the scan.  Note: hkl is moved
        *after* the other motors.
    vortex_sgz : bool, optional
        Trigger the Vortex detector via softgluezynq.  Requires both
        the ``vortex`` and ``sgz_vortex`` devices to exist.
    g_sgz : bool, optional
        Add the ``pos_stream`` position-stream device to the scan so
        motor positions are captured through the softgluezynq pipeline.
    per_step : callable, optional
        Hook for customizing the inner-loop messages.  See
        :func:`bluesky.plan_stubs.one_nd_step` (the default).
    md : dict, optional
        Metadata to add to the run start.

    See Also
    --------
    :func:`ascan`
    :func:`hklscan`
    :func:`hscan`
    :func:`kscan`
    """
    yield from _single_axis_scan(
        "l",
        "lscan",
        start,
        stop,
        number_of_points,
        time,
        detectors=detectors,
        lockin=lockin,
        dichro=dichro,
        fixq=fixq,
        vortex_sgz=vortex_sgz,
        g_sgz=g_sgz,
        per_step=per_step,
        md=md,
    )


_PSI_MODES = {
    "horizontal": "psi constant horizontal",
    "vertical": "psi constant vertical",
}


def psiscan(
    psi_start,
    psi_stop,
    number_of_points,
    time,
    hkl=None,
    hkl2=None,
    orientation="horizontal",
    detectors=None,
    psi_axis=None,
    fail_on_exception=False,
    md=None,
):
    """
    Azimuthal psi scan at fixed (h, k, l).

    Wraps `hklpy2.scan_psi`, holding (h, k, l) fixed while sweeping the
    azimuthal extra parameter from ``psi_start`` to ``psi_stop`` in
    ``number_of_points`` points. Runs on the active diffractometer (e.g.
    ``huber_euler``) — its hkl engine exposes the ``psi constant
    horizontal`` / ``psi constant vertical`` modes used here.

    Parameters
    ----------
    psi_start, psi_stop : float
        Azimuthal angle range (degrees).
    number_of_points : int
        Number of points (inclusive of endpoints).
    time : float
        Count time per point. Must be > 0.
    hkl : sequence of float, optional
        Fixed reflection (h, k, l). If None (default), use the current
        diffractometer position.
    hkl2 : sequence of float, optional
        Reference reflection (h2, k2, l2) defining psi=0. If None (default),
        read from the active diffractometer's ``core.all_extras`` (the
        non-psi entries, in order). Must not be parallel to (h, k, l).
    orientation : {'horizontal', 'vertical'}, optional
        Scattering plane. Selects the psi mode passed to
        ``hklpy2.scan_psi``: ``"psi constant horizontal"`` (default) or
        ``"psi constant vertical"``.
    detectors : list, optional
        Detectors to read. If None, uses ``counters.detectors``.
    psi_axis : str, optional
        Name of the psi extra axis. Auto-detected when None.
    fail_on_exception : bool, optional
        Forwarded to `hklpy2.scan_psi`. When False (default), per-point
        forward-calculation failures are printed and the scan continues.
    md : dict, optional
        Metadata to add to the run start.

    Notes
    -----
    Unlike `ascan`/`grid_scan`, this plan does not support `dichro`,
    `lockin`, `fixq`, or `vortex_sgz` because `hklpy2.scan_psi` runs its own
    inner loop and does not accept a `per_step` hook.

    See Also
    --------
    :func:`hklpy2.scan_psi`
    """

    if time <= 0:
        raise ValueError("time must be greater than zero.")

    if orientation not in _PSI_MODES:
        raise ValueError(
            f"orientation must be one of {list(_PSI_MODES)}, got "
            f"{orientation!r}."
        )
    mode = _PSI_MODES[orientation]

    diff = get_diffractometer()
    if diff is None:
        raise ValueError(
            "There is no diffractometer setup. Please use "
            "`change_diffractometer` to setup the diffractometer."
        )

    if hkl is None:
        hkl = (diff.h.position, diff.k.position, diff.l.position)
    if len(hkl) != 3:
        raise ValueError(f"hkl must have 3 elements, got {len(hkl)}: {hkl}")
    h, k, l = hkl  # noqa: E741

    if hkl2 is None:
        ext = diff.core.all_extras
        ref_keys = [name for name in ext if "psi" not in name.lower()]
        if len(ref_keys) != 3:
            raise ValueError(
                f"Cannot auto-detect hkl2 from {diff.name}.core.all_extras="
                f"{ext}. Expected exactly 3 non-psi entries, found "
                f"{ref_keys}. Pass hkl2= explicitly."
            )
        hkl2 = tuple(ext[name] for name in ref_keys)

    flag.vortex_sgz = False

    if detectors is None:
        detectors = _setup_detectors(time)

    _configure_dichro(False)
    _configure_fixq(False)

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_file_io(
        detectors
    )

    extras = yield from _collect_extras(())

    _md = _build_scan_md(
        detectors,
        _master_fullpath,
        _dets_file_paths,
        _rel_dets_paths,
        dichro=False,
        lockin=False,
    )
    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])
    _md["plan_name"] = "psiscan"
    _md["hints"]["scan_type"] = "psiscan"
    psi_axis_name = psi_axis or "psi"
    _md["hints"]["dimensions"] = [
        ([f"{diff.name}_extras_{psi_axis_name}"], "primary")
    ]
    # scan_extra puts `reals=None` into the start doc; the NeXus writer
    # cannot serialize None, so override with an empty dict.
    _md["reals"] = {}
    _md.update(md or {})

    @configure_counts_decorator(detectors, time)
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_psiscan():
        yield from hklpy2_scan_psi(
            detectors + extras,
            diff,
            h=h,
            k=k,
            l=l,
            hkl2=hkl2,
            psi_start=psi_start,
            psi_stop=psi_stop,
            num=number_of_points,
            mode=mode,
            psi_axis=psi_axis,
            fail_on_exception=fail_on_exception,
            md=_md,
        )
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_psiscan())
