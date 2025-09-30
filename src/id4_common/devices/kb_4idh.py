from ophyd import Component, Device, EpicsSignalRO, EpicsMotor

# TODO: Will add some as read only for now, but may be able to run as motors.

# This is very similar to the g KB, but not the same motor numbers...


class Vertical(Device):
    ds_piezo = Component(EpicsMotor, "m2", labels=("motor",))
    ds_pico = Component(EpicsMotor, "m8")
    ds_capsensor = Component(EpicsSignalRO, "m16.RBV")

    us_piezo = Component(EpicsMotor, "m1", labels=("motor",))
    us_pico = Component(EpicsMotor, "m7", labels=("motor",))
    us_capsensor = Component(EpicsSignalRO, "m15.RBV")

    y = Component(EpicsSignalRO, "vert:t2.D")
    thx = Component(EpicsSignalRO, "vert:t2.C")

    stripe = Component(EpicsMotor, "m20", labels=("motor",))


class Horizontal(Device):
    # Pitch angle
    thy_piezo = Component(EpicsMotor, "m6", labels=("motor",))
    thy_pico = Component(EpicsMotor, "m11", labels=("motor",))
    thy_capsensor = Component(EpicsSignalRO, "m19.RBV")
    thy = Component(EpicsSignalRO, "SM1.RBV")

    # Roll
    thz_pico = Component(EpicsMotor, "m14", labels=("motor",))
    thz_capsensor = Component(EpicsSignalRO, "cap2:pos")
    thz = Component(EpicsSignalRO, "SM2.RBV")

    # Normal
    x_piezo = Component(EpicsMotor, "m4", labels=("motor",))
    x_pico = Component(EpicsMotor, "m12", labels=("motor",))
    x = Component(EpicsSignalRO, "m18.RBV")

    # Along beam
    z_piezo = Component(EpicsMotor, "m5", labels=("motor",))
    z_pico = Component(EpicsMotor, "m13", labels=("motor",))
    z = Component(EpicsSignalRO, "m17.RBV")

    # Stripe
    stripe = Component(EpicsMotor, "m22", labels=("motor",))


class KBDevice(Device):
    v = Component(Vertical, "")
    h = Component(Horizontal, "")
