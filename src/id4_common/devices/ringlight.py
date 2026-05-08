"""Ringlight illuminator (PVA NTEnum, e.g. RINGLIGHT:STATE).

The IOC exposes a single NTEnum control PV with these choices:

    index   choice    convenience method
    -----   -------   -------------------
    0       OFF       off()
    1       100%      full()
    2       50%       half()
    3       25%       quarter()
    4       12.5%     eighth()
    5       RAINBOW   rainbow()

Implemented with classic ophyd ``Device`` + a small ``Signal`` subclass
wrapping ``pvapy.Channel`` (same pattern this beamline uses for the
PositionerStream PVA controls). pvapy is the working PVA client in this
environment; ``p4p``/``ophyd_async`` PVA backends time out on this IOC.
"""

from ophyd import Device
from ophyd import FormattedComponent
from ophyd import Signal
from ophyd.status import Status
from pvapy import Channel


class PVANTEnumSignal(Signal):
    """Read/write an NTEnum PV via pvapy.

    The PV's value is a struct ``{index: int, choices: [str]}``. ``get()``
    returns the human-readable choice string; ``put()`` accepts either an
    integer index or a choice string.
    """

    def __init__(self, *args, pv_name, **kwargs):
        # Declare dtype="string" so Signal initializes _readback to
        # UNSET_VALUE (instead of a _DefaultFloat sentinel) and describe()
        # reports dtype="string". Without this, bluesky writes the
        # descriptor as "number" and the NeXus writer turns the readings
        # into a numpy <U3 array, which h5py rejects.
        super().__init__(*args, dtype="string", **kwargs)
        self._pva = Channel(pv_name)
        self._pv_name = pv_name

    def get(self, **kwargs):
        v = self._pva.get().toDict()["value"]
        # The IOC's percent labels (e.g. "100%", "12.5%") trip up
        # downstream consumers; strip the trailing '%' so "OFF" /
        # "RAINBOW" / "100" / "12.5" are returned as plain strings.
        val = v["choices"][v["index"]].rstrip("%")
        # Cache the readback so describe()/read() see a string and bluesky
        # tags the descriptor's dtype correctly.
        self._readback = val
        return val

    def put(self, value, **kwargs):
        if isinstance(value, bool):
            # bool is a subclass of int — reject explicitly to avoid
            # accidentally writing 0/1 from True/False.
            raise TypeError(
                f"Refusing to put bool to {self._pv_name}; "
                "use an int index or a choice string."
            )
        if isinstance(value, int):
            self._pva.putInt(value)
        elif isinstance(value, str):
            self._pva.putString(value)
        else:
            raise TypeError(
                f"Cannot put {type(value).__name__} to {self._pv_name}; "
                "expected int (choice index) or str (choice label)."
            )

    def set(self, value, **kwargs):
        # pvapy puts are synchronous and raise on failure; mirror the
        # PVASignal/PositionerStream convention by returning an
        # already-finished Status.
        self.put(value)
        st = Status()
        st.set_finished()
        return st

    def wait_for_connection(self, timeout=5.0):
        # pvapy.Channel.get(timeout=...) raises if the PV is unreachable;
        # Channel.get(<float>) treats the float as a request timeout in
        # seconds. Discard the value — we only care that it returns.
        self._pva.get(float(timeout))


class Ringlight(Device):
    """Sample-area ringlight controlled via a single NTEnum state PV (PVA)."""

    STATES = {
        "off": 0,
        "full": 1,
        "half": 2,
        "quarter": 3,
        "eighth": 4,
        "rainbow": 5,
    }

    state = FormattedComponent(
        PVANTEnumSignal,
        pv_name="{self.prefix}STATE",
        # FormattedComponent only formats names listed in add_prefix
        # (default ("suffix", "write_pv")). Add "pv_name" so our
        # template gets expanded against the parent's attributes.
        add_prefix=("pv_name",),
    )

    def __init__(self, prefix, *, name="", labels=None, **kwargs):
        super().__init__(prefix, name=name, **kwargs)
        # Mirror the classic ophyd labels= convention so the project's
        # oregistry findall(label=...) keeps working.
        self._ophyd_labels_ = set(labels or [])

    def set_state(self, value):
        """Write a state.

        Accepts an integer index (0-5), a short name
        (``off``/``full``/``half``/``quarter``/``eighth``/``rainbow``),
        or the raw NTEnum choice string (e.g. ``"100%"``, ``"OFF"``).
        """
        if isinstance(value, str):
            key = value.lower()
            if key in self.STATES:
                value = self.STATES[key]
        self.state.put(value)

    def off(self):
        """Turn the ringlight off."""
        self.set_state(0)

    def full(self):
        """100% intensity."""
        self.set_state(1)

    def half(self):
        """50% intensity."""
        self.set_state(2)

    def quarter(self):
        """25% intensity."""
        self.set_state(3)

    def eighth(self):
        """12.5% intensity."""
        self.set_state(4)

    def rainbow(self):
        """Rainbow color cycle."""
        self.set_state(5)
