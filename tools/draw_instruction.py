"""Draw with MathPaper, save live Parquet snapshots and export reviewed pairs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
MATHPAPER = ROOT.parent / "mathmath"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(MATHPAPER / "src"))
sys.path.append(str(ROOT / ".venv/Lib/site-packages"))

import httpx
from agent.latex.tikz import validate_tikz
from PIL import Image


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def review_digest(row: dict) -> str:
    """Bind review to the exact inputs, target/PNG, rubric and source-family lineage."""
    fields = ("task", "instruction", "current_tikz", "target_tikz", "evaluation_rubric",
              "source", "source_group", "provenance", "grade", "diagram_types")
    image = target_image(row)
    payload = {key: row.get(key) for key in fields}
    payload["tikz_image_sha256"] = hashlib.sha256(image["bytes"]).hexdigest() if image else None
    return hashlib.sha256(encoded(payload).encode("utf-8")).hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen, splits = set(), {}
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                           for k in ("id", "instruction", "source", "source_group")):
            raise ValueError("Each row needs nonempty id, instruction, source and source_group")
        if row["id"] in seen or row.get("task") not in ("Generate", "Edit"):
            raise ValueError(f"{row['id']}: duplicate ID or invalid task")
        seen.add(row["id"])
        split = row.get("split")
        if split not in (None, "train", "validation", "test"):
            raise ValueError(f"{row['id']}: invalid split")
        group = row["source_group"]
        if split is not None and group in splits and splits[group] != split:
            raise ValueError(f"{group}: conflicting family splits")
        if split is not None:
            splits[group] = split
        encoded(row)
    if not rows:
        raise ValueError("No input rows")
    return rows


def validate_requests(rows: list[dict]) -> None:
    for row in rows:
        if "base_id" in row:
            raise ValueError(f"{row['id']}: base_id is unsupported; supply actual current_tikz for Edit")
        if "current_tikz" not in row:
            raise ValueError(f"{row['id']}: current_tikz is required (null for Generate)")
        current = row["current_tikz"]
        if row["task"] == "Generate":
            if current is not None:
                raise ValueError(f"{row['id']}: Generate requires null current_tikz")
        else:
            if not isinstance(current, str) or not current.strip():
                raise ValueError(f"{row['id']}: Edit requires complete actual current_tikz")
            validate_tikz(current)


def save_json(path: Path, value: object) -> None:
    """Replace a checkpoint only after its complete JSON has been written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(encoded(value) + "\n", encoding="utf-8")
    temporary.replace(path)


def target_image(row: dict) -> dict | None:
    """Embed only a PNG bound to this exact target by native or compile evidence."""
    target = row.get("target_tikz")
    if not isinstance(target, str) or not target.strip():
        return None
    source_digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
    for origin in ("native", "compiled"):
        if origin == "native":
            if row.get("rendered_tikz_sha256") != source_digest:
                continue
            path, image_digest = row.get("rendered_png_path"), row.get("rendered_png_sha256")
        else:
            review = row.get("verification")
            report_path = review.get("report_path") if isinstance(review, dict) else None
            if not isinstance(report_path, str) or not report_path:
                continue
            try:
                report = json.loads(Path(report_path).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            evidence = report.get("target") if isinstance(report, dict) else None
            if not isinstance(evidence, dict) or not isinstance(evidence.get("artifacts"), dict):
                continue
            artifact = evidence["artifacts"].get("page-1.png")
            if not isinstance(artifact, dict):
                continue
            if (evidence.get("input_tikz_sha256") != source_digest
                    or evidence.get("status") != "needs_review" or not artifact.get("complete")):
                continue
            path, image_digest = artifact.get("path"), artifact.get("sha256")
        if not isinstance(path, str) or not path or not isinstance(image_digest, str) or not image_digest:
            continue
        try:
            data = Path(path).read_bytes()
            if hashlib.sha256(data).hexdigest() != image_digest:
                continue
            with Image.open(BytesIO(data)) as preview:
                if preview.format != "PNG":
                    continue
                preview.verify()
        except (OSError, ValueError):
            continue
        return {"bytes": data, "path": f"{source_digest}.png"}
    return None


def write_parquet(rows: list[dict], path: Path) -> None:
    """Write a closed, readable HF image table, then replace the previous snapshot."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    fields = ("id", "task", "instruction", "current_tikz", "target_tikz", "source", "source_group", "split",
              "grade", "diagram_types")
    schema = pa.schema([(k, pa.string()) for k in fields[:8]] +
                       [("grade", pa.int64()), ("diagram_types", pa.list_(pa.string())),
                        ("evaluation_rubric", pa.string()), ("metadata", pa.string()),
                        ("tikz_image", pa.struct([("bytes", pa.binary()), ("path", pa.string())]))],
                       metadata={"huggingface": encoded({"info": {"features": {"tikz_image": {"_type": "Image"}}}})})
    records = []
    for row in rows:
        image = target_image(row)
        metadata = {k: v for k, v in row.items() if k not in fields and k != "evaluation_rubric"}
        if image:
            metadata.update(target_tikz_sha256=hashlib.sha256(row["target_tikz"].encode("utf-8")).hexdigest(),
                            tikz_image_sha256=hashlib.sha256(image["bytes"]).hexdigest())
        records.append({**{k: row.get(k) for k in fields}, "evaluation_rubric": encoded(row.get("evaluation_rubric")),
                        "metadata": encoded(metadata), "tikz_image": image})
    temporary = path.with_suffix(".parquet.tmp")
    try:
        pq.write_table(pa.Table.from_pylist(records, schema=schema), temporary,
                       compression="zstd", row_group_size=100)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def save_candidates(output: Path, latest: dict[str, dict]) -> None:
    rows = list(latest.values())
    temporary = output / "candidates.tmp"
    temporary.write_text("".join(encoded(row) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(output / "candidates.jsonl")
    # ponytail: rewrite the ~1,500-row snapshot per result; use fragments for much larger runs.
    write_parquet(rows, output / "candidates.parquet")


def saved_rows(output: Path) -> dict[str, dict]:
    path = output / "candidates.jsonl"
    saved = {row["id"]: row for row in load_rows(path)} if path.is_file() and path.stat().st_size else {}
    for checkpoint in (output / "cases").glob("*/candidate.json"):
        row = json.loads(checkpoint.read_text(encoding="utf-8"))
        saved[row["id"]] = row
    return saved


def completed_rows(rows: list[dict], output: Path, *, resume: bool = False,
                   retry_ids: list[str] | None = None) -> dict[str, dict]:
    """Reuse supplied or saved targets; failed/incomplete drawings remain pending."""
    validate_requests(rows)
    retry = set(retry_ids or [])
    if retry - {row["id"] for row in rows}:
        raise ValueError(f"Unknown retry IDs: {sorted(retry - {row['id'] for row in rows})}")
    if output.exists() and not resume:
        raise FileExistsError(f"{output} already exists; use --resume")
    saved = saved_rows(output) if resume else {}
    completed = {}
    keys = ("task", "instruction", "current_tikz", "source", "source_group")
    for row in rows:
        if row["id"] in retry:
            continue
        previous = saved.get(row["id"])
        if previous and any(previous.get(key) != row.get(key) for key in keys):
            continue
        candidate = previous or row
        target = candidate.get("target_tikz")
        if (not isinstance(target, str) or not target.strip() or candidate.get("success") is False
                or candidate.get("drawing_status") in ("failed", "usable_with_issues")):
            continue
        try:
            validate_tikz(target)
        except ValueError:
            continue
        record = {**candidate, **row}
        for key in ("target_tikz", "success", "drawing_status", "trace_id", "artifact_dir",
                    "rendered_png_path", "rendered_tikz_sha256", "rendered_png_sha256",
                    "unresolved_issues", "elapsed_seconds", "session_dir"):
            if key in candidate:
                record[key] = candidate[key]
        record.setdefault("success", None)
        record.setdefault("drawing_status", "provided_target")
        record.setdefault("verification", {"status": "candidate", "reviewed_by": None})
        completed[row["id"]] = record
    return completed


def draw_batch(rows: list[dict], output: Path, *, agent, compiler_http: httpx.Client | None,
               workers: int = 4, project: str = "", trace_client=None, run_metadata: dict | None = None,
               resume: bool = False, retry_ids: list[str] | None = None) -> list[dict]:
    """Draw independent rows using only their explicit instruction and starting TikZ."""
    from agent.workflows.problem_tikz import problem_tikz
    from langsmith import tracing_context

    outcomes = completed_rows(rows, output, resume=resume, retry_ids=retry_ids)
    latest = saved_rows(output) if resume else {}
    pending = [row for row in rows if row["id"] not in outcomes]
    if workers < 1:
        raise ValueError("workers must be positive")
    # ponytail: one process per run directory; add a file lock if separate processes share it.
    output.mkdir(parents=True, exist_ok=resume)
    session = output / "sessions" / uuid4().hex
    session.mkdir(parents=True)
    inputs = "".join(encoded(row) + "\n" for row in rows).encode("utf-8")
    (output / "inputs.jsonl").write_bytes(inputs)
    (session / "inputs.jsonl").write_bytes(inputs)
    profile = []
    modules = ("agent.prompts.tikz", "agent.prompts.problem_tikz", "agent.latex.tikz",
               "agent.workflows.problem_tikz", "agent.workflows.tikz", "agent.schemas.tikz")
    paths = [Path(sys.modules[name].__file__) for name in modules] + [ROOT / "tools/cpa.py", Path(__file__)]
    for path in paths:
        data = path.read_bytes()
        snapshot = session / "harness" / path.relative_to(MATHPAPER if path.is_relative_to(MATHPAPER) else ROOT)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
        profile.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
    report = {**(run_metadata or {}), "rows": len(rows), "workers": workers,
              "pending_rows": len(pending), "skipped_rows": len(outcomes), "session_dir": str(session),
              "langsmith_project": project, "harness_files": profile,
              "tikz_prompt_version": sys.modules["agent.prompts.tikz"].TIKZ_PROMPT_VERSION,
              "task_prompt_version": sys.modules["agent.prompts.problem_tikz"].PROBLEM_TIKZ_PROMPT_VERSION,
              "input_sha256": hashlib.sha256(inputs).hexdigest()}
    save_json(session / "report.json", report)
    save_json(output / "report.json", report)
    if not pending:
        report["max_model_calls_total"] = 0

    def draw_one(row: dict) -> dict:
        record = {**row, "current_tikz": row.get("current_tikz"), "target_tikz": "",
                  "success": False, "rendered_png_path": None, "unresolved_issues": [],
                  "rendered_tikz_sha256": None, "rendered_png_sha256": None,
                  "verification": {"status": "candidate", "reviewed_by": None}}
        trace_id, started = uuid4(), perf_counter()
        case = output / "cases" / hashlib.sha256(row["id"].encode("utf-8")).hexdigest()
        directory = case / str(trace_id)
        directory.mkdir(parents=True)
        record.update(trace_id=str(trace_id), artifact_dir=str(directory), session_dir=str(session))
        try:
            with tracing_context(enabled=trace_client is not None, client=trace_client,
                                 project_name=project, parent=False):
                configured = agent.with_config(run_id=trace_id, tags=["synthetic-tikz"],
                                               metadata={"record_id": row["id"], "source_group": row["source_group"]})
                result = problem_tikz(instruction=row["instruction"], current_tikz=record["current_tikz"],
                                      artifact_dir=directory, agent=configured, compiler_http=compiler_http)
            record.update(success=result.success, drawing_status=result.status, target_tikz=result.tikz,
                          rendered_png_path=result.rendered_png_path, unresolved_issues=result.unresolved_issues)
            if result.tikz and result.rendered_png_path:
                record.update(rendered_tikz_sha256=hashlib.sha256(result.tikz.encode("utf-8")).hexdigest(),
                              rendered_png_sha256=hashlib.sha256(Path(result.rendered_png_path).read_bytes()).hexdigest())
        except Exception as error:  # noqa: BLE001 -- preserve one remote failure without discarding the batch
            record.update(success=False, drawing_status="failed", rendered_png_path=None,
                          rendered_tikz_sha256=None, rendered_png_sha256=None,
                          unresolved_issues=[f"{type(error).__name__}: {error}"])
        record["elapsed_seconds"] = round(perf_counter() - started, 3)
        save_json(directory / "candidate.json", record)
        save_json(case / "candidate.json", record)
        return record

    for record in outcomes.values():
        case = output / "cases" / hashlib.sha256(record["id"].encode("utf-8")).hexdigest()
        save_json(case / "candidate.json", record)
        print(encoded({"id": record["id"], "drawing_status": "skipped_existing_target"}), flush=True)
    latest.update(outcomes)
    save_candidates(output, latest)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = [pool.submit(draw_one, row) for row in pending]
        for job in as_completed(jobs):
            record = job.result()
            outcomes[record["id"]] = record
            latest[record["id"]] = record
            save_candidates(output, latest)
            print(encoded({"id": record["id"], "drawing_status": record["drawing_status"]}), flush=True)
    report["counts"] = dict(Counter(row["drawing_status"] for row in outcomes.values()))
    save_json(session / "report.json", report)
    save_json(output / "report.json", report)
    return [outcomes[row["id"]] for row in rows]


def export_rows(rows: list[dict], output: Path) -> dict:
    """Export reviewed pairs only; never infer readiness from drawing completion."""
    seen = set()
    for row in rows:
        review = row.get("verification", {})
        if (not isinstance(review, dict) or review.get("status") != "ready"
                or not isinstance(review.get("reviewed_by"), str) or not review["reviewed_by"].strip()
                or review.get("reviewed_input_sha256") != review_digest(row)):
            raise ValueError(f"{row['id']}: missing review or changed instruction/target/rubric")
        if row.get("split") is None or not isinstance(row.get("evaluation_rubric"), list):
            raise ValueError(f"{row['id']}: assigned split and fixed rubric required")
        grade, types = row.get("grade"), row.get("diagram_types")
        if (grade is not None and (type(grade) is not int or not 6 <= grade <= 12)
                or not isinstance(types, list) or not types
                or any(not isinstance(code, str) or code not in {f"G{n:02d}" for n in range(1, 18)} for code in types)):
            raise ValueError(f"{row['id']}: invalid grade or diagram_types")
        if not isinstance(row.get("target_tikz"), str) or not row["target_tikz"].strip():
            raise ValueError(f"{row['id']}: complete target_tikz required")
        validate_tikz(row["target_tikz"])
        if target_image(row) is None:
            raise ValueError(f"{row['id']}: a verified PNG for this exact target_tikz is required")
        current = row.get("current_tikz")
        if row["task"] == "Generate" and current is not None:
            raise ValueError(f"{row['id']}: Generate has starting TikZ")
        if row["task"] == "Edit":
            if not isinstance(current, str) or not current.strip() or current == row["target_tikz"]:
                raise ValueError(f"{row['id']}: Edit needs an actual changed starting/ending pair")
            validate_tikz(current)
        key = tuple(row.get(k) for k in ("task", "instruction", "current_tikz", "target_tikz"))
        if key in seen:
            raise ValueError(f"{row['id']}: duplicate task/input/target")
        seen.add(key)
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for task in ("Generate", "Edit"):
        for split in ("train", "validation", "test"):
            selected = [row for row in rows if row["task"] == task and row["split"] == split]
            if not selected:
                continue
            path = output / task.lower() / f"{split}.parquet"
            path.parent.mkdir(exist_ok=True)
            write_parquet(selected, path)
            files[str(path)] = len(selected)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Explicit task-input JSONL, or reviewed JSONL with --export")
    parser.add_argument("--output", required=True, type=Path, help="Run directory; export requires a fresh directory")
    parser.add_argument("--resume", action="store_true", help="Reuse completed targets and retry failed/incomplete rows")
    parser.add_argument("--retry-id", action="append", help="Redraw this ID even if it has a completed target; may repeat")
    parser.add_argument("--export", action="store_true", help="Export ready reviewed pairs; no model calls")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-model-calls", type=int, default=4)
    parser.add_argument("--limit", type=int, default=128, help="Maximum pending rows to draw in this invocation")
    parser.add_argument("--compiler-url", default=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"))
    args = parser.parse_args()
    try:
        rows = load_rows(args.input)
        if args.export:
            print(encoded(export_rows(rows, args.output.resolve())))
            return 0
        validate_requests(rows)
        if not 1 <= args.workers <= 4 or not 2 <= args.max_model_calls <= 4:
            raise ValueError("workers must be 1-4; max-model-calls must be 2-4")
        complete = completed_rows(rows, args.output.resolve(), resume=args.resume, retry_ids=args.retry_id)
        if args.limit < 1 or len(rows) - len(complete) > args.limit:
            raise ValueError(f"Pending rows exceed the declared drawing budget ({args.limit})")
        if len(complete) == len(rows):
            draw_batch(rows, args.output.resolve(), agent=None, compiler_http=None, workers=args.workers,
                       resume=args.resume, retry_ids=args.retry_id)
            print((args.output / "report.json").read_text(encoding="utf-8"))
            return 0
        from agent.workflows.tikz import build_tikz_agent
        from cpa import build_model
        from langchain_core.tracers.langchain import wait_for_all_tracers
        from langsmith import Client

        model = build_model()
        if not os.environ.get("LANGSMITH_API_KEY") or not os.environ.get("LANGSMITH_PROJECT"):
            raise ValueError("Configured LANGSMITH_API_KEY and LANGSMITH_PROJECT are required")
        agent = build_tikz_agent(model, max_model_calls=args.max_model_calls)
        endpoint = urlsplit(str(model.openai_api_base))
        safe_endpoint = endpoint._replace(netloc=endpoint.netloc.rsplit("@", 1)[-1], query="", fragment="").geturl()
        client = Client()
        try:
            with httpx.Client(base_url=args.compiler_url, timeout=150, trust_env=False) as compiler:
                ready = compiler.get("/readyz")
                ready.raise_for_status()
                result = draw_batch(rows, args.output.resolve(), agent=agent, compiler_http=compiler,
                                    workers=args.workers, project=os.environ["LANGSMITH_PROJECT"], trace_client=client,
                                    resume=args.resume, retry_ids=args.retry_id,
                                    run_metadata={"max_model_calls_per_row": args.max_model_calls,
                                                  "max_model_calls_total": (len(rows) - len(complete)) * args.max_model_calls,
                                                  "row_budget": args.limit, "model": model.model_name,
                                                  "provider_endpoint": safe_endpoint,
                                                  "packages": {name: version(name) for name in
                                                               ("langchain", "langchain-core", "langgraph", "langsmith", "langchain-openai", "openai")},
                                                  "toolchain_id": ready.json().get("toolchain_id")})
            wait_for_all_tracers()
            client.flush()
        finally:
            client.close()
        output = args.output.resolve()
        print((output / "report.json").read_text(encoding="utf-8"))
        return int(any(row.get("success") is False for row in result))
    except (OSError, ValueError, ImportError, httpx.HTTPError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
