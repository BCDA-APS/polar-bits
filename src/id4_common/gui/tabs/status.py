"""Session status tab: catalog, user, scan number, output files, console log."""

import datetime
import time
from pathlib import Path

from qtpy.QtCore import QRegularExpression
from qtpy.QtCore import QSettings
from qtpy.QtCore import Qt
from qtpy.QtCore import QTimer
from qtpy.QtGui import QRegularExpressionValidator
from qtpy.QtWidgets import QFileDialog
from qtpy.QtWidgets import QFormLayout
from qtpy.QtWidgets import QGroupBox
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QLineEdit
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QSpinBox
from qtpy.QtWidgets import QVBoxLayout

from .. import config
from ..transcript import BYTES_PER_MB
from ..transcript import DEFAULT_MAX_MB
from ..transcript import DEFAULT_PREFIX
from ..transcript import log_file_name
from .base import PLACEHOLDER
from .base import BaseTab
from .base import value_label

#: Kernel states that mean the RunEngine cannot be queried right now.
_BUSY_STATES = ("busy", "dead")

#: Shared with ``app.py`` and ``tabs/macro.py``, which re-declare them for the
#: same reason: importing from ``app`` would be circular.
#: The application half is ``config.qsettings_app()``, per station and so
#: called at each use.  It matters most here: the ``LOG_*`` keys below are
#: what ``app.MainWindow`` reads to auto-start the transcript, and a shared
#: scope would have a 4IDB session appending its console to 4IDG's log files.
SETTINGS_ORG = config.QSETTINGS_ORG
LOG_DIR_KEY = "console/log_dir"
LOG_PREFIX_KEY = "console/log_prefix"
LOG_MAX_MB_KEY = "console/log_max_mb"
LOG_ENABLED_KEY = "console/log_enabled"

#: The single log file of earlier versions.  Read once, to seed the
#: directory and prefix when neither has been stored yet.
LOG_PATH_KEY = "console/log_path"

#: Bounds of the "Split at" spin box.
LOG_MAX_MB_RANGE = (1, 1000)

#: How often the "12.4 kB since 15:04" line is refreshed.  Its own timer, not
#: ``kernel_values_changed``: those stop arriving during a scan, which is
#: exactly when watching the log grow is worth anything.
LOG_STATUS_INTERVAL_MS = 1000


def _format_size(count):
    """Render a byte count compactly, for the log status line."""
    if count < 1024:
        return f"{count} B"
    if count < 1024 * 1024:
        return f"{count / 1024:.1f} kB"
    return f"{count / (1024 * 1024):.1f} MB"


def stored_log_target(settings):
    """Return the remembered ``(directory, prefix, max_mb)`` of the log.

    ``directory`` is ``""`` when nothing has been chosen yet, leaving the
    caller to default it to the working directory.  A path stored by the
    single-file log of earlier versions stands in for both directory and
    prefix -- ``/data/console.log`` becomes ``/data`` and ``console`` -- so an
    upgrade carries on logging where it did before.
    """
    directory = settings.value(LOG_DIR_KEY, "", type=str)
    prefix = settings.value(LOG_PREFIX_KEY, "", type=str)
    if not directory:
        legacy = settings.value(LOG_PATH_KEY, "", type=str)
        if legacy:
            directory = str(Path(legacy).parent)
            prefix = prefix or Path(legacy).stem
    max_mb = settings.value(LOG_MAX_MB_KEY, DEFAULT_MAX_MB, type=int)
    low, high = LOG_MAX_MB_RANGE
    return directory, prefix or DEFAULT_PREFIX, min(max(max_mb, low), high)


class StatusTab(BaseTab):
    """Overview of the current Bluesky session."""

    title = "Session"

    def __init__(self, parent=None):
        """Build the Session, Scan, Files and Console log groups."""
        super().__init__(parent)

        self._fields = {}
        self._re_state = None
        self._kernel_state = None
        self._kernel_cwd = None
        self._settings = QSettings(SETTINGS_ORG, config.qsettings_app())

        layout = QVBoxLayout(self)
        layout.addWidget(
            self._group(
                "Session",
                [
                    ("catalog", "Catalog"),
                    ("n_runs", "Runs in catalog"),
                    ("login_id", "User"),
                    ("proposal_id", "Proposal"),
                    ("beamline_id", "Beamline"),
                    ("instrument_name", "Instrument"),
                ],
            )
        )
        layout.addWidget(
            self._group(
                "Scan",
                [
                    ("scan_id", "Last scan #"),
                    ("re_state", "RunEngine"),
                    ("kernel_state", "Kernel"),
                ],
            )
        )
        layout.addWidget(
            self._group(
                "Files",
                [
                    ("spec_file", "SPEC file"),
                    ("sample", "Sample"),
                    ("exp_path", "Experiment path"),
                    ("cwd", "Working directory"),
                ],
            )
        )
        layout.addWidget(self._build_log_group())
        layout.addStretch(1)

        # Runs only while logging, so an idle session pays nothing for it.
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(LOG_STATUS_INTERVAL_MS)
        self._log_timer.timeout.connect(self._refresh_log_status)

    def _group(self, title, fields):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setLabelAlignment(form.labelAlignment())
        for key, caption in fields:
            label = value_label()
            self._fields[key] = label
            row = QHBoxLayout()
            row.addWidget(label)
            row.addStretch(1)
            form.addRow(f"{caption}:", row)
        return box

    def _set(self, key, value):
        label = self._fields.get(key)
        if label is None:
            return
        if value is None or value == "":
            label.setText(PLACEHOLDER)
        else:
            label.setText(str(value))

    # -- console log ----------------------------------------------------------

    def _build_log_group(self):
        """Directory, prefix, split size, Start/Stop and a live status line.

        The console is the only record of what was done to the instrument, and
        it does not survive: qtconsole trims its scrollback, Restart clears the
        pane, and closing the window loses everything.  This group points that
        traffic at a series of files, ``<prefix>_<date>_<NNN>.log``.
        """
        box = QGroupBox("Console log")
        form = QFormLayout(box)

        self._log_dir_edit = QLineEdit()
        self._log_dir_edit.setPlaceholderText(str(self._default_dir()))
        self._log_dir_edit.setToolTip(
            "Folder the console log files are written to.  Missing folders "
            "are created."
        )
        self._log_browse = QPushButton("Browse…")
        self._log_browse.clicked.connect(self._browse_log)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._log_dir_edit, 1)
        dir_row.addWidget(self._log_browse)
        form.addRow("Directory:", dir_row)

        self._log_prefix_edit = QLineEdit()
        self._log_prefix_edit.setPlaceholderText(DEFAULT_PREFIX)
        # A name, not a path: the directory has its own field.
        self._log_prefix_edit.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"[^/\\]*"), self._log_prefix_edit
            )
        )
        self._log_prefix_edit.setToolTip(
            "Start of every file name.  The date and a file number are "
            "added automatically."
        )
        self._log_prefix_edit.textChanged.connect(self._refresh_log_pattern)
        self._log_pattern = QLabel()
        self._log_pattern.setEnabled(False)
        prefix_row = QHBoxLayout()
        prefix_row.addWidget(self._log_prefix_edit, 1)
        prefix_row.addWidget(self._log_pattern)
        form.addRow("Prefix:", prefix_row)

        self._log_max_mb = QSpinBox()
        self._log_max_mb.setRange(*LOG_MAX_MB_RANGE)
        self._log_max_mb.setValue(DEFAULT_MAX_MB)
        self._log_max_mb.setSuffix(" MB")
        self._log_max_mb.setKeyboardTracking(False)
        # Focus on a click only.  The application's wheel guard (nowheel.py)
        # already keeps a scroll from stepping it; this keeps Tab from
        # landing on it too.
        self._log_max_mb.setFocusPolicy(Qt.ClickFocus)
        self._log_max_mb.setToolTip(
            "Start the next file once the current one is this big.  A new "
            "file is also started when the date changes.  Takes effect "
            "immediately, even while logging."
        )
        self._log_max_mb.valueChanged.connect(self._set_log_max_mb)
        size_row = QHBoxLayout()
        size_row.addWidget(self._log_max_mb)
        size_row.addStretch(1)
        form.addRow("Split at:", size_row)

        self._log_button = QPushButton("Start logging")
        self._log_button.clicked.connect(self._toggle_log)
        hint = QLabel(
            "New file each day or past the size limit; never overwritten."
        )
        hint.setEnabled(False)
        button_row = QHBoxLayout()
        button_row.addWidget(self._log_button)
        button_row.addWidget(hint)
        button_row.addStretch(1)
        form.addRow("", button_row)

        self._log_status = value_label()
        status_row = QHBoxLayout()
        status_row.addWidget(self._log_status)
        status_row.addStretch(1)
        form.addRow("Status:", status_row)
        self._refresh_log_pattern()
        return box

    def _default_dir(self):
        """Where to log when nothing has been chosen yet.

        The polled ``cwd`` -- what the Working directory field shows -- is
        preferred over ``session_cwd``, which is only a snapshot taken when the
        window was built.  ``experiment_setup()`` chdirs the kernel into the
        experiment folder, so the snapshot goes stale as soon as it runs and
        would put the log next to the source checkout instead of the data.
        """
        base = self._kernel_cwd or self.session_cwd
        return Path(base) if base else Path.cwd()

    def _log_prefix(self):
        return self._log_prefix_edit.text().strip() or DEFAULT_PREFIX

    def _refresh_log_pattern(self):
        """Show the file names the prefix will produce."""
        name = log_file_name(self._log_prefix(), datetime.date.today())
        self._log_pattern.setText(f"→ {name}")

    def _follow_cwd(self, cwd):
        """Move the default log directory with the kernel's working directory.

        Only an untouched default follows.  A directory the user typed or
        browsed to, one remembered from a previous session, and that of a log
        that is already running are all left where they are -- the point is to
        default sensibly, not to move the log out from under anyone.
        """
        if cwd == self._kernel_cwd:
            return
        stale = str(self._default_dir())
        self._kernel_cwd = cwd
        fresh = str(self._default_dir())
        self._log_dir_edit.setPlaceholderText(fresh)
        transcript = self.transcript
        if transcript is not None and transcript.active:
            return
        if self._log_dir_edit.text().strip() in ("", stale):
            self._log_dir_edit.setText(fresh)

    def sync_transcript(self):
        """Show the state of the shared transcript.

        Called by ``MainWindow`` once ``transcript`` and ``session_cwd`` are
        set -- which is *after* the window has already auto-resumed logging, so
        the tab has to read the transcript rather than assume it is idle.
        """
        directory, prefix, max_mb = stored_log_target(self._settings)
        transcript = self.transcript
        if transcript is not None and transcript.active:
            self._log_dir_edit.setText(str(transcript.directory))
            self._log_prefix_edit.setText(transcript.prefix)
        else:
            if not self._log_dir_edit.text().strip():
                self._log_dir_edit.setText(
                    directory or str(self._default_dir())
                )
            if not self._log_prefix_edit.text().strip():
                self._log_prefix_edit.setText(prefix)
        self._log_max_mb.setValue(max_mb)
        self._log_dir_edit.setPlaceholderText(str(self._default_dir()))
        self._update_log_controls()

    def _browse_log(self):
        """Pick the folder the log files go in."""
        current = self._log_dir_edit.text().strip() or str(self._default_dir())
        path = QFileDialog.getExistingDirectory(
            self, "Console log folder", current
        )
        if path:
            self._log_dir_edit.setText(path)

    def _set_log_max_mb(self, value):
        """Remember the split size, and apply it to a log already running."""
        self._settings.setValue(LOG_MAX_MB_KEY, value)
        if self.transcript is not None:
            self.transcript.max_bytes = value * BYTES_PER_MB

    def _toggle_log(self):
        """Start logging with the chosen directory and prefix, or stop."""
        transcript = self.transcript
        if transcript is None:
            self._log_status.setText("no transcript available")
            return
        if transcript.active:
            transcript.stop()
            self._settings.setValue(LOG_ENABLED_KEY, False)
        else:
            directory = self._log_dir_edit.text().strip() or str(
                self._default_dir()
            )
            prefix = self._log_prefix()
            self._log_dir_edit.setText(directory)
            self._log_prefix_edit.setText(prefix)
            # Remembered even if the start fails: an unwritable directory is
            # usually a mount that is not up yet, and the next launch may well
            # work.
            self._settings.setValue(LOG_PREFIX_KEY, prefix)
            self._settings.setValue(LOG_DIR_KEY, directory)
            max_bytes = self._log_max_mb.value() * BYTES_PER_MB
            if transcript.start(directory, prefix, max_bytes):
                self._settings.setValue(LOG_DIR_KEY, str(transcript.directory))
                self._settings.setValue(LOG_ENABLED_KEY, True)
        self._update_log_controls()

    def _update_log_controls(self):
        """Match the button, the fields and the timer to the log state."""
        transcript = self.transcript
        active = transcript is not None and transcript.active
        self._log_button.setText("Stop logging" if active else "Start logging")
        self._log_button.setEnabled(transcript is not None)
        # Locked while writing, so the files cannot be swapped out from under
        # an open handle -- stop first.  The split size stays editable: it is
        # read afresh before every write.
        self._log_dir_edit.setEnabled(not active)
        self._log_prefix_edit.setEnabled(not active)
        self._log_browse.setEnabled(not active)
        if active:
            self._log_timer.start()
        else:
            self._log_timer.stop()
        self._refresh_log_status()

    def _refresh_log_status(self):
        """One line: what is being written, how much of it, and since when."""
        transcript = self.transcript
        if transcript is None:
            self._log_status.setText(PLACEHOLDER)
            return
        if self._log_timer.isActive() and not transcript.active:
            # The transcript closed itself -- a full disk, a vanished mount.
            # Stop the timer first, so re-entering here cannot recurse.
            self._log_timer.stop()
            self._update_log_controls()
            return
        if transcript.active:
            since = time.strftime(
                "%H:%M", time.localtime(transcript.started_at)
            )
            self._log_status.setText(
                f"writing to {transcript.path.name} — "
                f"{_format_size(transcript.bytes_written)} since {since}"
            )
        elif transcript.error:
            # Covers both a refused start and a log that stopped itself on a
            # full disk, which the user would otherwise never hear about.
            self._log_status.setText(f"not logging — {transcript.error}")
        else:
            self._log_status.setText("not logging")

    def on_metadata(self, metadata):
        """Fill the fields carried by the RunEngine metadata file."""
        self._set("catalog", metadata.get("databroker_catalog"))
        self._set("login_id", metadata.get("login_id"))
        self._set("proposal_id", metadata.get("proposal_id"))
        self._set("beamline_id", metadata.get("beamline_id"))
        self._set("instrument_name", metadata.get("instrument_name"))
        self._set("scan_id", metadata.get("scan_id"))

    def on_document(self, name, doc):
        """Take the scan number from a run as it opens.

        The poll cannot do this one: it is held back while the kernel is
        busy, which is the whole length of a scan.  Documents arrive over
        ZMQ instead, so this is the only path that moves the number while
        the scan it belongs to is still running.
        """
        if name == "start" and doc.get("scan_id") is not None:
            self._set("scan_id", doc["scan_id"])

    def on_kernel_values(self, values):
        """Fill the fields that only the kernel can answer."""
        if "n_runs" in values:
            self._set("n_runs", values["n_runs"])
        if "spec_file" in values:
            self._set("spec_file", values["spec_file"])
        if "cwd" in values:
            self._set("cwd", values["cwd"])
            self._follow_cwd(values["cwd"])
        # Absent whenever experiment_setup() has not been run yet.
        self._set("sample", values.get("sample"))
        self._set("exp_path", values.get("exp_path"))
        if "re_state" in values:
            self._re_state = values["re_state"]
        self._refresh_state()

    def on_kernel_state(self, state):
        """Track kernel liveness and refresh the derived RunEngine state."""
        self._kernel_state = state
        self._refresh_state()

    def _refresh_state(self):
        """Show kernel state, and derive RunEngine state when it is busy.

        A running plan holds the shell channel, so ``RE.state`` cannot be
        polled mid-scan; busy is reported as ``running`` instead of going
        stale.
        """
        self._set("kernel_state", self._kernel_state)
        if self._kernel_state == "busy":
            self._set("re_state", "running")
        elif self._kernel_state in _BUSY_STATES:
            self._set("re_state", None)
        else:
            self._set("re_state", self._re_state)
