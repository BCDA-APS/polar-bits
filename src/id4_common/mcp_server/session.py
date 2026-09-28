"""Talk to a running GUI session's kernel.

:class:`HklSession` is a plain ``jupyter_client`` client with one method that
matters, :meth:`HklSession.call`.  It has **no ``mcp`` import**, so everything
below can be built and tested before the SDK is installed, and the protocol
layer in :mod:`id4_common.mcp_server.server` stays a declaration of tools and
nothing else.

Finding the kernel
------------------
The GUI writes ``.polar-gui-kernel-<station>.json`` into its kernel's working
directory (see :meth:`id4_common.gui.kernel.KernelSession.start`) and removes
it on close.  Discovery walks up from the current directory looking for that
file, which means an MCP client launched with ``cwd`` anywhere inside the
session's directory tree finds it; ``POLAR_GUI_KERNEL_FILE`` and the
constructor argument override.

The name carries the station because four POLAR stations share one filesystem
and one checkout.  6-ID-B could use a fixed name -- there is one session there
-- but here a station-blind pointer would let a client attach to the wrong
beamline's kernel, which is the one discovery failure this must not have.

Deliberately **not** :func:`jupyter_client.find_connection_file`, whose
no-argument form returns the newest runtime file -- which may be an unrelated
notebook, and attaching to the wrong kernel is exactly the failure this must
not have.

Not blocking on a busy kernel
-----------------------------
A running scan holds the shell channel, and a request sent to a busy kernel is
*queued*: it would run when the scan ends, possibly an hour later, long after
the model gave up on it.  Silently changing an orientation an hour after it was
asked for is worse than refusing, so :meth:`call` sends an empty, silent probe
first and refuses if that does not come back promptly.  The probe is a no-op,
so a queued one that lands later does nothing.

Watching without the kernel
---------------------------
That refusal is right, and it leaves a gap: while an approved move or a scan
runs, *every* kernel call is refused, which is exactly when a client most wants
to know what is happening.  :meth:`HklSession.status` answers from two sources
outside the shell channel, both already proven elsewhere in this package:

* **Channel Access, from this process.**  The readback PV of each axis, read
  with ``epics.PV`` -- the same trick the HKL tab's progress bar uses to follow
  a move while the kernel is blocked by it (``tabs/hkl.py:_start_progress``).
  The PV names arrive in ``real_pvs`` from ``get_state`` and are cached, so a
  client that has read state once can watch the machine forever.
* **The session's ``RE.md`` on disk**, for ``scan_id`` and the run metadata.
  At the beamline that is a ``bluesky.utils.PersistentDict`` -- a *directory*
  of msgpack files under ``RUN_ENGINE.MD_PATH``, written through on every
  assignment, so ``scan_id`` is on disk the moment a run opens.  The
  development config points ``MD_PATH`` at a file instead, which is an
  ``apstools.utils.StoredDict`` (one YAML file, written after a short delay).
  Neither path is guessable from here -- it is per station and not under the
  kernel's working directory -- so it is asked of the kernel once while it is
  idle and remembered, the same bargain the PV cache makes.
"""

import json
import os
import queue
from pathlib import Path

from ..gui import config as _config
from .bridge import DEFAULT_DEVICE
from .bridge import READ_OPS
from .bridge import SESSION_DEVICE
from .motion import MOTION_READ_OPS

#: Every op that only reads, from both kernel-side modules.  Combined here
#: rather than in ``bridge``, which ``motion`` imports -- the other direction
#: would be a cycle.
ALL_READ_OPS = READ_OPS | MOTION_READ_OPS

#: Any station's pointer file.  Used when the station-specific name is not
#: found: naming the session that *is* running beats "no session".
POINTER_GLOB = ".polar-gui-kernel-*.json"

#: The ``RE.md`` keys :meth:`HklSession.status` reports.  Named rather than
#: reading the whole store: ``iconfig`` alone is a couple of kilobytes of
#: nested configuration, and unpacking it once a second buys nothing.
MD_KEYS = ("scan_id", "sample", "proposal_id", "beamline_id")

#: How long a Channel Access read may take before it is reported as unknown.
#: Short: this path exists to answer while the kernel cannot.
CA_TIMEOUT = 1.0

#: Overrides discovery with an explicit pointer *or* connection file.
POINTER_ENV = "POLAR_GUI_KERNEL_FILE"

#: How long to wait for the no-op probe that proves the kernel is free.  Short:
#: an idle kernel answers in milliseconds, and everything longer is either a
#: scan or a dead process.
PROBE_TIMEOUT = 3.0

#: The kernel name a mutating call assigns its reply to.  Not ``_``, which is
#: IPython's own last-output variable -- clobbering it would surprise whoever
#: is typing in the console.
REPLY_NAME = "_gui_mcp_reply"

#: How long to wait for the operation itself.  Longer than the probe because
#: ``calc_angles`` runs the solver, but still bounded.
CALL_TIMEOUT = 30.0

_BUSY = (
    "The beamline session is busy -- most likely running a scan. Nothing was "
    "sent. Try again when it finishes."
)


class SessionError(RuntimeError):
    """Raised when no live GUI session can be reached."""


def pointer_name():
    """Name of the pointer file this client is looking for.

    A function rather than a module constant because ``ID4_STATION`` may be
    set after import -- the GUI's ``--station`` flag does exactly that -- and a
    constant frozen at import time would send a client launched for id4_h
    looking for id4_g's session.
    """
    return _config.pointer_filename()


def find_pointer(start=None):
    """Return the path of the GUI's pointer file, or None.

    Looks at :data:`POINTER_ENV` first, then *start* (default: the current
    directory) and each of its parents.
    """
    override = os.environ.get(POINTER_ENV)
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    wanted = pointer_name()
    here = Path(start or Path.cwd()).expanduser().resolve()
    for directory in [here, *here.parents]:
        candidate = directory / wanted
        if candidate.is_file():
            return candidate
    return None


def find_other_pointers(start=None):
    """Return pointer files for *other* stations, nearest directory first.

    Only for the error message.  Four stations share this filesystem, so
    "no session" is usually wrong and misleading -- what actually happened is
    that a session for a different station is running, and the fix is
    ``--station`` (or ``ID4_STATION``), not starting a second GUI.
    """
    wanted = pointer_name()
    here = Path(start or Path.cwd()).expanduser().resolve()
    found = []
    for directory in [here, *here.parents]:
        for candidate in sorted(directory.glob(POINTER_GLOB)):
            if candidate.name != wanted:
                found.append(candidate)
    return found


def read_pointer(explicit=None, start=None):
    """Return the GUI's pointer file as a dict, or an empty one.

    A connection file passed as *explicit* has no ``connection_file`` key and
    comes back empty, which is the honest answer: it says nothing about where
    the kernel is working.
    """
    path = Path(explicit).expanduser() if explicit else find_pointer(start)
    if path is None or not path.is_file():
        return {}
    try:
        info = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return info if isinstance(info, dict) and "connection_file" in info else {}


def _pid_alive(pid):
    """Whether *pid* names a live process."""
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def resolve_connection_file(explicit=None, start=None):
    """Return the kernel connection file to attach to.

    *explicit* may be either a connection file or a pointer file -- they are
    told apart by content, so a user who passes the wrong one still gets a
    working session rather than a puzzle.  Raises :class:`SessionError` with a
    sentence saying what to do when there is nothing to attach to.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise SessionError(f"No such file: {path}")
    else:
        path = find_pointer(start)
        if path is None:
            others = find_other_pointers(start)
            if others:
                names = ", ".join(sorted({p.name for p in others}))
                raise SessionError(
                    f"No running POLAR {_config.station()} GUI session found, "
                    f"but another station's is: {names}. Set ID4_STATION (or "
                    "start this server with the right station) to reach it -- "
                    "do not start a second GUI."
                )
            raise SessionError(
                "No running POLAR GUI session found. Start it with "
                "`polar-gui`, and run this server from the same directory "
                f"(or set {POINTER_ENV} to its {pointer_name()})."
            )

    try:
        info = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SessionError(f"Could not read {path}: {exc}") from exc

    # A connection file has ports; a pointer file has a connection_file key.
    if "connection_file" not in info:
        return str(path)

    pid = info.get("pid")
    if pid is not None and not _pid_alive(pid):
        raise SessionError(
            f"{path} points at PID {pid}, which is no longer running. The GUI "
            "did not shut down cleanly; start it again."
        )
    connection = Path(info["connection_file"]).expanduser()
    if not connection.is_file():
        raise SessionError(
            f"The connection file named by {path} is gone ({connection}). "
            "Start the GUI again."
        )
    return str(connection)


class HklSession:
    """A client for the ``_gui_mcp`` dispatcher in a live GUI kernel."""

    def __init__(self, connection_file=None, start=None, device=DEFAULT_DEVICE):
        """Prepare a session; nothing is opened until :meth:`connect`."""
        self._explicit = connection_file
        self._start = start
        self.device = device
        self.connection_file = None
        self.session_cwd = None
        self.client = None
        #: Requests we stopped waiting for.  Their replies still arrive and
        #: must be discarded rather than handed to whoever asks next.
        self._abandoned = set()
        #: ``"<device>.<axis>"`` -> readback PV name, harvested from whatever
        #: ``get_state`` has been read so far.  This is what lets
        #: :meth:`status` answer while the kernel is blocked.
        self._pv_names = {}
        #: The live ``epics.PV`` objects, kept so repeated status calls are
        #: monitor reads rather than fresh connections.
        self._pvs = {}
        #: ``{"kind": ..., "path": ...}`` from ``get_md_store``, once the
        #: kernel has been idle enough to answer.  This is what lets
        #: :meth:`status` report the scan number during a scan.
        self._md_store = None

    # -- lifecycle ---------------------------------------------------------

    def connect(self):
        """Attach to the kernel, raising :class:`SessionError` if there is none."""
        if self.client is not None:
            return
        from jupyter_client import BlockingKernelClient

        self.connection_file = resolve_connection_file(
            self._explicit, self._start
        )
        cwd = read_pointer(self._explicit, self._start).get("cwd")
        self.session_cwd = Path(cwd) if cwd else None
        client = BlockingKernelClient()
        client.load_connection_file(self.connection_file)
        client.start_channels()
        self.client = client

    def close(self):
        """Detach.  The kernel keeps running -- it is not ours."""
        for pv in self._pvs.values():
            try:
                pv.disconnect()
            except Exception:  # noqa: BLE001 - closing must not raise
                pass
        self._pvs.clear()
        if self.client is None:
            return
        try:
            self.client.stop_channels()
        finally:
            self.client = None

    # -- the one operation -------------------------------------------------

    def call(self, op, device=None, **args):
        """Run one operation and return the dispatcher's reply.

        *device* names the diffractometer for an orientation or hkl op, and is
        :data:`~id4_common.mcp_server.bridge.SESSION_DEVICE` for one that acts on
        the session as a whole; it defaults to ``self.device``.  The kernel
        checks it again against the op's own scope, so getting it wrong here is
        a refusal in words, not a wrong device.

        Always returns ``{"ok": bool, "message": str, "data": ...}``, including
        for transport failures, so a caller never has to tell a refusal apart
        from a broken connection by its type.
        """
        try:
            self.connect()
        except SessionError as exc:
            return {"ok": False, "message": str(exc), "data": None}

        payload = json.dumps(
            {
                "op": op,
                "device": device or self.device,
                "args": {k: v for k, v in args.items() if v is not None},
            }
        )
        expression = f"_gui_mcp({payload!r})"

        if not self._probe_idle():
            return {"ok": False, "message": _BUSY, "data": None}

        if op in ALL_READ_OPS:
            # Empty code: no ``execute_input`` on iopub, so a model polling
            # state leaves nothing in the console or the transcript.  The call
            # rides in as the expression to evaluate.
            code, expressions = "", {"r": expression}
        else:
            # Real code, so the operator sees the call in the console and the
            # transcript keeps it.  Assigned rather than called bare: a bare
            # call is an expression and IPython displays its JSON as
            # ``Out[n]``, burying the readable ``[LLM]`` line the dispatcher
            # prints.  (A trailing ``;`` does not suppress it here -- measured,
            # not assumed.)  The reply is read back out of ``_gui_mcp_last``.
            code = f"{REPLY_NAME} = {expression}"
            expressions = {"r": "_gui_mcp_last"}

        try:
            reply = self._request(code, expressions, CALL_TIMEOUT)
        except TimeoutError:
            return {
                "ok": False,
                "message": (
                    "The session stopped responding while running this "
                    "operation. It may still complete; check the GUI before "
                    "retrying."
                ),
                "data": None,
            }
        except Exception as exc:  # noqa: BLE001 - reported, never raised on
            return {
                "ok": False,
                "message": f"Could not reach the session: {exc}",
                "data": None,
            }

        result = (
            (reply.get("content") or {}).get("user_expressions", {}).get("r")
        )
        if not result or result.get("status") != "ok":
            detail = (result or {}).get("evalue", "no reply")
            if "_gui_mcp" in str(detail) or "not defined" in str(detail):
                detail += (
                    " -- the session predates the MCP helpers; restart the "
                    "kernel from the GUI's Restart button."
                )
            return {
                "ok": False,
                "message": f"The session refused the call: {detail}",
                "data": None,
            }

        text = result["data"]["text/plain"]
        try:
            # ``text`` is the repr of the dispatcher's JSON string.
            answer = json.loads(_unrepr(text))
        except Exception as exc:  # noqa: BLE001 - malformed reply is a bug
            return {
                "ok": False,
                "message": f"Unreadable reply from the session ({exc}): {text[:200]}",
                "data": None,
            }
        self._harvest_pvs(device or self.device, answer.get("data"))
        return answer

    # -- watching while the kernel is busy ---------------------------------

    def _harvest_pvs(self, device, data):
        """Remember the readback PV of every axis a reply mentioned.

        ``get_state`` carries ``real_pvs``; a soft axis has ``None`` there and
        is skipped, so a diffractometer on simulated motors contributes none.
        """
        if not isinstance(data, dict):
            return
        for axis, pvname in (data.get("real_pvs") or {}).items():
            if pvname:
                self._pv_names[f"{device}.{axis}"] = pvname

    def _read_pvs(self):
        """Channel Access read of every cached axis, without the kernel."""
        if not self._pv_names:
            return {}, "No axis PVs are known yet -- read the state once first."
        try:
            import epics
        except ImportError:
            return {}, "pyepics is not installed, so positions cannot be read."
        values = {}
        for axis, pvname in sorted(self._pv_names.items()):
            pv = self._pvs.get(pvname)
            if pv is None:
                pv = epics.PV(pvname)
                self._pvs[pvname] = pv
            try:
                values[axis] = pv.get(timeout=CA_TIMEOUT)
            except Exception:  # noqa: BLE001 - an unreachable IOC is a value
                values[axis] = None
        return values, None

    def _md_store_info(self, ask=False):
        """Where ``RE.md`` lives -- asked of the kernel once, then kept.

        *ask* is the caller's promise that the kernel is idle.  Without it the
        question is not put at all: ``call`` would probe, the probe would time
        out against a scan, and every status call would pay
        :data:`PROBE_TIMEOUT` twice over for an answer that cannot arrive
        while the kernel is busy anyway.

        So a client whose very first call lands mid-scan gets no metadata for
        that one call.  One idle moment at any point in the session settles it
        for good.
        """
        if self._md_store is None and ask:
            answer = self.call("get_md_store", device=SESSION_DEVICE)
            if answer.get("ok") and isinstance(answer.get("data"), dict):
                self._md_store = answer["data"]
        return self._md_store

    def _read_metadata(self, ask=False):
        """The session's ``RE.md``, off disk, so it answers during a scan."""
        info = self._md_store_info(ask=ask) or {}
        path = info.get("path")
        if not path:
            return {}
        try:
            if info.get("kind") == "directory":
                if not Path(path).is_dir():
                    return {}
                return _read_md_directory(path)
            return _read_md_file(path)
        except Exception:  # noqa: BLE001 - absent or half-written is not fatal
            return {}

    def status(self):
        """Report what can be known *without* the kernel's shell channel.

        This is the one call that still answers during a scan or an approved
        move.  ``busy`` is the probe's own verdict, so it is the same notion of
        busy every other call uses.
        """
        try:
            self.connect()
        except SessionError as exc:
            return {"ok": False, "message": str(exc), "data": None}

        busy = not self._probe_idle()
        positions, problem = self._read_pvs()
        # The probe just told us whether the kernel can be asked anything.
        metadata = self._read_metadata(ask=not busy)
        data = {
            "busy": busy,
            "positions": positions,
            "scan_id": metadata.get("scan_id"),
            "sample": metadata.get("sample"),
            "proposal_id": metadata.get("proposal_id"),
            "beamline_id": metadata.get("beamline_id"),
            "session_cwd": None
            if self.session_cwd is None
            else str(self.session_cwd),
        }
        message = (
            "A scan or an approved move is running; only this status call "
            "answers until it finishes."
            if busy
            else "The session is idle."
        )
        if problem:
            message += " " + problem
        return {"ok": True, "message": message, "data": data}

    # -- plumbing ----------------------------------------------------------

    def _probe_idle(self):
        """Whether the kernel answers a no-op now.

        A queued probe that lands later executes empty code, so a false
        negative costs nothing.
        """
        try:
            self._request("", {}, PROBE_TIMEOUT, silent=True)
        except Exception:  # noqa: BLE001 - busy, dead or unreachable
            return False
        return True

    def _request(self, code, expressions, timeout, silent=False):
        """Send one execute request and wait for *its* reply."""
        import time

        msg_id = self.client.execute(
            code,
            # silent=True suppresses user_expressions entirely, so only the
            # probe -- which asks for none -- may use it.
            silent=silent,
            store_history=False,  # keeps the console's prompt numbering intact
            allow_stdin=False,
            user_expressions=expressions,
        )
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._abandoned.add(msg_id)
                raise TimeoutError(f"No reply within {timeout:g}s")
            try:
                reply = self.client.get_shell_msg(timeout=remaining)
            except queue.Empty:
                self._abandoned.add(msg_id)
                raise TimeoutError(f"No reply within {timeout:g}s") from None
            parent = (reply.get("parent_header") or {}).get("msg_id")
            if parent == msg_id:
                return reply
            self._abandoned.discard(parent)  # a late reply we gave up on


def _read_md_directory(path):
    """Read :data:`MD_KEYS` out of a ``PersistentDict`` directory.

    Deliberately **not** by constructing a ``PersistentDict``.  That class
    registers a ``weakref.finalize`` which writes its entire cache back to
    disk when the object is collected, and zict 3 supports one process at a
    time -- a reader here would eventually overwrite the running session's
    metadata with whatever it happened to have read minutes earlier.

    ``zict.File`` is the layer underneath it and only lists and reads.  Using
    it also keeps the ``key#serial`` filename mangling in the library that
    invented it, rather than reimplementing that guess here.
    """
    import zict
    from bluesky.utils import PersistentDict

    # zict.File creates the directory when it is missing; the caller checks
    # first, so a wrong path is never turned into an empty store on disk.
    store = zict.File(path)
    values = {}
    for key in MD_KEYS:
        try:
            values[key] = PersistentDict._load(store[key])
        except Exception:  # noqa: BLE001 - absent key, or rewritten mid-read
            continue
    return values


def _read_md_file(path):
    """Read a ``StoredDict`` -- one YAML file -- through its own loader."""
    from apstools.utils import StoredDict

    data = StoredDict.load(path)
    return data if isinstance(data, dict) else {}


def _unrepr(text):
    """Turn a repr of a string back into the string."""
    import ast

    value = ast.literal_eval(text)
    if not isinstance(value, str):
        raise ValueError(f"expected a string, got {type(value).__name__}")
    return value
