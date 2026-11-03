"""Append the console's traffic to plain text files.

Everything the session does passes through the IPython console -- typed
commands, the device-loading log, BEC's scan tables, tracebacks, and every
command a tab runs through :meth:`~id4_common.gui.tabs.base.BaseTab.run_in_console`
-- and none of it survives on its own: qtconsole trims its scrollback, the
Restart button clears the pane, and closing the window loses the lot.

The content comes from the kernel's **iopub** channel rather than from the
widget.  iopub is a broadcast, so the poll client sees every message the
console renders even though the console is on a different client
(:meth:`~id4_common.gui.kernel.StatusPoller._drain_iopub` was already reading it to
track busy/idle).  Taking it from there means the file is unaffected by the
scrollback limit or by clearing the console, and it keeps filling **while a
scan is running**, which is when it matters most.

Two things keep the files a manageable size:

* **Progress bars are left out.**  Bluesky redraws a motor's progress bar
  several times a second -- ``"\\r" + meter``, a newline, then a cursor-up --
  and with the cursor movement stripped every redraw became a line of its own.
  One long session put ~2 GB of ``huber_euler: 100%|███…`` in a log whose real
  content was a few hundred scan-table rows.  Stream text is assembled into
  lines, and a line that a carriage return led into and that looks like a bar
  is dropped; the console still shows the bars.  Nothing else is filtered:
  prints, warnings, and above all tracebacks are always kept.
* **The output is split across files** named
  ``<prefix>_<YYYY-MM-DD>_<NNN>.log`` in a chosen directory.  The next file is
  opened when the current one passes a size limit or the date changes, and
  starting again appends to the newest file of the day if it still has room.

Not IPython's ``%logstart``: that records input and results but not stream
output, tracebacks or the device-loading log, which is most of what is wanted
here.  ``apsbits``' ``logging_setup`` already starts one, into
``<cwd>/.logs/ipython_log.py``; this is the complement to it, not a duplicate.

Deliberately Qt-free, so it can be tested without a ``QApplication``.
"""

import datetime
import logging
import re
import time
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

#: Used when no prefix is given, and the Session tab's placeholder.
DEFAULT_PREFIX = "console"

#: Size, in MB, past which the next file is started.
DEFAULT_MAX_MB = 10
BYTES_PER_MB = 1024 * 1024

#: CSI escape sequences.  IPython colours its tracebacks and ophyd colours some
#: warnings; left in, they make the file unreadable in an editor.  This also
#: removes the cursor-up a progress bar writes after each redraw.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

#: Line endings in stream text, each on its own.  ``\r\n`` needs no special
#: case: the empty line between the two is dropped like any blank line a
#: carriage return led into -- and a bar with an empty meter writes exactly
#: ``"\r" + "" + "\n"``, which must not become a blank line in the log.
_LINE_END = re.compile(r"[\r\n]")

#: A bluesky progress bar: tqdm's ``50%|███`` meter; its bar-less form for a
#: move of zero length, ``huber_euler: 0.0 [00:00, ?/s]``, recognised by the
#: elapsed-time bracket; or the fallback for a status that reports no
#: progress.  Loose on purpose -- ``OneLineProgressBar`` may cut the fallback
#: short -- because it is only tried on lines that a carriage return led into,
#: which ordinary output never is.
_PROGRESS = re.compile(
    r"\d+%\|"
    r"|\[(?:\d+:)?\d{2}:\d{2}(?:<[^,\]]*)?, [^\]]*\]"
    r"|\[(?:In progress|Complete)\b"
)

#: Prompt for the first line of an input cell, and for the ones after it.
#: Matches what IPython itself shows, so a logged cell can be pasted back.
_IN_PROMPT = "In [{count}]: "
_CONTINUATION = "   ...: "

#: Marks the start of a session and the end of one.  Comment syntax, so a log
#: of a Python session stays valid Python if anyone feeds it back in.
_HEADER = "# ======== POLAR {station} console — session started {when} ========"
_FOOTER = "# ======== logging stopped {when} ========"
_NOTE = "# -------- {text} — {when} --------"
_CONTINUED_IN = "# -------- continued in {name} — {when} --------"
_CONTINUED_FROM = (
    "# ======== POLAR {station} console — continued from {name}, {when} "
    "========"
)

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _clean(text):
    """Strip ANSI escapes from *text*."""
    return _ANSI.sub("", text or "")


def _now():
    return time.strftime(_TIME_FORMAT)


def _today():
    """Return today's date; a function so tests can move midnight."""
    return datetime.date.today()


def _is_progress(segment):
    """Whether *segment* is part of a progress bar, given a ``\\r`` led to it.

    Blank counts: a finished bar is erased by overwriting it with spaces.
    """
    return not segment.strip() or _PROGRESS.search(segment) is not None


def log_file_name(prefix, day, index=None):
    """Return the name of file number *index* for *prefix* on *day*.

    With no *index* the number reads ``NNN``, for showing the pattern.
    """
    number = "NNN" if index is None else f"{index:03d}"
    return f"{prefix}_{day:%Y-%m-%d}_{number}.log"


class ConsoleTranscript:
    """Write the console's input and output to files, as the session runs.

    Feed :meth:`handle` every iopub message; call :meth:`start` and
    :meth:`stop` to open and close the log.  Writing never raises: an
    :class:`OSError` stops logging and is reported through :attr:`error`,
    because this is driven from a timer that must keep running.
    """

    def __init__(self):
        """Create an inactive transcript."""
        self._file = None
        self.path = None
        self.directory = None
        self.prefix = DEFAULT_PREFIX
        #: Size at which the next file is started.  May be changed while
        #: logging; it is checked before every write.
        self.max_bytes = DEFAULT_MAX_MB * BYTES_PER_MB
        self.started_at = None
        self.bytes_written = 0
        self.error = None
        # The file currently open: its date, its number, and its size
        # including whatever an earlier session left in it.
        self._file_day = None
        self._file_index = None
        self._file_bytes = 0
        self._rotating = False
        # Stream text not yet ended by a newline, which stream it came from,
        # and whether the last line ending seen was a bare carriage return.
        self._pending = ""
        self._pending_name = None
        self._after_cr = False

    @property
    def active(self):
        """Whether a file is currently open for writing."""
        return self._file is not None

    def start(self, directory, prefix=DEFAULT_PREFIX, max_bytes=None):
        """Start logging into *directory*, and write the session header.

        Today's newest ``<prefix>_<date>_<NNN>.log`` is appended to if it is
        under *max_bytes*, so one experiment stays together and pressing
        Start by mistake cannot destroy an earlier transcript; otherwise the
        next number is opened.  Returns True on success; on failure
        :attr:`error` says why.
        """
        self.stop()
        self.error = None
        self._pending = ""
        self._pending_name = None
        self._after_cr = False
        self.directory = Path(directory).expanduser()
        self.prefix = prefix or DEFAULT_PREFIX
        if max_bytes is not None:
            self.max_bytes = max_bytes
        day = _today()
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            index = self._first_index(day)
        except OSError as exc:
            self.error = str(exc)
            logger.warning(
                "Could not open console log in %s: %s", self.directory, exc
            )
            return False
        if not self._open(day, index):
            return False

        self.started_at = time.time()
        self.bytes_written = 0
        self._write(
            _HEADER.format(station=config.station(), when=_now()) + "\n\n"
        )
        return self.active

    def stop(self):
        """Write the footer and close the file, if one is open."""
        if self._file is None:
            return
        self._flush_stream()
        self._write("\n" + _FOOTER.format(when=_now()) + "\n")
        self._close()

    def note(self, text):
        """Record *text* as a marker line.

        Used for events the kernel cannot report itself -- a deliberate
        restart, say, which clears the console but leaves the file intact.
        """
        if self._file is None:
            return
        self._flush_stream()
        self._write("\n" + _NOTE.format(text=text, when=_now()) + "\n\n")

    def handle(self, msg):
        """Write one iopub message.

        Unknown message types are ignored, so comm traffic and anything a
        future kernel adds cost nothing.
        """
        if self._file is None:
            return
        content = msg.get("content") or {}
        handler = getattr(self, f"_on_{msg.get('msg_type')}", None)
        if handler is not None:
            handler(content)

    # -- one method per message type ---------------------------------------

    def _on_status(self, content):
        # A line printed without a newline at the end of a cell is otherwise
        # held until the next output; going idle is the moment to write it.
        if content.get("execution_state") == "idle":
            self._flush_stream()

    def _on_execute_input(self, content):
        self._flush_stream()
        code = _clean(content.get("code", "")).rstrip("\n")
        if not code:
            return
        prompt = _IN_PROMPT.format(count=content.get("execution_count", " "))
        lines = code.split("\n")
        body = "\n".join(
            [prompt + lines[0]] + [_CONTINUATION + ln for ln in lines[1:]]
        )
        self._write("\n" + body + "\n")

    def _on_stream(self, content):
        # Assembled into lines first: a progress bar can only be recognised
        # whole, and the kernel cuts stream text wherever its buffer was
        # flushed, mid-line included.
        name = content.get("name")
        if name != self._pending_name:
            self._flush_stream()
            self._pending_name = name
        # Cleaned after joining, so an escape cut in two is still removed.
        text = _clean(self._pending + (content.get("text") or ""))
        start = 0
        for match in _LINE_END.finditer(text):
            self._write_line(text[start : match.start()], match.group())
            start = match.end()
        self._pending = text[start:]

    def _on_execute_result(self, content):
        self._flush_stream()
        text = _clean((content.get("data") or {}).get("text/plain", ""))
        if text:
            self._write(f"Out[{content.get('execution_count', ' ')}]: {text}\n")

    def _on_display_data(self, content):
        self._flush_stream()
        # Only the text form: an image has no place in a text transcript, and
        # the plain-text alternative is what qtconsole falls back to anyway.
        text = _clean((content.get("data") or {}).get("text/plain", ""))
        if text:
            self._write(text + "\n")

    def _on_error(self, content):
        self._flush_stream()
        traceback = content.get("traceback") or []
        if traceback:
            self._write(_clean("\n".join(traceback)) + "\n")
            return
        name = content.get("ename", "Error")
        self._write(f"{name}: {content.get('evalue', '')}\n")

    # -- stream lines ---------------------------------------------------------

    def _write_line(self, segment, ending):
        """Write one line of stream text, unless it is a progress bar.

        A bare ``\\r`` with nothing before it moves the cursor and nothing
        else; a line led into by one and shaped like a bar is a redraw.  Any
        other line is kept, ending in a plain newline -- a ``\\r`` left in a
        log file shows up as ``^M`` in an editor.
        """
        after_cr = self._after_cr
        self._after_cr = ending == "\r"
        if ending == "\r" and not segment:
            return
        if after_cr and _is_progress(segment):
            return
        self._write(segment + "\n")

    def _flush_stream(self):
        """Write stream text still waiting for its newline."""
        text, self._pending = self._pending, ""
        if not text:
            return
        if self._after_cr and _is_progress(text):
            return
        self._after_cr = False
        self._write(text)

    # -- files ------------------------------------------------------------

    def _first_index(self, day):
        """Return the number to open on *day*: the newest, if it has room."""
        pattern = re.compile(
            re.escape(f"{self.prefix}_{day:%Y-%m-%d}_") + r"(\d+)\.log"
        )
        numbers = [
            int(match.group(1))
            for entry in self.directory.iterdir()
            if (match := pattern.fullmatch(entry.name))
        ]
        return self._free_index(day, max(numbers, default=1))

    def _free_index(self, day, index):
        """Return the first number from *index* on whose file has room."""
        while True:
            path = self.directory / log_file_name(self.prefix, day, index)
            try:
                if path.stat().st_size < self.max_bytes:
                    return index
            except FileNotFoundError:
                return index
            index += 1

    def _open(self, day, index):
        """Open file *index* of *day* for appending; return True on success."""
        path = self.directory / log_file_name(self.prefix, day, index)
        try:
            existing = path.stat().st_size if path.exists() else 0
            # Line buffered, so the file is current without explicit flushing:
            # `tail -f` follows the session, and nothing is lost if the GUI is
            # killed.  Only valid in text mode, which is what we want anyway.
            self._file = open(  # noqa: SIM115 - closed by _close()
                path, "a", encoding="utf-8", errors="replace", buffering=1
            )
        except OSError as exc:
            self._file = None
            self.error = str(exc)
            logger.warning("Could not open console log %s: %s", path, exc)
            return False
        self.path = path
        self._file_day = day
        self._file_index = index
        self._file_bytes = existing
        if existing:
            self._emit("\n")
        return True

    def _close(self):
        try:
            self._file.close()
        except OSError:  # pragma: no cover - closing a broken handle
            logger.debug("Could not close %s.", self.path, exc_info=True)
        self._file = None

    def _rotation_due(self):
        return self._file_bytes >= self.max_bytes or _today() != self._file_day

    def _rotate(self):
        """Close the current file and carry on in the next one.

        Called from :meth:`_write` before the text that needed the room, so
        a split lands between two writes -- between lines, since stream text
        arrives here a line at a time.  Nothing pending is flushed: it
        belongs *after* the text being written, and follows it into the new
        file.
        """
        self._rotating = True
        try:
            day = _today()
            try:
                if day == self._file_day:
                    index = self._free_index(day, self._file_index + 1)
                else:
                    index = self._first_index(day)
            except OSError as exc:
                self.error = str(exc)
                logger.warning("Console log rotation failed, stopping: %s", exc)
                self._close()
                return
            name = log_file_name(self.prefix, day, index)
            previous = self.path.name
            self._emit(
                "\n" + _CONTINUED_IN.format(name=name, when=_now()) + "\n"
            )
            if self._file is None:
                return
            self._close()
            if self._open(day, index):
                self._emit(
                    _CONTINUED_FROM.format(
                        station=config.station(), name=previous, when=_now()
                    )
                    + "\n\n"
                )
        finally:
            self._rotating = False

    # -- writing ------------------------------------------------------------

    def _write(self, text):
        """Write *text*, starting the next file first if this one is full."""
        if self._file is None or not text:
            return
        if not self._rotating and self._rotation_due():
            self._rotate()
        self._emit(text)

    def _emit(self, text):
        """Write *text*, stopping the log rather than raising on failure."""
        if self._file is None or not text:
            return
        try:
            self._file.write(text)
            # Line buffering only flushes on a newline; a partial line
            # written at the end of a cell would otherwise sit in memory.
            if not text.endswith("\n"):
                self._file.flush()
        except OSError as exc:
            # A full disk or a vanished mount must not take the poll timer --
            # and with it the whole status display -- down with it.
            self.error = str(exc)
            logger.warning("Console log write failed, stopping: %s", exc)
            handle, self._file = self._file, None
            try:
                handle.close()
            except OSError:
                logger.debug("Could not close %s.", self.path, exc_info=True)
            return
        size = len(text.encode("utf-8", "replace"))
        self.bytes_written += size
        self._file_bytes += size
