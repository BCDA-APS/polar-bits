"""Incremental SWMR reader for live flyscan plotting.

The acquisition pipeline writes three HDF5 files per scan in SWMR mode:
``pos_stream``, ``eiger``, and ``vortex``. :class:`LiveScanReader` keeps a
small amount of state (cursors + the open trigger group's running aggregates)
so that each :meth:`tick` reads only the rows / frames that have been
appended since the previous call.

The reductions mirror :mod:`process_flyscan` exactly so that running this
backend to exhaustion on a finished scan gives the same arrays as the
post-scan processing.

The class is Qt-free — it is meant to be driven from a worker thread.
"""

from dataclasses import dataclass
import os
import re
import time

import h5py
import hdf5plugin  # noqa: F401  -- registers HDF5 codecs (LZ4, Bitshuffle, ...)
import numpy as np

from .flyscan_gui import _FNAME_PATTERNS, _resolve_h5  # noqa: F401  -- _FNAME_PATTERNS re-exported
from .process_flyscan import flag_partial_groups, raw_slice_for_roi


# Match both the padded (scan_000244.h5) and unpadded (scan_244.h5) naming
# conventions supported by `_FNAME_PATTERNS`. Files like `scan5_000254.h5`
# (a stray typo in the NdFeB folder) deliberately do NOT match.
_SCAN_NAME_RE = re.compile(r"^scan_(\d+)\.h5$")


def find_latest_scan(folder):
    """Return the highest scan number found in ``<folder>/pos_stream/``.

    Returns ``None`` if the directory does not exist or contains no
    matching files. Used by the live GUI's auto-latest mode to detect
    a newly-created scan and switch to it.
    """
    pos_dir = os.path.join(folder, "pos_stream")
    try:
        it = os.scandir(pos_dir)
    except (FileNotFoundError, NotADirectoryError):
        return None
    latest = None
    with it:
        for entry in it:
            if not entry.is_file():
                continue
            m = _SCAN_NAME_RE.match(entry.name)
            if not m:
                continue
            n = int(m.group(1))
            if latest is None or n > latest:
                latest = n
    return latest


@dataclass
class TickResult:
    """Snapshot of the reader's cumulative state after one tick."""

    xs: np.ndarray
    ys: np.ndarray
    i0s: np.ndarray
    dxs: np.ndarray
    dys: np.ndarray
    trigs: np.ndarray     # eigerTrig value of each closed group
    counts: np.ndarray    # rows actually recorded in each closed group
    coverage: np.ndarray  # ckIM ticks each closed group spans
    partial: np.ndarray   # bool: group spans less than a full exposure
    eiger_z: np.ndarray
    vortex_z: np.ndarray
    n_triggers_closed: int
    n_eiger_frames: int
    n_vortex_frames: int
    grew: bool
    pos_available: bool
    eiger_available: bool
    vortex_available: bool


class LiveScanReader:
    """Incrementally read a flyscan's HDF5 files while the writer is still
    appending. Designed to be invoked from a background thread; the only
    public entry points (:meth:`tick`, :meth:`reprocess_eiger`,
    :meth:`reprocess_vortex`, :meth:`close`) are the ones that touch the
    HDF5 handles, so all of them must run on the same worker thread.
    """

    def __init__(self, folder, scan_number, eiger_roi, vortex_roi, batch=100):
        self.folder = folder
        self.scan_number = int(scan_number)
        # ROIs are kept mutable so the GUI can change them between ticks.
        self.eiger_roi = (
            (int(eiger_roi[0][0]), int(eiger_roi[0][1])),
            (int(eiger_roi[1][0]), int(eiger_roi[1][1])),
        )
        self.vortex_roi = (int(vortex_roi[0]), int(vortex_roi[1]))
        self.batch = int(batch)

        # File handles + dataset handles. Open lazily on the first tick (and
        # re-attempted on each subsequent tick until they succeed).
        self._pos_file = None
        self._pos_dset = None
        self._eiger_file = None
        self._eiger_dset = None
        self._vortex_file = None
        self._vortex_dset = None

        # Cumulative outputs — one entry per CLOSED trigger / processed frame.
        # We keep these as numpy arrays and concatenate in-place each tick.
        self.xs = np.empty(0, dtype=np.float64)
        self.ys = np.empty(0, dtype=np.float64)
        self.i0s = np.empty(0, dtype=np.float64)
        self.dxs = np.empty(0, dtype=np.float64)
        self.dys = np.empty(0, dtype=np.float64)
        # Per closed group: its eigerTrig value (which ties it to a detector
        # frame), the rows recorded, and the ckIM ticks spanned. Coverage is
        # what flags a partial exposure; rows below coverage means the MCS
        # dropped a sample without shortening the exposure window.
        self.trigs = np.empty(0, dtype=np.int64)
        self.counts = np.empty(0, dtype=np.int64)
        self.coverage = np.empty(0, dtype=np.int64)
        self.eiger_z = np.empty(0, dtype=np.float64)
        self.vortex_z = np.empty(0, dtype=np.float64)

        # Cursors.
        self._pos_cursor = 0           # next raw pos_stream row to read
        self._eiger_cursor = 0         # next detector frame to sum
        self._vortex_cursor = 0        # next spectrum to sum

        # Pending (open) trigger group state.
        self._pending_trig = None
        self._pending_count = 0
        self._pending_sum_x = 0.0
        self._pending_sum_y = 0.0
        self._pending_min_x = 0.0
        self._pending_max_x = 0.0
        self._pending_min_y = 0.0
        self._pending_max_y = 0.0
        self._pending_min_i0 = 0.0
        self._pending_max_i0 = 0.0
        self._pending_min_ck = 0.0
        self._pending_max_ck = 0.0

        # Activity tracking for the GUI's idle-timeout heuristic.
        self.last_growth_time = time.monotonic()

    # ------------------------------------------------------------------ files

    def _open_one(self, stream):
        """Try to (lazily) open one of the three stream files in SWMR mode.

        Returns ``(file, dset, fname_format)`` on success, ``(None, None, None)``
        if the file does not yet exist or cannot be opened.
        """
        path, fmt = _resolve_h5(self.folder, stream, self.scan_number)
        if path is None or not os.path.exists(path):
            return None, None, None
        try:
            # libver="latest" + swmr=True is what the writer uses; readers
            # must request swmr=True so libhdf5 honours the writer's
            # incremental flushes.
            f = h5py.File(path, "r", swmr=True)
        except (OSError, IOError):
            # File may exist but not yet have SWMR enabled (the writer has
            # to call f.swmr_mode = True after creating the dataset).
            return None, None, None
        try:
            dset = f["entry/data/data"]
        except KeyError:
            f.close()
            return None, None, None
        return f, dset, fmt

    def _ensure_open(self):
        if self._pos_dset is None:
            self._pos_file, self._pos_dset, _ = self._open_one("pos_stream")
        if self._eiger_dset is None:
            self._eiger_file, self._eiger_dset, _ = self._open_one("eiger")
        if self._vortex_dset is None:
            self._vortex_file, self._vortex_dset, _ = self._open_one("vortex")

    def close(self):
        for attr in ("_pos_file", "_eiger_file", "_vortex_file"):
            f = getattr(self, attr)
            if f is not None:
                try:
                    f.close()
                except Exception:
                    pass
            setattr(self, attr, None)
        self._pos_dset = None
        self._eiger_dset = None
        self._vortex_dset = None

    # ----------------------------------------------------------- pending group

    def _reset_pending(self, run_trig):
        self._pending_trig = int(run_trig)
        self._pending_count = 0
        self._pending_sum_x = 0.0
        self._pending_sum_y = 0.0
        # min/max get seeded on the first accumulation.
        self._pending_min_x = np.inf
        self._pending_max_x = -np.inf
        self._pending_min_y = np.inf
        self._pending_max_y = -np.inf
        self._pending_min_i0 = np.inf
        self._pending_max_i0 = -np.inf
        self._pending_min_ck = np.inf
        self._pending_max_ck = -np.inf

    def _accumulate(self, run):
        """Fold a contiguous run of samples (all sharing one trigger index)
        into the pending aggregates. Columns: 0=I0, 1=ckIM counter, 3=x, 4=y.
        """
        n = run.shape[0]
        if n == 0:
            return
        self._pending_count += n
        self._pending_sum_x += float(run[:, 3].sum())
        self._pending_sum_y += float(run[:, 4].sum())
        self._pending_min_x = min(self._pending_min_x, float(run[:, 3].min()))
        self._pending_max_x = max(self._pending_max_x, float(run[:, 3].max()))
        self._pending_min_y = min(self._pending_min_y, float(run[:, 4].min()))
        self._pending_max_y = max(self._pending_max_y, float(run[:, 4].max()))
        self._pending_min_i0 = min(self._pending_min_i0, float(run[:, 0].min()))
        self._pending_max_i0 = max(self._pending_max_i0, float(run[:, 0].max()))
        self._pending_min_ck = min(self._pending_min_ck, float(run[:, 1].min()))
        self._pending_max_ck = max(self._pending_max_ck, float(run[:, 1].max()))

    def _flush_pending(self):
        """Emit the pending trigger group as a new (x, y, I0, dx, dy) entry."""
        if self._pending_trig is None or self._pending_count == 0:
            return
        x = self._pending_sum_x / self._pending_count
        y = self._pending_sum_y / self._pending_count
        dx = self._pending_max_x - self._pending_min_x
        dy = self._pending_max_y - self._pending_min_y
        i0 = self._pending_max_i0 - self._pending_min_i0
        self.xs = np.append(self.xs, x)
        self.ys = np.append(self.ys, y)
        self.dxs = np.append(self.dxs, dx)
        self.dys = np.append(self.dys, dy)
        self.i0s = np.append(self.i0s, i0)
        self.trigs = np.append(self.trigs, self._pending_trig)
        self.counts = np.append(self.counts, self._pending_count)
        # Span the group in ckIM ticks, so a dropped row doesn't masquerade
        # as a short exposure.
        self.coverage = np.append(
            self.coverage, int(self._pending_max_ck - self._pending_min_ck) + 1)

    # ------------------------------------------------------------- pos stream

    def _process_pos(self):
        """Read new pos_stream rows and update closed/pending trigger state.

        Returns True if any rows were consumed (and hence one or more trigger
        groups may have closed since the previous tick).
        """
        if self._pos_dset is None:
            return False
        try:
            self._pos_dset.id.refresh()
        except Exception:
            return False
        n = self._pos_dset.shape[0]
        if n <= self._pos_cursor:
            return False
        chunk = self._pos_dset[self._pos_cursor:n, :]
        self._pos_cursor = n

        trig = chunk[:, 2]
        # Boundary indices WITHIN this chunk where the trigger value changes.
        boundary = np.where(np.diff(trig) != 0)[0] + 1
        splits = np.concatenate(([0], boundary, [len(trig)]))

        for k in range(len(splits) - 1):
            a, b = splits[k], splits[k + 1]
            run_trig = int(trig[a])

            if self._pending_trig is None:
                self._reset_pending(run_trig)
            elif run_trig != self._pending_trig:
                # A new trigger value has arrived → the previous one is closed.
                self._flush_pending()
                self._reset_pending(run_trig)

            self._accumulate(chunk[a:b])

        return True

    # ---------------------------------------------------------------- eiger

    def _sum_eiger_range(self, start, stop, roi):
        """Sum the eiger ROI for frames ``[start, stop)`` and return a 1-D array.

        *roi* is in display coordinates -- the rotated frame the user drew it
        on -- so it is mapped back to raw row/column indices here.
        """
        (r0, r1), (c0, c1) = raw_slice_for_roi(roi, self._eiger_dset.shape[2])
        out = np.empty(stop - start, dtype=np.float64)
        for i in range(start, stop, self.batch):
            j = min(i + self.batch, stop)
            out[i - start:j - start] = self._eiger_dset[i:j, r0:r1, c0:c1].sum(axis=(1, 2))
        return out

    def _process_eiger(self):
        if self._eiger_dset is None:
            return False
        try:
            self._eiger_dset.id.refresh()
        except Exception:
            return False
        n = self._eiger_dset.shape[0]
        if n <= self._eiger_cursor:
            return False
        new = self._sum_eiger_range(self._eiger_cursor, n, self.eiger_roi)
        self.eiger_z = np.concatenate([self.eiger_z, new])
        self._eiger_cursor = n
        return True

    # ---------------------------------------------------------------- vortex

    def _sum_vortex_range(self, start, stop, roi):
        e0, e1 = roi
        out = np.empty(stop - start, dtype=np.float64)
        for i in range(start, stop, self.batch):
            j = min(i + self.batch, stop)
            out[i - start:j - start] = self._vortex_dset[i:j, :, e0:e1].sum(axis=(1, 2))
        return out

    def _process_vortex(self):
        if self._vortex_dset is None:
            return False
        try:
            self._vortex_dset.id.refresh()
        except Exception:
            return False
        n = self._vortex_dset.shape[0]
        if n <= self._vortex_cursor:
            return False
        new = self._sum_vortex_range(self._vortex_cursor, n, self.vortex_roi)
        self.vortex_z = np.concatenate([self.vortex_z, new])
        self._vortex_cursor = n
        return True

    # ------------------------------------------------------------------ tick

    def tick(self):
        """Drive one polling cycle. Returns a :class:`TickResult` snapshot."""
        self._ensure_open()
        grew = False
        if self._process_pos():
            grew = True
        if self._process_eiger():
            grew = True
        if self._process_vortex():
            grew = True
        if grew:
            self.last_growth_time = time.monotonic()
        return self._snapshot(grew)

    def finalize(self):
        """Close the trigger group still open at the end of a scan.

        A group is normally emitted only when the *next* trigger value shows
        up, so the last exposure of a scan never closes on its own and its
        detector frame ends up with no position. Once the writer has stopped
        there is no next trigger coming, so the GUI calls this when it decides
        the scan is over; the group lands like any other, short coverage and
        all, and is flagged partial. Returns a fresh snapshot, or None if
        there was nothing left to flush.
        """
        if self._pending_trig is None or self._pending_count == 0:
            return None
        self._flush_pending()
        # Don't let a second call emit the same group again.
        self._pending_trig = None
        self._pending_count = 0
        return self._snapshot(False)

    def _snapshot(self, grew):
        return TickResult(
            xs=self.xs.copy(),
            ys=self.ys.copy(),
            i0s=self.i0s.copy(),
            dxs=self.dxs.copy(),
            dys=self.dys.copy(),
            trigs=self.trigs.copy(),
            counts=self.counts.copy(),
            coverage=self.coverage.copy(),
            partial=flag_partial_groups(self.coverage),
            eiger_z=self.eiger_z.copy(),
            vortex_z=self.vortex_z.copy(),
            n_triggers_closed=int(self.xs.size),
            n_eiger_frames=int(self._eiger_cursor),
            n_vortex_frames=int(self._vortex_cursor),
            grew=grew,
            pos_available=self._pos_dset is not None,
            eiger_available=self._eiger_dset is not None,
            vortex_available=self._vortex_dset is not None,
        )

    # ------------------------------------------------- single-frame access

    def read_eiger_frame(self, index):
        """Return Eiger frame ``index`` as float32, or None if it isn't there.

        Goes through the reader's own SWMR handle, so it sees every frame the
        writer has flushed — and, like :meth:`tick`, must not run at the same
        time as another method on this instance.
        """
        if self._eiger_dset is None:
            return None
        try:
            self._eiger_dset.id.refresh()
        except Exception:
            pass
        index = int(index)
        if index < 0 or index >= self._eiger_dset.shape[0]:
            return None
        return self._eiger_dset[index].astype(np.float32)

    # ----------------------------------------------- ROI reprocess (mid-scan)

    def reprocess_eiger(self, new_roi):
        """Replace ``eiger_z`` with sums computed for the new ROI over all
        frames already consumed. The cursor is unchanged, so the next tick
        continues from where it left off using the new ROI.
        """
        new_roi = (
            (int(new_roi[0][0]), int(new_roi[0][1])),
            (int(new_roi[1][0]), int(new_roi[1][1])),
        )
        self.eiger_roi = new_roi
        if self._eiger_dset is None or self._eiger_cursor == 0:
            self.eiger_z = np.empty(0, dtype=np.float64)
            return self.eiger_z
        try:
            self._eiger_dset.id.refresh()
        except Exception:
            pass
        self.eiger_z = self._sum_eiger_range(0, self._eiger_cursor, new_roi)
        return self.eiger_z

    def reprocess_vortex(self, new_roi):
        new_roi = (int(new_roi[0]), int(new_roi[1]))
        self.vortex_roi = new_roi
        if self._vortex_dset is None or self._vortex_cursor == 0:
            self.vortex_z = np.empty(0, dtype=np.float64)
            return self.vortex_z
        try:
            self._vortex_dset.id.refresh()
        except Exception:
            pass
        self.vortex_z = self._sum_vortex_range(0, self._vortex_cursor, new_roi)
        return self.vortex_z
