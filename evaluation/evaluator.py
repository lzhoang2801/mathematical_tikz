"""Score compilation, executable givens, drawn content and label readability."""
from __future__ import annotations

import json
from typing import Any

from evaluation.tikz_coverage import carrier_scene, compare_content, content_contract
from evaluation.tikz_geometry import evaluate_checks
from evaluation.tikz_observations import read_scene
from evaluation.tikz_readability import inspect_readability

VERSION = "tikz-evaluation:v11"


def _count(states: list[str]) -> dict[str, int]:
    return {"passed": sum(s in {"pass", "match"} for s in states),
            "failed": sum(s in {"fail", "different"} for s in states),
            "unresolved": sum(s == "unknown" for s in states), "total": len(states)}


def _percent(counts: dict[str, int]) -> float | None:
    return 100 * counts["passed"] / counts["total"] if counts["total"] else None


def _givens(rubric: list[dict[str, Any]], geometry_space: str) -> list[dict[str, Any]]:
    """Flatten existing dataset criteria; grouping and duplicate checks carry no weight."""
    if not isinstance(rubric, list):
        raise TypeError("evaluation_rubric must be a list")
    checks, ids, seen = [], set(), set()
    for criterion in rubric:
        if (not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str)
                or not criterion["id"] or criterion["id"] in ids):
            raise ValueError("Rubric criteria require unique IDs")
        if criterion.get("dimension") != "mathematical_correctness":
            raise ValueError("Only mathematical givens belong in evaluation_rubric; other metrics use shared checks")
        ids.add(criterion["id"])
        if not isinstance(criterion.get("checks", []), list):
            raise TypeError("Criterion checks must be a list")
        for check in criterion.get("checks") or [{"op": "unspecified", "criterion": criterion["id"]}]:
            if not isinstance(check, dict):
                raise TypeError("Each given must be a check object")
            check = {"geometry_space": criterion.get("geometry_space", geometry_space), **check}
            key = json.dumps(check, sort_keys=True, allow_nan=False)
            if key not in seen:
                seen.add(key)
                checks.append(check)
    return checks


def evaluate(
    target: dict[str, Any], output: dict[str, Any], *,
    evaluation_rubric: list[dict[str, Any]] | None = None,
    geometry_space: str = "euclidean_2d",
    content_requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Percentages award credit only for verified units, keeping unresolved units in the denominator."""
    givens = _givens(evaluation_rubric if evaluation_rubric is not None else [], geometry_space)
    scenes, errors, mathematics = {}, [], {}
    for role, observation in (("target", target), ("output", output)):
        if observation.get("compile_success"):
            try:
                scenes[role] = read_scene(observation)
            except (OSError, ValueError, RuntimeError) as error:
                errors.append(f"{role}: {error}")
        points = {
            label: {"status": "measured", "x": point["pdf_x"], "y": point["pdf_y"], "unit": "pdf_pt",
                    "frame": "original_pdf", "evidence_id": point.get("evidence_id"),
                    "coordinate_error_bound": point.get("pdf_coordinate_error_bound_pt", 0.0)}
            for label, point in scenes.get(role, {}).get("bindings", {}).items() if point.get("status") == "measured"
        }
        mathematics[role] = evaluate_checks(givens, points, geometry_space=geometry_space)
    content, readability, coverage_states = {}, {}, []
    if "output" in scenes and ("target" in scenes or content_requirements is not None):
        content = compare_content(scenes.get("target", {"points": {}, "strokes": []}), scenes["output"],
                                  content_requirements=content_requirements, geometry_space=geometry_space)
        point_checks = content["checks"]["points"]
        for name in point_checks["required"]:
            coverage_states.append("different" if name in point_checks["missing"] else
                                   "unknown" if name in point_checks["unresolved"] else "match")
        coverage_states += [row["status"] for row in content["checks"]["connections"]["requirements"]]
        circle_output = content["checks"]["circles"]
        coverage_states += [row["status"] for row in circle_output["requirements"]]
        extra_count = len(point_checks["extra"]) + len(content["checks"]["connections"]["extra_connections"])
        extra_count += max(0, circle_output.get("observed_count", 0) - circle_output.get("required_count", 0))
        coverage_states += ["different"] * extra_count
        # Unsupported emitted objects cannot disappear from a perfect coverage score.
        coverage_states += ["unknown"] * len(content["limitations"])
        for role, circles in (("target", content.pop("target_circles")), ("output", circle_output)):
            mathematics[role] += [
                {"check": row["requirement"], "status": {"match": "pass", "different": "fail"}.get(row["mathematical_status"], "unknown"),
                 "residual": row["residual"], "tolerance": row["tolerance"], **({"reason": row["reason"]} if row.get("reason") else {})}
                for row in circles["requirements"]
            ]
    if "output" in scenes:
        scene = scenes["output"]
        readability = inspect_readability(carrier_scene(scene, content.get("contract") or content_contract(scene)))
    counts = {
        "mathematical_correctness": _count([row["status"] for row in mathematics["output"]]),
        "content_coverage": _count(coverage_states),
        "visual_readability": _count([row["status"] for row in readability.get("labels", [])]),
    }
    outcome = output.get("compile", {}).get("outcome")
    compile_score = 1 if output.get("compile_success") else 0 if outcome not in (None, "unknown") else None
    scores = {"compile": compile_score, **{name: _percent(value) for name, value in counts.items()}}
    if "output" in scenes and not scenes["output"]["text"]:
        scores["visual_readability"] = 100.0
    return {"version": VERSION, "scores": scores, "counts": counts,
            "checks": {"mathematical_correctness": mathematics, "content_coverage": content, "visual_readability": readability},
            "source_hashes": {role: observation.get("metadata", {}).get("input_tikz_sha256")
                              for role, observation in (("target", target), ("output", output))},
            "errors": errors}
