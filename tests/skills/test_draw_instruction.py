"""Software checks with doubles; these do not approve mathematical training targets."""
import hashlib
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event, Lock

import httpx
import pytest
from langchain_core.runnables import RunnableLambda
from PIL import Image

from tools import draw_instruction as drawing

TIKZ_A = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
TIKZ_B = r"\begin{tikzpicture}\coordinate (A) at (1,0);\end{tikzpicture}"


def row(case_id, task="Generate", **changes):
    return {"id": case_id, "task": task, "instruction": f"Givens for {case_id}",
            "source": "fixture.tex#problem=1", "source_group": "fixture-family",
            "current_tikz": None, "grade": 8, "diagram_types": ["G01"], "split": None, **changes}


def preview(directory, color="white"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "diagram.png"
    Image.new("RGB", (3, 3), color).save(path)
    return str(path)


def test_parallel_draw_uses_actual_current_tikz_and_preserves_failures(tmp_path, monkeypatch):
    native = importlib.import_module("agent.workflows.problem_tikz")
    from agent.schemas.tikz import TikzResult

    lock, barrier, calls = Lock(), Barrier(2), []
    active = peak = 0

    def fake_draw(*, instruction, current_tikz, artifact_dir, agent, compiler_http):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            calls.append((instruction, current_tikz))
        try:
            if current_tikz is None:
                barrier.wait(timeout=3)
            if instruction == "Givens for bad":
                raise RuntimeError("provider unavailable")
            messages = [{"type": "ai", "response_metadata": {"finish_reason": "tool_calls"},
                         "usage_metadata": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}},
                        {"type": "ai", "content": "Model call limits exceeded", "usage_metadata": None}]
            (artifact_dir / "messages.jsonl").write_text("\n".join(json.dumps(item) for item in messages), encoding="utf-8")
            return TikzResult(success=True, status="accepted", usable=True,
                              tikz=TIKZ_B, rendered_png_path=preview(artifact_dir))
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(native, "problem_tikz", fake_draw)
    rows = [row("arbitrary/../base:α", target_tikz="HIDDEN TARGET", evaluation_rubric=[{"secret": True}]),
            row("bad"), row("edit unrelated ID", "Edit", current_tikz=TIKZ_A)]
    with httpx.Client() as compiler:
        outcomes = drawing.draw_batch(rows, tmp_path / "run", agent=RunnableLambda(lambda x: x),
                                      compiler_http=compiler, workers=2)
    assert peak == 2 and len(calls) == 3
    assert ("Givens for edit unrelated ID", TIKZ_A) in calls
    assert outcomes[2]["current_tikz"] == TIKZ_A and outcomes[2]["target_tikz"] == TIKZ_B
    assert outcomes[1]["drawing_status"] == "failed"
    assert outcomes[2]["model_calls"] == 1 and outcomes[2]["usage"]["total_tokens"] == 15
    assert all(outcome["verification"]["status"] == "candidate" for outcome in outcomes)
    assert all("HIDDEN TARGET" not in instruction for instruction, _ in calls)
    saved = [json.loads(line) for line in (tmp_path / "run/candidates.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(saved) == 3
    import pyarrow.parquet as pq
    snapshot = {item["id"]: item for item in pq.read_table(tmp_path / "run/candidates.parquet").to_pylist()}
    assert len(snapshot) == 3 and snapshot["bad"]["tikz_image"] is None
    for item in outcomes:
        if item["success"]:
            assert snapshot[item["id"]]["tikz_image"]["bytes"] == Path(item["rendered_png_path"]).read_bytes()
    assert all(Path(item["rendered_png_path"]).is_relative_to(tmp_path / "run")
               for item in outcomes if item["success"])
    report = json.loads((tmp_path / "run/report.json").read_text(encoding="utf-8"))
    assert report["tikz_prompt_version"] and len(report["harness_files"]) == 8
    assert json.loads((tmp_path / "run/inputs.jsonl").read_text(encoding="utf-8").splitlines()[0]) == rows[0]


def test_cli_accepts_twelve_workers_without_redrawing_cached_targets(tmp_path, monkeypatch):
    source = tmp_path / "inputs.jsonl"
    source.write_text(drawing.encoded(row("existing", target_tikz=TIKZ_A)) + "\n", encoding="utf-8")
    output = tmp_path / "higher-workers"
    monkeypatch.setattr(drawing.sys, "argv", ["draw_instruction.py", str(source), "--output", str(output), "--workers", "12"])
    assert drawing.main() == 0
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["workers"] == 12 and report["max_model_calls_total"] == 0


def test_compiler_queue_limits_requests_and_releases_failed_slot():
    barrier, lock = Barrier(2), Lock()
    active = peak = 0

    def compiler(request):
        nonlocal active, peak
        if request.url.path == "/failed":
            raise httpx.ConnectError("fixture connection failure", request=request)
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            barrier.wait(timeout=5)
            return httpx.Response(200, json={"ok": True})
        finally:
            with lock:
                active -= 1

    with drawing.CompilerClient(concurrency=2, base_url="http://compiler.test", transport=httpx.MockTransport(compiler)) as client:
        with pytest.raises(httpx.ConnectError), client.stream("POST", "/failed"):
            pass
        def render(index):
            with client.stream("POST", f"/compile-{index}") as response:
                response.read()
                return response.status_code
        with ThreadPoolExecutor(max_workers=12) as workers:
            assert list(workers.map(render, range(12))) == [200] * 12
    assert peak == 2


@pytest.mark.parametrize("rows", [
    [row("edit", "Edit")],
    [row("edit", "Edit", current_tikz="")],
    [row("edit", "Edit", current_tikz=123)],
    [row("edit", "Edit", current_tikz=r"\documentclass{article}")],
    [row("generate", current_tikz=TIKZ_A)],
    [row("generate", instruction="   ")],
    [row("generate", instruction=None)],
    [row("generate", instruction=123)],
    [row("edit", "Edit", base_id="legacy-shortcut")],
    [row("edit", "Edit", base_id="legacy-shortcut", current_tikz=TIKZ_A)],
    [{key: value for key, value in row("generate").items() if key != "current_tikz"}],
])
def test_invalid_current_tikz_batch_cannot_start(rows, tmp_path):
    with httpx.Client() as compiler, pytest.raises(ValueError):
        drawing.draw_batch(rows, tmp_path / "run", agent=None, compiler_http=compiler)
    assert not (tmp_path / "run").exists()


def test_family_split_conflicts_and_duplicate_ids_are_rejected(tmp_path):
    source = tmp_path / "any-name.jsonl"
    for rows in ([row("a", split="train"), row("b", split="test")], [row("a"), row("a")]):
        source.write_text("".join(json.dumps(item) + "\n" for item in rows), encoding="utf-8")
        with pytest.raises(ValueError):
            drawing.load_rows(source)


def test_export_rejects_original_parent_leakage_across_tasks_and_family_names(tmp_path):
    records = [row("g", split="train", target_tikz=TIKZ_A, evaluation_rubric=[]),
               row("e", "Edit", split="test", source_group="another-family", current_tikz=TIKZ_A,
                   target_tikz=TIKZ_B, evaluation_rubric=[])]
    for item in records:
        item.update(provenance={"parents": ["shared-original"]},
                    rendered_png_path=preview(tmp_path / item["id"]),
                    rendered_tikz_sha256=hashlib.sha256(item["target_tikz"].encode()).hexdigest())
        item["rendered_png_sha256"] = hashlib.sha256(Path(item["rendered_png_path"]).read_bytes()).hexdigest()
        item["verification"] = {"status": "ready", "reviewed_by": "test double",
                                "reviewed_input_sha256": drawing.review_digest(item)}
    with pytest.raises(ValueError, match="conflicting lineage splits"):
        drawing.export_rows(records, tmp_path / "leaked-export")
    assert not (tmp_path / "leaked-export").exists()
    records[0]["instruction"] = "Đường tròn đường kính MN; OM và ON."
    records[0]["verification"]["reviewed_input_sha256"] = drawing.review_digest(records[0])
    drawing.export_rows(records[:1], tmp_path / "reviewed-instruction-export")
    with pytest.raises(ValueError, match="nonempty"):
        drawing.validate_instruction("   ")


def test_reviewed_parquet_roundtrip_and_stale_review_gate(tmp_path):
    records = [row("g", split="train", target_tikz=TIKZ_A, evaluation_rubric=[],
                   provenance={"parents": ["source-1", "source-2"], "augmentation": "mock fixture"}),
               row("e", "Edit", split="train", current_tikz=TIKZ_A, target_tikz=TIKZ_B,
                   evaluation_rubric=[{"requirement": "fixture only", "checks": []}])]
    for item in records:
        item.update(rendered_png_path=preview(tmp_path / item["id"]),
                    rendered_tikz_sha256=hashlib.sha256(item["target_tikz"].encode()).hexdigest())
        item["rendered_png_sha256"] = hashlib.sha256(Path(item["rendered_png_path"]).read_bytes()).hexdigest()
        item["verification"] = {"status": "ready", "reviewed_by": "unit-test double; no real approval",
                                "reviewed_input_sha256": drawing.review_digest(item)}
    files = drawing.export_rows(records, tmp_path / "parquet")
    import pyarrow.parquet as pq
    assert len(files) == 2
    exported = pq.read_table(tmp_path / "parquet/generate/train.parquet").to_pylist()[0]
    assert exported["instruction"] == records[0]["instruction"] and exported["target_tikz"] == TIKZ_A
    assert json.loads(exported["metadata"])["provenance"]["parents"] == ["source-1", "source-2"]
    assert json.loads(exported["evaluation_rubric"]) == []
    assert exported["tikz_image"]["bytes"] == Path(records[0]["rendered_png_path"]).read_bytes()
    assert not Path(exported["tikz_image"]["path"]).is_absolute()
    schema = pq.read_schema(tmp_path / "parquet/generate/train.parquet")
    assert json.loads(schema.metadata[b"huggingface"])["info"]["features"]["tikz_image"] == {"_type": "Image"}
    records[0]["instruction"] += " changed"
    with pytest.raises(ValueError, match="changed"):
        drawing.export_rows(records, tmp_path / "stale")
    assert not (tmp_path / "stale").exists()
    with pytest.raises(FileExistsError):
        drawing.export_rows([records[1]], tmp_path / "parquet")
    records[1]["source_group"] = "changed-family"
    with pytest.raises(ValueError, match="changed"):
        drawing.export_rows([records[1]], tmp_path / "changed-family")
    records[1]["source_group"] = "fixture-family"
    records[1]["verification"]["status"] = "candidate"
    with pytest.raises(ValueError, match="review"):
        drawing.export_rows([records[1]], tmp_path / "unreviewed")


def test_live_parquet_is_readable_before_the_next_drawing_completes(tmp_path, monkeypatch):
    native = importlib.import_module("agent.workflows.problem_tikz")
    import pyarrow.parquet as pq
    from agent.schemas.tikz import TikzResult

    written, observed = Event(), []
    real_write = drawing.write_parquet

    def observe_write(rows, path):
        real_write(rows, path)
        snapshot = pq.read_table(path).to_pylist()
        observed.append({item["id"] for item in snapshot})
        if observed[-1] == {"first"}:
            assert snapshot[0]["target_tikz"] == TIKZ_A and snapshot[0]["tikz_image"]["bytes"]
            written.set()

    def fake_draw(*, instruction, current_tikz, artifact_dir, agent, compiler_http):
        if instruction == "Givens for second":
            assert written.wait(timeout=5), "First result must be published before second completes"
        return TikzResult(success=True, status="accepted", usable=True, tikz=TIKZ_A,
                          rendered_png_path=preview(artifact_dir))

    monkeypatch.setattr(native, "problem_tikz", fake_draw)
    monkeypatch.setattr(drawing, "write_parquet", observe_write)
    result = drawing.draw_batch([row("first"), row("second")], tmp_path / "run",
                                agent=RunnableLambda(lambda x: x), compiler_http=None, workers=2)
    assert all(item["success"] for item in result)
    assert {"first"} in observed and observed[-1] == {"first", "second"}


def test_image_binding_and_atomic_parquet_failure(tmp_path, monkeypatch):
    import pyarrow.parquet as pq

    item = row("image", target_tikz=TIKZ_A, rendered_png_path=preview(tmp_path / "image"))
    item.update(rendered_tikz_sha256=hashlib.sha256(TIKZ_A.encode()).hexdigest(),
                rendered_png_sha256=hashlib.sha256(Path(item["rendered_png_path"]).read_bytes()).hexdigest())
    assert drawing.target_image(item)
    assert drawing.target_image({**item, "target_tikz": TIKZ_B}) is None
    invalid = {**item, "target_tikz": TIKZ_B, "split": "train", "evaluation_rubric": []}
    invalid["verification"] = {"status": "ready", "reviewed_by": "test double",
                               "reviewed_input_sha256": drawing.review_digest(invalid)}
    with pytest.raises(ValueError, match="verified PNG"):
        drawing.export_rows([invalid], tmp_path / "invalid-export")
    assert not (tmp_path / "invalid-export").exists()
    reviewed = {**item, "split": "train", "evaluation_rubric": []}
    reviewed["verification"] = {"status": "ready", "reviewed_by": "test double",
                                "reviewed_input_sha256": drawing.review_digest(reviewed)}
    preview(tmp_path / "image", "red")
    assert drawing.target_image(item) is None
    assert drawing.target_image({**item, "rendered_png_path": "missing.png"}) is None
    item["rendered_png_sha256"] = hashlib.sha256(Path(item["rendered_png_path"]).read_bytes()).hexdigest()
    reviewed["rendered_png_sha256"] = item["rendered_png_sha256"]
    with pytest.raises(ValueError, match="changed"):
        drawing.export_rows([reviewed], tmp_path / "changed-image")
    path = tmp_path / "snapshot.parquet"
    drawing.write_parquet([item], path)
    before = path.read_bytes()

    def interrupted_write(table, where, **kwargs):
        Path(where).write_bytes(b"partial write")
        raise OSError("disk full")

    monkeypatch.setattr(pq, "write_table", interrupted_write)
    with pytest.raises(OSError, match="disk full"):
        drawing.write_parquet([item], path)
    assert path.read_bytes() == before and pq.read_table(path).num_rows == 1
    assert not path.with_suffix(".parquet.tmp").exists()


def test_compile_helper_image_evidence_is_reused_without_native_hash_fields(tmp_path):
    path = preview(tmp_path)
    evidence = {"target": {"status": "needs_review", "input_tikz_sha256": hashlib.sha256(TIKZ_A.encode()).hexdigest(),
                           "artifacts": {"page-1.png": {"path": path, "complete": True,
                                         "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}}}}
    report = tmp_path / "report.json"
    report.write_text(json.dumps(evidence), encoding="utf-8")
    item = row("compiled", target_tikz=TIKZ_A, verification={"report_path": str(report)})
    assert drawing.target_image(item)["bytes"] == Path(path).read_bytes()
    assert drawing.target_image({**item, "target_tikz": TIKZ_B}) is None
    missing_native = {**item, "rendered_tikz_sha256": evidence["target"]["input_tikz_sha256"],
                      "rendered_png_path": "missing-native.png", "rendered_png_sha256": "stale"}
    assert drawing.target_image(missing_native)["bytes"] == Path(path).read_bytes()
    drawing.write_parquet([missing_native], tmp_path / "compiled.parquet")
    import pyarrow.parquet as pq
    exported = pq.read_table(tmp_path / "compiled.parquet").to_pylist()[0]
    metadata = json.loads(exported["metadata"])
    assert metadata["target_tikz_sha256"] == hashlib.sha256(TIKZ_A.encode()).hexdigest()
    assert metadata["tikz_image_sha256"] == hashlib.sha256(exported["tikz_image"]["bytes"]).hexdigest()
    assert metadata["rendered_png_sha256"] == "stale"  # Original native-attempt evidence stays intact.


@pytest.mark.parametrize("options", [["--workers", "33"], ["--compiler-concurrency", "3"], ["--max-model-calls", "5"], ["--limit", "1"]])
def test_cli_rejects_over_budget_inputs_before_any_remote_execution(tmp_path, monkeypatch, options):
    monkeypatch.setattr("cpa.build_model", lambda **kwargs: pytest.fail("Invalid budgets must never initialize a provider"))
    source = tmp_path / "requests.jsonl"
    source.write_text("".join(json.dumps(row(item)) + "\n" for item in ("a", "b")), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["draw_instruction.py", str(source), "--output", str(tmp_path / "run"), *options])
    with pytest.raises(SystemExit) as error:
        drawing.main()
    assert error.value.code == 2 and not (tmp_path / "run").exists()

def test_resume_retries_failures_and_partial_targets_and_recovers_checkpoints(tmp_path, monkeypatch):
    native = importlib.import_module("agent.workflows.problem_tikz")
    from agent.schemas.tikz import TikzResult

    calls, recovered = [], False

    def fake_draw(*, instruction, current_tikz, artifact_dir, agent, compiler_http):
        calls.append(instruction)
        if not recovered and instruction == "Givens for fail":
            raise RuntimeError("provider unavailable")
        partial = not recovered and instruction == "Givens for partial"
        return TikzResult(success=not partial, status="usable_with_issues" if partial else "accepted",
                          usable=True, tikz=TIKZ_B, rendered_png_path=preview(artifact_dir),
                          unresolved_issues=["incomplete"] if partial else [])

    monkeypatch.setattr(native, "problem_tikz", fake_draw)
    rows = [row("good"), row("fail", target_tikz=TIKZ_A, success=False, rendered_png_path="old.png"), row("partial")]
    output = tmp_path / "run"
    first = drawing.draw_batch(rows, output, agent=RunnableLambda(lambda x: x), compiler_http=None, workers=2)
    assert sorted(calls) == ["Givens for fail", "Givens for good", "Givens for partial"]
    old_attempts = [Path(item["artifact_dir"]) / "candidate.json" for item in first]
    assert all(path.is_file() for path in old_attempts)
    assert first[1]["rendered_png_path"] is None
    recovered = True
    calls.clear()
    second = drawing.draw_batch(rows, output, agent=RunnableLambda(lambda x: x),
                                compiler_http=None, resume=True, workers=2)
    assert sorted(calls) == ["Givens for fail", "Givens for partial"]
    assert second[0]["trace_id"] == first[0]["trace_id"]
    assert all(item["success"] for item in second)
    assert json.loads(old_attempts[1].read_text(encoding="utf-8"))["success"] is False
    assert json.loads(old_attempts[2].read_text(encoding="utf-8"))["target_tikz"] == TIKZ_B
    assert all(Path(item["artifact_dir"]) != Path(first[index]["artifact_dir"])
               for index, item in enumerate(second) if index)
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["skipped_rows"] == 1 and report["pending_rows"] == 2
    (output / "candidates.jsonl").unlink()  # Interrupted before the aggregate export.
    source = tmp_path / "inputs.jsonl"
    source.write_text("".join(json.dumps(item) + "\n" for item in rows), encoding="utf-8")
    import cpa
    monkeypatch.setattr(cpa, "build_model", lambda: pytest.fail("Completed rows must not initialize a model"))
    monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: pytest.fail("Completed rows must not call a compiler"))
    monkeypatch.setattr("sys.argv", ["draw_instruction.py", str(source), "--output", str(output), "--resume", "--limit", "1"])
    assert drawing.main() == 0
    latest = drawing.load_rows(output / "candidates.jsonl")
    assert len(latest) == 3 and len(calls) == 2


def test_resume_changed_inputs_and_explicit_retry_redraw_only_selected_rows(tmp_path, monkeypatch):
    native = importlib.import_module("agent.workflows.problem_tikz")
    from agent.schemas.tikz import TikzResult

    calls, colors = [], {}

    def fake_draw(*, instruction, current_tikz, artifact_dir, agent, compiler_http):
        calls.append((instruction, current_tikz))
        colors[instruction] = colors.get(instruction, 0) + 1
        return TikzResult(success=True, status="accepted", usable=True,
                          tikz=TIKZ_A if current_tikz == TIKZ_B else TIKZ_B,
                          rendered_png_path=preview(artifact_dir, (colors[instruction], 0, 0)))

    monkeypatch.setattr(native, "problem_tikz", fake_draw)
    rows = [row("g"), row("e", "Edit", current_tikz=TIKZ_A)]
    output = tmp_path / "run"
    drawing.draw_batch(rows, output, agent=RunnableLambda(lambda x: x), compiler_http=None)
    changed = [{**rows[0], "instruction": "Changed givens"}, {**rows[1], "current_tikz": TIKZ_B}]
    calls.clear()
    drawing.draw_batch(changed, output, agent=RunnableLambda(lambda x: x), compiler_http=None, resume=True)
    assert set(calls) == {("Changed givens", None), ("Givens for e", TIKZ_B)}
    import pyarrow.parquet as pq
    before = {item["id"]: item for item in pq.read_table(output / "candidates.parquet").to_pylist()}
    calls.clear()
    drawing.draw_batch(changed, output, agent=RunnableLambda(lambda x: x),
                       compiler_http=None, resume=True, retry_ids=["g"])
    assert calls == [("Changed givens", None)]
    after = {item["id"]: item for item in pq.read_table(output / "candidates.parquet").to_pylist()}
    assert len(after) == 2 and after["e"] == before["e"]
    assert after["g"]["tikz_image"]["bytes"] != before["g"]["tikz_image"]["bytes"]
    with pytest.raises(ValueError, match="Unknown retry"):
        drawing.completed_rows(changed, output, resume=True, retry_ids=["absent"])
    # Resuming a subset must not remove unselected completed rows.
    drawing.draw_batch(changed[:1], output, agent=None, compiler_http=None, resume=True)
    assert {item["id"] for item in drawing.load_rows(output / "candidates.jsonl")} == {"g", "e"}
    assert {item["id"] for item in pq.read_table(output / "candidates.parquet").to_pylist()} == {"g", "e"}


def test_existing_target_is_preserved_without_inventing_approval(tmp_path):
    rows = [row("provided", target_tikz=TIKZ_A)]
    result = drawing.draw_batch(rows, tmp_path / "run", agent=None, compiler_http=None)
    assert result[0]["target_tikz"] == TIKZ_A and result[0]["drawing_status"] == "provided_target"
    assert result[0]["success"] is None and result[0]["verification"]["status"] == "candidate"
    assert "trace_id" not in result[0]
    report = json.loads((tmp_path / "run/report.json").read_text(encoding="utf-8"))
    assert report["pending_rows"] == 0 and report["max_model_calls_total"] == 0


@pytest.mark.parametrize("permanent", [False, True])
def test_parquet_replace_retries_short_locks_without_losing_previous_snapshot(tmp_path, monkeypatch, permanent):
    import pyarrow.parquet as pq

    target = tmp_path / "snapshot.parquet"
    drawing.write_parquet([row("old")], target)
    original = target.read_bytes()
    replace = Path.replace
    attempts = []

    def locked(path, destination):
        attempts.append(1)
        if permanent or len(attempts) < 3:
            raise PermissionError("locked reader")
        return replace(path, destination)

    monkeypatch.setattr(Path, "replace", locked)
    monkeypatch.setattr(drawing, "sleep", lambda seconds: None)
    if permanent:
        with pytest.raises(PermissionError):
            drawing.write_parquet([row("new")], target)
        assert len(attempts) == 4 and target.read_bytes() == original
    else:
        drawing.write_parquet([row("new")], target)
        assert len(attempts) == 3
        assert pq.read_table(target).to_pylist()[0]["id"] == "new"
    assert not target.with_suffix(".parquet.tmp").exists()


@pytest.mark.parametrize("kind", ["checkpoint", "production", "candidates"])
@pytest.mark.parametrize("permanent", [False, True])
def test_json_snapshot_replace_retries_and_preserves_old_file(tmp_path, monkeypatch, kind, permanent):
    from tools import run_synthetic_dataset as production

    target = tmp_path / ("candidates.jsonl" if kind == "candidates" else "snapshot.jsonl")
    target.write_text("old\n", encoding="utf-8")
    replace = Path.replace
    attempts = []

    def locked(path, destination):
        if destination == target:
            attempts.append(1)
            if permanent or len(attempts) < 3:
                raise PermissionError("locked reader")
        return replace(path, destination)

    monkeypatch.setattr(Path, "replace", locked)
    monkeypatch.setattr(drawing, "sleep", lambda seconds: None)
    monkeypatch.setattr(drawing, "write_parquet", lambda rows, path: None)

    def write():
        if kind == "checkpoint":
            drawing.save_json(target, row("new"))
        elif kind == "production":
            production.write_rows(target, [row("new")])
        else:
            drawing.save_candidates(tmp_path, {"new": row("new")})

    if permanent:
        with pytest.raises(PermissionError):
            write()
        assert len(attempts) == 4
        assert target.read_text(encoding="utf-8") == "old\n"
    else:
        write()
        assert len(attempts) == 3
        assert json.loads(target.read_text(encoding="utf-8"))["id"] == "new"
