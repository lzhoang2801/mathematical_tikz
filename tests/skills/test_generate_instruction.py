"""CPA instruction workflow checks; they do not approve mathematical cases."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from threading import Barrier, Lock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from tools import generate_instruction as author

TIKZ_A = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
TIKZ_B = r"\begin{tikzpicture}\coordinate (B) at (1,0);\end{tikzpicture}"
SOURCE_A = "grade_8_sgk_1-L4197"
SOURCE_B = "grade_8_sgk_2-L4874"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source(source_id: str, book: str, lines: tuple[int, int], givens: str) -> dict:
    start, end = lines
    source_md = f"8/{book}/book.final.md"
    source_text = givens
    return {
        "id": source_id,
        "grade": 8,
        "book": book,
        "source_kind": "example",
        "source_md": source_md,
        "start_line": start,
        "end_line": end,
        "source_text": source_text,
        "source_group": f"curriculum-{source_id}",
        "source": f"{source_md}:L{start}-{end} ({source_id})",
        "source_sha256": _sha(f"book hash fixture: {book}"),
        "source_text_sha256": _sha(source_text),
        "diagram_types": ["G03", "G06"],
    }


SOURCES = {
    SOURCE_A: _source(
        SOURCE_A,
        "grade_8_sgk_1",
        (3978, 4003),
        "ABC vuông tại A; AH là đường cao; I, K là trung điểm AH, HB.",
    ),
    SOURCE_B: _source(
        SOURCE_B,
        "grade_8_sgk_2",
        (4537, 4542),
        "AH là đường cao; HE, HF là các đường cao phụ thuộc trong hai tam giác.",
    ),
}


def _context(batch_id: str, sources: list[dict], task: str = "Generate") -> dict:
    return {
        "batch_id": batch_id,
        "seed": 42,
        "rows_requested": 1,
        "tasks": [task],
        "requested_counts": {task: 1},
        "audit_documents": {source["book"]: f"G/F/Aux/C audit fixture for {source['id']}"
                            for source in sources},
        "sources": sources,
        "request": "Use only these allowlisted sources.",
    }


def _instruction(task: str, text: str, parents: list[str], *, starting_givens: str | None = None) -> author.Instruction:
    return author.Instruction(
        task=task,
        instruction=text,
        parents=parents,
        augmentation="fixture operation",
        starting_givens=starting_givens,
        diagram_types=["G03"],
    )


def _batch_for(context: dict) -> author.InstructionBatch:
    source = context["sources"][0]
    return author.InstructionBatch(
        instructions=[_instruction("Generate", source["source_text"], [source["id"]])],
        notes=[],
    )


class FakeCPA:
    model_name = "fake-cpa"

    def __init__(self, invoke):
        self._invoke = invoke
        self.schemas = []

    def with_structured_output(self, schema, **kwargs):
        self.schemas.append((schema, kwargs))
        return RunnableLambda(self._invoke)


def _messages_context(messages) -> tuple[SystemMessage, dict]:
    system = next(message for message in messages if isinstance(message, SystemMessage))
    human = next(message for message in messages if isinstance(message, HumanMessage))
    return system, json.loads(human.content)


def _response(batch: author.InstructionBatch, label: str, *, parsing_error=None) -> dict:
    return {
        "raw": AIMessage(content=f"raw CPA response: {label}"),
        "parsed": batch,
        "parsing_error": parsing_error,
    }


def test_parallel_calls_include_skill_audit_and_keep_batch_checkpoints(tmp_path):
    barrier = Barrier(2)
    lock = Lock()
    active = 0
    peak = 0
    seen = []

    def invoke(messages):
        nonlocal active, peak
        system, context = _messages_context(messages)
        with lock:
            seen.append((system, context))
            active += 1
            peak = max(peak, active)
        try:
            barrier.wait(timeout=5)
            return _response(_batch_for(context), context["batch_id"])
        finally:
            with lock:
                active -= 1

    contexts = [
        _context("batch-a", [SOURCES[SOURCE_A]]),
        _context("batch-b", [SOURCES[SOURCE_B]]),
    ]
    model = FakeCPA(invoke)
    output = tmp_path / "run"

    report = author.generate(contexts, output, model=model, sources=SOURCES, workers=2)

    assert peak == 2
    assert model.schemas == [(author.InstructionBatch,
                              {"method": "function_calling", "include_raw": True})]
    skill = (author.SKILL / "SKILL.md").read_text(encoding="utf-8")
    strategy = (author.SKILL / "references/run-prompt.md").read_text(encoding="utf-8")
    assert len(seen) == 2
    for system, context in seen:
        assert skill in system.content and strategy in system.content
        assert "| G03 |" in system.content and "| G17 |" in system.content
        source_id = context["sources"][0]["id"]
        assert context["audit_documents"]
        assert source_id in json.dumps(context["audit_documents"], ensure_ascii=False)

    checkpoints = list((output / "batches").glob("*/result.json"))
    assert len(checkpoints) == 2
    for checkpoint in checkpoints:
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        attempt = checkpoint.parent / saved["trace_id"]
        request = json.loads((attempt / "request.json").read_text(encoding="utf-8"))
        response = json.loads((attempt / "response.json").read_text(encoding="utf-8"))
        attempt_result = json.loads((attempt / "result.json").read_text(encoding="utf-8"))
        assert saved["status"] == attempt_result["status"] == "completed"
        assert request["context"]["batch_id"] in ("batch-a", "batch-b")
        assert "raw CPA response" in json.dumps(response, ensure_ascii=False)
        assert saved["rows"][0]["provenance"]["trace_id"] == saved["trace_id"]
        source_id = saved["rows"][0]["provenance"]["parents"][0]
        assert saved["rows"][0]["source"].endswith(f"({source_id})")
        assert saved["rows"][0]["provenance"]["parent_hashes"][source_id] == SOURCES[source_id]["source_text_sha256"]

    rows = [json.loads(line) for line in (output / "generate-inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2 and all(row["current_tikz"] is None for row in rows)
    assert report["calls_completed"] == 2 and report["calls_failed"] == 0
    assert not list(output.rglob("*.csv"))


def test_materialize_rejects_unscoped_and_boilerplate_and_keeps_edits_unstarted(tmp_path, monkeypatch):
    context = _context("validation", [SOURCES[SOURCE_A]])
    context["tasks"] = ["Generate", "Edit"]
    batch = author.InstructionBatch(
        instructions=[
            _instruction("Generate", "Tam giác ABC vuông tại A; AH là đường cao.", [SOURCE_A]),
            _instruction("Edit", "E là hình chiếu của H lên AB.", [SOURCE_A],
                         starting_givens="ABC vuông tại A; AH là đường cao."),
            _instruction("Generate", "Một givens hợp lệ.", ["unknown-source"]),
            _instruction("Generate", "Hình gồm các đoạn AB, AC.", [SOURCE_A]),
            _instruction("Generate", "ABC vuông tại A; có các đoạn AH, BH.", [SOURCE_A]),
        ],
        notes=[],
    )

    rows, rejected = author.materialize(batch, context, "d" * 64, "trace-fixture", {})

    assert [row["task"] for row in rows] == ["Generate", "Edit"]
    assert all(row["current_tikz"] is None and "target_tikz" not in row for row in rows)
    assert rows[0]["provenance"]["parents"] == [SOURCE_A]
    assert rows[1]["provenance"]["starting_givens"] == "ABC vuông tại A; AH là đường cao."
    assert [entry["index"] for entry in rejected] == [2, 3, 4]
    assert "outside the supplied scope" in rejected[0]["reason"]
    assert "boilerplate" in rejected[1]["reason"]
    assert "boilerplate" in rejected[2]["reason"]
    author.validate_instruction("Tam giác ABC; AB, AC vuông góc.")

    output = tmp_path / "pending"
    report = author.save_instructions(output, [{"status": "completed", "rows": rows}], SOURCES)
    generated = [json.loads(line) for line in (output / "generate-inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(generated) == 1 and generated[0]["current_tikz"] is None
    assert (output / "edit-inputs.jsonl").read_text(encoding="utf-8") == ""
    assert report["edit_awaiting_starting_tikz"] == 1
    author.save_json(output / "supervision.json", {"rows": [
        {"id": rows[0]["id"], "decision": "needs_revision", "reason": "fixture instruction hold"}]})
    held = author.save_instructions(output, [{"status": "completed", "rows": rows}], SOURCES)
    assert held["review_held_instructions"] == 1
    assert (output / "generate-inputs.jsonl").read_text(encoding="utf-8") == ""
    assert len(author.jsonl(output / "instructions.jsonl")) == 2
    author.save_json(output / "sources.json", SOURCES)
    author.save_json(output / "batches/fixture/result.json", {"status": "completed", "rows": rows})
    monkeypatch.setattr(author.sys, "argv", ["generate_instruction.py", "--output", str(output), "--review-only"])
    monkeypatch.setattr(author, "build_model", lambda **kwargs: pytest.fail("Review must not build a model"))
    assert author.main() == 0
    assert (output / "generate-inputs.jsonl").read_text(encoding="utf-8") == ""

    checked_base = {
        "id": "checked-generate",
        "task": "Generate",
        "instruction": "ABC vuông tại A; AH là đường cao.",
        "current_tikz": None,
        "target_tikz": TIKZ_B,
        "source_group": "already-merged-family",
        "split": "train",
        "provenance": {"parents": [SOURCE_A]},
        "verification": {"status": "ready", "reviewed_by": "test fixture"},
    }
    edit = author.InstructionBatch(
        instructions=[_instruction("Edit", "E là hình chiếu của H lên AB.", [SOURCE_A],
                                   starting_givens=checked_base["instruction"])],
        notes=[],
    )
    copied, rejected = author.materialize(edit, context, "e" * 64, "edit-trace", {"checked": checked_base})
    assert rejected == [] and len(copied) == 1
    assert copied[0]["current_tikz"] == checked_base["target_tikz"]
    assert copied[0]["split"] == "train"
    assert copied[0]["provenance"]["starting_record_id"] == checked_base["id"]
    revised = batch.model_copy(deep=True)
    revised.instructions[0].instruction += " AB = 2AC."
    changed, _ = author.materialize(revised, context, "d" * 64, "revised-trace", {})
    assert changed[0]["id"] != rows[0]["id"]


def test_exact_instruction_duplicates_merge_parent_groups(tmp_path):
    context = _context("duplicate", [SOURCES[SOURCE_A], SOURCES[SOURCE_B]])
    batch = author.InstructionBatch(
        instructions=[
            _instruction("Generate", "Tam giác ABC vuông tại A; AH là đường cao.", [SOURCE_A]),
            _instruction("Generate", "Tam giác ABC vuông tại A; AH là đường cao.", [SOURCE_B]),
        ],
        notes=[],
    )
    rows, rejected = author.materialize(batch, context, "f" * 64, "duplicate-trace", {})
    assert rejected == [] and len(rows) == 2

    report = author.save_instructions(tmp_path / "duplicates", [{"status": "completed", "rows": rows}], SOURCES)

    saved = [json.loads(line) for line in (tmp_path / "duplicates/instructions.jsonl").read_text(encoding="utf-8").splitlines()]
    groups = json.loads((tmp_path / "duplicates/source-groups.json").read_text(encoding="utf-8"))
    assert report["exact_duplicates"] == 1 and len(saved) == 1
    assert groups[SOURCE_A] == groups[SOURCE_B] == saved[0]["source_group"]
    # The deduplicated row keeps one representative parent; both parents map to
    # its merged family in the sidecar, so the full lineage remains recoverable.
    assert saved[0]["provenance"]["parents"] == [SOURCE_A]
    assert report["sources_used"] == 2
    rows[0]["split"], rows[1]["split"] = "train", "test"
    with pytest.raises(ValueError, match="conflicting assigned splits"):
        author.save_instructions(tmp_path / "duplicates", [{"status": "completed", "rows": rows}], SOURCES)


def test_numeric_renaming_padding_and_edit_parameter_changes_do_not_become_cases(tmp_path):
    context = _context("auxiliary", [SOURCES[SOURCE_A]])
    context["tasks"] = ["Generate", "Edit"]
    statements = ["Tam giác ABC có AB = 20 cm; AH là đường cao.",
                  "Tam giác MNP có MN = 32 cm; MK là đường cao.",
                  "Tam giác ABC có AB = 20 cm; AH là đường cao; I là trung điểm AH."]
    batch = author.InstructionBatch(instructions=[
        *[_instruction("Generate", text, [SOURCE_A]) for text in statements],
        _instruction("Edit", "Thay độ dài AB bằng 24 cm.", [SOURCE_A], starting_givens=statements[0])], notes=[])
    rows, rejected = author.materialize(batch, context, "q" * 64, "fixture-trace", {})
    assert len(rows) == 3 and len(rejected) == 1
    report = author.save_instructions(tmp_path / "variants", [{"status": "completed", "rows": rows}], SOURCES)
    assert report["number_or_label_variants"] == 1
    assert len(author.jsonl(tmp_path / "variants/generate-inputs.jsonl")) == 2
    context["existing_instructions"] = [{"task": "Generate", "instruction": statements[0]}]
    repeated, rejects = author.materialize(batch, context, "r" * 64, "fixture-trace", {})
    assert len(repeated) == 1 and "Repeated existing case" in rejects[0]["reason"]


def test_resume_retries_failed_batch_once_and_preserves_completed_rows(tmp_path):
    calls = Counter()

    def invoke(messages):
        _, context = _messages_context(messages)
        batch_id = context["batch_id"]
        calls[batch_id] += 1
        if batch_id == "retry" and calls[batch_id] == 1:
            return _response(author.InstructionBatch(instructions=[], notes=[]), batch_id,
                             parsing_error=ValueError("fixture parse failure"))
        return _response(_batch_for(context), batch_id)

    contexts = [
        _context("completed", [SOURCES[SOURCE_A]]),
        _context("retry", [SOURCES[SOURCE_B]]),
    ]
    output = tmp_path / "resume"
    model = FakeCPA(invoke)

    first = author.generate(contexts, output, model=model, sources=SOURCES, workers=1)
    initial = [json.loads(line) for line in (output / "instructions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert first["calls_completed"] == 1 and first["calls_failed"] == 1
    assert len(initial) == 1 and initial[0]["provenance"]["parents"] == [SOURCE_A]
    batch_dirs = list((output / "batches").iterdir())
    failed_dir = next(path for path in batch_dirs
                      if json.loads((path / "result.json").read_text(encoding="utf-8"))["status"] == "failed")
    failed_trace = json.loads((failed_dir / "result.json").read_text(encoding="utf-8"))["trace_id"]
    subset = author.generate(contexts[:1], output, model=None, sources=SOURCES, workers=1, resume=True)
    assert subset["calls_failed"] == 1 and calls == Counter({"completed": 1, "retry": 1})

    second = author.generate(contexts, output, model=model, sources=SOURCES, workers=1, resume=True)

    latest = [json.loads(line) for line in (output / "instructions.jsonl").read_text(encoding="utf-8").splitlines()]
    latest_by_parent = {row["provenance"]["parents"][0]: row for row in latest}
    failed_history = json.loads((failed_dir / failed_trace / "result.json").read_text(encoding="utf-8"))
    recovered = json.loads((failed_dir / "result.json").read_text(encoding="utf-8"))
    assert calls == Counter({"completed": 1, "retry": 2})
    assert second["calls_completed"] == 2 and second["calls_failed"] == 0
    assert set(latest_by_parent) == {SOURCE_A, SOURCE_B}
    assert latest_by_parent[SOURCE_A]["id"] == initial[0]["id"]
    assert failed_history["status"] == "failed" and recovered["status"] == "completed"
    assert recovered["trace_id"] != failed_trace
    contexts[0]["existing_instructions"] = [{"task": "Generate", "instruction": "new accumulated history"}]
    cached = author.generate(contexts[:1], output, model=None, sources=SOURCES, workers=1, resume=True)
    assert cached["calls_completed"] == 2
    assert calls == Counter({"completed": 1, "retry": 2})
    assert len(author.jsonl(output / "instructions.jsonl")) == 2
