"""Evaluate TikZ pairs or re-evaluate saved, verified compiler artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import statistics
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

import httpx
from agent.latex.tikz import standalone_tikz_document

from evaluation.evaluator import VERSION, evaluate
from evaluation.tikz_observations import compile_observe as observe_tikz
from evaluation.tikz_preview import write_preview

logger = logging.getLogger(__name__)
GENERATION_FAILURES = {"generation_failed", "missing_tikz", "provider_error", "parse_error"}


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def verify_cached_observation(observation: dict[str, Any], tikz: str) -> None:
    """Verify saved execution evidence before cache reuse or offline rescoring."""
    if observation.get("metadata", {}).get("input_tikz_sha256") != _digest(tikz.encode("utf-8")):
        raise ValueError("Cached observation has a different input")
    records = list(observation.get("artifacts", {}).get("original", {}).values())
    records += list(observation.get("metadata", {}).get("measurement", {}).get("artifacts", {}).values())
    records += list(observation.get("metadata", {}).get("discovery", {}).get("artifacts", {}).values())
    if observation.get("pdf_path"):
        pdf = observation.get("artifacts", {}).get("original", {}).get("result.pdf")
        if not pdf or Path(pdf["path"]).resolve() != Path(observation["pdf_path"]).resolve():
            raise ValueError("Cached PDF is not the original recorded artifact")
    for record in records:
        artifact = Path(record["path"])
        if not artifact.is_file() or _digest(artifact.read_bytes()) != record["sha256"]:
            raise ValueError(f"Cached artifact is missing or changed: {artifact}")


def summarize(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep planned cases and source groups in denominators; never pool systems."""
    if len({row["id"] for row in cases}) != len(cases) or len({row["id"] for row in results}) != len(results):
        raise ValueError("Duplicate case or result IDs")
    result_by_id = {row["id"]: row for row in results}
    if result_by_id.keys() - {row["id"] for row in cases}:
        raise ValueError("Results outside the planned cases")
    partitions, splits = defaultdict(list), {}
    for case in cases:
        if case.get("task") not in {"Generate", "Edit", "Reconstruct"} or not isinstance(case.get("source_group"), str) or not case["source_group"]:
            raise ValueError("Every case requires task and source_group")
        if case.get("grade") is not None and (type(case["grade"]) is not int or not 6 <= case["grade"] <= 12):
            raise ValueError("Only grades 6-12 are in scope")
        split = case.get("split") or case.get("provenance", {}).get("split") or "unspecified"
        if splits.setdefault(case["source_group"], split) != split:
            raise ValueError("Source group spans multiple splits")
        result = result_by_id.get(case["id"], {})
        if any(key in result and result[key] != case.get(key) for key in ("task", "source_group")):
            raise ValueError("Result metadata differs from its planned case")
        comparison = result.get("comparison", {})
        for role in ("target", "output"):
            expected = comparison.get("source_hashes", {}).get(role)
            if expected and role + "_tikz" in case and expected != _digest(case[role + "_tikz"].encode()):
                raise ValueError(f"Stale {role} evidence: {case['id']}")
        cohort = case.get("cohort") or ("model_outputs" if case.get("worker_path") or case.get("system_id") else "candidates")
        system = case.get("system_id") or (str(Path(case["worker_path"]).parent.parent) if case.get("worker_path") else "unspecified")
        partitions[(cohort, system, split, case["task"])].append((case, comparison))
    summaries = []
    for (cohort, system, split, task), rows in sorted(partitions.items()):
        summary = {"cohort": cohort, "system_id": system, "split": split, "task": task,
                   "n_scheduled": len(rows), "n_results": sum(case["id"] in result_by_id for case, _ in rows),
                   "n_source_groups": len({case["source_group"] for case, _ in rows}),
                   "generation_failures": sum(case.get("generation_status") in GENERATION_FAILURES for case, _ in rows),
                   "scores": {}}
        for name in ("compile", "mathematical_correctness", "content_coverage", "visual_readability"):
            values, groups = [], defaultdict(list)
            for case, comparison in rows:
                value = comparison.get("scores", {}).get(name)
                if value is not None:
                    values.append(value)
                    groups[case["source_group"]].append(value)
            summary["scores"][name] = {
                "mean": statistics.fmean(values) if values else None,
                "source_group_mean": statistics.fmean(statistics.fmean(group) for group in groups.values()) if groups else None,
                "available": len(values), "missing": len(rows) - len(values),
                "unresolved_units": sum(comparison.get("counts", {}).get(name, {}).get("unresolved", 0) for _, comparison in rows),
            }
        summaries.append(summary)
    return summaries


def _snapshot_sources(output: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    hashes, sources = {}, {}
    for name in ("evaluator.py", "tikz_geometry.py", "tikz_coverage.py", "tikz_observations.py", "tikz_readability.py", "run.py"):
        source = Path(__file__).with_name(name)
        digest = _digest(source.read_bytes())
        snapshot = output / "evaluator-sources" / digest / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(source.read_bytes())
        hashes[name], sources[name] = digest, {"path": str(snapshot), "sha256": digest}
    return hashes, sources


def _evaluate_case(case: dict[str, Any], target: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    return evaluate(target, output, evaluation_rubric=case.get("evaluation_rubric"),
                    geometry_space=case.get("geometry_space", "euclidean_2d"),
                    content_requirements=case.get("content_requirements"))


def run(cases_path: Path, output: Path, worker_runs: list[Path] | None = None) -> Path:
    """Render development pairs, retain raw evidence, and write a review preview."""
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({row["id"] for row in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    for worker_run in worker_runs or []:
        manifest_path = worker_run / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        selected = manifest.get("selected_candidate_ids")
        for original in [row for row in cases if row["variant"] == "identity"]:
            candidate_id = original["provenance"]["source_candidate_id"]
            if selected is not None and candidate_id not in selected:
                continue
            worker_path = worker_run / candidate_id / "worker.json"
            candidate_path = worker_path.parent / "candidate.json"
            frozen = json.loads(candidate_path.read_text(encoding="utf-8"))
            if any(frozen.get(key) != original.get(key) for key in ("instruction", "current_tikz", "task")):
                raise ValueError(f"Saved worker input mismatch: {candidate_id}")
            if worker_path.is_file():
                worker = json.loads(worker_path.read_text(encoding="utf-8"))
                worker["saved_result_sha256"] = _digest(worker_path.read_bytes())
            else:
                worker = {"error": "Requested worker result is missing"}
            cases.append({**original, "id": original["id"].replace("identity", "native-worker-" + worker_run.name), "variant": f"native worker output saved in {worker_run} (comparison makes no model call)", "output_tikz": worker.get("tikz") or "", "worker": worker, "worker_path": str(worker_path), "worker_manifest_path": str(manifest_path.resolve()), "worker_manifest_sha256": _digest(manifest_path.read_bytes()), "worker_unavailable": not worker_path.is_file(), "system_id": str(worker_run.resolve()), "generation_status": "missing_saved_output" if not worker_path.is_file() else "returned_tikz" if worker.get("tikz") else "generation_failed" if worker.get("error") else "missing_tikz", "cohort": "model_outputs", "preparation_route": "saved_native_output"})
    if len({row["id"] for row in cases}) != len(cases):
        raise ValueError("Duplicate case IDs after merging worker runs")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "report.json").exists():
        raise ValueError("Report already exists: choose a fresh output directory")
    summarize(cases, [])
    _save(output / "inputs.json", cases)
    inputs_hash = _digest((output / "inputs.json").read_bytes())
    evaluator_hashes, evaluator_sources = _snapshot_sources(output)
    runtime = {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "shapely", "PyMuPDF", "httpx")}}
    with httpx.Client(base_url="http://127.0.0.1:18080", timeout=200, trust_env=False) as compiler:
        ready = compiler.get("/readyz")
        ready.raise_for_status()
        toolchain = ready.json()["toolchain_id"]
        profile = {"toolchain_id": toolchain, "observer_sha256": evaluator_hashes["tikz_observations.py"], "wrapper_sha256": _digest(standalone_tikz_document(r"\begin{tikzpicture}\end{tikzpicture}").encode())}
        profile_path = output / "compiler-profile.json"
        if profile_path.exists() and json.loads(profile_path.read_text(encoding="utf-8")) != profile:
            raise ValueError("Compiler profile changed: choose a fresh output directory")
        _save(profile_path, profile)
        memo: dict[str, dict[str, Any]] = {}

        def observe(tikz: str) -> dict[str, Any]:
            key = _digest(tikz.encode("utf-8"))
            if key not in memo:
                directory = output / "compiled" / key
                path = directory / "observation.json"
                if path.exists():
                    memo[key] = json.loads(path.read_text(encoding="utf-8"))
                    verify_cached_observation(memo[key], tikz)
                else:
                    memo[key] = observe_tikz(tikz, directory, compiler)
                    _save(path, memo[key])
            return memo[key]

        reviews, results = [], []
        for row in cases:
            target = observe(row["target_tikz"])
            produced = {"compile_success": False, "compile": {"outcome": "unknown"}} if row.get("worker_unavailable") or row.get("generation_status") in GENERATION_FAILURES | {"missing_saved_output"} else observe(row["output_tikz"])
            comparison = _evaluate_case(row, target, produced)
            results.append({"id": row["id"], "task": row["task"], "source_group": row["source_group"], "comparison": comparison})
            reviews.append({"candidate": row, "source": {"source_image_path": row.get("source_image_path"), "provenance": row.get("provenance")}, "target": {**target, "tikz": row["target_tikz"], "compiler": target.get("compile")}, "current": {**observe(row["current_tikz"]), "tikz": row["current_tikz"]} if row.get("current_tikz") else {}, "output": {**produced, "tikz": row["output_tikz"], "pair_comparison": comparison}, "worker": row.get("worker", {})})
            logger.info("%s", json.dumps({"id": row["id"], **comparison["scores"]}))
            _save(output / "review.json", reviews)
            write_preview(reviews, output)
    report = {"evaluator_sha256": evaluator_hashes, "evaluator_sources": evaluator_sources, "runtime": runtime,
              "comparator_version": VERSION, "cases_sha256": _digest(cases_path.read_bytes()),
              "compiler_profile": profile, "results": results}
    report["inputs_sha256"] = inputs_hash
    _save(output / "report.json", report)
    _save(output / "summary.json", summarize(cases, results))
    return output / "preview.html"


def rescore(report_path: Path, output: Path) -> Path:
    """Re-evaluate original artifacts without compiler or model calls."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    inputs = report_path.with_name("inputs.json")
    if report.get("inputs_sha256") and report["inputs_sha256"] != _digest(inputs.read_bytes()):
        raise ValueError("Saved input manifest changed")
    cases = json.loads(inputs.read_text(encoding="utf-8"))
    previous = report["results"]
    summarize(cases, previous)
    reviews = json.loads(report_path.with_name("review.json").read_text(encoding="utf-8"))
    review_by_id = {row["candidate"]["id"]: row for row in reviews}
    if len(review_by_id) != len(reviews) or review_by_id.keys() - {row["id"] for row in cases}:
        raise ValueError("Duplicate or foreign saved reviews")
    if (output / "report.json").exists():
        raise ValueError("Report already exists: choose a fresh output directory")
    results, refreshed = [], []
    for case in cases:
        review = review_by_id.get(case["id"])
        if review is None:
            continue
        if any(review["candidate"].get(key) != case.get(key) for key in ("task", "instruction", "current_tikz", "source_image_path", "evaluation_rubric", "geometry_space", "diagram_types", "content_requirements")):
            raise ValueError("Saved review input differs from the planned case")
        for role in ("target", "output"):
            observation = review[role]
            if observation.get("tikz") != case[role + "_tikz"]:
                raise ValueError("Saved review differs from the planned TikZ")
            if observation.get("metadata") or observation.get("compile_success") or observation.get("pdf_path"):
                verify_cached_observation(observation, case[role + "_tikz"])
        comparison = _evaluate_case(case, review["target"], review["output"])
        results.append({"id": case["id"], "task": case["task"], "source_group": case["source_group"], "comparison": comparison})
        refreshed.append({**review, "output": {**review["output"], "pair_comparison": comparison}})
    hashes, sources = _snapshot_sources(output)
    _save(output / "inputs.json", cases)
    _save(output / "review.json", refreshed)
    _save(output / "report.json", {"comparator_version": VERSION, "evaluator_sha256": hashes, "evaluator_sources": sources,
                                  "runtime": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "shapely", "PyMuPDF", "httpx")}},
                                  "compiler_profile": report.get("compiler_profile"),
                                  "inputs_sha256": _digest((output / "inputs.json").read_bytes()), "results": results,
                                  "rescored_from": {"path": str(report_path.resolve()), "sha256": _digest(report_path.read_bytes())}})
    _save(output / "summary.json", summarize(cases, results))
    write_preview(refreshed, output)
    return output / "report.json"


def main() -> None:
    """Run the local development comparison CLI."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--cases", type=Path, help="Frozen cases for the current evaluation contract")
    inputs.add_argument("--report", type=Path, help="Re-evaluate adjacent inputs.json and review.json offline")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker-run", type=Path, action="append")
    args = parser.parse_args()
    logger.info("Result: %s", rescore(args.report, args.output) if args.report else run(args.cases, args.output, args.worker_run))


if __name__ == "__main__":
    main()
