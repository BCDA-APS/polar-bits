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
]

from bluesky.plans import (
    scan,
    grid_scan as bp_grid_scan,
    count as bp_count,
    list_scan,
)
from bluesky.plan_stubs import (
    mv as bps_mv,
    abs_set as bps_abs_set,
    rd,
    trigger_and_read,
    move_per_step,
)
from bluesky.preprocessors import (
    reset_positions_decorator,
    relative_set_decorator,
    subs_decorator,
    monitor_during_decorator,
)
from bluesky.plan_patterns import chunk_outer_product_args
from .local_preprocessors import (
    configure_counts_decorator,
    extra_devices_decorator,
    stage_dichro_decorator,
)

from toolz import partition
from pathlib import Path
from numpy import array
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from hkl.user import current_diffractometer
from logging import getLogger

from ..callbacks.nexus_data_file_writer import nxwriter
from ..callbacks.dichro_stream import dichro as dichro_device
from ..utils.experiment_utils import experiment
from ..utils.run_engine import RE
from ..utils.counters_class import counters

try:
    # change to import this only if needed?
    from ..utils.pr_setup import pr_setup
except ModuleNotFoundError:
    pr_setup = None

iconfig = get_config()

logger = getLogger(__name__)
logger.info(__file__)

HDF1_NAME_FORMAT = Path(iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"])


class LocalFlag:
    """Stores flags that are used to select and run local scans."""

    dichro = False
    fixq = False
    hkl_pos = {}
    dichro_steps = None
    vortex_sgz = False


flag = LocalFlag()


def _collect_extras(args):
    """Collect all detectors that need to be read during a scan."""

    # TODO: most or all of this can be removed if we add these to the energy
    # device directly.dichro_bec

    # Initialize the list of extra devices with the standard set from counters
    extras = counters.extra_devices.copy()

    energy = oregistry.find("energy", allow_none=True)
    escan_flag = False if energy is None or energy not in args else True
    if escan_flag:
        undulators = oregistry.find("undulators", allow_none=True)
        if undulators is None:
            logger.warning(
                "Undulators device not found. Will not record the undulator "
                "energy during scan."
            )
        else:
            for und in (undulators.ds, undulators.us):
                und_track = yield from rd(und.tracking)
                if und_track:
                    extras.append(und.energy)

        # Do the same for phase plates
        prs = oregistry.findall("phase retarders", allow_none=True)
        if prs is None:
            logger.warning(
                "No phase retarder device not found. Will not record its "
                "position energy during scan."
            )
        else:
            for pr in prs:
                # Fetch tracking status asynchronously
                pr_track = yield from rd(pr.tracking)
                if pr_track:
                    extras.append(pr.th)

    diff = current_diffractometer()
    huber_flag = False if diff is None or diff.name not in str(args) else True
    if huber_flag:
        extras.append(current_diffractometer())

    return extras


def dichro_steps(devices_to_read, take_reading):
    """
    Switch the x-ray polarization for each scan point.
    This will increase the number of points in a scan by a factor that is equal
    to the length of the `pr_setup.dichro_steps` list.
    """
    devices_to_read += [pr_setup.positioner]
    for pos in flag.dichro_steps:
        yield from mv(pr_setup.positioner, pos)
        yield from take_reading(devices_to_read)


def one_local_step(detectors, step, pos_cache, take_reading=trigger_and_read):
    """
    Inner loop for fixQ and dichro scans.

    It is always called in the local plans defined here. It is used as a
    `per_step` kwarg in Bluesky scan plans, such as `bluesky.plans.scan`. But
    note that it requires the `LocalFlag` class.

    Parameters
    ----------
    detectors : iterable
        devices to read
    step : dict
        mapping motors to positions in this step
    pos_cache : dict
        mapping motors to their last-set positions
    take_reading : plan, optional
        function to do the actual acquisition ::
           def take_reading(dets, name='primary'):
                yield from ...
        Callable[List[OphydObj], Optional[str]] -> Generator[Msg], optional
        Defaults to `trigger_and_read`
    """

    devices_to_read = list(step.keys()) + list(detectors)
    yield from move_per_step(step, pos_cache)

    if flag.fixq:
        huber = current_diffractometer()
        devices_to_read += [huber]
        args = (
            huber.h,
            flag.hkl_pos[huber.h],
            huber.k,
            flag.hkl_pos[huber.k],
            huber.l,
            flag.hkl_pos[huber.l],
        )
        yield from bps_mv(*args)

    if flag.dichro:
        yield from dichro_steps(devices_to_read, take_reading)
    else:
        if flag.vortex_sgz:
            # TODO: Is there a better way for this?
            sgz_vortex = oregistry.find("sgz_vortex")
            vortex = oregistry.find("vortex")

            # Reset SGZ
            yield from sgz_vortex.reset()

            # Arm Vortex
            yield from vortex.arm_plan()

        yield from take_reading(devices_to_read)


def one_local_shot(detectors, take_reading=trigger_and_read):
    """
    Inner loop for fixQ and dichro scans.
    To be used as a `per_shot` kwarg in the Bluesky `bluesky.plans.count`.
    It is always called in the local `count` plan defined here. It is used as a
    `per_shot` kwarg in the Bluesky `bluesky.plans.count`. But note that it
    requires the `LocalFlag` class.
    Parameters
    ----------
    detectors : iterable
        devices to read
    take_reading : plan, optional
        function to do the actual acquisition ::
           def take_reading(dets, name='primary'):
                yield from ...
        Callable[List[OphydObj], Optional[str]] -> Generator[Msg], optional
        Defaults to `trigger_and_read`
    """

    devices_to_read = list(detectors)
    if flag.dichro:
        yield from dichro_steps(devices_to_read, take_reading)
    else:
        if flag.vortex_sgz:
            # TODO: Is there a better way for this?
            sgz_vortex = oregistry.find("sgz_vortex")
            vortex = oregistry.find("vortex")

            # Reset SGZ
            yield from sgz_vortex.reset()

            # Arm Vortex
            yield from vortex.arm_plan()

        yield from take_reading(devices_to_read)


def _setup_paths(detectors):

    if None in (experiment.base_experiment_path, experiment.file_base_name):
        raise ValueError(
            "The experiment needs to be setup, please run experiment_setup()"
        )

    _scan_id = RE.md["scan_id"] + 1

    # Master file
    _master_fullpath = str(HDF1_NAME_FORMAT) % (
        str(experiment.experiment_path),
        experiment.file_base_name,
        _scan_id,
    )
    _master_fullpath += "_master.hdf"

    # Setup area detectors
    _dets_file_paths = {}
    # Relative paths are used in the master file so that data can be copied.
    _rel_dets_paths = {}
    for det in list(detectors):
        # Check if we can and want to get images from this detector
        _setup_images = getattr(det, "setup_images", None)
        _flag = getattr(det, "save_image_flag", False)
        if _setup_images and _flag:
            _fp, _rp = _setup_images(
                experiment.experiment_path,
                experiment.file_base_name,
                _scan_id,
                flyscan=False,
            )
            _dets_file_paths[det.name] = str(_fp)
            _rel_dets_paths[det.name] = str(_rp)

    # Check if any of these files exists
    for _fname in [_master_fullpath] + list(_dets_file_paths.values()):
        if Path(_fname).is_file():
            raise FileExistsError(
                f"The file {_fname} already exists! Will not overwrite, "
                "quitting."
            )

    return _master_fullpath, _dets_file_paths, _rel_dets_paths


def setup_nxwritter(_base_path, _master_fullpath, _rel_dets_paths):
    nxwriter.external_files = _rel_dets_paths
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(_base_path)


def setup_detectors(is_monitor_time):
    # If counting against time, then all good, can just use the detectors
    # setup in counters
    if is_monitor_time:
        dets = counters.detectors

        if flag.vortex_sgz:
            vortex = oregistry.find("vortex", allow_none=True)
            if vortex is None:
                raise ValueError(
                    "Vortex detector not found by oregistry! It is "
                    "required for vortex_sgz mode."
                )

            sgz_vortex = oregistry.find("sgz_vortex", allow_none=True)
            if sgz_vortex is None:
                raise ValueError(
                    "sgz_vortex detector not found by oregistry! It is "
                    "required for vortex_sgz mode."
                )
            if vortex not in dets:
                dets.append(vortex)
            if sgz_vortex not in dets:
                dets.append(sgz_vortex)

        return dets  # this should have all scalers by default
    # If counting against a monitor, it only works if the detectors is in the
    # same scaler channel.
    else:
        if counters.monitor == "Time":
            raise ValueError(
                "Monitor is set to 'Time', but you are trying to count against "
                "a scaler channel. Please run counters.plotselect() to change "
                "the monitor to a scaler channel."
            )

        monitor_scaler = counters.detectors_plot_options.loc[
            counters.detectors_plot_options["channels"] == counters.monitor
        ]["detectors"].iloc[0]

        if any(
            [
                det_name != monitor_scaler
                for det_name in counters.selected_plot_detectors
            ]
        ):
            raise ValueError(
                "You can only count against monitor if all detectors are in "
                "the same scaler of the monitor. But "
                f"{counters.selected_plot_detectors} have been selected."
                "Run counters.plotselect() to change the detector channels."
            )

        return [oregistry.find(monitor_scaler)]


def count(
    num,
    time,
    detectors=None,
    lockin=False,
    dichro=False,
    vortex_sgz=False,
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

    flag.vortex_sgz = vortex_sgz

    fixq = False
    if detectors is None:
        detectors = setup_detectors(time > 0)

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step * _offset for step in _steps]

    flag.fixq = fixq

    if per_shot is not None and (fixq or dichro):
        logger.warning(
            "there is a custom per_shot, but fixQ or dichro was selected."
        )
    elif per_shot is None:
        per_shot = one_local_shot if fixq or dichro else None

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_paths(
        detectors
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(("",))

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    _md = dict(
        hints={"monitor": counters.monitor, "detectors": []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])

    _md.update(md or {})

    @monitor_during_decorator([dichro_device] if dichro else [])
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, [None])
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

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        # detectors = counters.detectors
        detectors = setup_detectors(time > 0)

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step * _offset for step in _steps]

    flag.fixq = fixq
    if per_step is None:
        per_step = one_local_step if fixq or dichro else None
    if fixq:
        huber = current_diffractometer()
        flag.hkl_pos = {
            huber.h: huber.h.get().setpoint,
            huber.k: huber.k.get().setpoint,
            huber.l: huber.l.get().setpoint,
        }

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_paths(
        detectors
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(args)

    _md = dict(
        hints={"monitor": counters.monitor, "detectors": []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])

    _md["hints"]["scan_type"] = "ascan"

    _md.update(md or {})

    motors = [motor for motor, _, _ in partition(3, args)]

    @monitor_during_decorator([dichro_device] if dichro else [])
    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, motors)
    @extra_devices_decorator(extras)
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
        special mode that requires the 'vortex' and 'sgz_vortex' devices to\
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

    _md = {"plan_name": "rel_scan"}
    md = md or {}
    _md.update(md)
    motors = [motor for motor, _, _ in partition(3, args)]

    @reset_positions_decorator(motors)
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
                per_step=per_step,
                md=_md,
            )
        )

    return (yield from inner_lup())


def grid_scan(
    *args,
    detectors=None,
    snake_axes=None,
    lockin=False,
    dichro=False,
    fixq=False,
    vortex_sgz=False,
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

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        detectors = setup_detectors(time > 0)

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step * _offset for step in _steps]

    flag.fixq = fixq
    if per_step is None:
        per_step = one_local_step if fixq or dichro else None

    if fixq:
        huber = current_diffractometer()
        flag.hkl_pos = {
            huber.h: huber.h.get().setpoint,
            huber.k: huber.k.get().setpoint,
            huber.l: huber.l.get().setpoint,
        }

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_paths(
        detectors
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    extras = yield from _collect_extras(args)

    _md = dict(
        hints={"monitor": counters.monitor, "detectors": []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    for item in detectors:
        _md["hints"]["detectors"].extend(item.hints["fields"])

    _md["hints"]["scan_type"] = "gridscan"

    _md.update(md or {})

    motors = [m[0] for m in chunk_outer_product_args(args)]

    @monitor_during_decorator([dichro_device] if dichro else [])
    @subs_decorator(nxwriter.receiver)
    @configure_counts_decorator(detectors, time)
    @stage_dichro_decorator(dichro, lockin, motors)
    @extra_devices_decorator(extras)
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

    flag.vortex_sgz = vortex_sgz

    if detectors is None:
        detectors = setup_detectors(time > 0)

    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = pr_setup.positioner.parent.center.get()
        _steps = pr_setup.dichro_steps
        flag.dichro_steps = [_center + step * _offset for step in _steps]

    flag.fixq = fixq

    if per_step is None:
        per_step = one_local_step if fixq or dichro else None

    if fixq:
        huber = current_diffractometer()
        flag.hkl_pos = {
            huber.h: huber.h.get().setpoint,
            huber.k: huber.k.get().setpoint,
            huber.l: huber.l.get().setpoint,
        }

    # Get energy argument and extras

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

    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_paths(
        detectors
    )

    setup_nxwritter(
        experiment.experiment_path, _master_fullpath, _rel_dets_paths
    )

    _md = dict(
        hints={"monitor": counters.monitor, "detectors": []},
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(_master_fullpath),
        detectors_file_full_path=_dets_file_paths,
        detectors_file_relative_path=_rel_dets_paths,
    )

    # TODO: The md handling might go well in a decorator.
    # TODO: May need to add reference to stream.
    # _md = {'hints': {'monitor': counters.monitor, 'detectors': []}}
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
    @stage_dichro_decorator(dichro, lockin, [energy])
    @extra_devices_decorator(extras)
    def _inner_qxscan():
        yield from list_scan(
            detectors + extras, *args, per_step=per_step, md=_md
        )

        # put original times back.
        for det, preset in _ct.items():
            yield from mv(det.preset_monitor, preset)

        yield from nxwriter.wait_writer_plan_stub()

    return (yield from _inner_qxscan())


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

    def _inner_abs_set():
        yield from bps_abs_set(*args, **kwargs)

    return (yield from _inner_abs_set())
