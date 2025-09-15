"""
Toroidal Mirror
"""


from ophyd import (
    Component,
    Device,
    EpicsMotor,
    EpicsSignal,
    EpicsSignalRO,
)

class MR3(Device):

    # Combined motions motors
    y = Component(EpicsMotor, "m11", labels=("motor",))
    yaw = Component(EpicsMotor, "m12", labels=("motor",))
    x = Component(EpicsMotor, "m13", labels=("motor",))
    pitch = Component(EpicsMotor, "m14", labels=("motor",))

    # Individual motors
    yu = Component(EpicsMotor, "m1", labels=("motor",))
    yd = Component(EpicsMotor, "m2", labels=("motor",))
    xu = Component(EpicsMotor, "m3", labels=("motor",))
    xd = Component(EpicsMotor, "m4", labels=("motor",))

    # Stripe settings
    stripe_setpoint = Component(EpicsSignal, "MR3:Stripe", string=True)
    stripe_readback = Component(EpicsSignalRO, "MR3:StripeRBV", string=True)

    pos_silicon = Component(EpicsSignal, "MR3:SiPosition")
    pos_palladium = Component(EpicsSignal, "MR3:PdPosition")
    pos_platinum = Component(EpicsSignal, "MR3:PtPosition")

    # Bender motors and settings
    bender_avg = Component(EpicsMotor, "mr3:pm1", labels=("motor",))
    bender_dif = Component(EpicsMotor, "mr3:pm2", labels=("motor",))

    bender_u = Component(EpicsMotor, "m5", labels=("motor",))
    bender_d = Component(EpicsMotor, "m6", labels=("motor",))

    radius_setpoint = Component(EpicsSignal, "MR3:TargetRadius")
    radius_readback = Component(
        EpicsSignalRO, "MR3:RadiusEstimateDisp.SVAL"
    )
    flat_button = Component(EpicsSignal, "MR3:SetFlat", kind="omitted")


class MR4(Device):
    # Combined motions motors
    y = Component(EpicsMotor, "m15", labels=("motor",))
    yaw = Component(EpicsMotor, "m16", labels=("motor",))
    x = Component(EpicsMotor, "m17", labels=("motor",))
    pitch = Component(EpicsMotor, "m18", labels=("motor",))

    # Individual motors
    yu = Component(EpicsMotor, "m7", labels=("motor",))
    yd = Component(EpicsMotor, "m8", labels=("motor",))
    xu = Component(EpicsMotor, "m9", labels=("motor",))
    xd = Component(EpicsMotor, "m10", labels=("motor",))

    # Stripe settings
    stripe_setpoint = Component(EpicsSignal, "MR4:Stripe", string=True)
    stripe_readback = Component(EpicsSignalRO, "MR4:StripeRBV", string=True)

    pos_silicon = Component(EpicsSignal, "MR4:SiPosition")
    pos_palladium = Component(EpicsSignal, "MR4:PdPosition")
    pos_platinum = Component(EpicsSignal, "MR4:PtPosition")


class ToroidalMirror(Device):

    # MR3
    mr3 = Component(MR3, "")

    # MR4
    mr4 = Component(MR4, "")
