"""Compile authored Generate/Edit JSONL with MathPaper's shared TikZ compiler."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

import httpx
from agent.latex import tikz as wrapper
from agent.prompts import problem_tikz
from agent.prompts import tikz as prompt
from latex_compiler.client import compile as compile_latex
from latex_compiler.schemas import CompileRequest, Images, Outputs


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def save_json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value) + b"\n")


def load_candidates(data: bytes, ids: list[str] | None) -> list[dict[str, Any]]:
    rows, seen = [], set()
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip()
                                         for key in ("id", "instruction", "target_tikz")):
            raise ValueError(f"Line {number}: id, instruction and target_tikz must be nonempty strings")
        if row["id"] in seen:
            raise ValueError(f"Duplicate candidate ID: {row['id']}")
        seen.add(row["id"])
        current = row.get("current_tikz")
        if ("current_tikz" not in row or row.get("task") not in ("Generate", "Edit")
                or row["task"] == "Generate" and current is not None
                or row["task"] == "Edit" and (not isinstance(current, str) or not current.strip())):
            raise ValueError(f"Line {number}: Generate requires null current_tikz; Edit requires starting TikZ")
        for key in ("provenance", "verification"):
            if key in row and not isinstance(row[key], dict):
                raise ValueError(f"Line {number}: {key} must be an object")
        json_bytes(row)
        rows.append(row)
    if ids and set(ids) - seen:
        raise ValueError(f"Unknown candidate IDs: {sorted(set(ids) - seen)}")
    selected = [row for row in rows if not ids or row["id"] in ids]
    if not selected:
        raise ValueError("No candidates selected")
    return selected


def harness_profile() -> dict[str, Any]:
    return {"tikz_prompt_version": prompt.TIKZ_PROMPT_VERSION, "files": [
        {"path": str(Path(module.__file__).resolve()), "sha256": digest(Path(module.__file__).read_bytes())}
        for module in (prompt, problem_tikz, wrapper)
    ]}


def compile_one(tikz: str, directory: Path, compiler: httpx.Client) -> dict[str, Any]:
    directory.mkdir(parents=True)
    result: dict[str, Any] = {"input_tikz_sha256": digest(tikz.encode("utf-8")), "artifacts": {},
                              "compile": {"outcome": "not_run"}, "raster": {"outcome": "not_run"}}
    try:
        canonical = wrapper.validate_tikz(tikz)
        source = wrapper.standalone_tikz_document(canonical)
        request = CompileRequest(source=source, outputs=Outputs(pdf=True, images=Images()))
    except ValueError as error:
        return {**result, "status": "validation_failed", "diagnostic": str(error)}
    source_path = directory / "main.tex"
    source_path.write_text(source, encoding="utf-8", newline="\n")
    result.update(canonical_tikz_sha256=digest(canonical.encode("utf-8")),
                  source_path=str(source_path), source_sha256=digest(source_path.read_bytes()),
                  request=request.model_dump(exclude={"source"}))
    try:
        response = compile_latex(compiler, request)
    except (httpx.HTTPError, ValueError) as error:
        return {**result, "status": "unavailable", "diagnostic": str(error)}
    result.update(compile=response.compile.model_dump(), raster=response.raster.model_dump(),
                  toolchain_id=response.toolchain_id, source_digest=response.source_digest,
                  page_count=response.page_count)
    for artifact in response.artifacts:
        path = directory / artifact.name
        data = artifact.data
        path.write_bytes(data)
        result["artifacts"][artifact.name] = {"path": str(path), "sha256": digest(data),
                                               "complete": artifact.complete, "size_bytes": len(data)}
    result["status"] = ("unavailable" if response.compile.outcome in {"unknown", "timeout"} else
                        "compile_failed" if not response.compile.success else
                        "render_failed" if not response.raster.success or response.page_count != 1 else
                        "needs_review")
    if response.compile.success and response.page_count != 1:
        result["diagnostic"] = "Expected one PDF page for one TikZ picture"
    return result


def compile_batch(input_path: Path, output: Path, compiler: httpx.Client,
                  ids: list[str] | None = None) -> dict[str, Any]:
    """Save compile evidence and candidate copies; never approve a training target."""
    data = input_path.read_bytes()
    rows = load_candidates(data, ids)
    profile = harness_profile()
    for row in rows:
        previous = row.get("provenance", {}).get("harness_profile")
        if previous and previous != profile:
            raise ValueError(f"{row['id']}: pinned harness profile differs; review against the current prompt first")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "inputs.jsonl").write_bytes(data)
    snapshots = []
    for item in profile["files"]:
        source = Path(item["path"])
        snapshot = output / "harness" / source.relative_to(ROOT)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(source.read_bytes())
        snapshots.append({**item, "snapshot_path": str(snapshot)})
    save_json(output / "harness.json", {**profile, "snapshots": snapshots})
    compiled, results = {}, []
    candidates_path = output / "candidates.jsonl"
    with candidates_path.open("w", encoding="utf-8", newline="\n") as candidates:
        for row in rows:
            roles = {}
            for role in ("target", "current"):
                tikz = row.get(role + "_tikz")
                if tikz is None:
                    continue
                key = digest(tikz.encode("utf-8"))
                if key not in compiled:
                    compiled[key] = compile_one(tikz, output / "compiled" / key, compiler)
                roles[role] = compiled[key]
            status = next((item["status"] for item in roles.values() if item["status"] != "needs_review"), "needs_review")
            folder = output / "cases" / digest(row["id"].encode("utf-8"))
            folder.mkdir(parents=True)
            report_path = folder / "report.json"
            evidence_inputs = {key: row.get(key) for key in ("task", "instruction", "current_tikz", "target_tikz", "evaluation_rubric")}
            save_json(report_path, {"id": row["id"], "status": status, "candidate": row,
                                   "candidate_sha256": digest(json_bytes(row)),
                                   "input_sha256": digest(json_bytes({**evidence_inputs, "harness_profile": profile})),
                                   "harness_profile": profile, **roles})
            prepared = {**row, "provenance": {**row.get("provenance", {}), "harness_profile": profile},
                        "verification": {**row.get("verification", {}), "status": "candidate",
                                         "report_path": str(report_path), "reviewed_by": None}}
            prepared["verification"].setdefault("notes", [])
            candidates.write(json_bytes(prepared).decode("utf-8") + "\n")
            candidates.flush()
            results.append({"id": row["id"], "status": status, "report_path": str(report_path)})
    summary = {"version": "synthetic-tikz-compile:v1", "input_path": str(input_path.resolve()),
               "input_sha256": digest(data), "counts": dict(Counter(row["status"] for row in results)),
               "results": results, "candidates_path": str(candidates_path),
               "report_path": str(output / "report.json")}
    save_json(output / "report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Authored Generate/Edit candidate JSONL")
    parser.add_argument("--output", required=True, type=Path, help="Fresh directory under runs/<batch-id>/")
    parser.add_argument("--id", action="append", dest="ids", help="Compile only this ID; may be repeated")
    parser.add_argument("--compiler-url", default=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"))
    args = parser.parse_args()
    try:
        with httpx.Client(base_url=args.compiler_url, timeout=150, trust_env=False) as compiler:
            summary = compile_batch(args.input, args.output, compiler, args.ids)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
    return int(any(row["status"] != "needs_review" for row in summary["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
