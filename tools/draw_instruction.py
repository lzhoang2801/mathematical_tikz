"""Draw with the local native harness, save snapshots and export reviewed pairs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import perf_counter, sleep
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.append(str(ROOT / ".venv/Lib/site-packages"))

import httpx
from agent.latex.tikz import validate_tikz
from PIL import Image


class CompilerClient(httpx.Client):
    """Queue locally before the native compiler client's three-second pool deadline."""

    def __init__(self, *, concurrency: int, **kwargs):
        super().__init__(**kwargs)
        self._slots = BoundedSemaphore(concurrency)

    @contextmanager
    def stream(self, *args, **kwargs):
        with self._slots, super().stream(*args, **kwargs) as response:
            yield response


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def review_digest(row: dict) -> str:
    """Bind review to the exact inputs, target/PNG, rubric and source-family lineage."""
    fields = ("task", "instruction", "current_tikz", "target_tikz", "image", "evaluation_rubric",
              "source", "source_group", "provenance", "grade", "diagram_types")
    image = target_image(row)
    payload = {key: row.get(key) for key in fields}
    if row.get("review_evidence") is not None:
        payload["review_evidence"] = row["review_evidence"]
    if row.get('current_render') is not None:
        payload['current_render'] = row['current_render']
        current = target_image({**row['current_render'], 'target_tikz': row.get('current_tikz')})
        payload['current_image_sha256'] = hashlib.sha256(current['bytes']).hexdigest() if current else None
    payload["tikz_image_sha256"] = hashlib.sha256(image["bytes"]).hexdigest() if image else None
    if row.get("task") == "Reconstruct":
        source = source_image(row)
        payload["source_image_sha256"] = hashlib.sha256(source["bytes"]).hexdigest() if source else None
    return hashlib.sha256(encoded(payload).encode("utf-8")).hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen, splits = set(), {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("Each row needs a nonempty id")
        if row["id"] in seen or row.get("task") not in ("Generate", "Edit", "Reconstruct"):
            raise ValueError(f"{row['id']}: duplicate ID or invalid task")
        seen.add(row["id"])
        if row["task"] != "Reconstruct":
            validate_instruction(row.get("instruction"))
        split = row.get("split")
        if split not in (None, "train", "validation", "test"):
            raise ValueError(f"{row['id']}: invalid split")
        group = row.get("source_group")
        if group is not None and (not isinstance(group, str) or not group.strip()):
            raise ValueError(f"{row['id']}: source_group must be null or a nonempty string")
        if group is not None and split is not None and group in splits and splits[group] != split:
            raise ValueError(f"{group}: conflicting family splits")
        if group is not None and split is not None:
            splits[group] = split
        encoded(row)
    if not rows:
        raise ValueError("No input rows")
    return rows


def validate_instruction(instruction: str) -> None:
    """Check the input boundary; authoring quality belongs to the prompt and review."""
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("Instruction must be a nonempty string")


def validate_requests(rows: list[dict]) -> None:
    for row in rows:
        if row.get("task") not in ("Generate", "Edit"):
            raise ValueError("Drawing accepts Generate/Edit; imported Reconstruct pairs can be reviewed and exported")
        validate_instruction(row["instruction"])
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


def replace_snapshot(temporary: Path, path: Path) -> None:
    """Retry short Windows reader locks without overwriting the live file in place."""
    for attempt in range(4):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 3:
                raise
            sleep(0.25 * (attempt + 1))


def save_json(path: Path, value: object) -> None:
    """Replace a checkpoint only after its complete JSON has been written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(encoded(value) + "\n", encoding="utf-8")
    replace_snapshot(temporary, path)


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


def source_image(row: dict) -> dict | None:
    """Read the explicitly bound reconstruction input: original crop or synthetic render."""
    reference = row.get("image")
    if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
        return None
    try:
        data = Path(reference["path"]).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != reference.get("sha256"):
            return None
        with Image.open(BytesIO(data)) as picture:
            suffix = picture.format.lower()
            picture.verify()
    except (OSError, ValueError):
        return None
    return {"bytes": data, "path": f"{digest}.{suffix}"}


def write_parquet(rows: list[dict], path: Path) -> None:
    """Write a closed, readable HF image table, then replace the previous snapshot."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    fields = ("schema_version", "id", "task", "instruction", "current_tikz", "target_tikz", "source", "source_group", "split")
    schema = pa.schema([(k, pa.string()) for k in fields] +
                       [("evaluation_rubric", pa.string()), ("metadata", pa.string()),
                         ("tikz_image", pa.struct([("bytes", pa.binary()), ("path", pa.string())])),
                         ("image", pa.struct([("bytes", pa.binary()), ("path", pa.string())]))],
                       metadata={"huggingface": encoded({"info": {"features": {
                           "tikz_image": {"_type": "Image"}, "image": {"_type": "Image"}}}})})
    records = []
    for row in rows:
        image = target_image(row)
        metadata = {k: v for k, v in row.items() if k not in fields and k != "evaluation_rubric"}
        if image:
            metadata.update(target_tikz_sha256=hashlib.sha256(row["target_tikz"].encode("utf-8")).hexdigest(),
                            tikz_image_sha256=hashlib.sha256(image["bytes"]).hexdigest())
        records.append({**{k: row.get(k) for k in fields}, "evaluation_rubric": encoded(row.get("evaluation_rubric")),
                        "metadata": encoded(metadata), "tikz_image": image, "image": source_image(row)})
    temporary = path.with_suffix(".parquet.tmp")
    try:
        pq.write_table(pa.Table.from_pylist(records, schema=schema), temporary,
                       compression="zstd", row_group_size=100)
        replace_snapshot(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_candidates(output: Path, latest: dict[str, dict]) -> None:
    rows = list(latest.values())
    temporary = output / "candidates.tmp"
    temporary.write_text("".join(encoded(row) + "\n" for row in rows), encoding="utf-8")
    replace_snapshot(temporary, output / "candidates.jsonl")
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

    started = perf_counter()
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
               "agent.workflows.problem_tikz", "agent.workflows.tikz", "agent.schemas.tikz",
               "agent.middleware")
    paths = [Path(sys.modules[name].__file__) for name in modules] + [ROOT / "tools/cpa.py", Path(__file__)]
    for path in paths:
        data = path.read_bytes()
        snapshot = session / "harness" / path.relative_to(ROOT)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
        profile.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
    report = {**(run_metadata or {}), "rows": len(rows), "workers": workers, "pending_rows": len(pending),
              "skipped_rows": len(outcomes), "session_dir": str(session),
              "langsmith_project": project, "harness_files": profile,
              "tikz_prompt_version": sys.modules["agent.prompts.tikz"].TIKZ_PROMPT_VERSION,
              "task_prompt_version": sys.modules["agent.prompts.problem_tikz"].PROBLEM_TIKZ_PROMPT_VERSION,
              "input_sha256": hashlib.sha256(inputs).hexdigest(),
              "candidate_snapshot_count": 0, "candidate_snapshot_wall_seconds": 0.0,
              "checkpointed_rows": 0, "row_checkpoint_wall_seconds": 0.0,
              "row_checkpoint_wall_seconds_by_id": {}}
    save_json(session / "report.json", report)
    save_json(output / "report.json", report)
    if not pending:
        report["max_model_calls_total"] = 0

    snapshot_count, snapshot_seconds, last_snapshot = 0, 0.0, 0.0
    checkpoint_seconds_by_id: dict[str, float] = {}
    checkpoint_lock = Lock()

    def publish_snapshot() -> None:
        nonlocal snapshot_count, snapshot_seconds, last_snapshot
        snapshot_started = perf_counter()
        save_candidates(output, latest)
        snapshot_seconds += perf_counter() - snapshot_started
        snapshot_count += 1
        last_snapshot = perf_counter()
        with checkpoint_lock:
            checkpoint_times = dict(checkpoint_seconds_by_id)
        report.update(candidate_snapshot_count=snapshot_count,
                      candidate_snapshot_wall_seconds=round(snapshot_seconds, 6),
                      checkpointed_rows=len(checkpoint_times),
                      row_checkpoint_wall_seconds=round(sum(checkpoint_times.values()), 6),
                      row_checkpoint_wall_seconds_by_id=checkpoint_times,
                      rows_completed=len(outcomes),
                      counts=dict(Counter(row.get("drawing_status") for row in outcomes.values())),
                      successful_new_drawings=sum(outcomes.get(row_id, {}).get("success") is True
                                                   for row_id in (row["id"] for row in pending)))
        save_json(session / "report.json", report)
        save_json(output / "report.json", report)

    def draw_one(row: dict) -> dict:
        record = {**row, "current_tikz": row.get("current_tikz"), "target_tikz": "",
                  "success": False, "rendered_png_path": None, "unresolved_issues": [],
                  "rendered_tikz_sha256": None, "rendered_png_sha256": None,
                  "verification": {"status": "candidate", "reviewed_by": None}}
        trace_id, row_started = uuid4(), perf_counter()
        case = output / "cases" / hashlib.sha256(row["id"].encode("utf-8")).hexdigest()
        # Keep native UUID/render subdirectories below Windows' path-length limit.
        directory = output / "artifacts" / trace_id.hex
        directory.mkdir(parents=True)
        record.update(trace_id=str(trace_id), artifact_dir=str(directory), session_dir=str(session))
        try:
            with tracing_context(enabled=trace_client is not None, client=trace_client,
                                 project_name=project, parent=False):
                configured = agent.with_config(run_id=trace_id, tags=["synthetic-tikz"],
                                               metadata={"record_id": row["id"], "source_group": row.get("source_group")})
                result = problem_tikz(instruction=row["instruction"], current_tikz=record["current_tikz"],
                                      artifact_dir=directory, agent=configured, compiler_http=compiler_http)
            record.update(success=result.success, drawing_status=result.status, target_tikz=result.tikz,
                          rendered_png_path=result.rendered_png_path, unresolved_issues=result.unresolved_issues)
            messages = [json.loads(line) for line in (directory / "messages.jsonl").read_text(encoding="utf-8").splitlines()] if (directory / "messages.jsonl").is_file() else []
            responses = [message for message in messages if message.get("type") == "ai"
                         and (message.get("response_metadata") or message.get("usage_metadata"))]
            record["model_calls"] = len(responses)
            record["usage"] = {key: sum((message.get("usage_metadata") or {}).get(key, 0) or 0 for message in responses)
                               for key in ("input_tokens", "output_tokens", "total_tokens")}
            if result.tikz and result.rendered_png_path:
                record.update(rendered_tikz_sha256=hashlib.sha256(result.tikz.encode("utf-8")).hexdigest(),
                              rendered_png_sha256=hashlib.sha256(Path(result.rendered_png_path).read_bytes()).hexdigest())
        except Exception as error:  # noqa: BLE001 -- preserve one remote failure without discarding the batch
            record.update(success=False, drawing_status="failed", rendered_png_path=None,
                          rendered_tikz_sha256=None, rendered_png_sha256=None,
                          unresolved_issues=[f"{type(error).__name__}: {error}"])
        record["elapsed_seconds"] = round(perf_counter() - row_started, 3)
        checkpoint_started = perf_counter()
        save_json(directory / "candidate.json", record)
        save_json(case / "candidate.json", record)
        with checkpoint_lock:
            checkpoint_seconds_by_id[row["id"]] = round(perf_counter() - checkpoint_started, 6)
        return record

    for record in outcomes.values():
        case = output / "cases" / hashlib.sha256(record["id"].encode("utf-8")).hexdigest()
        checkpoint_started = perf_counter()
        save_json(case / "candidate.json", record)
        with checkpoint_lock:
            checkpoint_seconds_by_id[record["id"]] = round(perf_counter() - checkpoint_started, 6)
        print(encoded({"id": record["id"], "drawing_status": "skipped_existing_target"}), flush=True)
    latest.update(outcomes)
    if pending:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = [pool.submit(draw_one, row) for row in pending]
            for job in as_completed(jobs):
                record = job.result()
                outcomes[record["id"]] = record
                latest[record["id"]] = record
                if snapshot_count == 0 or perf_counter() - last_snapshot >= 30:
                    publish_snapshot()
                print(encoded({"id": record["id"], "drawing_status": record["drawing_status"]}), flush=True)
    # Per-ID checkpoints stay atomic; aggregate JSONL/Parquet snapshots can be coalesced.
    publish_snapshot()
    report["counts"] = dict(Counter(row["drawing_status"] for row in outcomes.values()))
    report["elapsed_seconds"] = round(perf_counter() - started, 3)
    report["successful_new_drawings"] = sum(outcomes[row["id"]].get("success") is True for row in pending)
    report["successful_drawings_per_minute"] = round(report["successful_new_drawings"] * 60 / max(perf_counter() - started, .001), 3)
    save_json(session / "report.json", report)
    save_json(output / "report.json", report)
    return [outcomes[row["id"]] for row in rows]


def validate_ready_pair(row: dict) -> None:
    """Validate recorded independent acceptance, never infer it from compilation."""
    validate_tikz(row.get("target_tikz", ""))
    review = row.get("verification", {})
    if (not isinstance(review, dict) or review.get("status") != "ready"
            or not isinstance(review.get("reviewed_by"), str) or not review["reviewed_by"].strip()
            or review.get("reviewed_input_sha256") != review_digest(row)):
        raise ValueError(f"{row['id']}: missing review or changed instruction/target/rubric")
    if target_image(row) is None:
        raise ValueError(f"{row['id']}: a verified PNG for this exact target_tikz is required")
    if row.get("task") in ("Generate", "Edit"):
        evidence = row.get("review_evidence")
        required = ("source", "instruction", "mathematics", "content", "readability")
        if row["task"] == "Edit":
            current_code = row.get("current_tikz")
            if not isinstance(current_code, str) or not current_code.strip() or current_code == row.get("target_tikz"):
                raise ValueError(f"{row['id']}: Edit needs an actual changed starting/ending pair")
            validate_tikz(current_code)
            required += ("edit_change", "edit_preservation")
            current = row.get("current_render")
            if not isinstance(current, dict) or target_image({**current, "target_tikz": row.get("current_tikz")}) is None:
                raise ValueError(f"{row['id']}: Edit review needs the exact starting PNG/code binding")
        if (review.get("method") != "independent_source_render_review"
                or not isinstance(evidence, dict) or evidence.get("unresolved") != []
                or any(not isinstance(evidence.get(key), str) or not evidence[key].strip() for key in required)):
            raise ValueError(f"{row['id']}: independent source/render review evidence is missing or unresolved")


def export_rows(rows: list[dict], output: Path) -> dict:
    """Export reviewed pairs only; never infer readiness from drawing completion."""
    seen, lineage_splits = set(), {}
    for row in rows:
        if row.get("task") not in ("Generate", "Edit", "Reconstruct"):
            raise ValueError(f"{row['id']}: unknown task")
        if row["task"] != "Reconstruct":
            validate_instruction(row.get("instruction"))
        validate_ready_pair(row)
        if row.get("split") not in (None, "train", "validation", "test"):
            raise ValueError(f"{row['id']}: invalid split")
        parents = (row.get("provenance") or {}).get("parents", [])
        if not isinstance(parents, list) or any(not isinstance(parent, str) or not parent.strip() for parent in parents):
            raise ValueError(f"{row['id']}: invalid original parents")
        for key in [("source", row.get("source")), ("family", row.get("source_group")), *(("parent", parent) for parent in parents)]:
            if key[1] is None or row.get("split") is None:
                continue
            if key in lineage_splits and lineage_splits[key] != row["split"]:
                raise ValueError(f"{key[1]}: conflicting lineage splits")
            lineage_splits[key] = row["split"]
        if not isinstance(row.get("target_tikz"), str) or not row["target_tikz"].strip():
            raise ValueError(f"{row['id']}: complete target_tikz required")
        validate_tikz(row["target_tikz"])
        if target_image(row) is None:
            raise ValueError(f"{row['id']}: a verified PNG for this exact target_tikz is required")
        current = row.get("current_tikz")
        if row["task"] == "Generate" and current is not None:
            raise ValueError(f"{row['id']}: Generate has starting TikZ")
        if row["task"] == "Reconstruct" and (current is not None or source_image(row) is None):
            raise ValueError(f"{row['id']}: Reconstruct requires its verified source image and null current_tikz")
        if row["task"] == "Edit":
            if not isinstance(current, str) or not current.strip() or current == row["target_tikz"]:
                raise ValueError(f"{row['id']}: Edit needs an actual changed starting/ending pair")
            validate_tikz(current)
        key = (*tuple(row.get(k) for k in ("task", "instruction", "current_tikz", "target_tikz")),
               (row.get("image") or {}).get("sha256"))
        if key in seen:
            raise ValueError(f"{row['id']}: duplicate task/input/target")
        seen.add(key)
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for task in ("Generate", "Edit", "Reconstruct"):
        for split in (None, "train", "validation", "test"):
            selected = [row for row in rows if row["task"] == task and row.get("split") == split]
            if not selected:
                continue
            path = output / task.lower() / f"{split or 'data'}.parquet"
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
    parser.add_argument("--compiler-concurrency", type=int, default=2,
                        help="Compiler HTTP connections; the shared service currently admits two operations")
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
        if not 1 <= args.workers <= 32 or not 1 <= args.compiler_concurrency <= 2 or not 2 <= args.max_model_calls <= 4:
            raise ValueError("workers must be 1-32; compiler-concurrency 1-2; max-model-calls 2-4")
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
            limits = httpx.Limits(max_connections=args.compiler_concurrency,
                                 max_keepalive_connections=args.compiler_concurrency)
            with CompilerClient(concurrency=args.compiler_concurrency, base_url=args.compiler_url,
                                timeout=150, trust_env=False, limits=limits) as compiler:
                ready = compiler.get("/readyz")
                ready.raise_for_status()
                result = draw_batch(rows, args.output.resolve(), agent=agent, compiler_http=compiler,
                                    workers=args.workers, project=os.environ["LANGSMITH_PROJECT"], trace_client=client,
                                    resume=args.resume, retry_ids=args.retry_id,
                                    run_metadata={"max_model_calls_per_row": args.max_model_calls,
                                                  "compiler_concurrency": args.compiler_concurrency,
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
