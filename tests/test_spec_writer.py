"""Tests for the local SPEC data file writer callback.

Regression coverage for the pymca "one column" bug: non-numeric columns
(e.g. ``eiger_hdf1_full_file_name``, a string path) must be dropped from the
SPEC output entirely so the data block stays a contiguous numeric matrix.
Previously they were substituted inline and reported on a ``#U`` line written
between every data row, which broke pymca's specfile column detection.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

# The shared conftest stubs ``id4_common.callbacks`` as an empty package, so a
# normal ``from id4_common.callbacks...`` import is blocked.  Load the writer
# module directly from its file (it only needs numpy + apstools at import).
_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "id4_common"
    / "callbacks"
    / "apstools_spec_file_writer.py"
)
_spec = importlib.util.spec_from_file_location(
    "apstools_spec_file_writer_under_test", _MODULE_PATH
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SpecWriterCallback2 = _mod.SpecWriterCallback2

# ---------------------------------------------------------------------------
# Synthetic Bluesky documents: a count with a scaler (numeric) plus an eiger
# string column.
# ---------------------------------------------------------------------------

START = {
    "uid": "uid-0001",
    "time": 1000.0,
    "scan_id": 1,
    "plan_name": "count",
    "plan_type": "generator",
    "detectors": ["scaler1", "eiger"],
    "motors": [],
    "hints": {},
}

DESCRIPTOR = {
    "uid": "desc-0001",
    "name": "primary",
    "time": 1000.0,
    "data_keys": {
        "scaler1_time": {"dtype": "number", "object_name": "scaler1"},
        "I0": {"dtype": "number", "object_name": "scaler1"},
        "eiger_hdf1_full_file_name": {
            "dtype": "string",
            "object_name": "eiger",
        },
    },
    "object_keys": {
        "scaler1": ["scaler1_time", "I0"],
        "eiger": ["eiger_hdf1_full_file_name"],
    },
    "hints": {"scaler1": {"fields": ["I0"]}},
}


def _event(seq_num, t, i0):
    return {
        "uid": f"ev-{seq_num}",
        "descriptor": "desc-0001",
        "seq_num": seq_num,
        "time": t,
        "data": {
            "scaler1_time": 1.0,
            "I0": i0,
            "eiger_hdf1_full_file_name": "/gdata/.../scan_000001.h5",
        },
        "timestamps": {
            "scaler1_time": t,
            "I0": t,
            "eiger_hdf1_full_file_name": t,
        },
    }


STOP = {
    "uid": "stop-0001",
    "time": 1003.0,
    "exit_status": "success",
    "num_events": {"primary": 2},
}


@pytest.fixture
def written_file(tmp_path):
    """Drive a full run through the writer and return the output file's lines."""
    sw = SpecWriterCallback2()
    sw.file_name = tmp_path / "test.dat"

    sw.receiver("start", dict(START))
    sw.receiver("descriptor", dict(DESCRIPTOR))
    sw.receiver("event", _event(1, 1001.0, 100))
    sw.receiver("event", _event(2, 1002.0, 200))
    sw.receiver("stop", dict(STOP))

    return sw.file_name.read_text().splitlines()


def _header_index(lines):
    for i, line in enumerate(lines):
        if line.startswith("#L "):
            return i
    raise AssertionError("no #L line found")


def test_string_column_dropped_from_labels(written_file):
    """The string column must not appear in #L."""
    lines = written_file
    label_line = lines[_header_index(lines)]
    assert "eiger_hdf1_full_file_name" not in label_line
    labels = label_line[len("#L ") :].split()
    assert labels == ["Epoch", "Epoch_float", "scaler1_time", "I0"]


def test_column_count_consistent(written_file):
    """#N matches the #L label count and every data-row token count."""
    lines = written_file
    li = _header_index(lines)
    labels = lines[li][len("#L ") :].split()

    n_line = next(x for x in lines if x.startswith("#N "))
    assert int(n_line.split()[1]) == len(labels) == 4

    data_rows = [
        x
        for x in lines[li + 1 :]
        if x and not x.startswith("#")
    ]
    assert len(data_rows) == 2
    for row in data_rows:
        assert len(row.split()) == len(labels)


def test_data_block_is_contiguous(written_file):
    """No '#' line may sit between data rows (the pymca-breaking pattern)."""
    lines = written_file
    li = _header_index(lines)

    # Walk from the first data row; the block ends at the first '#' line.
    block = []
    started = False
    for line in lines[li + 1 :]:
        if not line:
            if started:
                break
            continue
        if line.startswith("#"):
            if started:
                # First tag after data marks the end of the contiguous block.
                break
            continue
        started = True
        block.append(line)

    assert len(block) == 2  # both data rows in one uninterrupted block
    assert not any(line.startswith("#U eiger") for line in lines)
