from bluesky.magics import (
    BlueskyMagics,
    _print_devices,
    is_positioner,
    # get_labeled_devices,
)
from IPython.core.magic import line_magic, magics_class
from operator import attrgetter
from bluesky import RunEngineInterrupted
from numpy import round, ndarray
from apsbits.core.instrument_init import oregistry
from ..plans import mv, mvr
from pyRestTable import Table
import re

try:
    # cytools is a drop-in replacement for toolz, implemented in Cython
    from cytoolz import partition
except ImportError:
    from toolz import partition


@magics_class
class LocalMagics(BlueskyMagics):

    # @line_magic
    # def att(self, line):
    #    if len(line.split()) >1:
    #        raise TypeError("Wrong parameters. Expected: att position")
    #    elif len(line.split()) == 0:
    #        pass

    @line_magic
    def wm(self, line):
        result = Table()
        result.labels = ("Motor", "Position", "Limits")
        for arg in re.split(r"[, ]+", line):
            pos = eval(arg, self.shell.user_ns).user_readback.get()
            llm = eval(arg, self.shell.user_ns).low_limit_travel.get()
            hlm = eval(arg, self.shell.user_ns).high_limit_travel.get()
            result.rows.append(
                (
                    eval(arg, self.shell.user_ns).name,
                    f"{pos:.5f}",
                    f"[{llm:.5f},{hlm:.5f}]",
                )
            )
        print("")
        print(result.reST(fmt="markdown"))

    @line_magic
    def mov(self, line):
        if len(line.split()) % 2 != 0:
            raise TypeError(
                "Wrong parameters. Expected: "
                "%mov motor position (or several pairs like that)"
            )
        args = []
        for motor, pos in partition(2, line.split()):
            args.append(eval(motor, self.shell.user_ns))
            args.append(eval(pos, self.shell.user_ns))
        plan = mv(*args)
        self.RE.waiting_hook = self.pbar_manager
        try:
            self.RE(plan)
        except RunEngineInterrupted:
            pass
        self.RE.waiting_hook = None
        self._ensure_idle()
        return None

    @line_magic
    def movr(self, line):
        if len(line.split()) % 2 != 0:
            raise TypeError(
                "Wrong parameters. Expected: "
                "%mov motor position (or several pairs like that)"
            )
        args = []
        for motor, pos in partition(2, line.split()):
            args.append(eval(motor, self.shell.user_ns))
            args.append(eval(pos, self.shell.user_ns))
        plan = mvr(*args)
        self.RE.waiting_hook = self.pbar_manager
        try:
            self.RE(plan)
        except RunEngineInterrupted:
            pass
        self.RE.waiting_hook = None
        self._ensure_idle()
        return None

    @line_magic
    def wa(self, line):
        "List positioner info. 'wa' stands for 'where all'."
        # NOTE: This is needed here because of a bug in the bluesky
        # implementation. A PseudoPositioner has a `.position` that is
        # converted into a numpy.array by numpy.round (line 156 here), and the
        # numpy array cannot by formatted using the string format. This raises
        # the error "unsupported format string passed to
        # numpy.ndarray.__format__". Line 160 was added to mitigate this.

        # If the deprecated BlueskyMagics.positioners list is non-empty, it has
        # been configured by the user, and we must revert to the old behavior.
        if type(self).positioners:
            if line.strip():
                positioners = eval(line, self.shell.user_ns)
            else:
                positioners = type(self).positioners
            if len(positioners) > 0:
                _print_positioners(positioners, precision=self.FMT_PREC)
        else:
            # new behaviour
            # devices_dict = get_labeled_devices(user_ns=self.shell.user_ns)
            if line.strip():
                if "[" in line or "]" in line:
                    raise ValueError(
                        "It looks like you entered a list like "
                        "`%wa [motors, detectors]` "
                        "Magics work a bit differently than "
                        "normal Python. Enter "
                        "*space-separated* labels like "
                        "`%wa motors detectors`."
                    )
                # User has provided a white list of labels like
                # %wa label1 label2
                labels = line.strip().split()
            else:
                # Show all labels.
                # labels = list(devices_dict.keys())
                raise ValueError(
                    "Use labels like motor, detector, 4ida, 4idb, 4idg, 4idh, "
                    "preamp, "
                )
            for label in labels:
                print(label)
                try:
                    # devices = devices_dict[labelb]
                    devices = oregistry.findall(label)
                    all_children = [
                        (k, getattr(obj, k))
                        for obj in devices
                        for k in getattr(obj, "read_attrs", [])
                    ]
                except KeyError:
                    print("<no matches for this label>")
                    continue
                # Search devices and all their children for positioners.
                positioners = [
                    dev for dev in devices + all_children if is_positioner(dev)
                ]
                if positioners:
                    _print_positioners(
                        positioners, precision=self.FMT_PREC, prefix=" " * 2
                    )
                    print()  # blank line
                # Just display the top-level devices in the namespace (no
                # children).
                devices.sort(key=lambda x: x.name)
                devs = [(dev.name, dev) for dev in devices]
                _print_devices(devs, prefix=" " * 2)
                print()  # blank line


def _print_positioners(positioners, sort=True, precision=6, prefix=""):
    """
    This will take a list of positioners and try to print them.

    Parameters
    ----------
    positioners : list
        list of positioners

    sort : bool, optional
        whether or not to sort the list

    precision: int, optional
        The precision to use for numbers
    """
    # sort first
    if sort:
        positioners = sorted(set(positioners), key=attrgetter("name"))

    values = []
    for p in positioners:
        try:
            values.append(p.position)
        except Exception as exc:
            values.append(exc)

    headers = ["Positioner", "Value", "Low Limit", "High Limit", "Offset"]
    LINE_FMT = prefix + "{: <30} {: <11} {: <11} {: <11} {: <11}"
    lines = []
    lines.append(LINE_FMT.format(*headers))
    for p, v in zip(positioners, values):
        if not isinstance(v, Exception):
            try:
                prec = int(p.precision)
            except Exception:
                prec = precision
            value = round(v, decimals=prec)
            value = (
                value
                if not isinstance(value, ndarray)
                else str(value) if len(value) > 1 else value[0]
            )
            try:
                low_limit, high_limit = p.limits
            except Exception as exc:
                low_limit = high_limit = exc.__class__.__name__
            else:
                low_limit = round(low_limit, decimals=prec)
                high_limit = round(high_limit, decimals=prec)
            try:
                offset = p.user_offset.get()
            except Exception as exc:
                offset = exc.__class__.__name__
            else:
                offset = round(offset, decimals=prec)
        else:
            value = v.__class__.__name__  # e.g. 'DisconnectedError'
            low_limit = high_limit = offset = ""

        lines.append(
            LINE_FMT.format(p.name, value, low_limit, high_limit, offset)
        )
    print("\n".join(lines))
