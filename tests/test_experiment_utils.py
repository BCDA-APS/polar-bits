"""Tests for id4_common.utils.experiment_utils.ExperimentClass."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Helpers ----------------------------------------------------------------


def _scripted_prompt(answers):
    """Return a callable that yields the scripted answers in order.

    Raises AssertionError if the test exhausts the script (means the
    code asked for more input than expected — test or code bug).
    """
    iterator = iter(answers)

    def prompt(message):
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError(
                f"Unexpected prompt: {message!r} (script exhausted)"
            ) from exc

    return prompt


@pytest.fixture
def reset_re_md():
    """Clear ``RE.md`` between tests so they don't leak scan_id state."""
    from id4_common.utils.run_engine import RE

    RE.md.clear()
    yield RE.md
    RE.md.clear()


@pytest.fixture
def fresh_experiment(monkeypatch, reset_re_md):
    """Fresh ExperimentClass with prompt/printer mocks."""
    from id4_common.utils import experiment_utils

    printed = []
    prompts: list = []
    exp = experiment_utils.ExperimentClass(
        prompt=_scripted_prompt(prompts),
        printer=lambda *a, **kw: printed.append(" ".join(str(x) for x in a)),
    )
    return exp, prompts, printed


# scan_number_input ------------------------------------------------------


def test_scan_number_input_writes_literal_value(fresh_experiment):
    exp, _, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    exp.scan_number_input(reset_scan_id=0)
    assert RE.md["scan_id"] == 0  # next scan = 1

    exp.scan_number_input(reset_scan_id=47)
    assert RE.md["scan_id"] == 47  # next scan = 48


def test_scan_number_input_noop_sentinel(fresh_experiment):
    exp, _, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    RE.md["scan_id"] = 99
    exp.scan_number_input(reset_scan_id=-1)  # RESET_SCAN_ID_NOOP
    assert RE.md["scan_id"] == 99  # unchanged


def test_scan_number_input_invalid_negative_logs_warning(
    fresh_experiment, caplog
):
    exp, _, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    RE.md["scan_id"] = 5
    exp.scan_number_input(reset_scan_id=-2)  # invalid
    assert RE.md["scan_id"] == 5  # untouched
    assert "Ignoring invalid reset_scan_id" in caplog.text


def test_scan_number_input_interactive_yes_resets_to_zero(fresh_experiment):
    exp, prompts, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    RE.md["scan_id"] = 99
    prompts.append("yes")
    exp.scan_number_input(reset_scan_id=None)
    assert RE.md["scan_id"] == 0


def test_scan_number_input_interactive_no_keeps_value(fresh_experiment):
    exp, prompts, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    RE.md["scan_id"] = 7
    prompts.append("no")
    exp.scan_number_input(reset_scan_id=None)
    assert RE.md["scan_id"] == 7


# load_from_bluesky ------------------------------------------------------


def test_load_from_bluesky_restores_scan_id(monkeypatch, fresh_experiment):
    """Loading a past run restores the last scan_id from its metadata.

    Regression for the user-reported bug where load_from_bluesky left
    RE.md["scan_id"] unset (then later code crashed on ``+ 1``).
    """
    exp, _, _ = fresh_experiment
    from id4_common.utils import experiment_utils
    from id4_common.utils.run_engine import RE
    from id4_common.utils.run_engine import cat

    # Stub the run document with a scan_id of 47.
    metadata = {
        "esaf_id": "12345",
        "proposal_id": "67890",
        "base_name": "scan",
        "sample": "MySample",
        "server": "dserv",
        "experiment_name": "polar-test",
        "scan_id": 47,
    }
    cat.__getitem__ = MagicMock(
        return_value=MagicMock(metadata={"start": metadata})
    )

    # Skip DM and short-circuit setup_path / start_specwriter / save.
    monkeypatch.setattr(experiment_utils, "_dm_available", lambda: False)
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)
    monkeypatch.setattr(exp, "save_params_to_yaml", lambda: None)

    # Force a base_experiment_path so _resolve_base_path doesn't try to
    # consult get_current_run_name (already stubbed but be explicit).
    monkeypatch.setattr(
        exp,
        "_resolve_base_path",
        lambda: setattr(exp, "base_experiment_path", Path("/tmp/test")),
    )

    exp.load_from_bluesky()

    assert RE.md["scan_id"] == 47


# DM auto-detect ---------------------------------------------------------


def test_setup_with_dm_unreachable_falls_back_to_dserv(
    monkeypatch, fresh_experiment, caplog
):
    """When DM is unreachable, setup() must skip ESAF/proposal prompts."""
    exp, prompts, _ = fresh_experiment
    from id4_common.utils import experiment_utils
    from id4_common.utils.run_engine import RE

    monkeypatch.setattr(experiment_utils, "_dm_available", lambda: False)
    # Stub away the file-system + spec writer side effects.
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)
    monkeypatch.setattr(exp, "save_params_to_yaml", lambda: None)
    monkeypatch.setattr(
        exp,
        "_resolve_base_path",
        lambda: setattr(exp, "base_experiment_path", Path("/tmp/test")),
    )

    # Only experiment_name + sample + base_name should prompt
    # (esaf/proposal/server are auto-set when DM is down).
    prompts.extend(["polar-fallback", "MySample", "scan"])

    exp.setup()

    assert exp.server == "dserv"
    assert exp.esaf == "dev"
    assert exp.proposal == "dev"
    assert RE.md["esaf_id"] == "dev"
    assert RE.md["proposal_id"] == "dev"
    assert RE.md["server"] == "dserv"
    # scan_id always defined after setup (1.1).
    assert RE.md["scan_id"] == 0


def test_setup_initializes_scan_id_to_zero(monkeypatch, fresh_experiment):
    """setup() must guarantee RE.md["scan_id"] is set."""
    exp, prompts, _ = fresh_experiment
    from id4_common.utils import experiment_utils
    from id4_common.utils.run_engine import RE

    assert "scan_id" not in RE.md  # confirm fresh state
    monkeypatch.setattr(experiment_utils, "_dm_available", lambda: False)
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)
    monkeypatch.setattr(exp, "save_params_to_yaml", lambda: None)
    monkeypatch.setattr(
        exp,
        "_resolve_base_path",
        lambda: setattr(exp, "base_experiment_path", Path("/tmp/test")),
    )
    prompts.extend(["polar-fallback", "MySample", "scan"])

    exp.setup()
    assert isinstance(RE.md["scan_id"], int)


def test_setup_warns_when_scan_id_missing(
    monkeypatch, fresh_experiment, caplog
):
    """setup() warns when it has to default RE.md['scan_id']."""
    import logging

    exp, prompts, _ = fresh_experiment
    from id4_common.utils import experiment_utils
    from id4_common.utils.run_engine import RE

    assert "scan_id" not in RE.md
    monkeypatch.setattr(experiment_utils, "_dm_available", lambda: False)
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)
    monkeypatch.setattr(exp, "save_params_to_yaml", lambda: None)
    monkeypatch.setattr(
        exp,
        "_resolve_base_path",
        lambda: setattr(exp, "base_experiment_path", Path("/tmp/test")),
    )
    prompts.extend(["polar-fallback", "MySample", "scan"])

    with caplog.at_level(logging.WARNING):
        exp.setup()

    assert "RE.md['scan_id'] was not set" in caplog.text
    assert RE.md["scan_id"] == 0


def test_setup_no_warning_when_scan_id_present(
    monkeypatch, fresh_experiment, caplog
):
    """setup() does not warn (or overwrite) when scan_id is already set."""
    import logging

    exp, prompts, _ = fresh_experiment
    from id4_common.utils import experiment_utils
    from id4_common.utils.run_engine import RE

    RE.md["scan_id"] = 7
    monkeypatch.setattr(experiment_utils, "_dm_available", lambda: False)
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)
    monkeypatch.setattr(exp, "save_params_to_yaml", lambda: None)
    monkeypatch.setattr(
        exp,
        "_resolve_base_path",
        lambda: setattr(exp, "base_experiment_path", Path("/tmp/test")),
    )
    prompts.extend(["polar-fallback", "MySample", "scan"])

    with caplog.at_level(logging.WARNING):
        exp.setup()

    assert "RE.md['scan_id'] was not set" not in caplog.text
    assert RE.md["scan_id"] == 7


# Repr -------------------------------------------------------------------


def test_repr_no_side_effects(fresh_experiment, capsys):
    """repr(experiment) must not print anything by itself."""
    exp, _, _ = fresh_experiment
    text = repr(exp)
    assert isinstance(text, str)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# experiment_change_sample wrapper --------------------------------------


def test_experiment_change_sample_calls_start_specwriter(monkeypatch):
    """The module-level wrapper must call start_specwriter (regression 1.2)."""
    from id4_common.utils import experiment_utils

    calls = []
    monkeypatch.setattr(
        experiment_utils.experiment,
        "sample_input",
        lambda *a, **kw: calls.append("sample"),
    )
    monkeypatch.setattr(
        experiment_utils.experiment, "setup_path", lambda: calls.append("path")
    )
    monkeypatch.setattr(
        experiment_utils.experiment,
        "scan_number_input",
        lambda *a, **kw: calls.append("scan"),
    )
    monkeypatch.setattr(
        experiment_utils.experiment,
        "base_name_input",
        lambda *a, **kw: calls.append("name"),
    )
    monkeypatch.setattr(
        experiment_utils.experiment,
        "start_specwriter",
        lambda: calls.append("spec"),
    )
    monkeypatch.setattr(
        experiment_utils.experiment,
        "save_params_to_yaml",
        lambda: calls.append("save"),
    )

    experiment_utils.experiment_change_sample(sample_name="foo")

    assert (
        "spec" in calls
    ), "experiment_change_sample must trigger start_specwriter"


# YAML persistence -------------------------------------------------------


def test_yaml_save_load_roundtrip(monkeypatch, tmp_path, fresh_experiment):
    """Snapshot written by save_params_to_yaml round-trips via resume()."""
    exp, _, _ = fresh_experiment
    from id4_common.utils.run_engine import RE

    exp.esaf = {"esafId": 12345}
    exp.proposal = {"id": 67890, "title": "Test"}
    exp.server = "dserv"
    exp.experiment_name = "polar-test"
    exp.sample = "MySample"
    exp.file_base_name = "scan"
    exp.base_experiment_path = tmp_path
    RE.md["scan_id"] = 47

    exp.save_params_to_yaml()
    snapshot_path = tmp_path / ".polar_experiment.yml"
    assert snapshot_path.is_file()

    # Fresh class, then resume.
    from id4_common.utils import experiment_utils

    fresh = experiment_utils.ExperimentClass(
        prompt=_scripted_prompt([]),
        printer=lambda *a, **kw: None,
    )
    monkeypatch.setattr(fresh, "setup_path", lambda: None)
    monkeypatch.setattr(fresh, "start_specwriter", lambda: None)
    fresh.resume(tmp_path)

    assert fresh.esaf == 12345
    assert fresh.proposal == 67890
    assert fresh.server == "dserv"
    assert fresh.experiment_name == "polar-test"
    assert fresh.sample == "MySample"
    assert fresh.file_base_name == "scan"
    assert fresh.base_experiment_path == tmp_path
    assert RE.md["scan_id"] == 47


def test_resume_missing_file_no_raise(tmp_path, fresh_experiment, caplog):
    """resume() on a missing file logs a warning, does not raise."""
    exp, _, _ = fresh_experiment
    exp.resume(tmp_path / "does_not_exist.yml")
    assert "No saved experiment state" in caplog.text


# resume() default path discovery --------------------------------------


def _write_snapshot(directory, sample="DiscoveredSample"):
    """Drop a minimal valid snapshot in ``directory`` and return the path."""
    import yaml as _yaml
    from id4_common.utils.experiment_utils import PERSIST_FILENAME

    path = directory / PERSIST_FILENAME
    path.write_text(
        _yaml.safe_dump(
            {
                "esaf_id": 1,
                "proposal_id": 2,
                "server": "dserv",
                "experiment_name": "polar-discovery",
                "sample": sample,
                "file_base_name": "scan",
                "base_experiment_path": str(directory),
                "last_scan_id": 3,
            }
        )
    )
    return path


def test_resume_discovers_cwd_snapshot(monkeypatch, tmp_path, fresh_experiment):
    """resume() with no args picks up a snapshot sitting in cwd."""
    exp, _, _ = fresh_experiment
    _write_snapshot(tmp_path, sample="FromCwd")

    monkeypatch.setattr(
        "id4_common.utils.experiment_utils.Path.cwd", lambda: tmp_path
    )
    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)

    exp.resume()
    assert exp.sample == "FromCwd"


def test_resume_discovers_via_cat_when_cwd_empty(
    monkeypatch, tmp_path, fresh_experiment
):
    """When cwd has no snapshot, fall back to cat[-1]'s base_experiment_path."""
    exp, _, _ = fresh_experiment
    cwd_dir = tmp_path / "empty_cwd"
    cwd_dir.mkdir()
    cat_dir = tmp_path / "experiment_dir"
    cat_dir.mkdir()
    _write_snapshot(cat_dir, sample="FromCat")

    monkeypatch.setattr(
        "id4_common.utils.experiment_utils.Path.cwd", lambda: cwd_dir
    )

    fake_run = MagicMock()
    fake_run.metadata = {"start": {"base_experiment_path": str(cat_dir)}}
    from id4_common.utils.run_engine import cat as cat_stub

    cat_stub.__getitem__ = MagicMock(return_value=fake_run)

    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)

    exp.resume()
    assert exp.sample == "FromCat"


def test_resume_prompts_when_both_exist_and_differ(
    monkeypatch, tmp_path, fresh_experiment
):
    """When both candidates exist and differ, ask the user which to use."""
    exp, prompts, _ = fresh_experiment
    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    cat_dir = tmp_path / "cat"
    cat_dir.mkdir()
    _write_snapshot(cwd_dir, sample="FromCwd")
    _write_snapshot(cat_dir, sample="FromCat")

    monkeypatch.setattr(
        "id4_common.utils.experiment_utils.Path.cwd", lambda: cwd_dir
    )

    fake_run = MagicMock()
    fake_run.metadata = {"start": {"base_experiment_path": str(cat_dir)}}
    from id4_common.utils.run_engine import cat as cat_stub

    cat_stub.__getitem__ = MagicMock(return_value=fake_run)

    monkeypatch.setattr(exp, "setup_path", lambda: None)
    monkeypatch.setattr(exp, "start_specwriter", lambda: None)

    prompts.append("2")  # pick the cat candidate
    exp.resume()
    assert exp.sample == "FromCat"


def test_resume_no_args_no_snapshot_anywhere(
    monkeypatch, tmp_path, fresh_experiment, caplog
):
    """resume() with nothing to load logs a warning, doesn't raise."""
    exp, _, _ = fresh_experiment
    monkeypatch.setattr(
        "id4_common.utils.experiment_utils.Path.cwd", lambda: tmp_path
    )
    from id4_common.utils.run_engine import cat as cat_stub

    cat_stub.__getitem__ = MagicMock(side_effect=IndexError)

    exp.resume()
    assert "No experiment snapshot found" in caplog.text


# experiment_path properties --------------------------------------------


def test_experiment_path_no_more_dead_kwarg(fresh_experiment):
    """experiment_path is a plain property; windows variant is separate."""
    exp, _, _ = fresh_experiment
    exp.base_experiment_path = Path("/tmp/exp")
    exp.sample = "S"
    assert exp.experiment_path == Path("/tmp/exp/S")
    # windows path is None when no windows root configured
    assert exp.windows_experiment_path is None

    exp.windows_base_experiment_path = Path(r"\\server\exp")
    assert exp.windows_experiment_path == Path(r"\\server\exp/S")


def test_experiment_path_raises_when_unconfigured(fresh_experiment):
    exp, _, _ = fresh_experiment
    with pytest.raises(ValueError, match="not defined"):
        _ = exp.experiment_path
