"""Transfocator."""

from logging import getLogger
from time import sleep as tsleep

from apstools.devices import TrackingSignal
from bluesky.plan_stubs import mv
from numpy import loadtxt
from ophyd import Component
from ophyd import Device
from ophyd import DeviceStatus
from ophyd import DynamicDeviceComponent
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import EpicsSignalWithRBV
from ophyd import FormattedComponent
from ophyd import PVPositioner
from ophyd import Signal
from ophyd.status import AndStatus
from scipy.interpolate import interp1d
from toolz import partition

logger = getLogger(__name__)
DEFAULT_MOTORS_IOC = "4idgSoft:"
EPICS_ENERGY_SLEEP = 0.15


def _make_lenses_motors(motors: list):
    defn = {}
    for n, mot in enumerate(motors):
        defn[f"l{n}"] = (
            EpicsMotor,
            f"{mot}",
            dict(kind="config", labels=("motor",)),
        )
    return defn


class PyCRLSingleLens(PVPositioner):
    """Single CRL lens stack positioner."""

    readback = Component(EpicsSignalRO, "_RBV")
    setpoint = Component(EpicsSignal, "", put_complete=True)

    done = Component(EpicsSignal, "_matchCalc.C")
    done_value = 1

    # Settings
    num_lenses = Component(EpicsSignal, "_NumLens", kind="config")
    radius = Component(EpicsSignal, "_LensRadius", kind="config")
    location = Component(EpicsSignal, "_Location", kind="config")
    material = Component(EpicsSignal, "_Material", kind="config")
    thickness_error = Component(EpicsSignal, "_ThickErr", kind="config")
    in_limit = Component(EpicsSignal, "_RBV_calc.CC", kind="config")

    def set(
        self,
        new_position,
        *,
        timeout: float = None,
        moved_cb=None,
        wait: bool = False,
    ):
        """Set lens position, returning immediately if already there."""
        if self.readback.get() == new_position:
            _status = DeviceStatus(self)
            _status.set_finished()
            return _status
        else:
            return super().set(
                new_position, timeout=timeout, moved_cb=moved_cb, wait=wait
            )


class PyCRLSignal(EpicsSignal):
    """EpicsSignal with a value sub-component and EGU readback."""

    value = Component(EpicsSignal, "")
    egu = Component(EpicsSignalRO, ".EGU")


class PyCRL(Device):
    """PyCRL compound refractive lens controller."""

    # Energy
    energy_mono = Component(PyCRLSignal, "EnergyBeamline", kind="config")
    energy_local = Component(PyCRLSignal, "EnergyLocal", kind="config")
    energy_select = Component(PyCRLSignal, "EnergySelect", kind="config")

    # Slits
    slit_hor_size = Component(PyCRLSignal, "1:slitSize_H_RBV", kind="config")
    slit_hor_pv = Component(
        EpicsSignal, "1:slitSize_H.DOL", string=True, kind="config"
    )
    slit_vert_size = Component(PyCRLSignal, "1:slitSize_V_RBV", kind="config")
    slit_vert_pv = Component(
        EpicsSignal, "1:slitSize_V.DOL", string=True, kind="config"
    )

    # Focus info/control
    focal_size_setpoint = Component(EpicsSignal, "focalSize")
    focal_size_readback = Component(EpicsSignalRO, "fSize_actual")
    focal_power_index = Component(EpicsSignalWithRBV, "1:sortedIndex")
    focal_sizes = Component(EpicsSignal, "fSizes", kind="omitted")
    minimize_button = Component(
        EpicsSignal, "minimizeFsize.PROC", kind="omitted"
    )
    system_done = Component(EpicsSignalRO, "sysBusy", kind="omitted")

    # Parameters readbacks
    dq = Component(PyCRLSignal, "dq", kind="config")
    q = Component(PyCRLSignal, "q", kind="config")
    z_offset = Component(PyCRLSignal, "1:oePositionOffset_RBV", kind="config")
    z_offset_pv = Component(
        EpicsSignal, "1:oePositionOffset.DOL", kind="config"
    )
    z_from_source = Component(PyCRLSignal, "1:oePosition_RBV", kind="config")
    sample_offset = Component(
        PyCRLSignal, "samplePositionOffset_RBV", kind="config"
    )
    sample_offset_pv = Component(
        EpicsSignal, "samplePositionOffset.DOL", kind="config"
    )
    sample = Component(PyCRLSignal, "samplePosition_RBV", kind="config")

    # Lenses indices
    binary = Component(EpicsSignalRO, "1:lenses", kind="config")
    ind_control = Component(EpicsSignalRO, "1:lensConfig_BW", kind="config")
    readbacks = Component(EpicsSignalRO, "1:lensConfig_RBV", kind="config")

    # Other options
    preview_index = Component(EpicsSignal, "previewIndex", kind="config")
    focal_size_preview = Component(
        EpicsSignalRO, "fSize_preview", kind="config"
    )
    inter_lens_delay = Component(EpicsSignal, "1:interLensDelay", kind="config")
    verbose_console = Component(EpicsSignal, "verbosity", kind="config")
    thickness_error_flag = Component(
        EpicsSignal, "thickerr_flag", kind="config"
    )
    beam_mode = Component(EpicsSignalWithRBV, "beamMode", kind="config")

    # Lenses
    lens1 = Component(PyCRLSingleLens, "1:stack01")
    lens2 = Component(PyCRLSingleLens, "1:stack02")
    lens3 = Component(PyCRLSingleLens, "1:stack03")
    lens4 = Component(PyCRLSingleLens, "1:stack04")
    lens5 = Component(PyCRLSingleLens, "1:stack05")
    lens6 = Component(PyCRLSingleLens, "1:stack06")
    lens7 = Component(PyCRLSingleLens, "1:stack07")
    lens8 = Component(PyCRLSingleLens, "1:stack08")

    def __init__(self, *args, **kwargs):
        """Initialize PyCRL device."""
        super().__init__(*args, **kwargs)
        self._status = None

    def _post_connect_setup(self):
        """Set up EPICS subscriptions after connection is established."""
        self.system_done.subscribe(self._update_status_subscription, run=False)

    def _update_status_subscription(self, value, old_value, **kwarg):
        if (
            (self._status is not None)
            and (value in ["Done", 0])
            and (old_value in ["Changing", 1])
        ):
            self._status.set_finished()
            self._status = None

    def set(self, value, **kwargs):
        """Set the system state."""
        _st = DeviceStatus(self)

        if self.system_done.get() in ["Done", 0]:
            _st.set_finished()
        else:
            self._status = _st

        return _st


class EnergySignal(Signal):
    """Signal that moves the transfocator to a new energy."""

    _epics_sleep = EPICS_ENERGY_SLEEP

    def put(self, *args, **kwargs):
        """Raise NotImplementedError — use set() instead."""
        raise NotImplementedError("put operation not setup in this signal.")

    def set(self, value, **kwargs):
        """Move transfocator to the specified energy."""
        self._readback = value

        if self.parent.energy_select.get() != 1:
            self.parent.energy_select.set(1).wait(1)

        self.parent.energy_local.set(value).wait(1)
        tsleep(self._epics_sleep)
        # this is needed because the scan of the transfocator is 0.1 s

        zpos = self.parent.z.user_readback.get() - self.parent.dq.get() * 1000.0
        # dq in meters

        return self.parent.z.set(zpos, **kwargs)


class ZMotor(EpicsMotor):
    """EpicsMotor that optionally tracks X/Y when Z moves."""

    def set(self, new_position, **kwargs):
        """Move Z and optionally track X/Y."""
        zstatus = super().set(new_position, **kwargs)

        if self.parent.trackxy.get():
            if self.parent._x_interpolation is None:
                raise ValueError(
                    "The reference data for X tracking has not been entered. "
                    "Cannot track the X motion."
                )

            if self.parent._y_interpolation is None:
                raise ValueError(
                    "The reference data for Y tracking has not been entered. "
                    "Cannot track the Y motion."
                )

            xpos = (
                self.parent._x_interpolation(new_position)
                + self.parent.deltax.get()
            )
            ypos = (
                self.parent._y_interpolation(new_position)
                + self.parent.deltay.get()
            )

            xystatus = AndStatus(
                self.parent.x.set(xpos), self.parent.y.set(ypos)
            )

            return AndStatus(zstatus, xystatus)
        else:
            return zstatus

    def stop(self, *, success=False):
        """Stop Z and optionally X/Y."""
        super().stop(success=success)
        if self.parent.trackxy.get():
            self.parent.x.stop(success=success)
            self.parent.y.stop(success=success)


def make_transfocator_class(motors_ioc=DEFAULT_MOTORS_IOC):
    """Return a TransfocatorClass with lens motors bound to motors_ioc.

    Parameters
    ----------
    motors_ioc : str
        IOC prefix for the transfocator stage motors, e.g. ``"4idgSoft:"``.
    """
    lens_list = [f"{motors_ioc}m{n}" for n in [69, 68, 67, 66, 65, 64, 63, 62]]

    class TransfocatorClass(PyCRL):
        """Transfocator with parametric motor IOC prefix."""

        energy = Component(EnergySignal)
        tracking = Component(TrackingSignal, value=False, kind="config")

        # Motors
        x = FormattedComponent(
            EpicsMotor, "{_motors_IOC}m58", labels=("motor",)
        )
        y = FormattedComponent(
            EpicsMotor, "{_motors_IOC}m57", labels=("motor",)
        )
        z = FormattedComponent(ZMotor, "{_motors_IOC}m61", labels=("motor",))
        pitch = FormattedComponent(
            EpicsMotor, "{_motors_IOC}m60", labels=("motor",)
        )
        yaw = FormattedComponent(
            EpicsMotor, "{_motors_IOC}m59", labels=("motor",)
        )

        lens_motors = DynamicDeviceComponent(
            _make_lenses_motors(lens_list),
            component_class=FormattedComponent,
        )

        reference_data_x = Component(Signal, kind="config")
        reference_data_y = Component(Signal, kind="config")
        deltax = Component(Signal, value=0, kind="config")
        deltay = Component(Signal, value=0, kind="config")
        trackxy = Component(TrackingSignal, value=False, kind="config")

        def __init__(
            self,
            *args,
            motors_ioc=motors_ioc,
            lens_pos=30,
            default_distance=2591,
            **kwargs,
        ):
            """Initialize TransfocatorClass with motor IOC prefix."""
            self._motors_IOC = motors_ioc
            PyCRL.__init__(self, *args, **kwargs)
            self._lens_pos = lens_pos
            self._default_distance = default_distance  # mm
            self._x_interpolation = None
            self._y_interpolation = None
            self.reference_data_x.subscribe(
                self._update_interpolation_x, run=False
            )
            self.reference_data_y.subscribe(
                self._update_interpolation_y, run=False
            )

        def load_reference_data(self, fname, axis):
            """Load reference tracking data from file."""
            if axis not in "x y".split():
                raise ValueError(f"axis must be x or y. {axis} is not valid.")
            getattr(self, f"reference_data_{axis}").put(loadtxt(fname))

        def _update_interpolation_x(self, value, **kwargs):
            z = value[:, 0]
            x = value[:, 1]
            self._x_interpolation = interp1d(z, x)

        def _update_interpolation_y(self, value, **kwargs):
            z = value[:, 0]
            y = value[:, 1]
            self._y_interpolation = interp1d(z, y)

        def lens_status(self, i):
            """Return the status string of lens i."""
            return getattr(self, f"lens{i}").readback.get(as_string=True)

        @property
        def lenses_in(self):
            """Return list of inserted lens indices."""
            selected = []
            for i in range(1, 9):
                _status = self.lens_status(i)
                if _status == "In":
                    selected.append(i)
                elif _status == "Both out":
                    pass
            return selected

        def _setup_lenses_move(self, lenses_in: list = None):
            """Build args list for moving lenses in/out.

            Parameters
            ----------
            lenses_in : list or iterable
                Index of the lenses that will be inserted. The ones not in
                this list will be removed.
            """
            if lenses_in is None:
                lenses_in = []
            for i in lenses_in:
                if (i > 8) or (i < 1):
                    raise ValueError("Lens index must be from 1 to 8.")

            args = []
            for lens in range(1, 9):
                step = 1 if lens in lenses_in else 0
                args += [getattr(self, f"lens{lens}"), step]

            return args

        def set_lenses(self, selected_lenses: list):
            """Move lenses to the specified in/out configuration."""
            args = self._setup_lenses_move(selected_lenses)
            for dev, pos in partition(2, args):
                dev.setpoint.put(pos)

        def set_lenses_plan(self, selected_lenses: list):
            """Bluesky plan to move lenses to the specified configuration."""
            args = self._setup_lenses_move(selected_lenses)
            return (yield from mv(*args))

        def _check_z_lims(self, position):
            if (position > self.z.low_limit_travel.get()) & (
                position < self.z.high_limit_travel.get()
            ):
                return True
            else:
                return False

        def _setup_optimize_distance(self):
            if self.energy_select.get() in (1, "Local"):
                logger.info("WARNING: transfocator in 'Local' energy mode")

            distance = self.z.user_readback.get() - self.dq.get() * 1000

            if not self._check_z_lims(distance):
                raise ValueError(
                    f"The distance {distance} is outsize the Z travel "
                    "range. No motion will occur."
                )

            return distance

        def optimize_lenses(self):
            """Optimize lens configuration for minimum focal size."""
            self.focal_power_index.set(self.focal_sizes.get().argmin()).wait()

            self.z.move(self._setup_optimize_distance()).wait()

            self.set(1).wait()

        def optimize_lenses_plan(self):
            """Bluesky plan to optimize lens configuration."""

            def _moves():
                yield from mv(
                    self.focal_power_index,
                    self.focal_sizes.get().argmin(),
                )
                yield from mv(self.z, self._setup_optimize_distance(), self, 1)

            return (yield from _moves())

        def optimize_distance(self):
            """Move Z to the optimal focal distance."""
            self.z.move(self._setup_optimize_distance()).wait()

        def optimize_distance_plan(self):
            """Bluesky plan to move Z to the optimal focal distance."""
            return (yield from mv(self.z, self._setup_optimize_distance()))

        def default_settings(self):
            """Apply default stage signals for transfocator."""
            self.stage_sigs["energy_select"] = 1

    TransfocatorClass.__name__ = "TransfocatorClass"
    TransfocatorClass.__qualname__ = "TransfocatorClass"
    return TransfocatorClass


# Module-level default — backward-compatible; used by devices.yml as-is.
TransfocatorClass = make_transfocator_class()
