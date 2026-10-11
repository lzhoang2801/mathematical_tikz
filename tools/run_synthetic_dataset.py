"""Resume bounded source-grounded Generate/Edit production with the existing drawing harness."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from tools import draw_instruction as drawing
from tools import generate_instruction as author
from tools.cpa import build_model


def write_rows(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text("".join(drawing.encoded(row) + "\n" for row in rows), encoding="utf-8")
    drawing.replace_snapshot(temporary, path)


def excluded_ids(output: Path) -> set[str]:
    path = output / "excluded.jsonl"
    return {row["id"] for row in drawing.load_rows(path)} if path.is_file() and path.stat().st_size else set()


def completed(row: dict) -> bool:
    return (row.get("success") is True and row.get("verification", {}).get("status") not in
            ("needs_revision", "needs_review", "rejected") and drawing.target_image(row) is not None)


def derive_generate(edit: dict) -> dict:
    """Reuse an Edit's exact target with its separately authored complete givens."""
    instruction = edit["provenance"]["complete_instruction"]
    drawing.validate_instruction(instruction)
    row = {**edit, "id": str(uuid5(NAMESPACE_URL, "Generate:" + edit["id"] + ":" + instruction)),
           "task": "Generate", "instruction": instruction, "current_tikz": None,
           "provenance": {**edit["provenance"], "derived_from_edit": edit["id"]},
           "verification": {"status": "candidate", "reviewed_by": None}}
    return row


def coverage_first(rows: list[dict]) -> list[dict]:
    """Retain a representative of every parent record before filling a capped export."""
    representatives, remaining, covered = [], [], set()
    for row in rows:
        parents = set(row.get("provenance", {}).get("parents", []))
        if parents - covered:
            representatives.append(row)
            covered.update(parents)
        else:
            remaining.append(row)
    return representatives + remaining


def source_coverage(tasks: dict[str, list[dict]], source_ids) -> dict:
    selected = set(source_ids)
    missing = {task: sorted(selected - {parent for row in rows
               for parent in row.get("provenance", {}).get("parents", [])}) for task, rows in tasks.items()}
    return {"selected": len(selected), "covered": {task: len(selected) - len(ids) for task, ids in missing.items()},
            "missing": missing}


def collect(rows: list[dict], generate_goal: int, edit_goal: int,
            excluded: set[str] | None = None, *, cover_all_sources: bool = False) -> tuple[list[dict], list[dict]]:
    excluded = excluded or set()
    good = [row for row in rows if completed(row)]
    edits = [row for row in good if row["task"] == "Edit" and row["current_tikz"] != row["target_tikz"]]
    generated = [row for row in good if row["task"] == "Generate"]
    generated.extend(derive_generate(row) for row in edits if row.get("provenance", {}).get("complete_instruction"))
    unique_generate, unique_edit = {}, {}
    for row in generated:
        if row["id"] not in excluded:
            unique_generate.setdefault(author.case_key(row), row)
    for row in edits:
        if row["id"] not in excluded:
            unique_edit.setdefault(author.case_key(row), row)
    generated, edits = list(unique_generate.values()), list(unique_edit.values())
    if cover_all_sources:
        generated, edits = coverage_first(generated), coverage_first(edits)
    return generated[:generate_goal], edits[:edit_goal]


def write_review(output: Path, rows: list[dict], latest: dict[str, dict]) -> None:
    cards = []
    for row in rows:
        before = ""
        if row["task"] == "Edit":
            base = latest.get(row["provenance"].get("starting_record_id"))
            if base and base.get("rendered_png_path"):
                before = f'<figure><figcaption>Before</figcaption><img src="{html.escape(Path(base["rendered_png_path"]).as_uri())}"></figure>'
        image = html.escape(Path(row["rendered_png_path"]).as_uri())
        cards.append(f'<article><h2>{html.escape(row["task"])} · {html.escape(row["id"])}</h2>'
                     f'<p>{html.escape(row["instruction"])}</p><p>{html.escape(row["source"])}</p>'
                     f'{before}<figure><figcaption>Target</figcaption><img src="{image}"></figure>'
                     f'<details><summary>TikZ</summary><pre>{html.escape(row["target_tikz"])}</pre></details></article>')
    (output / "review.html").write_text('<!doctype html><meta charset="utf-8"><title>Synthetic TikZ review</title>'
        '<style>body{font:16px system-ui;margin:2rem}article{border-bottom:1px solid #ccc;padding:1rem 0}'
        'figure{display:inline-block;vertical-align:top;margin:1rem}img{max-width:560px;max-height:430px}pre{white-space:pre-wrap}</style>'
        '<h1>Candidate review</h1><p>Compilation is recorded; independent mathematical review is separate.</p>' + "\n".join(cards), encoding="utf-8")


def snapshot(output: Path, state: dict, latest: dict[str, dict]) -> dict:
    excluded = excluded_ids(output)
    generated, edits = collect(list(latest.values()), state["generate"], state["edit"], excluded,
                               cover_all_sources=state.get("cover_all_sources", False))
    for name, rows in (("generate", generated), ("edit", edits)):
        write_rows(output / f"{name}.jsonl", rows)
        drawing.write_parquet(rows, output / f"{name}.parquet")
    failures = [row for row in latest.values() if not completed(row)]
    write_rows(output / "failures.jsonl", failures)
    ready = sum(row.get("verification", {}).get("status") == "ready" and
                row["verification"].get("reviewed_input_sha256") == drawing.review_digest(row)
                for row in generated + edits)
    report = {"schema_version": "synthetic-tikz:v2", "requested": {"Generate": state["generate"], "Edit": state["edit"]},
              "completed_candidates": {"Generate": len(generated), "Edit": len(edits)},
              "independently_reviewed": ready, "source_families": len({row["source_group"] for row in generated + edits}),
              "derived_generate": sum("derived_from_edit" in row.get("provenance", {}) for row in generated),
              "cover_all_sources": state.get("cover_all_sources", False),
              "source_coverage": source_coverage({"Generate": generated, "Edit": edits}, state.get("source_hashes", {})),
              "author_calls_reserved": state["author_calls"], "drawing_attempts_reserved": sum(state["drawing_attempts"].values()),
              "failed_or_held_drawings": len(failures), "excluded_candidates": len(excluded),
              "status": state.get("status", "running"),
              "model": state.get("model"), "langsmith_project": state.get("project"),
              "elapsed_seconds": state.get("elapsed_seconds", 0),
              "review_note": "Completed candidates have exact compiled previews; mathematical/source review and splits remain explicit."}
    drawing.save_json(output / "report.json", report)
    write_review(output, generated + edits, latest)
    return report


def make_context(sources: dict[str, dict], latest: dict[str, dict], history: list[dict], state: dict,
                 batch_size: int, contexts_per_call: int = 10,
                 excluded: set[str] | None = None) -> tuple[dict, dict[str, dict]]:
    """Choose least-used sources/bases; the model supplies mathematics, never scheduling."""
    excluded = excluded or set()
    bases = [row for row in latest.values() if row["task"] == "Generate" and row["id"] not in excluded
             and completed(row) and row.get("split") not in ("validation", "test")]
    generated, edits = collect(list(latest.values()), state["generate"], state["edit"], excluded,
                               cover_all_sources=state.get("cover_all_sources", False))
    cover_all = state.get("cover_all_sources", False)
    base_counts = Counter(parent for row in bases for parent in row["provenance"]["parents"])
    edit_counts = Counter(parent for row in edits for parent in row["provenance"]["parents"])
    missing_bases = set(sources) - base_counts.keys() if cover_all else set()
    missing_edits = set(sources) - edit_counts.keys() if cover_all else set()
    task = "Generate" if (len(bases) < state["base_count"] or missing_bases
                          or (len(edits) >= state["edit"] and not missing_edits)) else "Edit"
    rng = random.Random(state["seed"] + state["round"])
    selected_bases = {}
    if task == "Generate":
        usage = Counter(parent for row in history for parent in row.get("provenance", {}).get("parents", []))
        remaining = (max(state["base_count"] - len(bases), len(missing_bases))
                     if len(bases) < state["base_count"] or missing_bases else state["generate"] - len(generated))
        requested = min(batch_size, remaining)
        chosen = [row["id"] for row in author.sample_inputs(list(sources.values()), min(contexts_per_call, requested),
                  rng, usage, priority=base_counts if cover_all else None)]
    else:
        usage = Counter(row.get("provenance", {}).get("starting_record_id") for row in history if row["task"] == "Edit")
        requested = min(batch_size, max(state["edit"] - len(edits), len(missing_edits)))
        priority = {row["id"]: min(edit_counts[parent] for parent in row["provenance"]["parents"])
                    for row in bases} if cover_all else None
        selected_bases = {row["id"]: row for row in author.sample_inputs(bases, min(contexts_per_call, requested),
                          rng, usage, priority=priority)}
        chosen = list(dict.fromkeys(parent for row in selected_bases.values() for parent in row["provenance"]["parents"]))
    context = {"batch_id": f"production-{state['round']:04d}", "seed": state["seed"] + state["round"],
               "rows_requested": requested, "tasks": [task], "requested_counts": {task: requested},
               "sources": [sources[key] for key in chosen],
               "available_starts": [{"id": row["id"], "instruction": row["instruction"],
                                   "source_group": row["source_group"], "parents": row["provenance"]["parents"],
                                   "grade": row.get("grade"), "diagram_types": row.get("diagram_types")}
                                  for row in selected_bases.values()],
               "existing_instructions": [{"task": row["task"], "instruction": row["instruction"],
                                           "starting_givens": row.get("provenance", {}).get("starting_givens")}
                                          for row in history if set(row.get("provenance", {}).get("parents", [])) & set(chosen)],
               "request": "Produce several distinct mathematical instructions for each supplied input, up to the total requested. Use purposeful auxiliary constructions; return the full resulting givens alongside each Edit."}
    return context, selected_bases


def run(args, *, model, agent, compiler, trace_client) -> dict:
    output = args.output.resolve()
    sources, _, _ = author.load_pool(args.sources)
    if not sources:
        raise ValueError("No selected source is available")
    harness = {name: hashlib.sha256((drawing.MATHPAPER / "src/agent" / name).read_bytes()).hexdigest()
               for name in ("prompts/tikz.py", "prompts/problem_tikz.py", "latex/tikz.py",
                            "workflows/tikz.py", "workflows/problem_tikz.py", "schemas/tikz.py")}
    fingerprint = {"sources": hashlib.sha256(drawing.encoded(sources).encode()).hexdigest(),
                   "prompt": hashlib.sha256((ROOT / "tools/instruction_prompt.md").read_bytes()).hexdigest(),
                   "harness": harness, "model": getattr(model, "model_name", None),
                   "max_model_calls": args.max_model_calls}
    source_hashes = {key: hashlib.sha256(drawing.encoded(value).encode()).hexdigest() for key, value in sources.items()}
    output.mkdir(parents=True, exist_ok=args.resume)
    state_path = output / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {
        "fingerprint": fingerprint, "source_hashes": source_hashes, "seed": args.seed, "base_count": args.base_count,
        "generate": args.generate, "edit": args.edit, "round": 0, "pending": None,
        "author_calls": 0, "drawing_attempts": {}, "elapsed_seconds": 0}
    if (any(state["fingerprint"].get(key) != value for key, value in fingerprint.items() if key not in ("prompt", "sources"))
            or state["seed"] != args.seed or args.base_count < state["base_count"]):
        raise ValueError("Drawing harness/model, seed changed or base count decreased")
    previous_sources = state.get("source_hashes")
    if previous_sources is None:
        if state["fingerprint"]["sources"] != fingerprint["sources"]:
            raise ValueError("Source pool changed without a saved source snapshot")
        previous_sources = source_hashes
    if any(source_hashes.get(key) != digest for key, digest in previous_sources.items()):
        raise ValueError("Previously selected source changed or was removed; keep its original audited text")
    cover_all = state.get("cover_all_sources", False) or getattr(args, "cover_all_sources", False)
    if cover_all and min(args.generate, args.edit) < len(sources):
        raise ValueError("Full source coverage requires each task quota to be at least the selected source count")
    state.update(source_hashes=source_hashes, base_count=args.base_count, cover_all_sources=cover_all)
    prompt_history = state.setdefault("prompt_history", [state["fingerprint"]["prompt"]])
    if prompt_history[-1] != fingerprint["prompt"]:
        prompt_history.append(fingerprint["prompt"])
    state["fingerprint"] = fingerprint
    state.update(generate=args.generate, edit=args.edit, model=getattr(model, "model_name", None),
                 project=os.environ.get("LANGSMITH_PROJECT", state.get("project", "")), status="running")
    started = perf_counter()
    drawings = output / "drawings"
    latest = drawing.saved_rows(drawings)
    excluded = excluded_ids(output)

    def draw(rows):
        remaining = args.max_draw_attempts - sum(state["drawing_attempts"].values())
        if len(rows) > remaining:
            rows = rows[:remaining]
        if not rows:
            return
        for row in rows:
            state["drawing_attempts"][row["id"]] = state["drawing_attempts"].get(row["id"], 0) + 1
        drawing.save_json(state_path, state)  # Reserve before remote calls, including an interrupted attempt.
        outcomes = drawing.draw_batch(rows, drawings, agent=agent, compiler_http=compiler,
            workers=args.workers, project=state["project"], trace_client=trace_client, resume=drawings.exists(),
            run_metadata={"model": state["model"], "max_model_calls_per_row": args.max_model_calls,
                          "max_model_calls_total": len(rows) * args.max_model_calls,
                          "compiler_concurrency": args.compiler_concurrency})
        latest.update({row["id"]: row for row in outcomes})

    try:
        while True:
            report = snapshot(output, state, latest)
            if (all(report["completed_candidates"][task] >= goal for task, goal in report["requested"].items())
                    and (not cover_all or not any(report["source_coverage"]["missing"].values()))):
                state["status"] = "candidate_quota_met"
                break
            if sum(state["drawing_attempts"].values()) >= args.max_draw_attempts:
                state["status"] = "drawing_budget_exhausted"
                break
            retry = [row for row in latest.values() if row["id"] not in excluded and row.get("success") is False
                     and row.get("verification", {}).get("status") not in ("needs_review", "needs_revision", "rejected")
                     and state["drawing_attempts"].get(row["id"], 0) < 2]
            if retry:
                draw(retry[:args.batch_size])
                continue
            history = [row for path in sorted((output / "rounds").glob("*/author/instructions.jsonl")) for row in author.jsonl(path)]
            if state["pending"] is None:
                if state["author_calls"] >= args.max_author_calls:
                    state["status"] = "author_budget_exhausted"
                    break
                state["round"] += 1
                context, bases = make_context(sources, latest, history, state, args.batch_size,
                                              args.contexts_per_call, excluded)
                plan = output / "rounds" / f"{state['round']:04d}" / "plan.json"
                drawing.save_json(plan, {"context": context, "bases": bases})
                state["pending"] = str(plan)
                drawing.save_json(state_path, state)
            plan = Path(state["pending"])
            saved = json.loads(plan.read_text(encoding="utf-8"))
            if set(saved.get("bases", {})) & excluded:
                state["pending"] = None
                drawing.save_json(state_path, state)
                continue
            authored = plan.parent / "author"
            checkpoints = list((authored / "batches").glob("*/result.json"))
            if any(json.loads(path.read_text(encoding="utf-8"))["status"] == "completed" for path in checkpoints):
                author.save_instructions(authored, [json.loads(path.read_text(encoding="utf-8")) for path in checkpoints], sources)
            else:
                if state["author_calls"] >= args.max_author_calls:
                    state["status"] = "author_budget_exhausted"
                    break
                state["author_calls"] += 1
                drawing.save_json(state_path, state)
                saved_sources = authored / "sources.json"
                call_sources = json.loads(saved_sources.read_text(encoding="utf-8")) if saved_sources.is_file() else sources
                author.generate([saved["context"]], authored, model=model, sources=call_sources, workers=1,
                                resume=authored.exists(), project=state["project"], trace_client=trace_client,
                                bases=saved["bases"])
            author_report = json.loads((authored / "report.json").read_text(encoding="utf-8"))
            if author_report["calls_failed"] and not author_report["calls_completed"]:
                state["status"] = "author_failed"
                break  # Resume retries this saved context after the provider/output issue is fixed.
            proposed = [row for name in ("generate-inputs.jsonl", "edit-inputs.jsonl")
                        for row in author.jsonl(authored / name)]
            known = {author.case_key(row) for row in latest.values()}
            pending = []
            for row in proposed:
                if row["id"] in excluded:
                    continue
                if row["id"] in latest and completed(latest[row["id"]]):
                    continue
                if latest.get(row["id"], {}).get("verification", {}).get("status") in ("needs_review", "needs_revision", "rejected"):
                    continue
                key = author.case_key(row)
                if key in known and row["id"] not in latest:
                    continue
                known.add(key)
                if state["drawing_attempts"].get(row["id"], 0) < 2:
                    pending.append(row)
            draw(pending)
            if not any(row["id"] not in latest for row in pending):
                state["pending"] = None
            drawing.save_json(state_path, state)
    finally:
        state["elapsed_seconds"] += round(perf_counter() - started, 3)
        drawing.save_json(state_path, state)
        report = snapshot(output, state, latest)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "dataset/audit_givens/selection.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "dataset/synthetic")
    parser.add_argument("--generate", type=int, default=50)
    parser.add_argument("--edit", type=int, default=50)
    parser.add_argument("--base-count", type=int, default=20)
    parser.add_argument("--cover-all-sources", action="store_true",
                        help="Require every selected source in both task exports; persists on resume")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--contexts-per-call", type=int, default=10, help="Randomized source/base inputs per call; try 5 or 10")
    parser.add_argument("--max-author-calls", type=int, default=30)
    parser.add_argument("--max-draw-attempts", type=int, default=150)
    parser.add_argument("--max-model-calls", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--compiler-concurrency", type=int, default=2)
    parser.add_argument("--compiler-url", default=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"))
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if (min(args.generate, args.edit, args.base_count, args.batch_size, args.contexts_per_call, args.max_author_calls, args.max_draw_attempts) < 1
            or args.base_count > args.generate or not 1 <= args.workers <= 32
            or not 1 <= args.compiler_concurrency <= 2 or not 2 <= args.max_model_calls <= 4):
        parser.error("Positive quotas/budgets, base-count <= Generate, workers 1-32, compiler 1-2 and model calls 2-4 required")
    from agent.workflows.tikz import build_tikz_agent
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langsmith import Client
    import httpx

    model = build_model(timeout=300, max_tokens=32000)
    if not os.environ.get("LANGSMITH_API_KEY") or not os.environ.get("LANGSMITH_PROJECT"):
        raise ValueError("LangSmith credentials and project are required")
    client = Client()
    try:
        with drawing.CompilerClient(concurrency=args.compiler_concurrency, base_url=args.compiler_url, timeout=150,
                trust_env=False, limits=httpx.Limits(max_connections=args.compiler_concurrency,
                                                    max_keepalive_connections=args.compiler_concurrency)) as compiler:
            compiler.get("/readyz").raise_for_status()
            report = run(args, model=model, agent=build_tikz_agent(model, max_model_calls=args.max_model_calls),
                         compiler=compiler, trace_client=client)
    finally:
        wait_for_all_tracers()
        client.flush()
        client.close()
    print(drawing.encoded(report), flush=True)
    return 0 if report["status"] == "candidate_quota_met" else 2


if __name__ == "__main__":
    raise SystemExit(main())
