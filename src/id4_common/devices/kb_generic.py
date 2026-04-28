"""Generic KB mirror device factory with configurable motor PV suffixes."""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignalRO


def make_kb_class(v_motors: dict, h_motors: dict) -> type:
    """Return a KBDevice class with specified motor PV suffixes.

    Parameters
    ----------
    v_motors : dict
        Mapping of vertical motor attribute names to PV suffixes, e.g.
        ``{"ds_piezo": "m4", "us_piezo": "m5", ...}``.
    h_motors : dict
        Mapping of horizontal motor attribute names to PV suffixes.

    Returns
    -------
    type
        A KBDevice class composed of Vertical and Horizontal sub-devices.
    """
    v_attrs = {
        name: Component(EpicsMotor, suffix, labels=("motor",))
        for name, suffix in v_motors.items()
    }
    v_attrs["y"] = Component(EpicsSignalRO, "vert:t2.D")
    v_attrs["thx"] = Component(EpicsSignalRO, "vert:t2.C")
    v_attrs["ds_capsensor"] = Component(EpicsSignalRO, "m16.RBV")
    v_attrs["us_capsensor"] = Component(EpicsSignalRO, "m15.RBV")

    h_attrs = {
        name: Component(EpicsMotor, suffix, labels=("motor",))
        for name, suffix in h_motors.items()
    }
    h_attrs["thy"] = Component(EpicsSignalRO, "SM1.RBV")
    h_attrs["thz"] = Component(EpicsSignalRO, "SM2.RBV")
    h_attrs["x"] = Component(EpicsSignalRO, "m18.RBV")
    h_attrs["z"] = Component(EpicsSignalRO, "m17.RBV")
    h_attrs["thy_capsensor"] = Component(EpicsSignalRO, "m19.RBV")
    h_attrs["thz_capsensor"] = Component(EpicsSignalRO, "cap2:pos")

    Vertical = type("Vertical", (Device,), v_attrs)
    Horizontal = type("Horizontal", (Device,), h_attrs)

    return type(
        "KBDevice",
        (Device,),
        {
            "v": Component(Vertical, ""),
            "h": Component(Horizontal, ""),
        },
    )


# 4-ID-G KB mirrors
GKBDevice = make_kb_class(
    v_motors={
        "ds_piezo": "m4",
        "ds_pico": "m11",
        "us_piezo": "m5",
        "us_pico": "m7",
        "stripe": "m20",
    },
    h_motors={
        "thy_piezo": "m1",
        "thy_pico": "m9",
        "thz_pico": "m10",
        "x_piezo": "m3",
        "x_pico": "m12",
        "z_piezo": "m2",
        "z_pico": "m8",
        "stripe": "m22",
    },
)

# 4-ID-H KB mirrors
HKBDevice = make_kb_class(
    v_motors={
        "ds_piezo": "m2",
        "ds_pico": "m8",
        "us_piezo": "m1",
        "us_pico": "m7",
        "stripe": "m20",
    },
    h_motors={
        "thy_piezo": "m6",
        "thy_pico": "m11",
        "thz_pico": "m14",
        "x_piezo": "m4",
        "x_pico": "m12",
        "z_piezo": "m5",
        "z_pico": "m13",
        "stripe": "m22",
    },
)
