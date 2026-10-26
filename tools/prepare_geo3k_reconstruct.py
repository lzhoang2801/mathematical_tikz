"""Prepare exact code-to-render Reconstruct candidates from the pinned Geo3K-TikZ snapshot."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from tools import draw_instruction as drawing

DATA = ROOT / "dataset" / "geo3k-tikz" / "data"
OUTPUT_REVISION = "5d12d94db6af2217827d103caa17b93804a7d8df"
DATASET_ID = "SunnyLin/geo3k-tikz"
SPLITS = ("train", "validation", "test")
NORMALIZATION_VERSION = "remove-leading-calc-library-v1"
COMPILER_HELPER = ROOT / ".agents" / "skills" / "synthetic-tikz" / "scripts" / "compile.py"
SNAPSHOT_INTERVAL = 25


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def normalize_code(code: str) -> str:
    """Remove only the upstream calc-library preamble line; preserve the picture bytes otherwise."""
    if not isinstance(code, str):
        raise ValueError("TikZ code is missing or is not text")
    first, separator, remainder = code.partition("\n")
    if first.endswith("\r"):
        first = first[:-1]
    if first == r"\usetikzlibrary{calc}":
        if not separator:
            raise ValueError("calc preamble has no TikZ picture after it")
        return remainder
    return code


def unique_candidates(
    source_rows: list[tuple[str, int, str | None, str | None]], parquet_hashes: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    """Keep the first exact normalized TikZ and retain every collapsed source locator."""
    by_hash: dict[str, dict] = {}
    invalid: list[dict] = []
    for split, index, raw_code, original_image_hash in source_rows:
        row_id = f"geo3k-tikz@{OUTPUT_REVISION}:{split}:{index}"
        if not isinstance(raw_code, str):
            invalid.append({"id": row_id, "upstream_split": split, "upstream_row_index": index,
                            "reason": "Missing or non-string code"})
            continue
        raw_hash = digest(raw_code.encode("utf-8"))
        try:
            target = normalize_code(raw_code)
        except ValueError as error:
            invalid.append({"id": row_id, "upstream_split": split, "upstream_row_index": index,
                            "upstream_code_sha256": raw_hash, "reason": str(error)})
            continue
        target_hash = digest(target.encode("utf-8"))
        origin = {"upstream_split": split, "upstream_row_index": index,
                  "upstream_parquet": f"data/{split}-00000-of-00001.parquet",
                  "upstream_parquet_sha256": parquet_hashes[split],
                  "upstream_code_sha256": raw_hash,
                  "upstream_original_image_sha256": original_image_hash}
        previous = by_hash.get(target_hash)
        if previous is not None:
            if previous["target_tikz"] != target:
                raise RuntimeError("SHA-256 collision between normalized TikZ bodies")
            previous["provenance"]["duplicate_origins"].append(origin)
            continue
        by_hash[target_hash] = {
            "schema_version": "synthetic-tikz:v2",
            "id": row_id,
            "task": "Reconstruct",
            "instruction": None,
            "current_tikz": None,
            "target_tikz": target,
            "source": f"{DATASET_ID}@{OUTPUT_REVISION} {split}:{index}",
            "source_kind": "synthetic_render",
            "source_group": (f"geo3k-image:{original_image_hash}" if original_image_hash
                             else f"geo3k-code:{target_hash}"),
            "split": None,
            "evaluation_rubric": None,
            "provenance": {
                **origin,
                "upstream_dataset": DATASET_ID,
                "upstream_revision": OUTPUT_REVISION,
                "upstream_normalized_code_sha256": target_hash,
                "normalization": NORMALIZATION_VERSION,
                "duplicate_origins": [],
            },
            "verification": {"status": "candidate", "reviewed_by": None},
        }
    return list(by_hash.values()), invalid


def load_source_rows(data_dir: Path) -> tuple[list[tuple[str, int, str | None, str | None]], dict, dict]:
    import pyarrow.parquet as pq

    rows, hashes, counts = [], {}, {}
    for split in SPLITS:
        path = data_dir / f"{split}-00000-of-00001.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"Missing pinned upstream split: {path}")
        hashes[split] = file_digest(path)
        table = pq.read_table(path, columns=["code", "image"])
        counts[split] = table.num_rows
        for index, (code, image) in enumerate(zip(table.column("code").to_pylist(),
                                                   table.column("image").to_pylist())):
            payload = image.get("bytes") if isinstance(image, dict) else None
            image_hash = digest(payload) if isinstance(payload, bytes) else None
            rows.append((split, index, code, image_hash))
    return rows, hashes, counts


def load_compile_helper():
    spec = importlib.util.spec_from_file_location("problem_tikz_shared_compile", COMPILER_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared compiler helper: {COMPILER_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def case_dir(output: Path, row_id: str) -> Path:
    return output / "cases" / digest(row_id.encode("utf-8"))


def cached_candidate(output: Path, expected: dict) -> dict | None:
    path = case_dir(output, expected["id"]) / "candidate.json"
    if not path.is_file():
        return None
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (row.get("success") is not True
            or row.get("target_tikz") != expected["target_tikz"]
            or row.get("provenance", {}).get("upstream_parquet_sha256")
            != expected["provenance"]["upstream_parquet_sha256"]
            or row.get("provenance", {}).get("upstream_code_sha256")
            != expected["provenance"]["upstream_code_sha256"]
            or drawing.target_image(row) is None
            or drawing.source_image(row) is None):
        return None
    cached = {**row, **expected,
              "image": row["image"],
              "verification": row["verification"],
              "success": True,
              "drawing_status": "prepared"}
    verification = cached["verification"]
    if (not isinstance(verification, dict)
            or verification.get("status") != "ready"
            or verification.get("reviewed_by") != "deterministic-code-render-binding"
            or verification.get("reviewed_input_sha256") != drawing.review_digest(cached)):
        return None
    source = drawing.source_image(cached)
    target = drawing.target_image(cached)
    if source is None or target is None or source["bytes"] != target["bytes"]:
        return None
    return cached


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(drawing.encoded(row) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(path)


def snapshot(output: Path, rows: list[dict], failures: list[dict], report: dict) -> None:
    write_jsonl(output / "candidates.jsonl", rows)
    write_jsonl(output / "failures.jsonl", failures)
    drawing.write_parquet(rows, output / "candidates.parquet")
    drawing.save_json(output / "report.json", report)


def successful(result: dict) -> bool:
    artifact = result.get("artifacts", {}).get("page-1.png")
    return (result.get("status") == "needs_review"
            and result.get("compile", {}).get("outcome") == "ok"
            and result.get("raster", {}).get("outcome") == "ok"
            and result.get("page_count") == 1
            and isinstance(artifact, dict) and artifact.get("complete") is True
            and isinstance(artifact.get("path"), str) and Path(artifact["path"]).is_file())


def compile_candidate(row: dict, output: Path, compiler, compile_one) -> tuple[dict, dict]:
    directory = case_dir(output, row["id"])
    directory.mkdir(parents=True, exist_ok=True)
    attempts = [path for path in directory.glob("compile-*") if path.is_dir()]
    attempt = directory / f"compile-{len(attempts) + 1:03d}"
    started = perf_counter()
    evidence = compile_one(row["target_tikz"], attempt, compiler)
    report_path = directory / "compile-evidence.json"
    drawing.save_json(report_path, {"target": evidence})
    artifact = evidence.get("artifacts", {}).get("page-1.png", {})
    row = {**row,
           "verification": {"status": "candidate", "reviewed_by": None, "report_path": str(report_path)},
           "success": successful(evidence),
           "drawing_status": "compiled" if successful(evidence) else evidence.get("status", "compile_failed"),
           "elapsed_seconds": round(perf_counter() - started, 3)}
    if row["success"]:
        render_path = Path(artifact["path"]).resolve()
        render_hash = digest(render_path.read_bytes())
        if render_hash != artifact.get("sha256"):
            row.update(success=False, drawing_status="artifact_hash_mismatch")
        else:
            row["image"] = {"path": str(render_path), "sha256": render_hash}
            source = drawing.source_image(row)
            target = drawing.target_image(row)
            if source is None or target is None or source["bytes"] != target["bytes"]:
                row.update(success=False, drawing_status="image_binding_failed")
            else:
                verification = {
                    "status": "ready",
                    "reviewed_by": "deterministic-code-render-binding",
                    "method": "deterministic-code-render-binding",
                    "report_path": str(report_path),
                }
                row["verification"] = verification
                verification["reviewed_input_sha256"] = drawing.review_digest(row)
                row["drawing_status"] = "prepared"
    return row, evidence


def run(args) -> dict:
    output = args.output.resolve()
    if output.exists() and not args.resume:
        raise FileExistsError(f"{output} already exists; use --resume")
    if args.resume and not output.is_dir():
        raise FileNotFoundError(f"Cannot resume missing output directory: {output}")

    source_rows, parquet_hashes, split_counts = load_source_rows(DATA)
    candidates, invalid = unique_candidates(source_rows, parquet_hashes)
    run_signature = {"dataset": DATASET_ID, "revision": OUTPUT_REVISION,
                     "parquet_sha256": parquet_hashes, "normalization": NORMALIZATION_VERSION}
    manifest_path = output / "run.json"
    if args.resume:
        if not manifest_path.is_file():
            raise ValueError("Resume requires the original run.json manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("signature") != run_signature:
            raise ValueError("Upstream data or normalization changed; use a new output directory")
    else:
        output.mkdir(parents=True, exist_ok=False)
        drawing.save_json(manifest_path, {"signature": run_signature, "started_with_limit": args.limit})

    compiler_helper = load_compile_helper()
    compile_one = compiler_helper.compile_one
    failures = list(invalid)
    for failure in invalid:
        invalid_dir = case_dir(output, failure["id"])
        invalid_dir.mkdir(parents=True, exist_ok=True)
        drawing.save_json(invalid_dir / "candidate.json", {**failure, "task": "Reconstruct",
            "success": False, "drawing_status": "invalid_code"})
    prepared: dict[str, dict] = {}
    for candidate in candidates:
        cached = cached_candidate(output, candidate)
        if cached is not None:
            prepared[candidate["id"]] = cached
    report = {"schema_version": "synthetic-tikz:v2", "task": "Reconstruct",
              "dataset": DATASET_ID, "upstream_revision": OUTPUT_REVISION,
              "requested_candidates": args.limit, "upstream_rows": sum(split_counts.values()),
              "upstream_rows_by_split": split_counts, "unique_normalized_codes": len(candidates),
              "exact_code_duplicates_removed": sum(len(row["provenance"]["duplicate_origins"]) for row in candidates),
              "candidates_with_original_image_hash": sum(
                  row["provenance"]["upstream_original_image_sha256"] is not None for row in candidates),
              "invalid_codes": len(invalid), "prepared_pairs": len(prepared),
              "independently_reviewed": 0,
              "verification_method": "deterministic-code-render-binding",
              "compiler_concurrency": args.compiler_concurrency,
              "status": "running",
              "input_policy": "The input PNG is rendered from the exact normalized target TikZ; no original-image agreement is assessed."}

    try:
        with drawing.CompilerClient(concurrency=args.compiler_concurrency,
                                    base_url=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"),
                                    timeout=150, trust_env=False) as compiler:
            ready = compiler.get("/readyz")
            ready.raise_for_status()
            report["toolchain_id"] = ready.json().get("toolchain_id")
            processed_since_snapshot = 0
            for candidate in candidates:
                if candidate["id"] in prepared:
                    continue
                if len(prepared) >= args.limit:
                    break
                row, evidence = compile_candidate(candidate, output, compiler, compile_one)
                directory = case_dir(output, row["id"])
                drawing.save_json(directory / "candidate.json", row)
                if row.get("success"):
                    prepared[row["id"]] = row
                else:
                    failures.append({"id": row["id"], "upstream_split": row["provenance"]["upstream_split"],
                                     "upstream_row_index": row["provenance"]["upstream_row_index"],
                                     "upstream_code_sha256": row["provenance"]["upstream_code_sha256"],
                                     "target_sha256": row["provenance"]["upstream_normalized_code_sha256"],
                                     "status": row["drawing_status"],
                                     "diagnostic": evidence.get("diagnostic", "")})
                report["prepared_pairs"] = len(prepared)
                processed_since_snapshot += 1
                if row["drawing_status"] == "unavailable":
                    report["status"] = "compiler_unavailable"
                else:
                    report["status"] = "running"
                print(drawing.encoded({"id": row["id"], "status": row["drawing_status"],
                                       "prepared_pairs": len(prepared)}), flush=True)
                if processed_since_snapshot >= SNAPSHOT_INTERVAL or report["status"] == "compiler_unavailable":
                    ordered = [prepared[item["id"]] for item in candidates if item["id"] in prepared]
                    snapshot(output, ordered[:args.limit], failures, report)
                    processed_since_snapshot = 0
                if report["status"] == "compiler_unavailable":
                    break
            if processed_since_snapshot:
                ordered = [prepared[item["id"]] for item in candidates if item["id"] in prepared]
                snapshot(output, ordered[:args.limit], failures, report)
    except (OSError, ValueError, drawing.httpx.HTTPError) as error:
        report.update(status="compiler_error", compiler_error=f"{type(error).__name__}: {error}")
        ordered = [prepared[item["id"]] for item in candidates if item["id"] in prepared]
        snapshot(output, ordered[:args.limit], failures, report)
        return report

    if report["status"] != "compiler_unavailable":
        report["status"] = "prepared_quota_met" if len(prepared) >= args.limit else "prepared_source_exhausted"
    report["prepared_pairs"] = min(len(prepared), args.limit)
    ordered = [prepared[item["id"]] for item in candidates if item["id"] in prepared]
    snapshot(output, ordered[:args.limit], failures, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=1500, help="Maximum unique compiled target candidates")
    parser.add_argument("--output", type=Path, default=ROOT / "dataset/synthetic/reconstruct",
                        help="Canonical Reconstruct checkpoints and dataset snapshots")
    parser.add_argument("--resume", action="store_true", help="Reuse exact successful row checkpoints and retry failures")
    parser.add_argument("--compiler-concurrency", type=int, default=1,
                        help="Shared compiler slots to reserve; maximum is two")
    args = parser.parse_args()
    if args.limit < 1 or not 1 <= args.compiler_concurrency <= 2:
        parser.error("limit must be positive; compiler-concurrency must be 1 or 2")
    try:
        report = run(args)
    except (OSError, ValueError, ImportError, drawing.httpx.HTTPError) as error:
        parser.exit(2, f"{type(error).__name__}: {error}\n")
    print(drawing.encoded(report), flush=True)
    return 0 if report["status"] == "prepared_quota_met" else 2


if __name__ == "__main__":
    raise SystemExit(main())
