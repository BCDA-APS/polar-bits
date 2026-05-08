"""
Modifed bluesky scans
"""

__all__ = [
    "lup",
    "ascan",
    "mv",
    "mvr",
    "grid_scan",
    "rel_grid_scan",
    "qxscan",
    "count",
    "abs_set",
    "psiscan",
    "hklscan",
    "hscan",
    "kscan",
    "lscan",
]

from logging import getLogger

from apsbits.core.instrument_init import oregistry
from bluesky.plan_patterns import chunk_outer_product_args
from bluesky.plan_stubs import abs_set as bps_abs_set
from bluesky.plan_stubs import mv as bps_mv
from bluesky.plan_stubs import rd
from bluesky.plans import count as bp_count
from bluesky.plans import grid_scan as bp_grid_scan
from bluesky.plans import list_scan
from bluesky.plans import scan
from bluesky.preprocessors import monitor_during_decorator
from bluesky.preprocessors import relative_set_decorator
from bluesky.preprocessors import reset_positions_decorator
from bluesky.preprocessors import subs_decorator
from hklpy2 import scan_psi as hklpy2_scan_psi
from hklpy2.user import get_diffractometer
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

logger = getLogger(__name__)
logger.info(__file__)

# Keep backward-compatible alias
setup_detectors = _setup_detectors


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


def grid_scan(
    *args,
    detectors=None,
    snake_axes=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Scan over a mesh; each motor is on an independent trajectory.

    Parameters
    ----------
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)
        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    time : float, optional
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
    detectors : list, optional
        List of detectors to be used in the scan. If None, will use the
        detectors defined in `counters.detectors`.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
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
    md: dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """

    if len(args) % 4 != 1:
        raise ValueError(
            "Invalid number of arguments provided. Expected a multiple of 4 "
            f"plus 1, but got {len(args)}."
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
    _md["hints"]["scan_type"] = "gridscan"
    _md.update(md or {})

    motors = [m[0] for m in chunk_outer_product_args(args)]

    magnet_option = _check_magnet911(args)

    @stage_magnet911_decorator(magnet_option)
    @stage_4idg_softglue_decorator(g_sgz)
    @monitor_during_decorator([dichro_device] if dichro else [])
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, vortex_sgz, motors)
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_grid_scan():
        yield from bp_grid_scan(
            detectors + extras,
            *args,
            snake_axes=snake_axes,
            per_step=per_step,
            md=_md,
        )
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_grid_scan())


def rel_grid_scan(
    *args,
    detectors=None,
    snake_axes=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
    g_sgz=False,
    per_step=None,
    md=None,
):
    """
    Scan over a mesh relative to current position.

    Each motor is on an independent trajectory.

    Parameters
    ----------
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)
        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
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
    md: dict, optional
        metadata

    See Also
    --------
    :func:`grid_scan`
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """

    _md = {"plan_name": "rel_grid_scan"}
    _md.update(md or {})
    motors = [m[0] for m in chunk_outer_product_args(args)]

    @reset_positions_decorator(motors)
    @reset_real_motors_decorator(_hkl_motors(fixq))
    @relative_set_decorator(motors)
    def inner_rel_grid_scan():
        return (
            yield from grid_scan(
                *args,
                detectors=detectors,
                snake_axes=snake_axes,
                lockin=lockin,
                dichro=dichro,
                fixq=fixq,
                vortex_sgz=vortex_sgz,
                g_sgz=g_sgz,
                per_step=per_step,
                md=_md,
            )
        )

    return (yield from inner_rel_grid_scan())


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
    ``number_of_points`` points. Delegates to :func:`ascan` so all the usual
    flags (dichro, lockin, vortex_sgz, g_sgz, per_step) are supported.

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
        Count time per point.
    detectors, lockin, dichro, vortex_sgz, g_sgz, per_step, md :
        See :func:`ascan`.

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
        Count time per point.
    detectors, lockin, dichro, fixq, vortex_sgz, g_sgz, per_step, md :
        See :func:`ascan`.

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
        Count time per point.
    detectors, lockin, dichro, fixq, vortex_sgz, g_sgz, per_step, md :
        See :func:`ascan`.

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
        Count time per point.
    detectors, lockin, dichro, fixq, vortex_sgz, g_sgz, per_step, md :
        See :func:`ascan`.

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


def mv(*args, **kwargs):
    """
    Move one or more devices to a setpoint, and wait for all to complete.

    This is a local version of `bluesky.plan_stubs.mv`. If more than one device
    is specifed, the movements are done in parallel.

    Parameters
    ----------
    args :
        device1, value1, device2, value2, ...
    kwargs :
        passed to bluesky.plan_stubs.mv

    Yields
    ------
    msg : Msg

    See Also
    --------
    :func:`bluesky.plan_stubs.mv`
    """

    magnet_option = _check_magnet911(args)

    @stage_magnet911_decorator(magnet_option)
    def _inner_mv():
        yield from bps_mv(*args, **kwargs)

    return (yield from _inner_mv())


def mvr(*args, **kwargs):
    """
    Move one or more devices to a relative setpoint. Wait for all to complete.

    If more than one device is specified, the movements are done in parallel.

    This is a local version of `bluesky.plan_stubs.mvr`.

    Parameters
    ----------
    args :
        device1, value1, device2, value2, ...
    kwargs :
        passed to bluesky.plan_stub.mvr

    Yields
    ------
    msg : Msg

    See Also
    --------
    :func:`bluesky.plan_stubs.rel_set`
    :func:`bluesky.plan_stubs.mv`
    """
    objs = []
    for obj, _ in partition(2, args):
        objs.append(obj)

    @relative_set_decorator(objs)
    def _inner_mvr():
        return (yield from mv(*args, **kwargs))

    return (yield from _inner_mvr())


def abs_set(*args, **kwargs):
    """
    Set a value. Optionally, wait for it to complete before continuing.

    This is a local version of `bluesky.plan_stubs.abs_set`. If more than one
    device is specifed, the movements are done in parallel.

    Parameters
    ----------
    obj : Device
    group : string (or any hashable object), optional
        identifier used by 'wait'
    wait : boolean, optional
        If True, wait for completion before processing any more messages.
        False by default.
    args :
        passed to obj.set()
    kwargs :
        passed to obj.set()

    Yields
    ------
    msg : Msg

    See Also
    --------
    :func:`bluesky.plan_stubs.rel_set`
    :func:`bluesky.plan_stubs.wait`
    :func:`bluesky.plan_stubs.mv`
    """

    magnet_option = _check_magnet911(args)

    @stage_magnet911_decorator(magnet_option, persistent=False)
    def _inner_abs_set():
        yield from bps_abs_set(*args, **kwargs)

    return (yield from _inner_abs_set())
