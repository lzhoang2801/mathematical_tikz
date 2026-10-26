"""Deterministic tests for the compact instruction-author contract."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from tools import generate_instruction as author

TIKZ = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
SOURCE_A = "grade_8_sgk_1-L4197"
SOURCE_B = "grade_8_sgk_2-L4874"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source(source_id: str, book: str, source_text: str) -> dict:
    source_md = f"8/{book}/book.final.md"
    return {
        "id": source_id, "grade": 8, "book": book, "source_kind": "example",
        "source_md": source_md, "source_path": source_md, "start_line": 10, "end_line": 10,
        "locator": {"record_id": source_id, "start_line": 10, "end_line": 10},
        "source_text": source_text, "source_group": f"family-{source_id}", "family": "triangle",
        "source": f"{source_md}:L10-10 ({source_id})", "image_paths": [f"8/{book}/images/figure.png"],
        "book_role": "textbook", "source_sha256": _sha(f"book:{book}"),
        "source_text_sha256": _sha(source_text), "diagram_types": ["G03"],
        "manifest_diagram_types": ["A02", "G03"], "audited_diagram_types": None,
    }


SOURCES = {
    SOURCE_A: _source(SOURCE_A, "grade_8_sgk_1", "Tam giác ABC vuông tại A; AH vuông góc BC."),
    SOURCE_B: _source(SOURCE_B, "grade_8_sgk_2", "M là trung điểm AB; N là trung điểm AC."),
}


def _base(source_ids: list[str] | None = None) -> dict:
    return {
        "id": "generate-base-1", "task": "Generate",
        "instruction": "Tam giác ABC có M là trung điểm AB.", "target_tikz": TIKZ,
        "source_group": SOURCES[SOURCE_A]["source_group"], "split": "train", "grade": 8,
        "diagram_types": ["G03"], "provenance": {"parents": source_ids or [SOURCE_A]},
    }


def _context(batch_id: str = "batch", *, task: str = "Generate", selected=None, starts=None,
             total: int = 3, requested_counts=None) -> dict:
    selected = list(SOURCES.values())[:1] if selected is None else selected
    starts = [] if starts is None else starts
    return {
        "batch_id": batch_id, "seed": 7, "rows_requested": total, "tasks": [task],
        "requested_counts": requested_counts or {task: total}, "sources": selected,
        "existing_instructions": [], "available_starts": starts,
        "request": "internal local scheduling note",
    }


def _instruction(task: str, source: str, text: str, complete: str | None = None) -> author.Instruction:
    return author.Instruction(task=task, source=source, instruction=text, complete_instruction=complete)


def _batch(items: list[author.Instruction]) -> author.InstructionBatch:
    return author.InstructionBatch(instructions=items)


class FakeCPA:
    model_name = "fake-cpa"

    def __init__(self, invoke):
        self.invoke_fn = invoke
        self.schemas = []

    def with_structured_output(self, schema, **kwargs):
        self.schemas.append((schema, kwargs))
        return RunnableLambda(self.invoke_fn)


def _messages(messages):
    system = next(message for message in messages if isinstance(message, SystemMessage))
    human = next(message for message in messages if isinstance(message, HumanMessage))
    return system, json.loads(human.content)


def _response(batch: author.InstructionBatch, label: str) -> dict:
    return {"raw": AIMessage(content=f"raw CPA response: {label}", usage_metadata={
                "input_tokens": 13, "output_tokens": 8, "total_tokens": 21}),
            "parsed": batch, "parsing_error": None}


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def test_load_pool_verifies_source_text_locator_and_hash(tmp_path, monkeypatch):
    root, corpus = tmp_path / "repo", tmp_path / "curriculums"
    monkeypatch.setattr(author, "ROOT", root)
    monkeypatch.setattr(author, "CORPUS", corpus)
    source_path = "8/book/book.final.md"
    content = "cover\nA mathematical example.\n"
    source_file = corpus / source_path
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(content.encode("utf-8"))
    _write_jsonl(root / "docs/dataset-selection/grade-8.problems.jsonl", [{
        "id": "source-a", "grade": 8, "book": "book", "book_role": "textbook",
        "source_kind": "example", "source_md": source_path, "start_line": 2, "end_line": 2,
        "source_text": "A mathematical example.", "image_paths": [], "diagram_types": ["A02", "G03"],
        "decision": "prepared",
    }])
    selected = {"record_id": "source-a", "source_group": "family-a", "source_path": source_path,
               "source_sha256": _sha(content), "locator": {"record_id": "source-a", "start_line": 2, "end_line": 2},
               "decision": "selected", "reason": "Selected after audit.", "givens": "Audited facts.",
               "auxiliaries": [], "family": "triangle"}
    path = tmp_path / "selection.jsonl"
    _write_jsonl(path, [selected])

    sources, batches, _ = author.load_pool(path)

    assert sources["source-a"]["source_text"] == "A mathematical example."
    assert sources["source-a"]["diagram_types"] == ["G03"]
    assert batches == [{"batch_id": "triangle", "problem_ids": ["source-a"]}]
    selected.pop("source_group")
    selected["diagram_types"] = None
    _write_jsonl(path, [selected])
    assert author.load_pool(path)[0]["source-a"]["source_group"] == "source-a"
    selected["source_sha256"] = "0" * 64
    _write_jsonl(path, [selected])
    with pytest.raises(ValueError, match="Stale source audit hash"):
        author.load_pool(path)


def test_author_payload_contains_only_compact_task_specific_context():
    base = _base()
    selected = [{**SOURCES[SOURCE_A], "givens": "Extra audit facts", "auxiliaries": ["Audit construction"]},
                SOURCES[SOURCE_B]]
    starts = [{"id": base["id"], "instruction": base["instruction"],
               "current_tikz": base["target_tikz"],
               "source_group": base["source_group"], "parents": [SOURCE_A], "grade": 8,
               "diagram_types": ["G03"]}]
    context = _context(task="both", selected=selected, starts=starts, total=12,
                       requested_counts={"Generate": 8, "Edit": 4})
    context["tasks"] = ["Generate", "Edit"]
    payload = author.author_payload(context)

    assert payload == [
        {"source": SOURCE_A, "source_text": SOURCES[SOURCE_A]["source_text"],
         "givens": "Extra audit facts", "auxiliaries": ["Audit construction"]},
        {"source": SOURCE_B, "source_text": SOURCES[SOURCE_B]["source_text"]},
        {"source": base["id"], "givens": base["instruction"], "current_tikz": TIKZ},
    ]
    encoded = json.dumps(payload, ensure_ascii=False)
    for hidden in ("source_sha256", "source_path", "locator", "reason", "diagram_types", "target_tikz", "reviewed_by", "request"):
        assert hidden not in encoded
    assert payload[2]["current_tikz"] == TIKZ
    assert set(payload[0]) == {"source", "source_text", "givens", "auxiliaries"}
    assert set(payload[2]) == {"source", "givens", "current_tikz"}

    altered = {**context, "available_starts": [{**starts[0], "current_tikz": TIKZ + "% altered"}]}
    with pytest.raises(ValueError, match="Checked start does not match"):
        author.validate_contexts([altered], {row["id"]: row for row in selected}, {base["id"]: base})


def test_materialize_uses_exact_source_and_base_ids_for_local_provenance():
    base = _base()
    starts = [{"id": base["id"], "instruction": base["instruction"],
               "current_tikz": base["target_tikz"],
               "source_group": base["source_group"], "parents": [SOURCE_A], "grade": 8,
               "diagram_types": ["G03"]}]
    context = _context(task="both", selected=list(SOURCES.values()), starts=starts, total=4,
                       requested_counts={"Generate": 2, "Edit": 2})
    context["tasks"] = ["Generate", "Edit"]
    complete = base["instruction"] + "; P là trung điểm BC và AP là trung tuyến."
    batch = _batch([
        _instruction("Generate", SOURCE_A, "ABC vuông tại A; AH vuông góc BC.", None),
        _instruction("Generate", SOURCE_B, "Tam giác XYZ có M là trung điểm XY.", None),
        _instruction("Edit", base["id"], "P là trung điểm BC; AP là trung tuyến.", complete),
        _instruction("Edit", "invented-base", "Q là trung điểm AC.", "Complete config."),
    ])

    rows, rejected = author.materialize(batch, context, "d" * 64, "trace-id", {base["id"]: base})

    assert len(rows) == 3 and [entry["index"] for entry in rejected] == [3]
    generated, generated_b, edited = rows
    assert generated["provenance"]["parents"] == [SOURCE_A]
    assert generated_b["provenance"]["parents"] == [SOURCE_B]
    assert not {"grade", "diagram_types", "book", "book_role", "source_kind", "source_path",
                "source_location", "image_paths"}.intersection(generated)
    assert set(generated["provenance"]["parent_sources"][SOURCE_A]) == {
        "source_path", "source_sha256", "source_text_sha256", "locator"}
    assert "target_tikz" not in generated
    assert edited["current_tikz"] == TIKZ
    assert edited["provenance"]["parents"] == [SOURCE_A]
    assert edited["provenance"]["starting_record_id"] == base["id"]
    assert edited["provenance"]["starting_givens"] == base["instruction"]
    assert edited["provenance"]["complete_instruction"] == complete


def test_exact_duplicates_are_screened_but_numeric_and_label_variants_are_not():
    context = _context(total=4)
    text = "Tam giác ABC có AB = 4 cm."
    batch = _batch([
        _instruction("Generate", SOURCE_A, text, None),
        _instruction("Generate", SOURCE_A, text, None),
        _instruction("Generate", SOURCE_A, "Tam giác MNP có MN = 8 cm.", None),
        _instruction("Generate", SOURCE_A, "Tam giác ABC có AB = 5 cm.", None),
    ])

    rows, rejected = author.materialize(batch, context, "a" * 64, "trace", {})

    assert len(rows) == 3 and [item["index"] for item in rejected] == [1]
    assert rejected[0]["reason"] == "Repeated exact input"


def test_generate_sends_compact_array_and_checkpoints_full_local_provenance(tmp_path):
    context = _context(total=2)
    outputs = [
        _instruction("Generate", SOURCE_A, "ABC vuông tại A; AH là đường cao.", None),
        _instruction("Generate", SOURCE_A, "ABC vuông tại A; D là trung điểm AB; CD là trung tuyến.", None),
    ]
    seen = []

    def invoke(messages):
        system, payload = _messages(messages)
        seen.append((system.content, payload))
        assert payload == [{"source": SOURCE_A, "source_text": SOURCES[SOURCE_A]["source_text"]}]
        return _response(_batch(outputs), "compact")

    output = tmp_path / "run"
    model = FakeCPA(invoke)
    report = author.generate([context], output, model=model, sources=SOURCES, workers=1)

    result_path = next((output / "batches").glob("*/result.json"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    request = json.loads((result_path.parent / result["trace_id"] / "request.json").read_text(encoding="utf-8"))
    assert seen and author.PROMPT_VERSION in seen[0][0] and "at most 2 instructions" in seen[0][0]
    assert model.schemas == [(author.InstructionBatch, {"method": "function_calling", "include_raw": True})]
    assert request["model_payload"] == seen[0][1]
    assert "source_sha256" in json.dumps(request["context"])
    assert "source_sha256" not in json.dumps(request["model_payload"])
    assert result["status"] == "completed" and result["response_format"] == "tool_call"
    assert result["usage"]["total_tokens"] == 21
    assert len(result["rows"]) == 2 and report["instruction_candidates"] == {"Generate": 2}
    assert all("grade" not in row and "diagram_types" not in row for row in result["rows"])
    assert TIKZ not in (output / "generate-inputs.jsonl").read_text(encoding="utf-8")


def test_save_instructions_requires_positive_supervision_and_retains_raw_rows(tmp_path):
    sources = {"source": {"id": "source", "source_group": "family"}}
    rows = [
        {"id": "usable", "task": "Generate", "instruction": "Triangle ABC has AB = AC.",
         "current_tikz": None, "provenance": {"parents": ["source"]}},
        {"id": "revise", "task": "Generate", "instruction": "Triangle DEF has DE = DF.",
         "current_tikz": None, "provenance": {"parents": ["source"]}},
        {"id": "unreviewed", "task": "Generate", "instruction": "Triangle GHI has GH = GI.",
         "current_tikz": None, "provenance": {"parents": ["source"]}},
    ]
    checkpoints = [{"status": "completed", "rows": rows}]
    report = author.save_instructions(tmp_path, checkpoints, sources)
    assert report["instruction_review_pending"] == 3
    assert report["caller_inputs"] == {"Generate": 0, "Edit": 0}
    assert [row["id"] for row in author.jsonl(tmp_path / "instructions.jsonl")] == [row["id"] for row in rows]
    assert author.jsonl(tmp_path / "generate-inputs.jsonl") == []

    supervision = {"rows": [
        {"id": "usable", "decision": "usable_instruction", "reason": "Complete self-contained givens."},
        {"id": "revise", "decision": "needs_revision", "reason": "The source condition is incomplete."},
    ]}
    (tmp_path / "supervision.json").write_text(json.dumps(supervision), encoding="utf-8")
    report = author.save_instructions(tmp_path, checkpoints, sources)
    assert report["instruction_review_pending"] == 1
    assert report["caller_inputs"] == {"Generate": 1, "Edit": 0}
    assert [row["id"] for row in author.jsonl(tmp_path / "generate-inputs.jsonl")] == ["usable"]
    assert [row["id"] for row in author.jsonl(tmp_path / "instructions.jsonl")] == [row["id"] for row in rows]

    supervision["rows"].append(
        {"id": "unreviewed", "decision": "needs_review", "reason": "The construction branch cannot be established."})
    (tmp_path / "supervision.json").write_text(json.dumps(supervision), encoding="utf-8")
    report = author.save_instructions(tmp_path, checkpoints, sources)
    assert report["instruction_review_pending"] == 0
    assert report["review_held_instructions"] == 2
    assert report["caller_inputs"] == {"Generate": 1, "Edit": 0}
    assert [row["id"] for row in author.jsonl(tmp_path / "generate-inputs.jsonl")] == ["usable"]
    assert [row["id"] for row in author.jsonl(tmp_path / "instructions.jsonl")] == [row["id"] for row in rows]


@pytest.mark.parametrize("negative_decision", ["needs_revision", "needs_review"])
def test_negative_supervision_vetoes_duplicate_usable_instruction(tmp_path, negative_decision):
    sources = {"source": {"id": "source", "source_group": "family"}}
    shared = {"task": "Generate", "instruction": "Triangle ABC has AB = AC.",
              "current_tikz": None, "provenance": {"parents": ["source"]}}
    rows = [{"id": "usable", **shared}, {"id": "held", **shared}]
    checkpoints = [{"status": "completed", "rows": rows}]
    (tmp_path / "supervision.json").write_text(json.dumps({"rows": [
        {"id": "usable", "decision": "usable_instruction", "reason": "Complete source facts."},
        {"id": "held", "decision": negative_decision, "reason": "This item is not approved."},
    ]}), encoding="utf-8")

    report = author.save_instructions(tmp_path, checkpoints, sources)

    assert report["instruction_review_pending"] == 0
    assert report["review_held_instructions"] == 1
    assert report["caller_inputs"] == {"Generate": 0, "Edit": 0}
    assert author.jsonl(tmp_path / "generate-inputs.jsonl") == []
    assert len(author.jsonl(tmp_path / "instructions.jsonl")) == 1


def test_edit_payload_includes_exact_starting_tikz_and_materializer_copies_exact_base(tmp_path):
    base = _base()
    starts = [{"id": base["id"], "instruction": base["instruction"],
               "current_tikz": base["target_tikz"],
               "source_group": base["source_group"], "parents": [SOURCE_A], "grade": 8,
               "diagram_types": ["G03"]}]
    context = _context(task="Edit", starts=starts, total=1)
    payload_expected = [{"source": base["id"], "givens": base["instruction"], "current_tikz": TIKZ}]
    complete = base["instruction"] + "; P là trung điểm BC."

    def invoke(messages):
        _, payload = _messages(messages)
        assert payload == payload_expected and payload[0]["current_tikz"] == TIKZ
        return _response(_batch([_instruction("Edit", base["id"], "P là trung điểm BC.", complete)]), "edit")

    output = tmp_path / "edit-run"
    author.generate([context], output, model=FakeCPA(invoke), sources=SOURCES, bases={base["id"]: base}, workers=1)
    raw_rows = author.jsonl(output / "instructions.jsonl")
    (output / "supervision.json").write_text(json.dumps({"rows": [
        {"id": raw_rows[0]["id"], "decision": "usable_instruction", "reason": "Edit is a meaningful local change."}]}),
        encoding="utf-8")
    author.save_instructions(output, [{"status": "completed", "rows": raw_rows}], SOURCES)
    row = author.jsonl(output / "edit-inputs.jsonl")[0]
    assert row["current_tikz"] == TIKZ
    assert row["provenance"]["starting_record_id"] == base["id"]
    assert row["provenance"]["complete_instruction"] == complete
    assert "grade" not in row and "diagram_types" not in row


def test_fenced_json_fallback_is_schema_checked_and_usage_is_preserved(tmp_path):
    context = _context(total=1)
    batch = _batch([_instruction("Generate", SOURCE_A, "Tam giác ABC có một cấu hình.", None)])
    content = "```json\n" + batch.model_dump_json() + "\n```"
    calls = 0

    def invoke(_messages):
        nonlocal calls
        calls += 1
        raw = AIMessage(content=content, usage_metadata={"input_tokens": 3, "output_tokens": 5, "total_tokens": 8})
        return {"raw": raw, "parsed": None, "parsing_error": None}

    output = tmp_path / "fallback"
    report = author.generate([context], output, model=FakeCPA(invoke), sources=SOURCES, workers=1)
    checkpoint = next((output / "batches").glob("*/result.json"))
    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert calls == 1 and saved["status"] == "completed"
    assert saved["response_format"] == "json_text_fallback"
    assert saved["usage"]["total_tokens"] == report["model_calls_actual"] * 8
    with pytest.raises(ValidationError):
        author.parse_instruction_json_text("prose " + content)


def test_resume_skips_unchanged_context_and_runs_changed_request_once(tmp_path, monkeypatch):
    calls = Counter()

    def invoke(messages):
        system, payload = _messages(messages)
        source_id = payload[0]["source"]
        calls[source_id] += 1
        output = _batch([_instruction("Generate", source_id, f"A distinct case from {source_id}.", None)])
        return _response(output, system.content[-20:])

    model = FakeCPA(invoke)
    output = tmp_path / "resume"
    first = _context("scope-a", total=2)
    author.generate([first], output, model=model, sources=SOURCES, workers=1)
    unchanged = author.generate([first], output, model=None, sources=SOURCES, workers=1, resume=True)
    changed = _context("scope-a", total=3)
    second = author.generate([changed], output, model=model, sources=SOURCES, workers=1, resume=True)

    assert calls == Counter({SOURCE_A: 2})
    assert unchanged["calls_completed"] == 1
    assert second["calls_completed"] == 2
    assert len(author.jsonl(output / "instructions.jsonl")) == 1
    assert second["exact_duplicates"] == 1
    revised_prompt = tmp_path / "revised_prompt.md"
    revised_prompt.write_text(author.PROMPT_PATH.read_text(encoding="utf-8") + "\nPrefer explicit carriers.\n", encoding="utf-8")
    monkeypatch.setattr(author, "PROMPT_PATH", revised_prompt)
    revised = author.generate([changed], output, model=model, sources=SOURCES, workers=1, resume=True)
    assert revised["calls_completed"] == 3 and calls[SOURCE_A] == 3
    author.generate([changed], output, model=None, sources=SOURCES, workers=1, resume=True)
    assert calls[SOURCE_A] == 3


def test_schema_requires_nullable_complete_instruction_and_forbids_extra_fields():
    with pytest.raises(ValidationError):
        author.Instruction(task="Generate", source=SOURCE_A, instruction="valid")
    with pytest.raises(ValidationError):
        author.Instruction(task="Generate", source=SOURCE_A, instruction="valid", complete_instruction=None,
                           parents=[SOURCE_A])
    assert author.Instruction.model_fields.keys() == {"task", "source", "instruction", "complete_instruction"}
    assert author.InstructionBatch.model_fields.keys() == {"instructions"}


def test_curated_text_is_bound_to_raw_source_but_only_clean_text_reaches_model(tmp_path, monkeypatch):
    root, corpus = tmp_path / "repo", tmp_path / "curriculums"
    monkeypatch.setattr(author, "ROOT", root)
    monkeypatch.setattr(author, "CORPUS", corpus)
    source_file = corpus / "11/grade_11_sgk_1/full.md"
    source_file.parent.mkdir(parents=True)
    content = "cover\nA noisy source statement.\n"
    source_file.write_text(content, encoding="utf-8")
    row = {"record_id": "curated-1", "source_group": "family-1", "source_path": str(source_file),
           "source_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
           "locator": {"record_id": "curated-1", "start_line": 2, "end_line": 2},
           "decision": "selected", "grade": None, "reason": "Checked against source figure",
           "family": "spatial section", "givens": "verified givens", "auxiliaries": [],
           "raw_source_text": "A noisy source statement.", "source_text": "Verified complete source statement."}
    path = tmp_path / "selection.jsonl"
    _write_jsonl(path, [row])
    sources, batches, _ = author.load_pool(path)
    context = author.build_contexts(sources, batches, calls=1, rows_per_call=12, task="Generate", seed=42)[0]
    assert author.author_payload(context) == [{"source": "curated-1", "source_text": row["source_text"],
                                               "givens": row["givens"]}]
    assert sources["curated-1"]["grade"] is None and sources["curated-1"]["diagram_types"] is None
    row["raw_source_text"] = "An unaudited replacement"
    _write_jsonl(path, [row])
    with pytest.raises(ValueError, match="Stale curated source text"):
        author.load_pool(path)
    row["raw_source_text"] = "A noisy source statement."
    for optional in ("reason", "family", "givens", "auxiliaries"):
        row.pop(optional, None)
    local_source = root / "Onn_generate/example.tex"
    local_source.parent.mkdir(parents=True)
    local_source.write_text(content, encoding="utf-8")
    row.update(source_path=str(local_source), source_sha256=hashlib.sha256(local_source.read_bytes()).hexdigest())
    _write_jsonl(path, [row])
    assert author.load_pool(path)[0]["curated-1"]["source_path"] == str(local_source)
    pdf = root / "[L9CB]_2025_10_10.pdf"
    pdf.write_bytes(b"PDF source stub")
    row.update(source_path=str(pdf), source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
               locator={"record_id": "curated-1", "page": 3})
    _write_jsonl(path, [row])
    assert ":p3" in author.load_pool(path)[0]["curated-1"]["source"]
    row["locator"]["page"] = 0
    _write_jsonl(path, [row])
    with pytest.raises(ValueError, match="one-based page"):
        author.load_pool(path)


def test_instruction_cli_mixes_sources_across_families_and_rotates_inputs():
    sources = {f"source-{i}": {"id": f"source-{i}", "source_text": f"Math {i}", "source_group": f"group-{i}"}
               for i in range(20)}
    batches = [{"batch_id": "a", "problem_ids": list(sources)[:10]},
               {"batch_id": "b", "problem_ids": list(sources)[10:]}]
    for size in (5, 10):
        contexts = author.build_contexts(sources, batches, calls=2, rows_per_call=30, task="Generate", seed=42,
                                         contexts_per_call=size)
        first, second = [{row["source"] for row in author.author_payload(context)} for context in contexts]
        assert len(first) == len(second) == size and not first & second
        assert contexts == author.build_contexts(sources, batches, calls=2, rows_per_call=30, task="Generate", seed=42,
                                                contexts_per_call=size)


def test_mixed_task_batch_bounds_model_inputs_without_dropping_edit_parent_lineage():
    sources = {**SOURCES, **{f"source-{i}": {**SOURCES[SOURCE_A], "id": f"source-{i}", "source_group": f"group-{i}"} for i in range(10)}}
    batches = [{"batch_id": "all", "problem_ids": list(sources)}]
    base = _base()
    contexts = author.build_contexts(sources, batches, calls=1, rows_per_call=30, contexts_per_call=5,
                                     task="both", seed=42, bases={base["id"]: base})
    context = contexts[0]
    author.validate_contexts(contexts, sources, {base["id"]: base})
    payload = author.author_payload(context)
    assert len(payload) == 5
    assert sum("source_text" in row for row in payload) == 4
    assert sum("givens" in row for row in payload) == 1
    assert payload[-1]["current_tikz"] == base["target_tikz"]
    assert SOURCE_A in {row["id"] for row in context["sources"]}


def test_reference_duplicates_rotate_without_occupying_multiple_context_slots():
    references = [{"id": "first", "source_group": "same"}, {"id": "copy", "source_group": "same"},
                  {"id": "other", "source_group": "other"}]
    chosen = author.sample_inputs(references, 10, random.Random(1), Counter({"first": 3}))
    assert {row["id"] for row in chosen} == {"copy", "other"}
    assert chosen[0]["id"] == "other"


def test_generate_payload_preserves_checked_context_without_review_metadata():
    source = {**SOURCES[SOURCE_A], "givens": "ABC right at A; AB<AC; H is the foot on BC.",
              "auxiliaries": ["I is midpoint AH; K is midpoint HB."],
              "verification": {"status": "ready"}, "target_tikz": TIKZ}
    payload = author.author_payload(_context(selected=[source]))
    assert payload == [{"source": SOURCE_A, "source_text": source["source_text"],
                        "givens": source["givens"], "auxiliaries": source["auxiliaries"]}]
    givens_only = {key: value for key, value in source.items() if key != "source_text"}
    assert author.author_payload(_context(selected=[givens_only])) == [
        {"source": SOURCE_A, "givens": source["givens"], "auxiliaries": source["auxiliaries"]}]


def test_edit_cannot_repeat_the_whole_starting_instruction():
    base = _base()
    start = {"id": base["id"], "instruction": base["instruction"], "current_tikz": base["target_tikz"],
             "source_group": base["source_group"], "parents": base["provenance"]["parents"],
             "grade": base["grade"], "diagram_types": base["diagram_types"]}
    context = _context(task="Edit", starts=[start])
    draft = _instruction("Edit", base["id"], "  " + base["instruction"] + "  ", base["instruction"])
    rows, rejected = author.materialize(_batch([draft]), context, "digest", "trace", {base["id"]: base})
    assert rows == [] and "repeats the complete starting instruction" in rejected[0]["reason"]


def test_user_source_exclusions_block_planning_and_stale_positive_queue(tmp_path, monkeypatch):
    path = tmp_path / "excluded.json"
    path.write_text(json.dumps([SOURCE_A]), encoding="utf-8")
    monkeypatch.setattr(author, "EXCLUDED_SOURCES_PATH", path)
    batches = [{"problem_ids": [SOURCE_A, SOURCE_B]}]
    contexts = author.build_contexts(SOURCES, batches, calls=1, rows_per_call=2,
                                    task="Generate", seed=7)
    assert [row["id"] for row in contexts[0]["sources"]] == [SOURCE_B]
    with pytest.raises(ValueError, match="user-excluded"):
        author.build_contexts(SOURCES, batches, calls=1, rows_per_call=1,
                              task="Generate", seed=7, source_ids=[SOURCE_A])
    with pytest.raises(ValueError, match="user-excluded"):
        author.validate_contexts([_context()], SOURCES, {})
    rows, _ = author.materialize(_batch([_instruction("Generate", SOURCE_A, "Triangle ABC.")]),
                                _context(), "digest", "trace", {})
    author.save_json(tmp_path / "supervision.json", {"rows": [
        {"id": rows[0]["id"], "decision": "usable_instruction", "reason": "Old approval."}]})
    before = (tmp_path / "supervision.json").read_bytes()
    report = author.save_instructions(tmp_path, [{"status": "completed", "rows": rows}], SOURCES)
    assert report["user_excluded_instructions"] == 1
    assert report["caller_inputs"] == {"Generate": 0, "Edit": 0}
    assert len(author.jsonl(tmp_path / "instructions.jsonl")) == 1
    assert (tmp_path / "supervision.json").read_bytes() == before


def test_source_exclusion_file_fails_closed_on_invalid_data(tmp_path, monkeypatch):
    path = tmp_path / "excluded.json"
    path.write_text('{"source": true}', encoding="utf-8")
    monkeypatch.setattr(author, "EXCLUDED_SOURCES_PATH", path)
    with pytest.raises(ValueError, match="JSON list"):
        author.excluded_source_ids()


def test_specific_instruction_exclusion_preserves_other_source_constructions(tmp_path, monkeypatch):
    path = tmp_path / "excluded-instructions.json"
    path.write_text(json.dumps([{"task": "Generate", "instruction": "Triangle ABC.",
                                 "parents": [SOURCE_A]}]), encoding="utf-8")
    monkeypatch.setattr(author, "EXCLUDED_INSTRUCTIONS_PATH", path)
    batch = _batch([_instruction("Generate", SOURCE_A, "Triangle  ABC."),
                    _instruction("Generate", SOURCE_A, "Triangle ABC with altitude AH.")])
    rows, rejected = author.materialize(batch, _context(), "digest", "trace", {})
    assert len(rows) == len(rejected) == 1
    assert "user-excluded" in rejected[0]["reason"]
    assert rows[0]["instruction"] == "Triangle ABC with altitude AH."
    old = {**rows[0], "id": "old-positive", "instruction": "Triangle ABC."}
    author.save_json(tmp_path / "supervision.json", {"rows": [
        {"id": old["id"], "decision": "usable_instruction", "reason": "Old approval."}]})
    report = author.save_instructions(tmp_path, [{"status": "completed", "rows": [old]}], SOURCES)
    assert report["user_excluded_instructions"] == 1
    assert report["caller_inputs"] == {"Generate": 0, "Edit": 0}
    allowed, rejected = author.materialize(
        _batch([_instruction("Generate", SOURCE_B, "Triangle ABC.")]),
        _context(selected=[SOURCES[SOURCE_B]]), "other", "trace", {})
    assert len(allowed) == 1 and rejected == []
