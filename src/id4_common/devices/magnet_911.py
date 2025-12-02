"""
9T magnet
"""

from ophyd import (
    Device,
    Component,
    DynamicDeviceComponent,
    FormattedComponent,
    EpicsMotor,
    EpicsSignalRO,
    EpicsSignal,
    PVPositioner
)
from ophyd.status import Status
from apstools.devices import PVPositionerSoftDoneWithStop
from collections import OrderedDict


class TableMotors(Device):
    x = Component(EpicsMotor, "m14", labels=("motor",))
    y = Component(EpicsMotor, "m15", labels=("motor",))
    z = Component(EpicsMotor, "m16", labels=("motor",))

    sx = Component(EpicsMotor, "m18", labels=("motor",))
    sz = Component(EpicsMotor, "m19", labels=("motor",))
    srot = Component(EpicsMotor, "m17", labels=("motor",))


class RamanMotors(Device):
    x = Component(EpicsMotor, "m24", labels=("motor",))
    y = Component(EpicsMotor, "m25", labels=("motor",))
    z = Component(EpicsMotor, "m26", labels=("motor",))

    tilt = Component(EpicsMotor, "m27", labels=("motor",))
    rot = Component(EpicsMotor, "m28", labels=("motor",))


class MagnetMotors(Device):
    y = FormattedComponent(EpicsMotor, "4idhAero:m2", labels=("motor",))
    th = FormattedComponent(EpicsMotor, "4idhAero:m1", labels=("motor",))



class FieldPositioner(PVPositioner):
    setpoint = Component(
        EpicsSignal, "TargetField", write_pv = "SetField.VAL", put_complete=True
    )

    readback = Component(EpicsSignalRO, "Field", kind="hinted")

    actuate = Component(EpicsSignal, "StartRamp.PROC", kind="omitted")
    actuate_value = 1

    # TODO: Should I make a stop logic? What about pause? there is a pause
    # button.
    # stop_signal = Component(EpicsSignal, "SetAbort.PROC", kind="omitted")
    # stop_value = 1

    done = Component(EpicsSignalRO, "Ready", kind="omitted")
    done_value = 1

    current = Component(EpicsSignalRO, "Current")
    voltage = Component(EpicsSignalRO, "Voltage", kind="config")

    egu_readback = Component(
        EpicsSignalRO, "TargetFieldUnits", string=True, kind="config"
    )
    egu_setpoint = Component(
        EpicsSignal,
        "TargetFieldUnits",
        write_pv="SetTargetFieldUnits",
        string=True,
        kind="config",
    )       

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readback.name = self.name
        self._tolerance = 0.05

    def move(self, position, wait=True, timeout=None, moved_cb=None):

        if (
            (self.parent.heater.get() in [0, "ON"]) &
            (abs(position-self.readback.get()) < self._tolerance)
        ):
            status = Status()
            status.set_finished()
            return status
        else:
            return super().move(
                position, wait=wait, timeout=timeout, moved_cb=moved_cb
            )


class PowerSupply(Device):

    field = Component(FieldPositioner, "")

    active_coil = Component(EpicsSignal, "SetActiveCoil", string=True)

    safety_message = FormattedComponent(
        EpicsSignalRO,
        "4idhSoft:911TMagnet:safety_msg.SVAL",
        string=True,
    )

    status = Component(EpicsSignalRO, "Status", string=True, kind="config")
    ready = Component(EpicsSignalRO, "Ready", kind="config")
    heater = Component(EpicsSignalRO, "Heater", string=True, kind="config")
    quench = Component(EpicsSignalRO, "Quench", string=True, kind="config")
    helium = Component(EpicsSignalRO, "HeliumLevel")
    persistent_field = Component(EpicsSignalRO, "PersField")

    ramp_rate = Component(
        EpicsSignal, "RampRate", write_pv="SetRampRate.VAL", kind="config"
    )
    ramp_rate_unit = Component(
        EpicsSignal,
        "RampRateUnits",
        write_pv="SetRampRateUnits",
        string=True,
        kind="config",
    )
    set_ignore_table = Component(
        EpicsSignal, "SetIgnoreTable", kind="config"
    )

    set_persistent = Component(
        EpicsSignal, "SetPersistent.PROC", kind="omitted"
    )
    set_pm_zero = Component(
        EpicsSignal, "SetPMZero.PROC", kind="omitted"
    )

    ramp_pause = Component(EpicsSignal, "SetPause", kind="config")
    ramp_start = Component(EpicsSignal, "StartRamp.PROC", kind="omitted")
    ramp_abort = Component(EpicsSignal, "SetAbort.PROC", kind="omitted")

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class MonChannel(Device):
    temperature_name = FormattedComponent(EpicsSignalRO, "{prefix}TempName{ch}")
    temperature = FormattedComponent(EpicsSignalRO, "{prefix}Temp{ch}")
    hall_resistance = FormattedComponent(EpicsSignalRO, "{prefix}HallRes{ch}")
    hall_field = FormattedComponent(EpicsSignalRO, "{prefix}HallField{ch}")

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")

    def __init__(self, *args, ch_num=1, **kwargs):
        self.ch = ch_num
        super().__init__(*args, **kwargs)


def _make_monitors(num=1):
    defn = OrderedDict()
    for i in range(1, num + 1):
        defn[f"m{i :02d}"] = (
            MonChannel,
            "911TMagnet:TMon:",
            {"ch_num": i, "kind": "normal"},
        )

    return defn


# TODO: Change these names to something more meaningful.
class VTIDevice(Device):
    sensor_a = Component(
        EpicsSignalRO, "SensorA", kind="hinted", labels=["temperature"]
    )

    sensor_b = Component(
        EpicsSignalRO, "SensorB", kind="hinted", labels=["temperature"]
    )

    sensor_c = Component(
        EpicsSignalRO, "SensorC", kind="hinted", labels=["temperature"]
    )

    sensor_d = Component(
        EpicsSignalRO, "SensorD", kind="hinted", labels=["temperature"]
    )

    setpoint_1 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint1",
        setpoint_pv="SetTemp1",
        tolerance=0.01,
    )

    setpoint_2 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint2",
        setpoint_pv="SetTemp2",
        tolerance=0.01,
    )

    setpoint_3 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint3",
        setpoint_pv="SetTemp3",
        tolerance=0.01,
    )

    setpoint_4 = Component(
        PVPositionerSoftDoneWithStop,
        "",
        readback_pv="Setpoint4",
        setpoint_pv="SetTemp4",
        tolerance=0.01,
    )

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class NVDevice(Device):
    control_mode = Component(
        EpicsSignal, "SetControlMode", string=True, kind="config"
    )

    pressure_control_switch = Component(
        EpicsSignal, "SetPressureControl", string=True, kind="config"
    )

    temp = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetTargetTemperature",
        readback_pv="Temperature",
        kind="config",
    )

    pressure = Component(
        PVPositionerSoftDoneWithStop,
        "",
        setpoint_pv="SetTargetPressure",
        readback_pv="Pressure",
        kind="config",
    )

    read_button = Component(EpicsSignal, "Read.PROC", kind="omitted")
    read_scan = Component(EpicsSignal, "Read.SCAN", string=True, kind="omitted")


class Magnet911(Device):

    connection = Component(EpicsSignalRO, "911TMagnet:asyn.CNCT", kind="config")

    tab = Component(TableMotors, "")
    raman = Component(RamanMotors, "")
    samp = Component(MagnetMotors, "911TMagnet:Motor:")

    ps = Component(PowerSupply, "911TMagnet:PSU:", labels=["magnet"])

    monitors = DynamicDeviceComponent(_make_monitors(num=6))

    temps = Component(VTIDevice, "911TMagnet:VTI:")

    needle_valve = Component(NVDevice, "911TMagnet:NV:")
