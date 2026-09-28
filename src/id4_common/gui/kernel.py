"""Jupyter kernel management and status polling for the Bluesky GUI.

Two independent clients talk to one kernel:

* the *console* client, owned by the ``RichJupyterWidget``;
* a *poll* client used only to fill the tabs.

They are kept separate so that polling never appears in the console.
``RichJupyterWidget.include_other_output`` defaults to ``False``, so messages
originating from the poll client's session are filtered out of the display.

Status comes from two sources, because the kernel is not always reachable:

``user_expressions``
    Evaluated by the kernel, so only usable while it is idle.  Everything the
    Session, Scan and Files groups show comes from here, the ``RE.md``
    identity fields included -- see ``_gui_session_metadata``.  An earlier
    version read those off ``.re_md_dict.yml`` in the kernel's working
    directory, a file this instrument never writes: ``RE.md`` is a
    ``PersistentDict`` directory under ``RUN_ENGINE.MD_PATH``.  The fields sat
    empty for it.

``streamed documents``
    Published over ZMQ (see :mod:`~id4_common.gui.docstream`) and therefore
    the one source that keeps arriving *during* a scan, when the poll is held
    back.  The scan number moves on the ``start`` document for that reason.
"""

import ast
import json
import logging
import os
import queue
import time
from collections import deque
from pathlib import Path

from jupyter_client import BlockingKernelClient
from qtconsole.manager import QtKernelManager
from qtpy.QtCore import QObject
from qtpy.QtCore import QTimer
from qtpy.QtCore import Signal

from ..mcp_server.bridge import MCP_HELPERS_CODE
from ..mcp_server.motion import MOTION_HELPERS_CODE
from ..mcp_server.session import pointer_name
from . import config
from .hkl_bridge import HKL_HELPERS_CODE
from .session_setup import SESSION_SETUP_CODE

logger = logging.getLogger(__name__)

#: Executed in the kernel to build the session.  Same line the IPython
#: workflow uses, so both front ends share one code path.
#:
#: The *station* package, not ``id4_common``: the shared package has no
#: ``startup`` of its own, and each station's binds a different
#: ``devices.yml`` and a catalog view filtered on its own instrument name.
#: Built at call time, since ``--station`` may set ``ID4_STATION`` after
#: this module is imported.
BOOTSTRAP_TEMPLATE = "from {station}.startup import *"


def bootstrap_code():
    """Return the import line that builds this station's session."""
    return BOOTSTRAP_TEMPLATE.format(station=config.station())


#: Helpers defined in the kernel for the GUI to call.  ``user_expressions``
#: evaluates expressions only -- it cannot run a ``try``/``except`` -- so
#: anything that needs error handling per device has to live here.
HELPERS_CODE = '''\
def _gui_device_table():
    """Return (name, class, prefix, labels, connected) for each root device."""
    rows = []
    for _d in sorted(oregistry.root_devices, key=lambda d: d.name):
        try:
            _conn = bool(_d.connected)
        except Exception:
            _conn = None          # lazy/area-detector devices can raise
        rows.append((
            _d.name,
            type(_d).__name__,
            str(getattr(_d, "prefix", "")),
            ",".join(sorted(getattr(_d, "_ophyd_labels_", None) or [])),
            _conn,
        ))
    return rows


def _gui_plot_signals(dev):
    """Return {channel label: signal} for a detector, however it exposes them.

    ``plot_signals`` is the interface the detectors implement directly.
    No detector in ``id4_common`` has it -- they implement ``plot_options``
    and ``select_plot``, which is enough for ``counters()`` and the Scan tab
    but not for editing a channel's ``Kind``.  Rather than require an edit to
    every detector class, three fallbacks are tried in turn:

    1. ``plot_signals``, if a station has added it.
    2. ``field_for_label(label)`` from ``devices/counters_mixin.py``, which
       returns the ophyd *field name* -- resolved back to the signal through a
       ``walk_signals`` index.  This covers the Eiger, Vimba, Lightfield and
       position-stream detectors.
    3. ``channels_name_map`` on the scalers, whose values are component attr
       names under ``.channels`` (the signal is ``.<attr>.s``).

    Anything still unresolved is left out rather than guessed at -- a wrong
    signal here would set ``Kind`` on the wrong channel.
    """
    _direct = getattr(dev, "plot_signals", None)
    if _direct:
        return dict(_direct)

    try:
        _labels = list(dev.plot_options or [])
    except Exception:
        return {}

    # The channels_name_map fallback below does
    # ``getattr(dev.channels, _attr)``, which instantiates a lazy scaler
    # channel and, unguarded, waits for it to connect -- once per channel,
    # per detector.  Behind a dead IOC that is minutes of a wedged kernel,
    # and the kernel serialises requests, so it takes the console and every
    # other tab down with it.  Only the signal object is wanted here, never
    # a value, so instantiating without the wait is enough.
    _guard = _gui_no_lazy_connect([dev])

    _by_field = None
    _out = {}

    with _guard:
        for _label in _labels:
            _sig = None
            try:
                _field = dev.field_for_label(_label)
            except Exception:
                _field = None
            if _field is not None:
                if _by_field is None:
                    _by_field = {}
                    try:
                        for _walk in dev.walk_signals(include_lazy=False):
                            _by_field[_walk.item.name] = _walk.item
                    except Exception:
                        pass
                _sig = _by_field.get(_field)

            if _sig is None:
                try:
                    _attr = dev.channels_name_map[_label]
                    _sig = getattr(dev.channels, _attr).s
                except Exception:
                    _sig = None

            if _sig is not None:
                _out[_label] = _sig

    return _out


def _gui_detector_kinds():
    """Return (device, prefix, channel, kind) for every detector channel.

    The registry label is ``detector``, singular -- the spelling every
    device in ``configs/devices.yml`` carries and the one
    ``CountersClass._available_detectors`` looks for.  Asked for as
    ``detectors`` it matches nothing at all, and with ``allow_none=True``
    that is an empty list rather than an error, so the tab renders zero rows
    and looks like it simply found no detectors.

    ``counters._available_detectors`` is preferred over the raw lookup
    because it applies the same ordering as ``detectors_plot_options``, so
    this tab lists devices in the order the rest of the session shows them.
    The label query stays as the fallback for a session where ``counters``
    is not up yet.
    """
    rows = []
    try:
        _dets = list(counters._available_detectors)
    except Exception:
        _dets = oregistry.findall("detector", allow_none=True) or []
    for _d in _dets:
        try:
            _signals = _gui_plot_signals(_d)
        except Exception:
            continue          # lazy components can raise when instantiated
        for _name, _sig in _signals.items():
            try:
                _kind = _sig.kind.name
            except Exception:
                _kind = None
            rows.append((_d.name, str(getattr(_d, "prefix", "")), _name, _kind))
    return rows


def _gui_extra_devices():
    """Return the names of devices recorded alongside the detectors."""
    try:
        return [d.name for d in counters.extra_devices]
    except Exception:
        return []


def _gui_addable_devices():
    """Root devices that are neither detectors nor already extras.

    Anything here can be recorded during a scan.  Extras skip
    ``configure_counts_wrapper``, so unlike a real detector they do not need a
    ``preset_monitor`` -- which is why a thermometer or capacitance bridge
    works as an extra but crashes as a detector.
    """
    taken = set()
    try:
        taken |= {d.name for d in counters.detectors}
        taken |= {d.name for d in counters.extra_devices}
    except Exception:
        pass
    rows = []
    for _d in sorted(oregistry.root_devices, key=lambda d: d.name):
        if _d.name in taken:
            continue
        rows.append((_d.name, type(_d).__name__, str(getattr(_d, "prefix", ""))))
    return rows


def _gui_add_extra(name):
    """Record *name* at every scan point (counters.extra_devices)."""
    try:
        current = list(counters.extra_devices)
        if any(d.name == name for d in current):
            return f"{name} is already an extra device."
        counters.extra_devices = current + [oregistry.find(name)]
        return f"Recording {name} during scans."
    except Exception as exc:
        return f"Could not add {name}: {exc}"


def _gui_remove_extra(name):
    """Stop recording *name*."""
    try:
        counters.extra_devices = [
            d for d in counters.extra_devices if d.name != name
        ]
        return f"No longer recording {name}."
    except Exception as exc:
        return f"Could not remove {name}: {exc}"


def _gui_set_kinds(changes):
    """Apply [(device, channel, kind_name), ...]; return what actually stuck."""
    from ophyd import Kind as _Kind

    applied = []
    for _dev, _chan, _kind in changes:
        try:
            _sig = _gui_plot_signals(oregistry.find(_dev))[_chan]
            _sig.kind = getattr(_Kind, _kind)
            applied.append((_dev, _chan, _sig.kind.name))
        except Exception as _exc:
            print(f"Could not set {_dev}.{_chan} to {_kind}: {_exc}")
    return applied


def _gui_extra_kinds(include_omitted=False):
    """Return (device, prefix, dotted_name, kind) for each extra device signal.

    Extras are arbitrary devices with no ``plot_signals`` mapping, so their
    signals are enumerated with ``walk_signals``.  Omitted signals are skipped
    by default: they are not recorded anyway, and on a motor bundle they are
    the majority (52 of sl1's 100) of motor-record internals.
    """
    rows = []
    try:
        extras = list(counters.extra_devices)
    except Exception:
        return rows
    for _d in extras:
        try:
            walk = list(_d.walk_signals(include_lazy=False))
        except Exception:
            continue
        for _w in walk:
            try:
                _kind = _w.item.kind.name
            except Exception:
                continue
            if _kind == "omitted" and not include_omitted:
                continue
            rows.append((
                _d.name,
                str(getattr(_d, "prefix", "")),
                _w.dotted_name,
                _kind,
            ))
    return rows


import contextlib


@contextlib.contextmanager
def _gui_no_lazy_connect(devices=None):
    """Let lazy components instantiate without waiting for a connection.

    Reading an attribute that is a *lazy* ophyd Component instantiates it,
    and ``Component.create_component`` then does::

        if self.lazy and hasattr(self.cls, "wait_for_connection"):
            if getattr(instance, "lazy_wait_for_connection", True):
                cpt_inst.wait_for_connection()

    So a plain ``getattr`` blocks for the whole connection timeout once per
    lazy signal sitting behind a dead IOC.  A helper that walks every
    component of every device then wedges the kernel for minutes -- and
    because the kernel serialises requests, every other tab's question waits
    in the queue behind it and its panel stays blank.

    Suppressing only the *wait* is enough for callers that inspect a
    component (``set``, ``position``, ``hints``) without reading a value.
    The flag is restored per device, so nothing else sees the change.
    """
    from ophyd import Device as _OphydDevice

    # The flag is read off the object that *owns* the component
    # (``getattr(instance, "lazy_wait_for_connection", True)``), so setting
    # it on the root devices alone misses sub-devices -- and the scaler
    # channels that `_gui_plot_signals` reaches are exactly that:
    # ``dev.channels.chan01`` is owned by ``dev.channels``.  Setting it on
    # the ophyd base class covers every depth in one move; the per-device
    # assignment stays for any class that pins its own value.
    _class_held = _OphydDevice.lazy_wait_for_connection
    _OphydDevice.lazy_wait_for_connection = False
    _held = []
    for _d in devices or ():
        try:
            _held.append((_d, _d.__dict__.get("lazy_wait_for_connection")))
            _d.lazy_wait_for_connection = False
        except Exception:
            pass
    try:
        yield
    finally:
        _OphydDevice.lazy_wait_for_connection = _class_held
        for _d, _value in _held:
            try:
                if _value is None:
                    _d.__dict__.pop("lazy_wait_for_connection", None)
                else:
                    _d.lazy_wait_for_connection = _value
            except Exception:
                pass


def _gui_scan_options():
    """Return the pick lists the Scan tab needs.

    Axes are found by capability, not class, because the classes disagree:
    ``EpicsMotor`` and the hklpy2 pseudo axes are ``PositionerBase``, but
    ``sim_motor`` is a ``SynAxis`` (not a positioner, yet has ``set`` and
    ``position``) and ``energy`` is an ``EnergySignal`` (``set`` but no
    ``position``).  All three are scannable.  Identifiers are dotted paths,
    which are valid Python in this namespace.

    Detectors: only those with ``preset_monitor``.  ``configure_counts_wrapper``
    calls ``rd(det.preset_monitor)`` on every detector, so anything else raises
    ``AttributeError`` when scanned.

    ``axis_fields`` maps each axis's *hinted field* back to its dotted path,
    which is what the Scan plot tab's peak buttons need: a scan's x axis is
    named in the documents by its hinted field (``huber_euler_h``), not by its
    path (``huber_euler.h``).  It falls out of the same walk, so it costs no extra
    round-trip -- and because containers are skipped here, only leaves appear,
    which is exactly the disambiguation the plans have to do the hard way.
    """
    from ophyd import Signal

    def _movable(cls):
        """Movability decided from the *class*, never from an instance.

        The instance test this replaced -- ``hasattr(obj, "position")`` --
        invokes the property, and on POLAR's own classes (the hklpy2
        diffractometer especially) that reaches EPICS.  One such call behind
        a dead IOC stalls this helper, and because the kernel serialises
        requests, a stalled helper freezes the console and blanks every
        other tab until it returns.

        Reading it off the class touches nothing: ``hasattr(cls,
        "position")`` finds the property object without calling its getter.
        The one behavioural difference is that an axis whose IOC is down is
        now still listed -- the instance test quietly dropped it, because
        the getter raised ``DisconnectedError`` and ``hasattr`` swallowed
        it -- so the Scan tab's pick list no longer changes shape depending
        on which IOCs happen to be up.
        """
        try:
            return callable(getattr(cls, "set", None)) and hasattr(
                cls, "position"
            )
        except Exception:
            return False

    axes, seen, fields = [], set(), {}

    def _add(obj, path):
        if path not in seen:
            seen.add(path)
            axes.append((path, type(obj).__name__))
            try:
                for _f in obj.hints.get("fields", ()):
                    fields.setdefault(_f, path)
            except Exception:
                pass

    _roots = sorted(oregistry.root_devices, key=lambda d: d.name)
    candidates = []

    # Both walks read attributes off every component, which instantiates the
    # lazy ones -- see _gui_no_lazy_connect for why that must not also wait
    # for them to connect.  `hasattr(_d, "preset_monitor")` is the same trap
    # as the getattr above it.
    with _gui_no_lazy_connect(_roots):
        for _d in _roots:
            _dcls = type(_d)
            _has_axis_children = False
            for _attr in getattr(_d, "component_names", ()):
                # The Component *descriptor* off the class, which says what
                # the component would be without building one.  Only the
                # handful that turn out to be axes are then instantiated,
                # instead of every signal on every device.
                _cmp = getattr(_dcls, _attr, None)
                _ccls = getattr(_cmp, "cls", None)
                if _ccls is None or not _movable(_ccls):
                    continue
                try:
                    _c = getattr(_d, _attr)
                except Exception:
                    continue
                _add(_c, f"{_d.name}.{_attr}")
                _has_axis_children = True
            # A movable with movable children (mono, huber_euler, gslt) is a
            # container: scan mono.energy or huber_euler.h, not the container.
            if _movable(_dcls) and not _has_axis_children:
                _add(_d, _d.name)
            elif issubclass(_dcls, Signal) and getattr(
                _d, "write_access", False
            ):
                _add(_d, _d.name)

            # Class again, so a lazy preset_monitor is not built just to be
            # counted.
            if hasattr(_dcls, "preset_monitor"):
                candidates.append(_d.name)

    try:
        selected = [d.name for d in counters.detectors]
        monitor = counters.monitor
    except Exception:
        selected, monitor = [], "Time"

    return {
        "axes": axes,
        "axis_fields": fields,
        "detector_candidates": candidates,
        "detectors_selected": selected,
        "monitor": monitor,
    }


def _gui_catalog():
    """Return the catalog the *session* is writing to.

    Deliberately the name bound in the user namespace, **not**
    ``id4_common.utils.run_engine.cat``.  Those are different objects here:
    ``run_engine`` builds the full catalog at import, and each station's
    ``startup.py`` then rebinds ``cat`` to a ``db_query`` view filtered on
    ``instrument_name``.  Reading the unfiltered one at 4-ID-G would happily
    return 4-ID-H's last scan -- a wrong number rather than an error, which is
    the worst kind.
    """
    return globals()["cat"]


def _gui_session_metadata():
    """Return the ``RE.md`` entries the Session tab shows.

    Asked of the session rather than read off disk.  ``RE.md`` is a
    ``PersistentDict`` -- a *directory* of msgpack blobs under
    ``RUN_ENGINE.MD_PATH``, with zict's ``key#serial`` file naming -- at every
    station, a ``StoredDict`` file when ``MD_PATH`` points at one, and a plain
    dict when it is unset.  Three formats and a path the GUI does not know;
    one expression the kernel answers in any of them.

    A key ``RE.md`` does not carry is left out; the Session tab shows its
    placeholder for it, which is the honest answer before
    ``experiment_setup()`` has run.
    """
    _md = {}
    for _key in (
        "databroker_catalog",
        "login_id",
        "proposal_id",
        "beamline_id",
        "instrument_name",
        "scan_id",
    ):
        try:
            _value = RE.md.get(_key)
        except Exception:
            continue
        if _value is not None:
            _md[_key] = _value
    return _md


def _gui_peak_fields():
    """Return the detector *field* names the last scan can give a peak for.

    Suggestions only: the Macro tab's Peak component takes free text, because
    a macro is usually written before the scan whose peak it will use.

    Read out of the catalog rather than off ``bec.peaks``: ``peaks`` is filled
    in asynchronously under a Qt backend, so it is still empty at the point a
    macro would consult it.

    Scalar detector fields only -- a hinted key with a non-empty ``shape`` is
    an image (the Eiger), and ``cen()`` cannot take a peak of one.
    ``peak_position._detector_fields`` returns the raw hint list including
    those, so the filtering is done here.
    """
    try:
        run = _gui_catalog()[-1]
        descriptors = run.primary.metadata["descriptors"]

        hinted = set(run.metadata["start"].get("hints", {}).get("detectors") or [])
        if not hinted:
            # No detector hints in the start doc -- fall back to the
            # descriptor's own per-object hints, which is where BEC looks.
            for desc in descriptors:
                for spec in (desc.get("hints") or {}).values():
                    hinted.update(spec.get("fields") or [])

        fields = []
        for desc in descriptors:
            for key, spec in desc["data_keys"].items():
                if key in hinted and not spec.get("shape"):
                    fields.append(key)
        return sorted(set(fields))
    except Exception:
        return []


def _gui_macro_targets(name):
    """Return [(dotted_path, class_name, kind)] that ``mv()`` can drive on *name*.

    Two kinds, positioners first because they are what a macro usually moves:

    ``positioner``
        The device itself when it is movable, and its movable children.
        ``walk_signals`` alone is wrong here -- ``mv(gslt.top, 3)`` wants the
        ``EpicsMotor``, not ``gslt.top.user_setpoint``.
    ``signal``
        Every writable signal underneath, for the things that are set rather
        than moved: a temperature setpoint, a source voltage, a filter
        transmission.

    Per device rather than all at once, so the tab never ships the several
    hundred signal names it will not use.
    """
    from ophyd import Signal as _Signal

    def _movable(obj):
        try:
            return callable(getattr(obj, "set", None)) and hasattr(obj, "position")
        except Exception:
            return False

    try:
        _dev = oregistry.find(name)
    except Exception:
        return []

    rows, seen = [], set()

    def _add(path, obj, kind):
        if path not in seen:
            seen.add(path)
            rows.append((path, type(obj).__name__, kind))

    if _movable(_dev):
        _add(_dev.name, _dev, "positioner")
    elif isinstance(_dev, _Signal) and getattr(_dev, "write_access", False):
        _add(_dev.name, _dev, "signal")

    for _attr in getattr(_dev, "component_names", ()):
        try:
            _c = getattr(_dev, _attr)
        except Exception:
            continue
        if _movable(_c):
            _add(f"{_dev.name}.{_attr}", _c, "positioner")

    signals = []
    try:
        walk = list(_dev.walk_signals(include_lazy=False))
    except Exception:
        walk = []
    for _w in walk:
        try:
            if not getattr(_w.item, "write_access", False):
                continue
        except Exception:
            continue        # a disconnected signal can raise on write_access
        signals.append((f"{_dev.name}.{_w.dotted_name}", _w.item))
    for _path, _sig in sorted(signals, key=lambda _row: _row[0]):
        _add(_path, _sig, "signal")
    return rows


def _gui_set_extra_kinds(changes):
    """Apply [(device, dotted_name, kind_name), ...] to extra-device signals."""
    import operator

    from ophyd import Kind as _Kind

    applied = []
    for _dev, _dotted, _kind in changes:
        try:
            _sig = operator.attrgetter(_dotted)(oregistry.find(_dev))
            _sig.kind = getattr(_Kind, _kind)
            applied.append((_dev, _dotted, _sig.kind.name))
        except Exception as _exc:
            print(f"Could not set {_dev}.{_dotted} to {_kind}: {_exc}")
    return applied
'''

POLL_INTERVAL_MS = 1000

#: How many of the poller's own request ids to remember, so their iopub echoes
#: can be told apart from the session's traffic.  One request goes out every
#: :data:`POLL_INTERVAL_MS`, so only the most recent few can still have replies
#: in flight; the rest is slack for ``execute_once`` bursts.
OWN_REQUEST_MEMORY = 64

#: Evaluated in the kernel when it is idle.  Each entry reports its own
#: ``status``, so one failing expression never blanks the others --
#: ``experiment.experiment_path`` raises until ``experiment_setup()`` has run,
#: which is the normal state at session start.
KERNEL_EXPRESSIONS = {
    "re_state": "RE.state",
    # The Session tab's identity fields.  Polled rather than watched on disk;
    # see _gui_session_metadata.
    "session_md": "_gui_session_metadata()",
    "spec_file": "str(specwriter.spec_filename)",
    "sample": "experiment.sample",
    "exp_path": "str(experiment.experiment_path)",
    "n_runs": "len(cat)",
    "cwd": "__import__('os').getcwd()",
    # The Agent tab's whole state: the request an MCP client has parked, the
    # recent outcomes, and whether motion requests are switched off.  Polled
    # with the rest rather than by a reader of its own.
    "mcp_pending": "_gui_mcp_pending_info()",
}


def _from_repr(text):
    """Convert a ``user_expressions`` repr back into a Python value."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


class KernelSession(QObject):
    """Own the kernel process and the two clients that talk to it."""

    #: Emitted once the kernel answers ``kernel_info``, i.e. it is safe to
    #: execute code in it.
    ready = Signal()

    def __init__(self, cwd, parent=None):
        """Prepare a session that will run its kernel in *cwd*."""
        super().__init__(parent)
        self.cwd = str(cwd)
        self.manager = None
        self.client = None
        self.poll_client = None
        #: Where this session advertises its kernel for the MCP server.
        self.pointer_path = None
        self._ready_timer = None
        self._ready_deadline = 0.0
        self._ready_last_request = 0.0

    def start(self):
        """Start the kernel and both clients.

        Returns the ``(manager, client)`` pair for the console widget.
        """
        self.manager = QtKernelManager(kernel_name="python3")
        # Autorestart off, deliberately.  A silent restart would drop every
        # EPICS connection and device mid-experiment with only a log line to
        # show for it; at a beamline a visibly dead kernel the user restarts on
        # purpose is safer.  It also stops qtconsole's restart handler from
        # resetting the console on a spurious "kernel died" poll at startup.
        self.manager.autorestart = False
        # cwd matters: it is where the data files, the console log and the
        # MCP pointer land, and what the Session tab reports as the working
        # directory.
        self.manager.start_kernel(cwd=self.cwd)

        self.client = self.manager.client()
        self.client.start_channels()

        # Deliberately does NOT wait_for_ready(): the bootstrap takes ~40 s and
        # blocking here would freeze the GUI before it is even shown.  The
        # poller tolerates a kernel that is not answering yet.
        self.poll_client = BlockingKernelClient()
        self.poll_client.load_connection_file(self.manager.connection_file)
        self.poll_client.start_channels()

        self._write_pointer()
        return self.manager, self.client

    def _write_pointer(self):
        """Advertise this kernel to the MCP server.

        A small file in the kernel's own working directory, so a server started
        anywhere inside the session's directory tree finds it by walking up.
        Deliberately not ``jupyter_client``'s runtime directory, whose newest
        entry may be an unrelated notebook -- attaching to the wrong kernel is
        the one failure this must not have.
        """
        self.pointer_path = Path(self.cwd) / pointer_name()
        try:
            self.pointer_path.write_text(
                json.dumps(
                    {
                        "connection_file": self.manager.connection_file,
                        "pid": os.getpid(),
                        "started": time.time(),
                        "cwd": self.cwd,
                    },
                    indent=2,
                )
                + "\n"
            )
        except OSError:
            # A read-only session directory costs the MCP server, nothing else.
            logger.warning(
                "Could not write %s.", self.pointer_path, exc_info=True
            )
            self.pointer_path = None

    def _remove_pointer(self):
        """Withdraw the advertisement, so nothing attaches to a dead kernel."""
        if self.pointer_path is None:
            return
        try:
            self.pointer_path.unlink(missing_ok=True)
        except OSError:
            logger.debug(
                "Could not remove %s.", self.pointer_path, exc_info=True
            )
        self.pointer_path = None

    def wait_until_ready(self, timeout_s=180.0):
        """Emit :attr:`ready` once the kernel answers, without blocking.

        Executing before the kernel has announced itself is what makes
        qtconsole misread the kernel's own ``status: starting`` message as a
        crash-restart (``_handle_status`` calls ``_handle_kernel_restarted``
        whenever that arrives while the widget is executing).  Waiting for a
        ``kernel_info_reply`` first avoids the race entirely.

        Uses the poll client, so call this before the status poller starts to
        keep one reader on the shell channel.
        """
        self._ready_deadline = time.monotonic() + timeout_s
        self._ready_last_request = 0.0
        if self._ready_timer is None:
            self._ready_timer = QTimer(self)
            self._ready_timer.setInterval(200)
            self._ready_timer.timeout.connect(self._check_ready)
        self._ready_timer.start()

    def _check_ready(self):
        client = self.poll_client
        if client is None:
            return
        now = time.monotonic()
        # Re-ask periodically: a request sent while the kernel was still
        # binding its sockets is simply lost.
        if now - self._ready_last_request > 2.0:
            self._ready_last_request = now
            try:
                client.kernel_info()
            except Exception:  # noqa: BLE001 - kernel not up yet
                logger.debug("kernel_info request failed.", exc_info=True)
        while True:
            try:
                msg = client.get_shell_msg(timeout=0)
            except queue.Empty:
                break
            except Exception:  # noqa: BLE001 - kernel not up yet
                break
            if msg.get("msg_type") == "kernel_info_reply":
                self._ready_timer.stop()
                self.ready.emit()
                return
        if now > self._ready_deadline:
            self._ready_timer.stop()
            logger.warning("Kernel never reported ready; continuing anyway.")
            self.ready.emit()

    def bootstrap(self, console, follow_up_code=None):
        """Run the Bluesky startup in the kernel, its output shown in *console*.

        Sent on the console's *own* client rather than through
        ``console.execute()``.  The cell is several hundred lines of GUI helper
        definitions, and ``execute()`` echoes all of it into the console and
        spends prompt ``In [1]`` on it, so the user's first command starts at
        ``[2]``.  ``silent=True`` suppresses the ``execute_input`` broadcast and
        leaves the execution counter alone: nothing is echoed and the session
        opens at ``In [1]``.

        This is *not* qtconsole's hidden execute -- ``console.execute(source,
        hidden=True)`` sets ``_hidden``, which also swallows every ``stream``
        and ``error`` message for the request.  Sending on the client directly
        means the widget never registers the request, so ``_hidden`` stays
        False and the device-loading log and any traceback still appear,
        inserted above the prompt the way background output is.

        It must be the console's client and not the poll client: separate
        sockets give no ordering guarantee, so *follow_up_code* (the live-plot
        publisher subscription) could arrive before the import and fail on a
        missing ``RE``.  It is appended to this same cell for that reason.
        """
        # Helper definitions come *before* the station import.  Every one of
        # these four blocks is plain ``def``s and literal assignments -- they
        # touch ``oregistry`` / ``counters`` only when called -- so none of
        # them needs the session to exist yet.
        #
        # Order matters because this is one cell: a cell stops at the first
        # exception, so with the import first, a station startup that fails
        # (or merely has not finished) leaves every ``_gui_*`` helper
        # undefined.  Each tab then asks for one via ``user_expressions``,
        # the expression raises ``NameError``, and the poller drops keys that
        # raised -- so the Devices, Detectors and Scan tabs sit empty with no
        # message, looking like a GUI bug rather than a session that never
        # started.  Defining the helpers first makes the tabs work as soon as
        # the devices exist, and report honestly before then.
        #
        # Nothing is shadowed by doing this: every name these blocks bind
        # starts with an underscore, which ``import *`` never rebinds.
        parts = [
            HELPERS_CODE,
            HKL_HELPERS_CODE,
            MCP_HELPERS_CODE,
            MOTION_HELPERS_CODE,
            bootstrap_code(),
        ]
        if follow_up_code:
            parts.append(follow_up_code)

        # Last: after the devices exist, and after the live-plot subscription,
        # so a bad AUTO_SETUP block cannot cost the plotting.  Being last also
        # leaves the experiment/counters summary on screen once the ~40 s of
        # device-loading log has scrolled past.
        parts.append(SESSION_SETUP_CODE)

        # The prompt is live while this runs, where ``console.execute()`` used
        # to block it, so say what is happening: a command typed now is queued
        # by the kernel and runs once the startup finishes -- which for the
        # first ~40 s means before the devices exist.
        notice = getattr(console, "append_stream", None)
        if notice is not None:
            notice(
                "Starting the Bluesky session. Anything typed before it "
                "finishes will run afterwards.\n"
            )

        console.kernel_client.execute(
            "\n".join(parts),
            silent=True,
            store_history=False,
            allow_stdin=False,
        )

    def restart(self):
        """Restart the kernel process, reusing the same ports.

        Ports are preserved so both clients stay valid across the restart.

        Note this does *not* emit ``QtKernelManager.kernel_restarted`` -- that
        signal fires only from the autorestarter, which is disabled.  Callers
        must run :meth:`bootstrap` themselves afterwards.
        """
        self.manager.restart_kernel(now=False)

    def is_alive(self):
        """Return whether the kernel process is running."""
        try:
            return self.manager is not None and self.manager.is_alive()
        except Exception:  # noqa: BLE001 - liveness must never raise
            return False

    def shutdown(self):
        """Stop the readiness timer and both clients, then kill the kernel."""
        self._remove_pointer()
        if self._ready_timer is not None:
            self._ready_timer.stop()
        for client in (self.poll_client, self.client):
            if client is None:
                continue
            try:
                client.stop_channels()
            except Exception:  # noqa: BLE001 - best effort during teardown
                logger.debug("Failed to stop channels.", exc_info=True)
        if self.manager is not None:
            try:
                self.manager.shutdown_kernel(now=True)
            except Exception:  # noqa: BLE001 - best effort during teardown
                logger.debug("Failed to shut down kernel.", exc_info=True)


class StatusPoller(QObject):
    """Poll session state and publish it to the tabs."""

    metadata_changed = Signal(dict)
    kernel_values_changed = Signal(dict)
    kernel_state_changed = Signal(str)

    #: One broadcast iopub message, everything the console renders included.
    #: Messages the poller itself provoked are filtered out first, so a
    #: subscriber sees the session and not the GUI's own housekeeping.  Used by
    #: the console transcript; see :mod:`id4_common.gui.transcript`.
    iopub_message = Signal(dict)

    def __init__(self, session, parent=None):
        """Poll state for *session*, a started :class:`KernelSession`."""
        super().__init__(parent)
        self._session = session
        #: Last metadata dict published, so an unchanged poll is not re-emitted
        #: to every tab once a second.
        self._metadata = None
        self._busy = False
        self._state = None
        self._pending = None
        self._once = {}
        # msg_ids of requests this poller sent.  Bounded because one goes out
        # every second: only the most recent can still have replies in flight.
        self._own_requests = deque(maxlen=OWN_REQUEST_MEMORY)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    @property
    def kernel_state(self):
        """Last known kernel state: ``idle``, ``busy``, ``dead`` or None.

        ``kernel_state_changed`` only fires on transitions, so anything that
        needs the *current* state -- rather than a change in it -- must read
        this.  A short operation can start and finish between two polls without
        ever producing a transition.
        """
        return self._state

    def start(self):
        """Begin polling."""
        self._timer.start()
        self._tick()

    def stop(self):
        """Stop polling."""
        self._timer.stop()

    def _tick(self):
        self._drain_iopub()
        self._poll_kernel()
        self._emit_state()

    def _drain_iopub(self):
        """Consume broadcast messages to track kernel busy/idle, and re-emit.

        iopub is broadcast to every client, so this sees execution driven from
        the console even though it runs on the poll client -- which is what
        makes it the capture point for the console transcript.  Anything this
        poller provoked itself is dropped first: :meth:`_poll_kernel` has to
        send ``silent=False`` (or ``user_expressions`` are ignored), so the
        kernel broadcasts an ``execute_input`` for an empty cell once a second,
        and a subscriber must not see it.  The bootstrap is deliberately *not*
        filtered -- it goes out on the console's client, and its device-loading
        log is worth keeping.
        """
        client = self._session.poll_client
        if client is None:
            return
        while True:
            try:
                msg = client.get_iopub_msg(timeout=0)
            except queue.Empty:
                return
            except Exception:  # noqa: BLE001 - a dead channel is not fatal
                return
            if msg.get("msg_type") == "status":
                state = msg.get("content", {}).get("execution_state")
                if state in ("busy", "idle"):
                    self._busy = state == "busy"
            parent = (msg.get("parent_header") or {}).get("msg_id")
            if parent in self._own_requests:
                continue
            self.iopub_message.emit(msg)

    def execute_once(self, code):
        """Run a statement in the kernel, invisibly to the console.

        Goes out on the poll client, so it is filtered out of the console
        display.  Returns True if the request was sent.
        """
        client = self._session.poll_client
        if client is None:
            return False
        try:
            msg_id = client.execute(
                code, silent=True, store_history=False, allow_stdin=False
            )
        except Exception:  # noqa: BLE001 - caller decides how to report
            logger.exception("Could not execute %r in the kernel.", code[:80])
            return False
        # Silent, so there is no execute_input to hide -- but a failing
        # statement still broadcasts an `error`, and a GUI-internal traceback
        # has no place in the console transcript.
        self._own_requests.append(msg_id)
        return True

    def request_once(self, expressions):
        """Evaluate *expressions* on the next poll, then forget them.

        Lets a tab ask an occasional expensive question (a device listing, say)
        without paying for it every second, and without opening a second reader
        on the shell channel.  Results arrive on ``kernel_values_changed``
        alongside the usual keys.
        """
        self._once.update(expressions)

    def _poll_kernel(self):
        """Request kernel-only values, at most one request in flight.

        Holding back while a request is outstanding is what stops a burst of
        queued polls from firing all at once when a long scan finishes.
        """
        client = self._session.poll_client
        if client is None:
            return
        if self._pending is not None:
            self._collect_reply(client)
            return
        if self._busy:
            return
        expressions = dict(KERNEL_EXPRESSIONS)
        expressions.update(self._once)
        try:
            self._pending = client.execute(
                "",
                silent=False,  # silent=True suppresses user_expressions
                store_history=False,  # keeps the console prompt number intact
                allow_stdin=False,
                user_expressions=expressions,
            )
        except Exception:  # noqa: BLE001 - kernel may be restarting
            self._pending = None
        else:
            self._own_requests.append(self._pending)
            self._once.clear()

    def _collect_reply(self, client):
        """Non-blocking check for the outstanding poll reply."""
        while True:
            try:
                reply = client.get_shell_msg(timeout=0)
            except queue.Empty:
                return
            except Exception:  # noqa: BLE001 - kernel may be restarting
                self._pending = None
                return
            if reply.get("parent_header", {}).get("msg_id") != self._pending:
                continue  # a stale reply from before a restart
            self._pending = None
            expressions = reply.get("content", {}).get("user_expressions") or {}
            values = {
                key: _from_repr(result["data"]["text/plain"])
                for key, result in expressions.items()
                if result.get("status") == "ok"
            }
            self._publish_metadata(values.pop("session_md", None))
            self.kernel_values_changed.emit(values)
            return

    def _publish_metadata(self, metadata):
        """Emit ``metadata_changed`` when the session identity has moved.

        Only on a change: the poll runs every second, and re-filling six
        labels with the values already in them would fight the user's
        selection every time they tried to copy one.
        """
        if not isinstance(metadata, dict) or metadata == self._metadata:
            return
        self._metadata = metadata
        self.metadata_changed.emit(metadata)

    def _emit_state(self):
        if not self._session.is_alive():
            state = "dead"
        else:
            state = "busy" if self._busy else "idle"
        if state != self._state:
            self._state = state
            self.kernel_state_changed.emit(state)

    def reset(self):
        """Forget cached state so a restarted kernel is re-read from scratch."""
        self._metadata = None
        self._pending = None
        self._busy = False
