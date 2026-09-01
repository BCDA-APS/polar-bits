"""
Local list-scan plans: ``list_scan`` and ``rel_list_scan``.

Polar-bits versions of :func:`bluesky.plans.list_scan` /
:func:`bluesky.plans.rel_list_scan` that wire in the standard counters /
dichro / lockin / softgluezynq / NeXus / baseline machinery.

Unlike ``ascan`` / ``grid_scan``, which build their trajectory from
``start, stop, num``, these take an explicit list of positions per motor.
Use them when the points are not evenly spaced -- a hand-picked set of
setpoints, a log-spaced grid, or an energy list computed elsewhere.  For
the XAFS-specific energy grid see :func:`id4_common.plans.base_scans.qxscan`.
"""

__all__ = [
    "list_scan",
    "rel_list_scan",
]

from logging import getLogger

from apsbits.core.instrument_init import oregistry
from bluesky.plans import list_scan as bp_list_scan
from bluesky.preprocessors import monitor_during_decorator
from bluesky.preprocessors import relative_set_decorator
from bluesky.preprocessors import reset_positions_decorator
from bluesky.preprocessors import subs_decorator
from toolz import partition

from ..callbacks.dichro_stream import dichro as dichro_device
from ..callbacks.nexus_data_file_writer import nxwriter
from ._local_scan_utils import _build_scan_md
from ._local_scan_utils import _check_magnet911
from ._local_scan_utils import _collect_extras
from ._local_scan_utils import _configure_dichro
from ._local_scan_utils import _configure_fixq
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


def _split_list_scan_args(args):
    """
    Validate ``list_scan`` positional arguments and split off the count time.

    Parameters
    ----------
    args : tuple
        ``motor1, list1, ..., motorN, listN, time``.

    Returns
    -------
    scan_args : tuple
        The ``motor1, list1, ..., motorN, listN`` portion, ready to hand to
        :func:`bluesky.plans.list_scan`.
    motors : list
        The motor objects, in the order given.
    time : float
        The trailing count time.
    """
    if len(args) % 2 != 1:
        raise ValueError(
            "Invalid number of arguments provided. Expected a multiple of 2 "
            f"plus 1, but got {len(args)}."
        )

    time = args[-1]
    scan_args = args[:-1]

    motors = []
    lengths = []
    for motor, positions in partition(2, scan_args):
        motors.append(motor)
        try:
            lengths.append(len(positions))
        except TypeError:
            raise ValueError(
                f"The positions for {getattr(motor, 'name', motor)} must be a "
                f"sized iterable (list, tuple, array), got {positions!r}."
            ) from None

    if len(set(lengths)) > 1:
        _detail = ", ".join(
            f"{getattr(m, 'name', m)}={n}"
            for m, n in zip(motors, lengths, strict=False)
        )
        raise ValueError(
            "All position lists must have the same length, but got "
            f"{_detail}."
        )

    return scan_args, motors, time


def list_scan(
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
    Scan over one or more motors using an explicit list of positions.

    All motors move together, one list entry per scan point, so every
    position list must have the same length.

    Parameters
    ----------
    ``*args``
        patterned like (``motor1, list1,``
                        ``motor2, list2,`` ...
                        ``motorN, listN,``
                        ``time``)
        Motors can be any 'settable' object (motor, temp controller, etc.)
        and each list is the sequence of positions that motor visits. The
        lists may be Python lists, tuples or numpy arrays.
    time : float
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
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
    md: dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.list_scan`
    :func:`rel_list_scan`
    :func:`ascan`
    """

    args, motors, time = _split_list_scan_args(args)

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
    _md["hints"]["scan_type"] = "list_scan"
    _md.update(md or {})

    magnet_option = _check_magnet911(args)

    @stage_magnet911_decorator(magnet_option)
    @stage_4idg_softglue_decorator(g_sgz)
    @monitor_during_decorator([dichro_device] if dichro else [])
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, vortex_sgz, motors)
    @extra_devices_decorator(extras)
    @subs_decorator(nxwriter.receiver)
    def _inner_list_scan():
        yield from bp_list_scan(
            detectors + extras, *args, per_step=per_step, md=_md
        )
        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_list_scan())


def rel_list_scan(
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
    Scan over an explicit list of positions relative to the current position.

    All motors move together, one list entry per scan point, so every
    position list must have the same length. The motors are returned to their
    starting positions when the scan finishes.

    Parameters
    ----------
    ``*args``
        patterned like (``motor1, list1,``
                        ``motor2, list2,`` ...
                        ``motorN, listN,``
                        ``time``)
        Motors can be any 'settable' object (motor, temp controller, etc.)
        and each list is the sequence of offsets, relative to that motor's
        current position, that it visits. The lists may be Python lists,
        tuples or numpy arrays.
    time : float
        If a number is passed, it will modify the counts over time. All
        detectors need to have a .preset_monitor signal.
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
    md: dict, optional
        metadata

    See Also
    --------
    :func:`list_scan`
    :func:`bluesky.plans.rel_list_scan`
    :func:`lup`
    """

    _md = {"plan_name": "rel_list_scan"}
    _md.update(md or {})

    _, motors, _ = _split_list_scan_args(args)

    @reset_positions_decorator(motors)
    @reset_real_motors_decorator(_hkl_motors(fixq))
    @relative_set_decorator(motors)
    def inner_rel_list_scan():
        return (
            yield from list_scan(
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

    return (yield from inner_rel_list_scan())
