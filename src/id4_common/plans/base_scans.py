"""
Local 1-D scan plans: ``count``, ``ascan``, ``lup``, ``qxscan``.

These are the polar-bits versions of the generic bluesky scan plans.  They
add the standard polar-bits machinery (counters / dichro / lockin /
softgluezynq stage signals, NeXus writer subscription, baseline file paths)
on top of the underlying ``bluesky.plans`` calls.
"""

__all__ = [
    "count",
    "ascan",
    "lup",
    "qxscan",
]

from logging import getLogger

from apsbits.core.instrument_init import oregistry
from bluesky.plan_stubs import rd
from bluesky.plans import count as bp_count
from bluesky.plans import list_scan
from bluesky.plans import scan
from bluesky.preprocessors import monitor_during_decorator
from bluesky.preprocessors import relative_set_decorator
from bluesky.preprocessors import reset_positions_decorator
from bluesky.preprocessors import subs_decorator
from numpy import array
from toolz import partition

from ..callbacks.dichro_stream import dichro as dichro_device
from ..callbacks.nexus_data_file_writer import nxwriter
from ._local_scan_utils import _build_scan_md
from ._local_scan_utils import _check_magnet911
from ._local_scan_utils import _collect_extras
from ._local_scan_utils import _configure_dichro
from ._local_scan_utils import _configure_fixq
from ._local_scan_utils import _default_per_shot
from ._local_scan_utils import _default_per_step
from ._local_scan_utils import _hkl_motors
from ._local_scan_utils import _setup_detectors
from ._local_scan_utils import _setup_file_io
from ._local_scan_utils import flag
from ._local_scan_utils import reset_real_motors_decorator
from .local_preprocessors import configure_counts_decorator
from .local_preprocessors import extra_devices_decorator
from .local_preprocessors import stage_4idg_softglue_decorator
from .local_preprocessors import stage_dichro_decorator
from .local_preprocessors import stage_magnet911_decorator
from .move_plans import mv

logger = getLogger(__name__)
logger.info(__file__)


def count(
    num,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    vortex_sgz=False,
    g_sgz=False,
    delay=None,
    per_shot=None,
    md=None,
):
    """
    Take one or more readings from detectors.

    This is a local version of `bluesky.plans.count`. Note that the `per_shot`
    cannot be set here, as it is used for dichro scans.

    Parameters
    ----------
    num : integer
        number of readings to take
        If None, capture data until canceled
    time : float
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of 'readable' objects. If None, will use the detectors defined in
        `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan.
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    vortex_sgz : boolean, optional
        Measures the Vortex detector using the softgluezynq triggers. This is a
        special mode that requires the 'vortex' and 'sgz_vortex' devices to
        exist otherwise an error will be thrown.
    delay : iterable or scalar, optional
        Time delay in seconds between successive readings; default is 0.
    per_shot: callable, optional
        Hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dict, optional
        metadata

    Notes
    -----
    If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
    the plan will raise a ``ValueError`` during iteration.
    """

    if time == 0:
        raise ValueError("time must be different from zero.")

    if g_sgz:
        pos_stream = oregistry.find("pos_stream")

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        detectors = _setup_detectors(time)

    _configure_dichro(dichro)
    _configure_fixq(False)

    if per_shot is not None and dichro:
        logger.warning("there is a custom per_shot, but dichro was selected.")
    elif per_shot is None:
        per_shot = _default_per_shot(dichro, vortex_sgz)

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_file_io(
        detectors if not g_sgz else detectors + [pos_stream]
    )

    extras = yield from _collect_extras(("",))

    _md = _build_scan_md(
        detectors,
        _master_fullpath,
        _dets_file_paths,
        _rel_dets_paths,
        dichro=dichro,
        lockin=lockin,
    )
    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])
    _md.update(md or {})

    @stage_magnet911_decorator(False)
    @stage_4idg_softglue_decorator(g_sgz)
    @monitor_during_decorator([dichro_device] if dichro else [])
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, vortex_sgz, [None])
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_count():
        yield from bp_count(
            detectors + extras, num=num, per_shot=per_shot, delay=delay, md=_md
        )
        # Wait for the master file to finish writing.
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_count())


def ascan(
    *args,
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
    Scan over one multi-motor trajectory.

    This is a local version of `bluesky.plans.scan`. Note that the `per_step`
    cannot be set here, as it is used for dichro scans.

    Parameters
    ----------
    *args :
        For one dimension, ``motor, start, stop, number of points, time``.
        In general:
        .. code-block:: python
            motor1, start1, stop1,
            motor2, start2, start2,
            ...,
            motorN, startN, stopN,
            number of points,
            time
        Motors can be any 'settable' object (motor, temp controller, etc.)
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan.
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    fixq : boolean, optional
        Flag for fixQ scans. If True, it will fix the diffractometer hkl
        position during the scan. This is particularly useful for energy scan.
        Note that hkl is moved ~after~ the other motors!
    vortex_sgz : boolean, optional
        Measures the Vortex detector using the softgluezynq triggers. This is a
        special mode that requires the 'vortex' and 'sgz_vortex' devices to
        exist otherwise an error will be thrown.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.scan`
    :func:`lup`
    """

    if len(args) % 3 != 2:
        raise ValueError(
            "Invalid number of arguments provided. Expected a multiple of 3 "
            f"plus 2, but got {len(args)}."
        )
    else:
        time = args[-1]
        args = args[:-1]

    if g_sgz:
        pos_stream = oregistry.find("pos_stream")

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        detectors = _setup_detectors(time)

    _configure_dichro(dichro)
    _configure_fixq(fixq)

    per_step = per_step or _default_per_step(fixq, dichro, vortex_sgz)

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_file_io(
        detectors if not g_sgz else detectors + [pos_stream]
    )

    extras = yield from _collect_extras(args)

    _md = _build_scan_md(
        detectors,
        _master_fullpath,
        _dets_file_paths,
        _rel_dets_paths,
        dichro=dichro,
        lockin=lockin,
    )
    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])
    _md["hints"]["scan_type"] = "ascan"
    _md.update(md or {})

    motors = [motor for motor, _, _ in partition(3, args)]

    magnet_option = _check_magnet911(args)

    @stage_magnet911_decorator(magnet_option)
    @stage_4idg_softglue_decorator(g_sgz)
    @monitor_during_decorator([dichro_device] if dichro else [])
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, vortex_sgz, motors)
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_ascan():
        yield from scan(detectors + extras, *args, per_step=per_step, md=_md)
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_ascan())


def lup(
    *args,
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
    Scan over one multi-motor trajectory relative to current position.

    This is a local version of `bluesky.plans.rel_scan`. Note that the
    `per_step` cannot be set here, as it is used for dichro scans.

    Parameters
    ----------
    *args :
        For one dimension, ``motor, start, stop, number of points``.
        In general:
        .. code-block:: python
            motor1, start1, stop1,
            motor2, start2, start2,
            ...,
            motorN, startN, stopN,
            number of points
        Motors can be any 'settable' object (motor, temp controller, etc.)
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan.
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    fixq : boolean, optional
        Flag for fixQ scans. If True, it will fix the diffractometer hkl
        position during the scan. This is particularly useful for energy scan.
        Note that hkl is moved ~after~ the other motors!
    vortex_sgz : boolean, optional
        Measures the Vortex detector using the softgluezynq triggers. This is a
        special mode that requires the 'vortex' and 'sgz_vortex' devices to
        exist otherwise an error will be thrown.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.rel_scan`
    :func:`ascan`
    """

    _md = {"plan_name": "lup"}
    md = md or {}
    _md.update(md)
    motors = [motor for motor, _, _ in partition(3, args)]

    @reset_positions_decorator(motors)
    @reset_real_motors_decorator(_hkl_motors(fixq))
    @relative_set_decorator(motors)
    def inner_lup():
        return (
            yield from ascan(
                *args,
                detectors=detectors,
                lockin=lockin,
                dichro=dichro,
                fixq=fixq,
                vortex_sgz=vortex_sgz,
                g_sgz=g_sgz,
                per_step=per_step,
                md=_md,
            )
        )

    return (yield from inner_lup())


def qxscan(
    edge_energy,
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
    Energy scan with fixed delta_K steps.

    WARNING: please run qxscan_params() before using this plan! It will
    use the parameters set in qxscan_params to determine the energy points.

    Parameters
    ----------
    edge_energy : float
        Absorption edge energy. The parameters in qxscan_params offset by this
        energy.
    time : float
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    lockin : boolean, optional
        Flag to do a lock-in scan. Please run pr_setup.config() prior do a
        lock-in scan
    dichro : boolean, optional
        Flag to do a dichro scan. Please run pr_setup.config() prior do a
        dichro scan. Note that this will switch the x-ray polarization at every
        point using the +, -, -, + sequence, thus increasing the number of
        points by a factor of 4
    fixq : boolean, optional
        Flag for fixQ scans. If True, it will fix the diffractometer hkl
        position during the scan. Note that hkl is moved ~after~ the other
        motors!
    md : dictionary, optional
        Metadata to be added to the run start.

    See Also
    --------
    :func:`bluesky.plans.scan`
    :func:`lup`
    """

    if g_sgz:
        pos_stream = oregistry.find("pos_stream")

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        detectors = _setup_detectors(time)

    _configure_dichro(dichro)
    _configure_fixq(fixq)

    per_step = per_step or _default_per_step(fixq, dichro, vortex_sgz)

    energy = oregistry.find("energy", allow_none=True)
    if energy is None:
        raise ValueError("energy device not found in registry.")

    qxscan_setup = oregistry.find("qxscan_setup", allow_none=True)
    if qxscan_setup is None:
        raise ValueError("qxxcan_setup device not found in registry.")

    energy_list = yield from rd(qxscan_setup.energy_list)
    args = (energy, array(energy_list) + edge_energy)

    extras = yield from _collect_extras(args)

    # Setup count time
    factor_list = yield from rd(qxscan_setup.factor_list)

    _ct = {}
    for det in detectors:
        _ct[det] = abs(time)
        args += (det.preset_monitor, abs(time) * array(factor_list))

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_file_io(
        detectors if not g_sgz else detectors + [pos_stream]
    )

    _md = _build_scan_md(
        detectors,
        _master_fullpath,
        _dets_file_paths,
        _rel_dets_paths,
        dichro=dichro,
        lockin=lockin,
    )
    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])
    _md["hints"]["scan_type"] = "qxscan"
    if dichro:
        _md["hints"]["scan_type"] += " dichro"
    if lockin:
        _md["hints"]["scan_type"] += " lockin"
    _md.update(md or {})

    @monitor_during_decorator([dichro_device] if dichro else [])
    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, vortex_sgz, [energy])
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_qxscan():
        yield from list_scan(
            detectors + extras, *args, per_step=per_step, md=_md
        )
        # put original times back.
        for det, preset in _ct.items():
            yield from mv(det.preset_monitor, preset)

        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_qxscan())
