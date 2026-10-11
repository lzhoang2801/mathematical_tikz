"""Generate source-grounded Generate/Edit instruction candidates through CPA."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import Client, tracing_context
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tools.cpa import build_model
from tools.draw_instruction import (
    encoded,
    load_rows,
    replace_snapshot,
    save_json,
    validate_tikz,
)

DEFAULT_SELECTION = ROOT / "dataset/audit_givens/selection.jsonl"
PROMPT_PATH = ROOT / "tools/instruction_prompt.md"
SCHEMA_VERSION = "synthetic-tikz:v2"
PROMPT_VERSION = "synthetic-tikz-instructions:v13"
AUTHOR_CALLS_PER_CONTEXT = 1
CORPUS = ROOT.parent / "curriculum_grounding/curriculums"


class Instruction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    task: Literal["Generate", "Edit"]
    source: str = Field(min_length=1, description="Exact source ID for Generate or available base ID for Edit.")
    instruction: str = Field(min_length=1, description="Concise Vietnamese mathematical givens or mathematical change.")
    complete_instruction: str | None = Field(description="Full resulting givens for Edit, retained offline for later Generate reuse; null for Generate.")


class InstructionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instructions: list[Instruction]


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def parse_instruction_json_text(content: str) -> InstructionBatch:
    """Parse a complete schema-shaped JSON response, optionally inside one exact JSON fence."""
    candidate = content
    for newline in ("\n", "\r\n"):
        opening, closing = f"```json{newline}", f"{newline}```"
        if content.startswith(opening) and content.endswith(closing):
            candidate = content[len(opening):-len(closing)]
            break
    return InstructionBatch.model_validate_json(candidate)


def _normalized_path(path: str) -> str:
    value = str(path).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def load_pool(selection_path: Path = DEFAULT_SELECTION) -> tuple[dict[str, dict], list[dict], dict[str, str]]:
    """Load selected sources, binding manifest or curated text to the audited source file."""
    selection_path = Path(selection_path)
    if not selection_path.is_absolute():
        selection_path = ROOT / selection_path
    if not selection_path.is_file():
        raise FileNotFoundError(f"Missing audited source selection: {selection_path}")

    manifests = {}
    for path in sorted((ROOT / "docs/dataset-selection").glob("*problems.jsonl")):
        grades = [int(value) for value in re.findall(r"(?:grade|grades)[-_]?(\d+)", path.stem)]
        if not grades or max(grades) < 6 or min(grades) > 12:
            continue
        for row in jsonl(path):
            if 6 <= row.get("grade", 0) <= 12:
                if row["id"] in manifests:
                    raise ValueError(f"Duplicate source manifest ID: {row['id']}")
                manifests[row["id"]] = row

    sources = {}
    source_files = {}
    for selection in jsonl(selection_path):
        decision = selection.get("decision")
        if decision not in ("selected", "skipped", "needs_review"):
            raise ValueError("Source decision must be selected, skipped or needs_review")
        if decision != "selected":
            continue

        key = selection.get("record_id")
        locator = selection.get("locator")
        if not isinstance(key, str) or not key or not isinstance(locator, dict) or locator.get("record_id") != key:
            raise ValueError("Selected source needs matching record_id and locator.record_id")
        if key in sources:
            raise ValueError(f"Duplicate selected source ID: {key}")
        row = manifests.get(key)
        curated = row is None
        source_path = selection.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            raise ValueError(f"Selected source needs a source path: {key}")
        if curated:
            source_text = selection.get("source_text")
            if not isinstance(source_text, str) or not source_text.strip():
                raise ValueError(f"Curated source needs a verified source_text: {key}")
            expected_path = Path(source_path)
            if not expected_path.is_absolute():
                expected_path = CORPUS / expected_path
            expected_path = expected_path.resolve()
            if expected_path.is_relative_to(CORPUS.resolve()):
                grade_dir = expected_path.relative_to(CORPUS.resolve()).parts[0]
                if grade_dir not in {str(grade) for grade in range(6, 13)}:
                    raise ValueError(f"Source grade is outside 6-12: {key}")
            elif not (expected_path.is_relative_to((ROOT / "Onn_generate").resolve())
                      or expected_path == (ROOT / "[L9CB]_2025_10_10.pdf").resolve()):
                raise ValueError(f"Source path is outside the authorized source roots: {key}")
            if selection.get("grade") is not None and selection["grade"] not in range(6, 13):
                raise ValueError(f"Source grade is outside 6-12: {key}")
            row = {"source_md": source_path, "grade": None, "diagram_types": None, **selection}
            start, end = locator.get("start_line"), locator.get("end_line")
        else:
            if row.get("decision") != "prepared" or not 6 <= row.get("grade", 0) <= 12:
                raise ValueError(f"Selected source is missing from a prepared grade 6-12 manifest: {key}")
            start, end = row.get("start_line"), row.get("end_line")
            if (type(locator.get("start_line")) is not int or type(locator.get("end_line")) is not int
                    or locator["start_line"] != start or locator["end_line"] != end):
                raise ValueError(f"Audit locator does not match the manifest: {key}")
            if _normalized_path(source_path) != _normalized_path(row.get("source_md", "")):
                raise ValueError(f"Audit source path does not match the manifest: {key}")
            expected_path = (CORPUS / row["source_md"]).resolve()
            if not expected_path.is_relative_to(CORPUS.resolve()) or Path(row["source_md"]).parts[0] != str(row["grade"]):
                raise ValueError(f"Source path is outside the declared grade/corpus: {key}")
        if expected_path not in source_files:
            data = expected_path.read_bytes()
            lines = None if expected_path.suffix.lower() == ".pdf" else data.decode("utf-8-sig").splitlines()
            source_files[expected_path] = (lines, hashlib.sha256(data).hexdigest())
        lines, file_digest = source_files[expected_path]
        if file_digest != selection.get("source_sha256"):
            raise ValueError(f"Stale source audit hash: {key}")
        if lines is None:
            if not curated or type(locator.get("page")) is not int or locator["page"] < 1:
                raise ValueError(f"PDF source needs an audited one-based page: {key}")
        else:
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
                raise ValueError(f"Invalid source locator: {key}")
            raw_text = "\n".join(lines[start - 1:end])
            if curated:
                if raw_text != selection.get("raw_source_text"):
                    raise ValueError(f"Stale curated source text: {key}")
            else:
                source_text = raw_text
                if source_text.strip() != row.get("source_text", "").strip():
                    raise ValueError(f"Stale source manifest text: {key}")
        if not isinstance(selection.get("source_group"), str) or not selection["source_group"].strip():
            raise ValueError(f"Selected source needs source_group: {key}")
        manifest_types = row.get("diagram_types") or []
        geometry_types = {f"G{number:02d}" for number in range(1, 18)}
        audited_types = selection.get("diagram_types")
        manifest_codes = [code for code in manifest_types if isinstance(code, str) and code in geometry_types]
        codes = audited_types if audited_types is not None else manifest_codes
        if codes == []:
            codes = None
        if (codes is not None and (not isinstance(codes, list)
                                   or any(not isinstance(code, str) or code not in geometry_types for code in codes))):
            raise ValueError(f"Selected source needs geometry diagram types: {key}")
        source = {**row, **selection, "id": key, "source_text": source_text,
                  "source_md": row["source_md"], "source_path": row["source_md"],
                  "manifest_diagram_types": manifest_types,
                  "audited_diagram_types": audited_types,
                  "diagram_types": codes,
                  "source_group": selection["source_group"],
                  "source": (f"{source_path}:p{locator['page']} ({key})" if lines is None
                             else f"{source_path}:L{start}-{end} ({key})"),
                  "source_sha256": file_digest,
                  "source_text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest()}
        sources[key] = source

    grouped = defaultdict(list)
    for key, source in sources.items():
        grouped[source.get("family") or source["source_group"]].append(key)
    batches = [{"batch_id": family, "problem_ids": sorted(ids)} for family, ids in sorted(grouped.items())]
    return sources, batches, {}


def sample_inputs(items: list[dict], count: int, rng: random.Random, usage: Counter,
                  priority: dict[str, int] | None = None) -> list[dict]:
    """Rotate reference variants while keeping each source family once per call."""
    if count < 1:
        return []
    choices = list(items)
    rng.shuffle(choices)
    groups = Counter()
    for item in choices:
        groups[item["source_group"]] += usage[item["id"]]
    choices.sort(key=lambda item: ((priority or {}).get(item["id"], 0),
                                   groups[item["source_group"]], usage[item["id"]]))
    selected, seen = [], set()
    for item in choices:
        if item["source_group"] not in seen:
            selected.append(item)
            seen.add(item["source_group"])
            if len(selected) == count:
                break
    return selected


def build_contexts(sources: dict[str, dict], batches: list[dict], *, calls: int, rows_per_call: int,
                   task: str, seed: int, existing_instructions: list[dict] | None = None,
                   bases: dict[str, dict] | None = None, source_ids: list[str] | None = None,
                   contexts_per_call: int = 10) -> list[dict]:
    if calls < 1 or rows_per_call < 1 or contexts_per_call < 1 or task not in ("Generate", "Edit", "both"):
        raise ValueError("Positive call/row limits and a supported task are required")
    if task == "both" and min(rows_per_call, contexts_per_call) < 2:
        raise ValueError("Mixed Generate/Edit calls require at least two input and output slots")
    bases = bases or {}
    allowed_source_ids = set(sources if source_ids is None else source_ids)
    if allowed_source_ids - sources.keys():
        raise ValueError("Source scope contains unknown IDs")
    if task in ("Edit", "both") and not bases:
        raise ValueError("Edit instruction authoring requires explicit checked bases")
    eligible_ids = sorted({key for batch in batches for key in batch["problem_ids"]} & allowed_source_ids)
    eligible_bases = [base for base in bases.values() if base.get("task") == "Generate"
                      and base.get("split") not in ("validation", "test")
                      and base.get("provenance", {}).get("parents")
                      and set(base["provenance"]["parents"]) <= set(eligible_ids)]
    if not eligible_ids or (task in ("Edit", "both") and not eligible_bases):
        raise ValueError("No source contexts match the requested scope")
    previous = existing_instructions or []
    source_usage = Counter(parent for row in previous for parent in row.get("provenance", {}).get("parents", []))
    base_usage = Counter(row.get("provenance", {}).get("starting_record_id") for row in previous)
    contexts = []
    for index in range(calls):
        rng = random.Random(seed + index)
        count = min(contexts_per_call, rows_per_call)
        starts = sample_inputs(eligible_bases, count if task == "Edit" else max(1, count // 2), rng, base_usage) if task != "Generate" else []
        chosen = ([row["id"] for row in sample_inputs([sources[key] for key in eligible_ids], count - len(starts), rng, source_usage)]
                  if task != "Edit" else [])
        generate_source_ids = list(chosen)
        source_usage.update(chosen)
        base_usage.update(base["id"] for base in starts)
        chosen = list(dict.fromkeys(chosen + [key for base in starts for key in base["provenance"]["parents"]]))
        selected = [sources[key] for key in chosen]
        ids = {source["id"] for source in selected}
        groups = {source["source_group"] for source in selected}
        history = []
        for row in previous:
            row_parents = set(row.get("provenance", {}).get("parents", []))
            if row_parents & ids or row.get("source_group") in groups:
                history.append({"task": row["task"], "instruction": row["instruction"],
                                "parents": row.get("provenance", {}).get("parents", []),
                                "starting_record_id": row.get("provenance", {}).get("starting_record_id"),
                                "starting_givens": row.get("provenance", {}).get("starting_givens"),
                                "starting_tikz_sha256": row.get("provenance", {}).get("starting_tikz_sha256"),
                                "complete_instruction": row.get("provenance", {}).get("complete_instruction")})
        available_starts = []
        if task in ("Edit", "both"):
            for base in starts:
                base_id = base["id"]
                parents = base.get("provenance", {}).get("parents", [])
                if (base.get("task") == "Generate" and base.get("split") not in ("validation", "test")
                        and parents and set(parents) <= ids):
                    available_starts.append({"id": base_id, "instruction": base["instruction"],
                                             "source_group": base["source_group"], "parents": parents,
                                             "grade": base.get("grade"), "diagram_types": base.get("diagram_types", [])})
        contexts.append({"batch_id": f"mixed-{index:04d}", "seed": seed + index,
                         "rows_requested": rows_per_call,
                         "tasks": ["Generate", "Edit"] if task == "both" else [task],
                         "requested_counts": ({"Generate": (rows_per_call + 1) // 2,
                                               "Edit": rows_per_call // 2}
                                              if task == "both" else {task: rows_per_call}),
                         "sources": selected, "generate_source_ids": generate_source_ids, "existing_instructions": history,
                         "available_starts": available_starts,
                         "request": "Produce distinct, mathematically valid cases from this audited cohort. Choose useful dependency-closed subsets; do not exhaust every auxiliary in the Generate base."})
    return contexts


def instruction_key(row: dict) -> tuple:
    values = (row["instruction"], row.get("current_tikz") or row.get("provenance", {}).get("starting_tikz_sha256"))
    return row["task"], *(" ".join(unicodedata.normalize("NFC", value or "").split()) for value in values)


def author_payload(context: dict) -> list[dict]:
    """Project rich, verified local context into the only fields sent to the model."""
    tasks = set(context["tasks"])
    payload = []
    if "Generate" in tasks:
        payload.extend({"source": source["id"], "source_text": source["source_text"]}
                       for source in context["sources"]
                       if "generate_source_ids" not in context or source["id"] in context["generate_source_ids"])
    if "Edit" in tasks:
        payload.extend({"source": base["id"], "givens": base["instruction"]}
                       for base in context.get("available_starts", []))
    return payload


def case_key(row: dict) -> tuple:
    """Use exact task-input identity; leave semantic similarity to review."""
    return instruction_key(row)


def materialize(batch: InstructionBatch, context: dict, digest: str, trace_id: str, bases: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    rows, rejected = [], []
    available = {source["id"]: source for source in context["sources"]}
    available_starts = {start["id"] for start in context.get("available_starts", [])}
    known_cases = {instruction_key({"task": previous["task"], "instruction": previous["instruction"],
                                    "current_tikz": previous.get("current_tikz"),
                                    "provenance": previous.get("provenance", {
                                        "starting_tikz_sha256": previous.get("starting_tikz_sha256")})})
                   for previous in context.get("existing_instructions", [])}
    for index, item in enumerate(batch.instructions):
        try:
            if item.task not in context["tasks"]:
                raise ValueError("Task is outside the supplied scope")
            if item.task == "Generate":
                if item.source not in available or item.source not in context.get("generate_source_ids", available):
                    raise ValueError("Generate source ID is outside the supplied scope")
                if item.complete_instruction is not None:
                    raise ValueError("Generate complete_instruction must be null")
                parents = [available[item.source]]
                base = None
            else:
                if item.source not in available_starts:
                    raise ValueError("Edit base ID is outside the supplied scope")
                if not item.complete_instruction:
                    raise ValueError("Edit requires a nonempty complete_instruction")
                base = bases.get(item.source)
                if not base or base.get("task") != "Generate" or base.get("split") in ("validation", "test"):
                    raise ValueError("Edit base ID does not resolve to an eligible Generate row")
                parent_ids = base.get("provenance", {}).get("parents", [])
                if not parent_ids or not set(parent_ids) <= available.keys():
                    raise ValueError("Edit base parents are outside the supplied audited source scope")
                parents = [available[key] for key in parent_ids]

            grades = {parent.get("grade") for parent in parents}
            current = None
            if item.task == "Edit":
                current = base.get("target_tikz")
                if not isinstance(current, str) or not current.strip():
                    raise ValueError("Edit base has no actual target TikZ")
                validate_tikz(current)
            source_refs = {parent["id"]: {"source_path": parent.get("source_path", parent.get("source_md")),
                          "source_sha256": parent.get("source_sha256"),
                          "source_text_sha256": parent.get("source_text_sha256"),
                          "locator": parent.get("locator", {"record_id": parent["id"],
                              "start_line": parent.get("start_line"), "end_line": parent.get("end_line")}),
                          "source_kind": parent.get("source_kind"), "book": parent.get("book"),
                          "book_role": parent.get("book_role"), "image_paths": parent.get("image_paths", []),
                          "diagram_types": parent.get("diagram_types"),
                          "source_group": parent["source_group"], "family": parent.get("family")}
                          for parent in parents}
            distinct = {}
            for key in ("source_kind", "book", "book_role"):
                values = {parent.get(key) for parent in parents}
                distinct[key] = next(iter(values)) if len(values) == 1 else None
            parent_ids = [parent["id"] for parent in parents]
            provenance = {"parents": parent_ids,
                          "complete_instruction": item.complete_instruction, "trace_id": trace_id,
                          "context_sha256": digest, "parent_sources": source_refs,
                          "parent_hashes": {parent["id"]: parent.get("source_sha256") for parent in parents}}
            if base:
                provenance.update(starting_record_id=item.source, starting_givens=base["instruction"],
                                  starting_tikz_sha256=hashlib.sha256(current.encode("utf-8")).hexdigest())
            record = {"schema_version": SCHEMA_VERSION,
                      "id": str(uuid5(NAMESPACE_URL, digest + encoded(item.model_dump()))), "task": item.task,
                      "instruction": item.instruction, "current_tikz": current,
                      "source": "; ".join(parent["source"] for parent in parents),
                      "source_path": parents[0].get("source_path", parents[0].get("source_md")),
                      "source_location": source_refs[parents[0]["id"]]["locator"],
                       "source_kind": distinct["source_kind"], "book": distinct["book"],
                       "book_role": distinct["book_role"],
                      "image_paths": list(dict.fromkeys(path for parent in parents for path in parent.get("image_paths", []))),
                      "source_group": base.get("source_group") if base else parents[0]["source_group"],
                      "split": base.get("split") if base else None,
                      "grade": (base.get("grade") if base else grades.pop() if len(grades) == 1 else None),
                      "diagram_types": None,
                      "provenance": provenance,
                      "verification": {"status": "candidate", "reviewed_by": None}}
            exact_key = instruction_key(record)
            if exact_key in known_cases:
                raise ValueError("Repeated exact input")
            known_cases.add(exact_key)
            rows.append(record)
        except ValueError as error:
            rejected.append({"index": index, "draft": item.model_dump(), "reason": str(error)})
    return rows, rejected


def validate_contexts(contexts: list[dict], sources: dict[str, dict], bases: dict[str, dict]) -> None:
    allowed_start_fields = {"id", "instruction", "source_group", "parents", "grade", "diagram_types"}
    for context in contexts:
        task_set = set(context.get("tasks", []))
        if not task_set or task_set - {"Generate", "Edit"}:
            raise ValueError("Context has an invalid task scope")
        selected = context.get("sources", [])
        source_ids = {row.get("id") for row in selected}
        if not selected or source_ids - sources.keys():
            raise ValueError("Context sources are empty or outside the audited pool")
        if any(row != sources[row["id"]] for row in selected):
            raise ValueError("Context source differs from its audited source snapshot")
        if any("target_tikz" in row or "current_tikz" in row or "evaluation_rubric" in row for row in selected):
            raise ValueError("Source context cannot include targets or drawing inputs")
        if any(any(key in row for key in ("target_tikz", "current_tikz", "evaluation_rubric", "verification"))
               for row in context.get("existing_instructions", [])):
            raise ValueError("Instruction history cannot include targets, drawing inputs or review metadata")
        starts = context.get("available_starts", [])
        for start in starts:
            if set(start) != allowed_start_fields:
                raise ValueError("Checked starts may contain only base ID, instruction, parents and classification")
            base = bases.get(start["id"])
            if (not base or base.get("task") != "Generate" or base.get("split") in ("validation", "test")
                    or base.get("instruction") != start["instruction"]
                    or base.get("source_group") != start["source_group"]
                    or base.get("provenance", {}).get("parents") != start["parents"]
                    or not set(start["parents"]) <= source_ids):
                raise ValueError("Checked start does not match an eligible supplied Generate row")
        if "Edit" in task_set and not starts:
            raise ValueError("Edit context requires at least one available Generate base")


def save_instructions(output: Path, checkpoints: list[dict], sources: dict[str, dict]) -> dict:
    """Merge parent families and exact duplicates without certifying mathematical validity."""
    roots = {key: key for key in sources}

    def find(key):
        while roots[key] != key:
            roots[key] = roots[roots[key]]
            key = roots[key]
        return key

    families = {}
    for key, source in sources.items():
        family = source["source_group"]
        if family in families:
            roots[find(key)] = find(families[family])
        families[family] = key
    rows = [dict(row) for result in checkpoints if result["status"] == "completed" for row in result["rows"]]
    used_sources = {parent for row in rows for parent in row["provenance"]["parents"]}
    for row in rows:
        parents = row["provenance"]["parents"]
        for parent in parents[1:]:
            roots[find(parent)] = find(parents[0])
    duplicates = {}
    for row in rows:
        parent = row["provenance"]["parents"][0]
        key = case_key(row)
        if key in duplicates:
            roots[find(parent)] = find(duplicates[key])
        duplicates[key] = parent
    groups = {}
    for key in sources:
        group = find(key)
        groups[group] = min(groups.get(group, sources[key]["source_group"]), sources[key]["source_group"])
    unique = {}
    for row in rows:
        row["source_group"] = groups[find(row["provenance"]["parents"][0])]
        unique.setdefault(case_key(row), row)
    exact_count = len(rows) - len({instruction_key(row) for row in rows})
    splits = {}
    for row in rows:
        if row.get("split") is not None:
            group = row["source_group"]
            if group in splits and splits[group] != row["split"]:
                raise ValueError("Combined parents have conflicting assigned splits")
            splits[group] = row["split"]
    rows = list(unique.values())
    for row in rows:
        row["split"] = splits.get(row["source_group"])
    review_path = output / "supervision.json"
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {"rows": []}
    by_id = {row["id"]: row for record in checkpoints if record["status"] == "completed" for row in record["rows"]}
    held = set()
    for decision in review["rows"]:
        if (decision["id"] not in by_id or decision["decision"] not in ("usable_instruction", "needs_revision")
                or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()):
            raise ValueError("Supervision must identify an existing instruction, decision and reason")
        if decision["decision"] == "needs_revision":
            held.add(case_key(by_id[decision["id"]]))
    eligible = [row for row in rows if case_key(row) not in held]
    save_json(output / "source-groups.json", {key: groups[find(key)] for key in sources})
    caller_inputs = {"Generate": [row for row in eligible if row["task"] == "Generate"],
                     "Edit": [row for row in eligible if row["task"] == "Edit" and row["current_tikz"]]}
    for name, selected in (("instructions", rows), ("generate-inputs", caller_inputs["Generate"]),
                           ("edit-inputs", caller_inputs["Edit"])):
        path = output / f"{name}.jsonl"
        temporary = path.with_suffix(".tmp")
        temporary.write_text("".join(encoded(row) + "\n" for row in selected), encoding="utf-8")
        replace_snapshot(temporary, path)
    summary = {"calls_completed": sum(result["status"] == "completed" for result in checkpoints),
               "calls_failed": sum(result["status"] == "failed" for result in checkpoints),
               "model_calls_reserved": sum(result.get("model_calls_reserved", 0) for result in checkpoints),
               "model_calls_actual": sum(result.get("model_calls_actual", 0) for result in checkpoints),
               "instruction_candidates": dict(Counter(row["task"] for row in rows)),
               "exact_duplicates": exact_count,
               "sources_used": len(used_sources),
               "loaded_sources": len(sources),
               "rejected_instructions": sum(len(result.get("rejected", [])) for result in checkpoints),
               "review_held_instructions": len(held), "caller_inputs": {task: len(items) for task, items in caller_inputs.items()},
               "edit_awaiting_starting_tikz": sum(row["task"] == "Edit" and not row["current_tikz"] for row in eligible),
               "mathematical_review": ("see supervision.json; unreviewed proposals remain pending" if review_path.is_file()
                                       else "pending; schema/source checks are not mathematical approval")}
    save_json(output / "report.json", summary)
    return summary


def generate(contexts: list[dict], output: Path, *, model, sources: dict[str, dict], workers: int = 4,
             resume: bool = False, project: str = "", trace_client=None, bases: dict[str, dict] | None = None) -> dict:
    if not contexts or not 1 <= workers <= 4:
        raise ValueError("Provide contexts and 1-4 workers")
    bases = bases or {}
    validate_contexts(contexts, sources, bases)
    output.mkdir(parents=True, exist_ok=resume)
    policy = PROMPT_PATH.read_text(encoding="utf-8")
    if not policy.startswith(f"# {PROMPT_VERSION}\n"):
        raise ValueError("Instruction prompt version does not match the application schema")
    structured = model.with_structured_output(InstructionBatch, method="function_calling", include_raw=True) if model else None
    records = []
    base_hashes = {key: hashlib.sha256(row["target_tikz"].encode("utf-8")).hexdigest()
                   for key, row in bases.items() if isinstance(row.get("target_tikz"), str)}

    def scope_hash(policy_text, context, model_payload, checked_base_hashes):
        payload = {"prompt_version": PROMPT_VERSION, "policy": policy_text, "context": context,
                   "model_payload": model_payload,
                   "checked_base_hashes": checked_base_hashes,
                   "author_calls_per_context": AUTHOR_CALLS_PER_CONTEXT}
        return hashlib.sha256(encoded(payload).encode("utf-8")).hexdigest()

    marker = output / "instruction-run.json"
    source_digest = hashlib.sha256(encoded(sources).encode("utf-8")).hexdigest()
    run_signature = {"schema_version": SCHEMA_VERSION, "prompt_version": PROMPT_VERSION,
                     "prompt_sha256": hashlib.sha256(policy.encode("utf-8")).hexdigest(),
                     "author_calls_per_context": AUTHOR_CALLS_PER_CONTEXT,
                     "source_sha256": source_digest}
    if marker.is_file():
        saved_signature = json.loads(marker.read_text(encoding="utf-8"))
        if any(saved_signature.get(key) != value for key, value in run_signature.items()
               if key not in ("prompt_version", "prompt_sha256")):
            raise ValueError("Source pool or instruction schema changed; start a new output directory")
    elif any((output / "batches").glob("*/result.json")):
        raise ValueError("Cannot resume legacy instruction checkpoints; preserve them and use a new output directory")
    save_json(marker, run_signature)

    cached_scopes = {}
    if resume:
        for path in (output / "batches").glob("*/result.json"):
            saved = json.loads(path.read_text(encoding="utf-8"))
            records.append(saved)
            key = saved.get("scope_sha256")
            if not key:
                request = json.loads((path.parent / saved["trace_id"] / "request.json").read_text(encoding="utf-8"))
                prior = {"prompt_version": request.get("prompt_version"), "policy": request["system"],
                         "context": request["context"], "model_payload": request.get("model_payload", []),
                         "checked_base_hashes": request.get("checked_base_hashes", {}),
                         "author_calls_per_context": request.get("author_calls_per_context", AUTHOR_CALLS_PER_CONTEXT)}
                if hashlib.sha256(encoded(prior).encode("utf-8")).hexdigest() == saved["context_sha256"]:
                    key = scope_hash(request["system"], request["context"], request.get("model_payload", []),
                                     request.get("checked_base_hashes", {}))
                    saved["scope_sha256"] = key
            if saved["status"] == "completed":
                cached_scopes[key] = saved
    jobs = []
    for context in contexts:
        model_payload = author_payload(context)
        request_limits = [f"For this call, return at most {context['rows_requested']} instructions total."]
        requested_counts = context.get("requested_counts", {})
        if requested_counts:
            request_limits.append("Per-task caps: " + ", ".join(
                f"{task} {count}" for task, count in sorted(requested_counts.items())) + ".")
        system = SystemMessage(content=policy + "\n\n" + " ".join(request_limits))
        payload = {"prompt_version": PROMPT_VERSION, "policy": system.content, "context": context,
                   "model_payload": model_payload,
                   "checked_base_hashes": base_hashes,
                   "author_calls_per_context": AUTHOR_CALLS_PER_CONTEXT}
        digest = hashlib.sha256(encoded(payload).encode("utf-8")).hexdigest()
        scope = scope_hash(system.content, context, model_payload, base_hashes)
        if scope in cached_scopes:
            continue
        directory = output / "batches" / scope
        checkpoint = directory / "result.json"
        if resume and checkpoint.is_file():
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            if saved["status"] == "completed":
                continue
        jobs.append((context, model_payload, system, digest, scope, directory))
    if jobs and structured is None:
        raise ValueError("A CPA model is required for pending batches")

    def call(job):
        context, model_payload, system, digest, scope, directory = job
        trace_id, started = str(uuid4()), perf_counter()
        attempt = directory / trace_id
        save_json(attempt / "request.json", {"prompt_version": PROMPT_VERSION, "system": system.content,
                                               "context": context, "model_payload": model_payload,
                                               "checked_base_hashes": base_hashes,
                                               "author_calls_per_context": AUTHOR_CALLS_PER_CONTEXT})
        record = {"context_sha256": digest, "scope_sha256": scope, "trace_id": trace_id, "status": "failed", "rows": [],
                  "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION,
                  "model_calls_reserved": AUTHOR_CALLS_PER_CONTEXT, "model_calls_actual": 1,
                  "response_format": None,
                  "requested_model": getattr(model, "model_name", None)}
        try:
            with tracing_context(enabled=trace_client is not None, client=trace_client, project_name=project, parent=False):
                result = structured.invoke([system, HumanMessage(content=encoded(model_payload))],
                    config={"run_id": UUID(trace_id), "run_name": "generate_instructions", "tags": ["synthetic-tikz", "instruction-author"],
                            "metadata": {"prompt_version": PROMPT_VERSION}})
            raw = result["raw"]
            save_json(attempt / "response.json", raw.model_dump(mode="json"))
            record.update(usage=raw.usage_metadata, response_metadata=raw.response_metadata)
            parsed = result.get("parsed")
            if isinstance(parsed, InstructionBatch) and result.get("parsing_error") is None:
                batch = parsed
                record["response_format"] = "tool_call"
            elif parsed is None and isinstance(raw.content, str):
                try:
                    batch = parse_instruction_json_text(raw.content)
                except ValidationError as error:
                    raise ValueError(f"Structured output failed: {result.get('parsing_error') or error}") from error
                record["response_format"] = "json_text_fallback"
                if result.get("parsing_error"):
                    record["structured_parser_error"] = str(result["parsing_error"])
            else:
                raise ValueError(f"Structured output failed: {result.get('parsing_error') or 'missing InstructionBatch output'}")
            if len(batch.instructions) > context["rows_requested"]:
                raise ValueError("Response exceeds the declared row scope")
            if any(count > context.get("requested_counts", {}).get(task, context["rows_requested"])
                   for task, count in Counter(item.task for item in batch.instructions).items()):
                raise ValueError("Response exceeds the declared per-task row scope")
            rows, rejected = materialize(batch, context, digest, trace_id, bases or {})
            record.update(status="completed", rows=rows, rejected=rejected)
        except Exception as error:  # noqa: BLE001 -- checkpoint a remote/validation failure; no automatic retry loop
            record["error"] = f"{type(error).__name__}: {error}"
        record["elapsed_seconds"] = round(perf_counter() - started, 3)
        save_json(attempt / "result.json", record)
        save_json(directory / "result.json", record)
        return record

    save_json(output / "sources.json", sources)
    summary = save_instructions(output, records, sources)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(call, job) for job in jobs]):
            result = future.result()
            records = [record for record in records if record.get("scope_sha256", record["context_sha256"])
                       != result["scope_sha256"]]
            records.append(result)
            summary = save_instructions(output, records, sources)
            print(encoded({"trace_id": result["trace_id"], "status": result["status"], "rows": len(result["rows"])}), flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SELECTION,
                        help="Audited selected-source JSONL; only selected rows enter prompts")
    parser.add_argument("--calls", type=int, default=1, help="Explicit maximum CPA calls; no refill/retry loop")
    parser.add_argument("--rows-per-call", type=int, default=24)
    parser.add_argument("--contexts-per-call", type=int, default=10, help="Randomized source/base inputs per call; try 5 or 10")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--task", choices=("Generate", "Edit", "both"), default="Generate")
    parser.add_argument("--source-id", action="append", help="Limit the context to these exact known source IDs")
    parser.add_argument("--bases", type=Path, help="Caller-supplied eligible Generate rows with actual target_tikz for Edit")
    parser.add_argument("--existing", type=Path, action="append", help="Existing instruction JSONL to avoid repeating its mathematical cases")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true", help="Save exact planned contexts without CPA calls")
    parser.add_argument("--review-only", action="store_true", help="Apply supervision and refresh existing caller inputs without model calls")
    args = parser.parse_args()
    if args.calls < 1 or args.rows_per_call < 1 or args.contexts_per_call < 1 or not 1 <= args.workers <= 4:
        parser.error("Positive calls/rows and 1-4 workers are required")
    if args.review_only:
        if args.prepare_only or not (args.output / "sources.json").is_file():
            parser.error("Review requires an existing output with saved sources")
        checkpoints = [json.loads(path.read_text(encoding="utf-8")) for path in (args.output / "batches").glob("*/result.json")]
        if not checkpoints:
            parser.error("No completed/failed batch checkpoints to review")
        report = save_instructions(args.output, checkpoints, json.loads((args.output / "sources.json").read_text(encoding="utf-8")))
        print(encoded(report))
        return int(report["calls_failed"] > 0)
    sources, batches, _ = load_pool(args.sources)
    if not sources:
        parser.error("The audited selection contains no selected sources")
    previous = [row for path in (args.existing or []) for row in load_rows(path)]
    previous.extend(row for path in (args.output / "batches").glob("*/result.json")
                    for row in json.loads(path.read_text(encoding="utf-8")).get("rows", []))
    if args.source_id:
        if set(args.source_id) - sources.keys():
            parser.error("Unknown or review-held source ID")
        batches = [{"batch_id": "explicit-scope", "problem_ids": sorted(set(args.source_id))}]
    bases = {row["id"]: row for row in load_rows(args.bases)} if args.bases else {}
    for base in bases.values():
        if base.get("task") != "Generate" or base.get("split") in ("validation", "test"):
            parser.error("Edit bases must be eligible Generate rows outside held-out splits")
        if not isinstance(base.get("target_tikz"), str) or not base["target_tikz"].strip():
            parser.error("Edit bases need the exact resulting target_tikz")
        validate_tikz(base["target_tikz"])
        parents = base.get("provenance", {}).get("parents", [])
        if not parents or set(parents) - sources.keys():
            parser.error("Starting diagrams require explicit parents from the audited source pool")
    try:
        contexts = build_contexts(sources, batches, calls=args.calls, rows_per_call=args.rows_per_call,
                                  task=args.task, seed=args.seed, existing_instructions=previous,
                                  bases=bases, source_ids=args.source_id, contexts_per_call=args.contexts_per_call)
        validate_contexts(contexts, sources, bases)
    except ValueError as error:
        parser.error(str(error))
    if args.prepare_only:
        if args.output.exists() and not args.resume:
            parser.error("Output directory exists; pass --resume or choose a new output directory")
        args.output.mkdir(parents=True, exist_ok=args.resume)
        save_json(args.output / "sources.json", sources)
        save_json(args.output / "contexts.json", contexts)
        print(encoded({"calls_planned": len(contexts), "loaded_sources": len(sources), "contexts": str(args.output / "contexts.json")}))
        return 0

    model = build_model(timeout=120, max_tokens=16000)
    if not os.environ.get("LANGSMITH_API_KEY") or not os.environ.get("LANGSMITH_PROJECT"):
        raise ValueError("LANGSMITH_API_KEY and LANGSMITH_PROJECT are required")
    client = Client()
    try:
        report = generate(contexts, args.output, model=model, sources=sources, workers=args.workers, resume=args.resume,
                          project=os.environ["LANGSMITH_PROJECT"], trace_client=client, bases=bases)
    finally:
        wait_for_all_tracers()
        client.flush()
        client.close()
    save_json(args.output / "contexts.json", contexts)
    print(encoded(report))
    return int(report["calls_failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
