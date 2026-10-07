"""Evaluation reporting preserves missing results, source groups and evidence."""
import hashlib
import json
from unittest.mock import MagicMock

import pytest

from evaluation import run


def planned(case_id, group, **extra):
    return {"id": case_id, "source_group": group, "task": "Generate", "system_id": "test-model", **extra}


def measured(case_id, value):
    return {"id": case_id, "comparison": {"scores": {"mathematical_correctness": value}}}


def test_missing_results_stay_scheduled_and_augmentation_does_not_change_group_mean():
    cases = [planned(str(i), "augmented") for i in range(3)] + [planned("bad", "other"), planned("missing", "missing")]
    results = [measured(str(i), 100) for i in range(3)] + [measured("bad", 0)]
    summary = run.summarize(cases, results)[0]
    assert summary["n_scheduled"] == 5 and summary["n_results"] == 4
    metric = summary["scores"]["mathematical_correctness"]
    assert metric == {"mean": 75, "source_group_mean": 50, "available": 4, "missing": 1, "unresolved_units": 0}
    cases.append(planned("more", "augmented"))
    results.append(measured("more", 100))
    assert run.summarize(cases, results)[0]["scores"]["mathematical_correctness"]["source_group_mean"] == 50
    results[0]["comparison"]["counts"] = {"mathematical_correctness": {"unresolved": 2}}
    assert run.summarize(cases, results)[0]["scores"]["mathematical_correctness"]["unresolved_units"] == 2


def test_systems_controls_tasks_and_splits_are_kept_separate():
    cases = [planned("control", "a", cohort="controls"), planned("model", "b"), planned("edit", "b", task="Edit")]
    assert len(run.summarize(cases, [measured(case["id"], 100) for case in cases])) == 3
    with pytest.raises(ValueError, match="multiple splits"):
        run.summarize([planned("train", "same", split="train"), planned("test", "same", task="Edit", split="test")], [])
    with pytest.raises(ValueError, match="outside"):
        run.summarize(cases, [measured("foreign", 100)])
    with pytest.raises(ValueError, match="Duplicate"):
        run.summarize(cases + [cases[0]], [])
    with pytest.raises(ValueError, match="Stale output"):
        run.summarize([planned("stale", "a", output_tikz="new")], [{"id": "stale", "comparison": {"source_hashes": {"output": hashlib.sha256(b"old").hexdigest()}}}])


@pytest.mark.parametrize("stage", ["provider_error", "parse_error"])
def test_generation_failure_does_not_become_a_compile_measurement(tmp_path, monkeypatch, stage):
    case = planned("failed", "a", variant="saved failure", generation_status=stage,
                   target_tikz="target", output_tikz="")
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    compiler = MagicMock()
    compiler.__enter__.return_value = compiler
    compiler.get.return_value.json.return_value = {"toolchain_id": "offline-test"}
    monkeypatch.setattr(run.httpx, "Client", lambda **kwargs: compiler)
    observer = MagicMock(return_value={"compile_success": True, "compile": {"outcome": "ok"},
                                      "metadata": {"input_tikz_sha256": hashlib.sha256(b"target").hexdigest()}})
    monkeypatch.setattr(run, "observe_tikz", observer)
    monkeypatch.setattr(run, "write_preview", MagicMock())
    output = tmp_path / "run"
    run.run(cases_path, output)
    assert observer.call_count == 1 and observer.call_args.args[0] == "target"
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["results"][0]["comparison"]["scores"]["compile"] is None
    assert report["inputs_sha256"] == hashlib.sha256((output / "inputs.json").read_bytes()).hexdigest()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))[0]
    assert summary["generation_failures"] == 1
    assert summary["scores"]["compile"]["available"] == 0
    assert summary["scores"]["compile"]["missing"] == 1
    assert not {"controlled_validation", "scope", "counts"} & report.keys()
    rescored = tmp_path / "rescore"
    run.rescore(output / "report.json", rescored)
    rescored_report = json.loads((rescored / "report.json").read_text(encoding="utf-8"))
    assert rescored_report["results"] == report["results"]
    assert observer.call_count == 1


def test_changed_cached_pdf_is_rejected(tmp_path):
    artifact = tmp_path / "result.pdf"
    artifact.write_bytes(b"recorded")
    observation = {"metadata": {"input_tikz_sha256": hashlib.sha256(b"tikz").hexdigest()}, "pdf_path": str(artifact),
                   "artifacts": {"original": {"result.pdf": {"path": str(artifact), "sha256": hashlib.sha256(b"recorded").hexdigest()}}}}
    run.verify_cached_observation(observation, "tikz")
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        run.verify_cached_observation(observation, "tikz")


def test_explicit_geometry_space_and_removed_policy_wrapper(monkeypatch):
    evaluator = MagicMock(return_value={})
    monkeypatch.setattr(run, "evaluate", evaluator)
    run._evaluate_case({"geometry_space": "affine_projection"}, {}, {})