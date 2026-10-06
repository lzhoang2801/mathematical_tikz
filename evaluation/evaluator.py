"""Evaluate four declared dimensions using original-PDF evidence and fixed requirements."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import httpx

from evaluation.tikz_coverage import COVERAGE_MINIMUM, PATH_TOLERANCE, compare_content
from evaluation.tikz_geometry import compare_point_geometry, evaluate_checks
from evaluation.tikz_observations import compile_observe as observe_tikz
from evaluation.tikz_observations import read_scene
from evaluation.tikz_readability import compare_readability

VERSION = "tikz-evaluation:v6"
DIMENSIONS = {
    "compile": ("compile",),
    "mathematical_correctness": ("point_geometry", "orientation"),
    "content_coverage": ("text", "strokes", "fills", "visibility"),
    "visual_readability": ("readability",),
}
CHECKS = ("compile", "point_geometry", "orientation", "text", "strokes", "fills",
          "annotations", "point_markers", "visibility", "readability")


def _status(checks: list[dict[str, Any]], limitations: list[str] | None = None) -> str:
    statuses = {check["status"] for check in checks}
    return ("different" if statuses & {"different", "fail"} else
            "unknown" if "unknown" in statuses or limitations else
            "review" if "review" in statuses else "match")


def _compile(target: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    unavailable = output.get("compile", {}).get("outcome") == "unknown"
    status = "unknown" if unavailable else "match" if target.get("compile_success") and output.get("compile_success") else "different" if target.get("compile_success") else "unknown"
    return {"status": status, "target": target.get("compile_success", False), "output": output.get("compile_success", False),
            "target_outcome": target.get("compile", {}).get("outcome"), "output_outcome": output.get("compile", {}).get("outcome")}


def _point_radius(scene: dict[str, Any]) -> float:
    points = [point for point in scene["points"].values() if point is not None]
    diameter = max((math.dist(a, b) for a in points for b in points), default=0.0)
    bound = max((point.get("pdf_coordinate_error_bound_pt", 0.0) for point in scene["bindings"].values()), default=0.0)
    return bound / diameter if diameter > 0 else 0.0


def _requirements(rubric: list[dict[str, Any]], bindings: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(rubric, list):
        raise TypeError("evaluation_rubric must be a list")
    results, ids = [], set()
    for criterion in rubric:
        if not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str) or not criterion["id"] or criterion["id"] in ids or criterion.get("dimension") not in DIMENSIONS:
            raise ValueError("Rubric criteria require unique IDs and a supported dimension")
        ids.add(criterion["id"])
        evidence = {}
        for role in ("target", "output"):
            points = {
                label: {"status": "measured", "x": point["pdf_x"], "y": point["pdf_y"], "unit": "pdf_pt",
                        "frame": "original_pdf", "evidence_id": point.get("evidence_id")}
                for label, point in bindings.get(role, {}).items() if point.get("status") == "measured"
            }
            evidence[role] = evaluate_checks(criterion.get("checks", []), points)
        statuses = [check["status"] for check in evidence["output"]]
        status = "fail" if "fail" in statuses else "pass" if statuses and all(value == "pass" for value in statuses) else "unknown"
        reason = None if statuses else "No executable predicate supplied; reference agreement does not certify this requirement"
        if criterion["dimension"] != "mathematical_correctness":
            status, reason = "unknown", "Coordinate predicates do not certify compile, content coverage or readability requirements"
        results.append({"id": criterion["id"], "dimension": criterion["dimension"], "status": status, **evidence, "reason": reason})
    digest = hashlib.sha256(json.dumps(rubric, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return {"rubric_sha256": digest, "results": results}


def _measurements(checks: dict[str, Any], reference_status: str, unsupported: bool) -> dict[str, Any]:
    metrics = {}
    geometry, readability = checks["point_geometry"], checks["readability"]
    observed = readability.get("output", {})

    def measure(name: str, value: float | None, n: int, *, partial: bool = False, not_applicable: bool = False) -> None:
        if value is not None and not math.isfinite(value):
            raise ValueError(f"Nonfinite measurement: {name}")
        metrics[name] = {"value": value, "state": "not_applicable" if not_applicable else "unavailable" if value is None else "partial" if partial else "observed", "n_observations": n}

    compiled = checks["compile"]
    compile_value = 100.0 if compiled["output"] else 0.0 if compiled["output_outcome"] not in (None, "unknown") or compiled["status"] == "different" else None
    measure("compile_success_pct", compile_value, int(compile_value is not None))
    measure("reference_match_pct", 100.0 if reference_status == "match" else 0.0 if reference_status == "different" else None, 1)
    count = len(geometry.get("labels", []))
    pairs = count * (count - 1) // 2
    partial = geometry["status"] == "unknown" or any(geometry.get(name) for name in ("missing", "extra", "unresolved_target", "unresolved_output", "invalid_target", "invalid_output"))
    measure("point_distance_max_error", geometry.get("global_distance", {}).get("max_abs_error"), pairs, partial=partial)
    ratios = geometry.get("local_ratios", {})
    measure("point_ratio_max_log_error", ratios.get("max_abs_log_error"), ratios.get("evaluated_pairs", 0), partial=partial or bool(ratios.get("unresolved_pairs")))
    for name, prefix in (("strokes", "stroke"), ("fills", "fill")):
        check = checks[name]
        for side in ("target", "output"):
            measure(prefix + "_" + side + "_coverage_pct", check.get(side + "_coverage_pct"), len(check.get(side + "_coverage", [])), partial=unsupported or partial, not_applicable=not unsupported and check.get(side + "_coverage") == [])
        measure(prefix + "_worst_component_coverage_pct", check.get("worst_component_coverage_pct"), sum(len(row.get("component_coverage", [row["covered_fraction"]])) for side in ("target", "output") for row in check.get(side + "_coverage", [])), partial=unsupported or partial, not_applicable=not unsupported and check.get("target_coverage") == [] and check.get("output_coverage") == [])
    complete = readability.get("collision_measurement_complete", False)
    resolved = observed.get("resolved_outline_label_count", 0)
    no_labels = complete and observed.get("text_count") == 0
    measure("stroke_collision_ink_pct", readability.get("collision_ink_pct"), resolved, partial=not complete, not_applicable=no_labels)
    collisions = sum(row.get("basis") == "font_outline" for row in observed.get("stroke_collision_evidence", []))
    measure("stroke_collision_label_pct", 100 * collisions / resolved if resolved else None, resolved, partial=not complete, not_applicable=no_labels)
    for name, key in (("text_overlap_count", "text_overlap_candidates"), ("glyph_overlap_count", "glyph_overlap_candidates"), ("clipped_label_count", "clipped_text")):
        measure(name, float(len(observed.get(key, []))) if "output" in readability else None, observed.get("text_count", 0), partial=not complete)
    measure("new_stroke_collision_count", float(len(readability.get("new_stroke_collision_candidates", []))) if "output" in readability else None, observed.get("text_count", 0), partial=not complete or bool(readability.get("target", {}).get("outline_issues")))
    paths = checks["visibility"].get("paths", [])
    measure("output_path_ink_support_pct", 100 * sum(path["output_ink_fraction"] for path in paths) / len(paths) if paths else None, len(paths), partial=unsupported or partial, not_applicable=not unsupported and not partial and checks["visibility"].get("paths") == [])
    return metrics


def evaluate(
    target: dict[str, Any], output: dict[str, Any], *,
    evaluation_rubric: list[dict[str, Any]] | None = None,
    allow_reflection: bool = False, distance_tolerance: float = 0.005,
    relative_tolerance: float = 0.02,
) -> dict[str, Any]:
    """Evaluate reference fidelity and the supported predicates of a frozen rubric."""
    checks = {name: {"status": "unknown", "reason": "Comparison prerequisites unavailable"} for name in CHECKS}
    checks["compile"] = _compile(target, output)
    result = {
        "version": VERSION, "meaning": "reference fidelity and explicit fixed predicates; not source/target approval",
        "policy": {
            "translation": True, "uniform_scale": True, "rotation": True, "reflection": allow_reflection,
            "point_tolerance": distance_tolerance, "relative_tolerance": relative_tolerance,
            "path_tolerance": PATH_TOLERANCE, "minimum_path_coverage": COVERAGE_MINIMUM,
            "component_relative_path_tolerance": 0.02, "component_path_floor_pdf_pt": 0.02,
            "tolerances": "experimental; checked on development controls only, not held-out calibrated",
            "ungraded_style": ["stroke width", "dash cadence and phase", "marker size", "font face", "unambiguous point-label reflow"],
        },
        "checks": checks, "limitations": [], "bindings": {},
        "evidence": {role: {"source": observation.get("metadata", {}), "pdf_path": observation.get("pdf_path"),
                            "artifacts": observation.get("artifacts", {})}
                     for role, observation in (("target", target), ("output", output))},
    }
    if checks["compile"]["status"] == "match":
        try:
            t, o = read_scene(target), read_scene(output)
        except (OSError, ValueError, RuntimeError) as error:
            result["limitations"].append(str(error))
        else:
            result["observation_issues"] = {"target": t["unsupported"], "output": o["unsupported"]}
            result["limitations"] = sorted(set(t["unsupported"] + o["unsupported"]))
            result["bindings"] = {"target": t["bindings"], "output": o["bindings"],
                                  "unresolved_target": t["unresolved"], "unresolved_output": o["unresolved"]}
            geometry = compare_point_geometry(
                t["points"], o["points"], distance_tolerance=distance_tolerance,
                relative_tolerance=relative_tolerance,
                target_uncertainty=_point_radius(t), output_uncertainty=_point_radius(o),
            )
            geometry["measurement"] = "Labeled mathematical points; coordinates are independent of label glyph placement"
            geometry["uncertainty_scope"] = "Reported serialization error; not a proof of label attachment or unsupported canvas transforms"
            checks["point_geometry"] = geometry
            checks["readability"] = compare_readability(t, o)
            content = compare_content(t, o, allow_reflection=allow_reflection, distance_tolerance=distance_tolerance)
            checks.update(content["checks"])
            result["limitations"].extend(content["limitations"])
            if content["alignment"] is not None:
                result["alignment"] = content["alignment"]
    reference = _status(list(checks.values()), result["limitations"])
    result["reference_status"] = result["status"] = reference
    if evaluation_rubric is not None:
        requirements = _requirements(evaluation_rubric, result["bindings"])
        result["requirements"] = requirements
        result["status"] = _status([{"status": reference}, *requirements["results"]])
    result["metrics"] = _measurements(checks, reference, bool(result.get("observation_issues") and any(result["observation_issues"].values())))
    result["dimensions"] = {}
    for dimension, names in DIMENSIONS.items():
        requirements = [criterion for criterion in result.get("requirements", {}).get("results", []) if criterion["dimension"] == dimension]
        evidence = ([{"status": checks["readability"].get("output_status", "unknown")}]
                    if dimension == "visual_readability" else [checks[name] for name in names])
        status = _status([*evidence, *requirements], result["limitations"])
        result["dimensions"][dimension] = {"status": status, "checks": list(names), "requirements": [criterion["id"] for criterion in requirements]}
    compiled = result["metrics"]["compile_success_pct"]["value"]
    compile_requirements = [criterion for criterion in result.get("requirements", {}).get("results", []) if criterion["dimension"] == "compile"]
    result["dimensions"]["compile"]["status"] = _status([
        {"status": "unknown" if compiled is None else "match" if compiled else "different"}, *compile_requirements])
    result["dimensions"]["mathematical_correctness"]["scope"] = "Observed labeled-point proportions, orientation and supplied coordinate predicates"
    result["dimensions"]["content_coverage"]["scope"] = "Rendered-label inventory and painted-path fidelity to the supplied target"
    result["dimensions"]["visual_readability"]["scope"] = "Glyph/stroke collision screening; dash gaps, fills and final compositing are not certified"
    result["limitations"].append("Absolute physical scale, 3D truth, target approval and instruction-allowed alternative geometry are outside this reference comparison.")
    return result


def evaluate_tikz(
    target_tikz: str, output_tikz: str, artifact_dir: Path, compiler_http: httpx.Client, *,
    evaluation_rubric: list[dict[str, Any]] | None = None, **policy: Any,
) -> dict[str, Any]:
    """Compile both inputs through the shared harness and evaluate their original artifacts."""
    target = observe_tikz(target_tikz, artifact_dir / "target", compiler_http)
    output = observe_tikz(output_tikz, artifact_dir / "output", compiler_http)
    return {"target": target, "output": output, "comparison": evaluate(target, output, evaluation_rubric=evaluation_rubric, **policy)}
