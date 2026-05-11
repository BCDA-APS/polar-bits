"""
Local mesh-scan plans: ``grid_scan`` and ``rel_grid_scan``.

Polar-bits versions of :func:`bluesky.plans.grid_scan` /
:func:`bluesky.plans.rel_grid_scan` that wire in the standard counters /
dichro / lockin / softgluezynq / NeXus / baseline machinery.
"""

__all__ = [
    "grid_scan",
    "rel_grid_scan",
]

from logging import getLogger

from apsbits.core.instrument_init import oregistry
from bluesky.plan_patterns import chunk_outer_product_args
from bluesky.plans import grid_scan as bp_grid_scan
from bluesky.preprocessors import monitor_during_decorator
from bluesky.preprocessors import relative_set_decorator
from bluesky.preprocessors import reset_positions_decorator
from bluesky.preprocessors import subs_decorator

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
