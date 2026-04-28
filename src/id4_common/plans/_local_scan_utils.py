"""Private helpers shared by local_scans.py plans."""

from logging import getLogger
from pathlib import Path

from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from bluesky.plan_stubs import move_per_step
from bluesky.plan_stubs import mv as bps_mv
from bluesky.plan_stubs import rd
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import finalize_wrapper

from ..callbacks.nexus_data_file_writer import nxwriter
from ..utils.counters_class import counters
from ..utils.experiment_utils import experiment
from ..utils.hkl_utils import current_diffractometer
from ..utils.run_engine import RE

try:
    from ..utils.pr_setup import pr_setup
except ModuleNotFoundError:
    pr_setup = None

iconfig = get_config()
HDF1_NAME_FORMAT = Path(iconfig["AREA_DETECTOR"]["HDF5_FILE_TEMPLATE"])
logger = getLogger(__name__)
logger.info(__file__)


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
    center = 0 if pr_setup.oscillate_pzt else pr_setup.positioner.position

    for pos in flag.dichro_steps:
        yield from bps_mv(pr_setup.positioner, pos + center)
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
            # yield from sleep(vortex._sleep_after_trigger)
            # logger.debug(vortex._sleep_after_trigger)

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


def _setup_detectors(time):
    """Resolve the detector list from counters based on count mode and flags.

    If time > 0, returns counters.detectors (possibly augmented with vortex_sgz
    devices). If time <= 0, validates that a single scaler can be used as
    monitor and returns it.
    """
    # If counting against time, then all good, can just use the detectors
    # setup in counters
    if time > 0:
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

            vortex._vortex_sgz = True

            freq = 1 / sgz_vortex.div_by_n.n.get() * sgz_vortex.clock_freq.get()
            pulses = int(time * freq)
            sgz_vortex.down_counter_pulse.preset.set(pulses).wait(5)

        return dets  # this should have all scalers by default
    # If counting against a monitor, it only works if the monitor is a scaler
    # channel and all detectors are in the same scaler.
    else:
        if not counters.is_scaler_monitor:
            return counters.detectors

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


def _configure_dichro(dichro):
    """Set flag.dichro and compute flag.dichro_steps from pr_setup."""
    flag.dichro = dichro
    if dichro:
        _offset = pr_setup.offset.get()
        _center = (
            pr_setup.positioner.parent.center.get()
            if pr_setup.oscillate_pzt
            else -1 * _offset
        )
        flag.dichro_steps = [
            _center + step * _offset for step in pr_setup.dichro_steps
        ]


def _configure_fixq(fixq):
    """Set flag.fixq and snapshot current HKL position into flag.hkl_pos."""
    flag.fixq = fixq
    if fixq:
        huber = current_diffractometer()
        flag.hkl_pos = {
            huber.h: huber.h.get().setpoint,
            huber.k: huber.k.get().setpoint,
            huber.l: huber.l.get().setpoint,
        }


def _hkl_motors(fixq):
    """
    Return the real (physical) motors of the diffractometer when fixq is True.

    Uses the actual motors rather than pseudo-motors so that the snapshot/
    reset wrapper can restore hardware positions directly, without depending
    on the current sample orientation or UB matrix.
    """
    if not fixq:
        return []
    huber = current_diffractometer()
    return list(huber.real_positioners) if huber is not None else []


def reset_real_motors_decorator(motors):
    """Snapshot motor positions at plan start and restore them on finalize.

    Unlike :func:`bluesky.preprocessors.reset_positions_decorator`, which
    records a position only when it observes a ``set`` message on the device,
    this decorator reads ``obj.position`` immediately when the plan begins
    iterating and restores it via ``mv`` in a ``finalize_wrapper``.

    Required for diffractometer real positioners that move via
    ``PseudoPositioner`` inverse kinematics (h/k/l ``set`` messages do not
    propagate as ``set`` messages on the underlying real motors), so
    ``reset_positions_decorator`` would never stash — and therefore never
    restore — their initial positions.
    """

    def decorator(plan_func):
        def inner(*args, **kwargs):
            initial = [(m, m.position) for m in motors]

            def reset():
                if not initial:
                    return
                pairs = []
                for m, v in initial:
                    pairs += [m, v]
                yield from bps_mv(*pairs)

            return (
                yield from finalize_wrapper(plan_func(*args, **kwargs), reset())
            )

        return inner

    return decorator


def _default_per_step(fixq, dichro, vortex_sgz):
    """Return one_local_step when any special scan mode is active, else None."""
    return one_local_step if (fixq or dichro or vortex_sgz) else None


def _default_per_shot(dichro, vortex_sgz):
    """Return one_local_shot when any special scan mode is active, else None."""
    return one_local_shot if (dichro or vortex_sgz) else None


def _build_scan_md(
    detectors,
    master_path,
    dets_file_paths,
    rel_dets_paths,
    dichro=False,
    lockin=False,
):
    """Build the base metadata dict common to all local scan plans."""
    if dichro:
        polarization = "dichro"
    elif lockin:
        polarization = "lockin"
    else:
        polarization = "fixed"

    return dict(
        hints={
            "monitor": counters.monitor_field,
            "detectors": [],
            "polarization": polarization,
        },
        data_management=experiment.data_management or "None",
        esaf=experiment.esaf,
        proposal=experiment.proposal,
        base_experiment_path=str(experiment.base_experiment_path),
        experiment_path=str(experiment.experiment_path),
        master_file_path=str(master_path),
        detectors_file_full_path=dets_file_paths,
        detectors_file_relative_path=rel_dets_paths,
    )


def _check_magnet911(args):
    """Return True when the magnet911 field motor appears in scan args."""
    magnet911 = oregistry.find("magnet911", allow_none=True)
    return False if magnet911 is None else (magnet911.ps.field in args)


def _setup_file_io(detectors):
    """Set up file I/O for a scan with validate-before-configure ordering.

    Three phases to ensure no detector PVs are written if any output file
    already exists (Issue #16):

    Phase 1 — predict: compute all output paths without any EPICS I/O.
    Phase 2 — validate: raise FileExistsError if any path already exists.
    Phase 3 — configure: write PVs on each detector and configure nxwriter.

    Parameters
    ----------
    detectors : list
        Detector devices for this scan (may include non-saving devices).

    Returns
    -------
    master_fullpath : str
        Full path to the NeXus master file.
    dets_file_paths : dict
        Mapping of detector name to full output file path string.
    rel_dets_paths : dict
        Mapping of detector name to relative output file path string.
    """
    if None in (experiment.base_experiment_path, experiment.file_base_name):
        raise ValueError(
            "The experiment needs to be setup, please run experiment_setup()"
        )

    _scan_id = RE.md["scan_id"] + 1

    # Phase 1: predict paths (no PV writes)
    _master_fullpath = (
        str(HDF1_NAME_FORMAT)
        % (
            str(experiment.experiment_path),
            experiment.file_base_name,
            _scan_id,
        )
        + "_master.hdf"
    )

    _predicted = {}  # det.name -> (predicted_full_path, det)
    for det in list(detectors):
        _has_setup = getattr(det, "setup_images", None)
        _flag = getattr(det, "save_image_flag", False)
        if _has_setup and _flag:
            _fp, _rp = det.predict_save_path(
                experiment.experiment_path,
                experiment.file_base_name,
                _scan_id,
            )
            if _fp is not None:
                _predicted[det.name] = (_fp, det)

    # Phase 2: validate — raise before any PV writes
    for _fname in [_master_fullpath] + [
        str(fp) for fp, _ in _predicted.values()
    ]:
        if Path(_fname).is_file():
            raise FileExistsError(
                f"The file {_fname} already exists!"
                " Will not overwrite, quitting."
            )

    # Phase 3: configure detectors (PV writes only after validation passes)
    _dets_file_paths = {}
    _rel_dets_paths = {}
    for name, (_fp, det) in _predicted.items():
        fp, rp = det.setup_images(
            experiment.experiment_path,
            experiment.file_base_name,
            _scan_id,
            flyscan=False,
        )
        _dets_file_paths[name] = str(fp)
        _rel_dets_paths[name] = str(rp)

    nxwriter.external_files = _rel_dets_paths
    nxwriter.file_name = str(_master_fullpath)
    nxwriter.file_path = str(experiment.experiment_path)

    return _master_fullpath, _dets_file_paths, _rel_dets_paths
