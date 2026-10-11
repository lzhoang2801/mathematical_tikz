"""Production-loop checks use doubles; they do not certify diagram mathematics."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from tools import run_synthetic_dataset as production


@pytest.mark.parametrize("interrupt_after_author_checkpoint", [False, True])
def test_loop_reuses_edit_targets_and_resume_does_not_repeat_paid_calls(tmp_path, monkeypatch, interrupt_after_author_checkpoint):
    sources = {"source": {"id": "source", "source_group": "family", "source_text": "source givens"}}
    monkeypatch.setattr(production.author, "load_pool", lambda path: (sources, [], {}))
    calls, drawings, contexts = [], [], []

    def propose(contexts_in, output, **kwargs):
        context = contexts_in[0]
        contexts.append(context)
        assert "target_tikz" not in production.drawing.encoded(context)
        assert "current_tikz" not in production.drawing.encoded(context)
        calls.append(context["batch_id"])
        task = context["tasks"][0]
        index = len(calls)
        base = next(iter(kwargs["bases"].values()), None)
        row = {"schema_version": "synthetic-tikz:v2", "id": f"row-{index}", "task": task,
               "instruction": {1: "Triangle with altitude", 2: "Perpendicular feet", 3: "A median"}[index],
               "current_tikz": base["target_tikz"] if base else None,
               "source": "source", "source_group": "family", "split": None, "grade": 8,
               "diagram_types": ["G03"], "provenance": {"parents": ["source"],
               "starting_record_id": base["id"] if base else None,
               "starting_givens": base["instruction"] if base else None,
               "complete_instruction": "Triangle with " + ("feet" if index == 2 else "median") if base else None}}
        output.mkdir(parents=True)
        production.drawing.save_json(output / "batches/scope/result.json", {"status": "completed", "rows": [row]})
        if interrupt_after_author_checkpoint and index == 1:
            raise RuntimeError("interrupted before author snapshot")
        production.author.save_instructions(output, [{"status": "completed", "rows": [row]}], sources)

    def draw(rows, output, **kwargs):
        output.mkdir(parents=True, exist_ok=True)
        outcomes = []
        for row in rows:
            drawings.append(row)
            target = r"\begin{tikzpicture}\coordinate (A) at (" + str(len(drawings)) + r",0);\end{tikzpicture}"
            image = output / f"{row['id']}.png"
            Image.new("RGB", (8, 8), "white").save(image)
            result = {**row, "success": True, "target_tikz": target, "drawing_status": "accepted",
                      "rendered_png_path": str(image), "rendered_tikz_sha256": hashlib.sha256(target.encode()).hexdigest(),
                      "rendered_png_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                      "verification": {"status": "candidate", "reviewed_by": None}}
            production.drawing.save_json(output / "cases" / row["id"] / "candidate.json", result)
            outcomes.append(result)
        return outcomes

    monkeypatch.setattr(production.author, "generate", propose)
    monkeypatch.setattr(production.drawing, "draw_batch", draw)
    args = SimpleNamespace(output=tmp_path / "run", sources=Path("unused"), seed=42, base_count=1,
                           generate=2, edit=2, resume=False, max_draw_attempts=6, max_author_calls=8,
                           batch_size=1, contexts_per_call=10, workers=2, max_model_calls=4, compiler_concurrency=2)
    model = SimpleNamespace(model_name="test-double")
    monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")
    if interrupt_after_author_checkpoint:
        with pytest.raises(RuntimeError, match="interrupted"):
            production.run(args, model=model, agent=None, compiler=None, trace_client=None)
        args.resume = True
    report = production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    assert report["completed_candidates"] == {"Generate": 2, "Edit": 2}
    assert report["derived_generate"] == 1 and report["independently_reviewed"] == 0
    assert len(calls) == len(drawings) == 3
    assert report["author_calls_reserved"] == 3
    base = production.author.jsonl(args.output / "generate.jsonl")[0]
    edits = production.author.jsonl(args.output / "edit.jsonl")
    assert all(row["current_tikz"] == base["target_tikz"] for row in edits)
    assert all(row["provenance"]["starting_record_id"] == base["id"] for row in edits)
    generated = production.author.jsonl(args.output / "generate.jsonl")
    assert generated[1]["target_tikz"] == edits[0]["target_tikz"]
    assert generated[1]["current_tikz"] is None
    args.resume = True
    monkeypatch.delenv("LANGSMITH_PROJECT")
    assert production.run(args, model=model, agent=None, compiler=None, trace_client=None)["status"] == "candidate_quota_met"
    assert len(calls) == len(drawings) == 3
    prompt = tmp_path / "tools/instruction_prompt.md"
    prompt.parent.mkdir()
    prompt.write_text("Updated author instructions", encoding="utf-8")
    monkeypatch.setattr(production, "ROOT", tmp_path)
    production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    state = json.loads((args.output / "state.json").read_text(encoding="utf-8"))
    assert len(state["prompt_history"]) == 2
    assert state["project"] == "test-project"
    assert len(calls) == len(drawings) == 3
    sources["new-source"] = {"id": "new-source", "source_group": "new-family", "source_text": "New audited source"}
    args.base_count = 2
    production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    assert len(calls) == len(drawings) == 3
    sources["source"]["source_text"] = "Changed original input"
    with pytest.raises(ValueError, match="Previously selected source changed"):
        production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    sources["source"]["source_text"] = "source givens"
    args.seed = 43
    with pytest.raises(ValueError, match="changed"):
        production.run(args, model=model, agent=None, compiler=None, trace_client=None)

    args.seed = 42
    args.resume = True
    args.max_draw_attempts = 3
    generated = production.author.jsonl(args.output / "generate.jsonl")
    derived = next(row for row in generated if "derived_from_edit" in row["provenance"])
    production.write_rows(args.output / "excluded.jsonl", [derived])
    report = production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    assert report["excluded_candidates"] == 1
    assert report["status"] == "candidate_quota_met"
    assert derived["id"] not in {row["id"] for row in production.author.jsonl(args.output / "generate.jsonl")}
    assert len(calls) == len(drawings) == 3


    args.cover_all_sources = True
    report = production.run(args, model=model, agent=None, compiler=None, trace_client=None)
    assert report["completed_candidates"] == {"Generate": 2, "Edit": 2}
    assert report["status"] == "drawing_budget_exhausted"
    assert report["source_coverage"]["missing"] == {"Generate": ["new-source"], "Edit": ["new-source"]}
    assert len(calls) == len(drawings) == 3
    args.cover_all_sources = False
    assert production.run(args, model=model, agent=None, compiler=None, trace_client=None)["cover_all_sources"]
    sources["third"] = {"id": "third", "source_group": "third", "source_text": "Third source"}
    with pytest.raises(ValueError, match="each task quota"):
        production.run(args, model=model, agent=None, compiler=None, trace_client=None)


def test_collect_exclusions_are_task_row_scoped(monkeypatch):
    monkeypatch.setattr(production, "completed", lambda row: True)
    edit = {"id": "edit-row", "task": "Edit", "instruction": "Shorter altitude",
            "current_tikz": r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}",
            "target_tikz": r"\begin{tikzpicture}\coordinate (A) at (1,0);\end{tikzpicture}",
            "provenance": {"complete_instruction": "A triangle has a shorter altitude."}}
    derived = production.derive_generate(edit)
    generated, edits = production.collect([edit], 10, 10, {edit["id"]})
    assert [row["id"] for row in generated] == [derived["id"]]
    assert edits == []
    generated, edits = production.collect([edit], 10, 10, {derived["id"]})
    assert generated == []
    assert [row["id"] for row in edits] == [edit["id"]]


def test_reconstruct_export_binds_source_image_separately_from_target(tmp_path):
    drawing = production.drawing
    target = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
    original, rendered = tmp_path / "input.png", tmp_path / "target.png"
    Image.new("RGB", (8, 8), "black").save(original)
    Image.new("RGB", (8, 8), "white").save(rendered)
    row = {"schema_version": "synthetic-tikz:v2", "id": "reconstruction", "task": "Reconstruct",
           "instruction": None, "current_tikz": None, "target_tikz": target,
           "source": None, "source_group": None, "grade": None, "diagram_types": None,
           "split": None, "provenance": None,
           "image": {"path": str(original), "sha256": hashlib.sha256(original.read_bytes()).hexdigest()},
           "rendered_png_path": str(rendered), "rendered_tikz_sha256": hashlib.sha256(target.encode()).hexdigest(),
           "rendered_png_sha256": hashlib.sha256(rendered.read_bytes()).hexdigest()}
    row["verification"] = {"status": "ready", "reviewed_by": "test double",
                           "reviewed_input_sha256": drawing.review_digest(row)}
    files = drawing.export_rows([row], tmp_path / "export")
    import pyarrow.parquet as pq
    saved = pq.read_table(next(iter(files))).to_pylist()[0]
    assert saved["image"]["bytes"] == original.read_bytes()
    assert saved["tikz_image"]["bytes"] == rendered.read_bytes()
    assert saved["instruction"] is None and saved["diagram_types"] is None
    production.write_rows(tmp_path / "reconstruct.jsonl", [row])
    assert drawing.load_rows(tmp_path / "reconstruct.jsonl")[0]["instruction"] is None
    Image.new("RGB", (8, 8), "blue").save(original)
    assert drawing.source_image(row) is None
    with pytest.raises(ValueError, match="review|source image"):
        drawing.export_rows([row], tmp_path / "stale")


def test_context_batch_samples_five_or_ten_inputs_before_reusing_sources(monkeypatch):
    sources = {f"source-{i}": {"id": f"source-{i}", "source_group": f"group-{i}",
                              "source_text": f"Math problem {i}"} for i in range(30)}
    history = [{"task": "Generate", "instruction": "Already used", "provenance": {"parents": ["source-0"]}}]
    state = {"seed": 12, "round": 1, "base_count": 100, "generate": 1500, "edit": 1500}
    for size in (5, 10):
        context, bases = production.make_context(sources, {}, history, state, 50, size)
        assert not bases and len(context["sources"]) == size
        assert "source-0" not in {row["id"] for row in context["sources"]}
        assert context == production.make_context(sources, {}, history, state, 50, size)[0]
        payload = production.author.author_payload(context)
        assert all(set(row) == {"source", "source_text"} for row in payload)
        assert context["rows_requested"] == 50

    monkeypatch.setattr(production, "completed", lambda row: True)
    latest = {f"base-{i}": {"id": f"base-{i}", "task": "Generate", "instruction": f"Base givens {i}",
                           "source_group": f"group-{i}", "provenance": {"parents": [f"source-{i}"]}}
              for i in range(20)}
    state["base_count"] = 20
    context, bases = production.make_context(sources, latest, [], state, 50, 10)
    assert len(bases) == 10
    state["base_count"] = 19
    context, bases = production.make_context(sources, latest, [], state, 50, 10, {"base-0"})
    assert context["tasks"] == ["Edit"]
    assert "base-0" not in bases
    payload = production.author.author_payload(context)
    assert len(payload) == 10 and all(set(row) == {"source", "givens"} for row in payload)


def test_author_failure_stops_and_resume_retries_the_same_context(tmp_path, monkeypatch):
    sources = {"source": {"id": "source", "source_group": "family", "source_text": "givens"}}
    monkeypatch.setattr(production.author, "load_pool", lambda path: (sources, [], {}))
    calls = []

    def fail(contexts, output, **kwargs):
        calls.append(contexts)
        checkpoint = {"status": "failed", "rows": [], "error": "provider unavailable"}
        production.drawing.save_json(output / "batches/scope/result.json", checkpoint)
        return production.author.save_instructions(output, [checkpoint], sources)

    monkeypatch.setattr(production.author, "generate", fail)
    args = SimpleNamespace(output=tmp_path / "run", sources=Path("unused"), seed=42, base_count=1,
                           generate=1, edit=1, resume=False, max_draw_attempts=8, max_author_calls=8,
                           batch_size=1, contexts_per_call=10, workers=8, max_model_calls=4, compiler_concurrency=2)
    model = SimpleNamespace(model_name="test-double")
    for expected_calls in (1, 2):
        report = production.run(args, model=model, agent=None, compiler=None, trace_client=None)
        assert report["status"] == "author_failed"
        assert report["author_calls_reserved"] == expected_calls
        assert report["drawing_attempts_reserved"] == 0
        state = json.loads((args.output / "state.json").read_text())
        assert state["round"] == 1 and state["pending"]
        args.resume = True
    assert len(calls) == 2 and calls[0] == calls[1]


def test_full_coverage_uses_missing_records_beyond_base_floor_and_reaches_both_exports(monkeypatch):
    monkeypatch.setattr(production, "completed", lambda row: row.get("success", True))
    sources = {key: {"id": key, "source_group": group, "source_text": key}
               for key, group in [("used", "shared"), ("copy", "shared"), ("other", "other")]}
    def base(key):
        return {"id": "base-" + key, "task": "Generate", "instruction": "Givens " + key,
                "target_tikz": key, "source_group": sources[key]["source_group"],
                "provenance": {"parents": [key]}}
    latest = {"base-used": base("used"), "base-other": base("other")}
    history = [{"task": "Generate", "instruction": "Failed proposal", "provenance": {"parents": ["copy"]}}] * 9
    state = {"seed": 42, "round": 1, "base_count": 2, "generate": 6, "edit": 6,
             "cover_all_sources": True}
    context, bases = production.make_context(sources, latest, history, state, 30, 10)
    assert context["tasks"] == ["Generate"] and not bases
    assert [row["id"] for row in context["sources"]] == ["copy"]
    assert production.author.author_payload(context) == [{"source": "copy", "source_text": "copy"}]
    latest["base-copy"] = base("copy")
    for key in ("used", "other"):
        latest["edit-" + key] = {"id": "edit-" + key, "task": "Edit", "instruction": "Auxiliary " + key,
            "source_group": sources[key]["source_group"], "current_tikz": key, "target_tikz": key + "-edited",
            "provenance": {"parents": [key], "starting_record_id": "base-" + key}}
    state["edit"] = 3
    context, bases = production.make_context(sources, latest, history, state, 1, 10)
    assert context["tasks"] == ["Edit"] and list(bases) == ["base-copy"]
    assert set(production.author.author_payload(context)[0]) == {"source", "givens"}
    # Once covered, the original sources stay in the same active pool.
    latest["edit-copy"] = {**latest["edit-used"], "id": "edit-copy", "instruction": "Auxiliary copy",
        "provenance": {"parents": ["copy"], "starting_record_id": "base-copy"}}
    state["edit"] = 6
    context, bases = production.make_context(sources, latest, history, state, 30, 10)
    assert {parent for row in bases.values() for parent in row["provenance"]["parents"]} & {"used", "other"}
    assert len({row["source_group"] for row in bases.values()}) == len(bases)
    _, bases = production.make_context(sources, latest, history, state, 30, 10, {"base-copy"})
    assert not bases  # Excluding the only base for a record makes Generate necessary again.


def test_capped_exports_keep_new_source_coverage_and_honor_exclusions(monkeypatch):
    monkeypatch.setattr(production, "completed", lambda row: True)
    rows = [{"id": key, "task": "Generate", "instruction": key, "provenance": {"parents": [parent]}}
            for key, parent in [("old-a", "a"), ("another-a", "a"), ("new-b", "b")]]
    generated, _ = production.collect(rows, 2, 2, cover_all_sources=True)
    assert [row["id"] for row in generated] == ["old-a", "new-b"]
    coverage = production.source_coverage({"Generate": generated}, {"a", "b"})
    assert coverage == {"selected": 2, "covered": {"Generate": 2}, "missing": {"Generate": []}}
    generated, _ = production.collect(rows, 2, 2, {"new-b"}, cover_all_sources=True)
    assert production.source_coverage({"Generate": generated}, {"a", "b"})["missing"] == {"Generate": ["b"]}


def test_duplicate_text_does_not_claim_an_unused_source_is_covered(monkeypatch):
    monkeypatch.setattr(production, "completed", lambda row: True)
    rows = [{"id": parent, "task": "Generate", "instruction": "Same complete givens",
             "provenance": {"parents": [parent]}} for parent in ["first", "copy"]]
    generated, _ = production.collect(rows, 2, 2, cover_all_sources=True)
    assert len(generated) == 1
    assert production.source_coverage({"Generate": generated}, {"first", "copy"})["missing"] == {"Generate": ["copy"]}
