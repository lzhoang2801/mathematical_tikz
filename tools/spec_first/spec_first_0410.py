"""Bounded Spec-First construction study for Onn 0410, Problem 2; no model calls."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import draw_instruction as drawing  # isort: skip -- existing MathPaper import setup

from evaluation.evaluator import _score_observations
from evaluation.tikz_coverage import connections
from evaluation.tikz_marks import right_angles as _right_angles
from evaluation.tikz_observations import compile_observe, read_scene
from evaluation.tikz_readability import inspect_readability

EXAMPLE = ROOT / "docs/examples/spec-first-0410"


def realize(R: float, r: float) -> dict:
    if not all(math.isfinite(v) and v > 0 for v in (R, r)):
        raise ValueError("Both radii must be finite and positive")
    d = R + r
    normal = np.array([(R - r) / d, 2 * math.sqrt(R * r) / d])
    o, op, a = np.array([0., 0.]), np.array([d, 0.]), np.array([R, 0.])
    b, c = R * normal, op + r * normal
    end_d, e = 2 * o - b, 2 * op - c
    # Solve the line intersection from its definition, without assuming I's closed form.
    u, _ = np.linalg.solve(np.column_stack((c - b, np.array([0., -1.]))), a - b)
    points = {"O": o, "O'": op, "A": a, "B": b, "C": c, "D": end_d, "E": e,
              "I": b + u * (c - b), "K": (end_d + e) / 2, "J": (o + op) / 2}
    return {name: p.tolist() for name, p in points.items()}


def check_math(points: dict, parameters: dict, tolerance: float = 0.005) -> dict:
    names = ("O", "O'", "A", "B", "C", "D", "E", "I", "J", "K")
    if any(name not in points or points[name] is None or len(points[name]) != 2
           or not all(math.isfinite(v) for v in points[name]) for name in names):
        return {"resolved_points": {"pass": False}}
    p = {name: np.asarray(points[name], dtype=float) for name in names}
    o, op, a, b, c, d, e, i, j, k = (p[name] for name in names)
    length = lambda v: float(np.linalg.norm(v))
    scale = length(op - o)
    if min(scale, length(a - o), length(a - op), length(c - b), length(i - a), length(e - d)) <= 1e-9:
        return {"nondegenerate_supports": {"pass": False}}
    cross = lambda u, v: float(u[0] * v[1] - u[1] * v[0])
    right = lambda u, v: abs(float(u @ v)) / max(length(u) * length(v), 1e-30)
    on_line = lambda x, u, v: abs(cross(x - u, v - u)) / (length(v - u) * scale)
    ro, rp = length(a - o), length(a - op)
    residuals = {
        "external_tangency": abs(scale - ro - rp) / scale,
        "given_radius_ratio": abs(ro / rp / (parameters["R"] / parameters["r"]) - 1),
        "B_on_circle_O": abs(length(b - o) - ro) / scale,
        "C_on_circle_Op": abs(length(c - op) - rp) / scale,
        "tangent_at_B": right(b - o, c - b),
        "tangent_at_C": right(c - op, c - b),
        "tangent_at_A": right(op - o, i - a),
        "I_on_BC": on_line(i, b, c),
        "D_antipode_B": length(b + d - 2 * o) / scale,
        "E_antipode_C": length(c + e - 2 * op) / scale,
        "K_midpoint_DE": length(k - (d + e) / 2) / scale,
        "J_midpoint_OOp": length(j - (o + op) / 2) / scale,
        "conclusion_B_A_E": on_line(a, b, e),
        "conclusion_C_A_D": on_line(a, c, d),
        "conclusion_equal_areas": abs(abs(cross(b - a, c - a)) - abs(cross(d - a, e - a))) / (2 * scale**2),
        "conclusion_right_angle_K": right(o - k, op - k),
        "conclusion_JI_perpendicular_BC": right(i - j, c - b),
        "conclusion_JK_equals_JO": abs(length(k - j) - length(o - j)) / scale,
        "conclusion_JI_equals_JO": abs(length(i - j) - length(o - j)) / scale,
    }
    return {name: {"pass": value <= tolerance, "residual": value} for name, value in residuals.items()}


def constructive(parameters: dict) -> str:
    return (EXAMPLE / "constructive-template.tikz").read_text(encoding="utf-8").replace("@R@", str(parameters["R"])).replace("@r@", str(parameters["r"]))


def numeric(parameters: dict) -> str:
    full = constructive(parameters)
    start = full.index(r"  \coordinate (O)")
    end = full.index(r"  \end{pgfinterruptboundingbox}") + len(r"  \end{pgfinterruptboundingbox}")
    coordinates = "\n".join(r"  \coordinate (" + name.replace("O'", "Oprime") + f") at ({x:.9f},{y:.9f});"
                            for name, (x, y) in realize(**parameters).items())
    return full[:start] + coordinates + full[end:]


def same_ray(points: dict, vertex: str, first: str, second: str, tolerance: float) -> bool:
    u = np.asarray(points[first]) - np.asarray(points[vertex])
    v = np.asarray(points[second]) - np.asarray(points[vertex])
    denominator = float(np.linalg.norm(u) * np.linalg.norm(v))
    return denominator > 0 and float(u @ v) > 0 and abs(float(u[0] * v[1] - u[1] * v[0])) <= tolerance * denominator


def check_render(observation: dict, parameters: dict, spec: dict) -> dict:
    if not observation["compile_success"]:
        raise RuntimeError("Compiler failed; inspect the saved observation and compiler log")
    scene = read_scene(observation)
    evidence = not scene["unsupported"] and not scene["unresolved"] and observation["raster_success"]
    checks = {"supported_evidence": {"pass": evidence, "unsupported": scene["unsupported"], "unresolved": scene["unresolved"]}}
    checks.update(check_math(scene["points"], parameters, spec["numeric_tolerance"]))
    if not evidence or "resolved_points" in checks or "nondegenerate_supports" in checks:
        return {"pass": False, "checks": checks}
    p = {name: np.asarray(value) for name, value in scene["points"].items()}
    scale = float(np.linalg.norm(p["O'"] - p["O"]))
    edges = connections(scene)
    expected = {tuple(sorted(pair)) for pair in spec["explicit_drawing_scope"]["solid_segments"]}
    actual = {tuple(edge["points"]) for edge in edges if not edge["dashed"]}
    checks["visible_segments"] = {"pass": actual == expected, "missing": sorted(expected - actual), "extra": sorted(actual - expected)}
    checks["point_names"] = {"pass": set(p) == set(spec["explicit_drawing_scope"]["points"])}
    checks["three_circles"] = {"pass": len(scene["circles"]) == 3, "observed": len(scene["circles"])}
    for center, through, dashed in (("O", ("A", "B", "D"), False), ("O'", ("A", "C", "E"), False), ("J", ("O", "O'", "K", "I"), True)):
        matches = [circle for circle in scene["circles"] if np.linalg.norm(np.asarray(circle["center"]) - p[center]) / scale <= spec["numeric_tolerance"]]
        residual = None
        if len(matches) == 1:
            circle = matches[0]
            residual = max(abs(float(np.linalg.norm(p[name] - circle["center"])) - circle["radius"]) / scale for name in through)
        checks[f"painted_circle_{center}"] = {"pass": len(matches) == 1 and residual <= spec["numeric_tolerance"] and matches[0]["dashed"] == dashed,
                                               "incidence_residual": residual}
    angles = _right_angles(scene, edges)
    required_angles = {(min(u, w), v, max(u, w)) for u, v, w in spec["explicit_drawing_scope"]["right_angle_marks"]}
    missing = []
    for u, vertex, w in sorted(required_angles):
        matched = any(vertex == v and any(same_ray(p, vertex, u, first, spec["numeric_tolerance"])
                                         and same_ray(p, vertex, w, second, spec["numeric_tolerance"])
                                         for first, second in ((a, b), (b, a))) for a, v, b in angles)
        if not matched:
            missing.append((u, vertex, w))
    checks["right_angle_marks"] = {"pass": not missing, "missing": missing}
    readable = inspect_readability(scene)
    checks["readability"] = {"pass": bool(readable["labels"]) and all(row["status"] == "pass" for row in readable["labels"]),
                             "labels": readable["labels"]}
    return {"pass": all(row["pass"] for row in checks.values()),
            "construction_pass": all(row["pass"] for name, row in checks.items() if name != "readability"), "checks": checks,
            "points_tex_pt": scene["points"], "circle_count": len(scene["circles"])}


def main() -> None:
    from tools.generate_instruction import load_pool

    spec = json.loads((EXAMPLE / "spec.json").read_text(encoding="utf-8"))
    sources, _, _ = load_pool()
    source = sources[spec["source_id"]]
    raw = (ROOT / spec["source_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["source_sha256"] or source["source_group"] != spec["source_group"]:
        raise ValueError("Source provenance changed")
    source_text = raw.decode("utf-8-sig")
    start = source_text.index(r"\begin{tikzpicture}", source_text.index(r"\begin{problem}", source_text.index(r"\newpage")))
    end = source_text.index(r"\end{tikzpicture}", start) + len(r"\end{tikzpicture}")
    original = source_text[start:end]
    (EXAMPLE / "original.tikz").write_text(original, encoding="utf-8")
    drawing.save_json(EXAMPLE / "source.json", source)
    template = (EXAMPLE / "instruction-template.txt").read_text(encoding="utf-8")
    base = spec["instances"]["reference"]
    code = constructive(base)
    cases = {name: (constructive(params), params, "valid") for name, params in spec["instances"].items()}
    cases["numeric_reference"] = (numeric(base), base, "valid")
    cases["wrong_midpoint"] = (code.replace("$(D)!0.5!(E)$", "$(D)!0.58!(E)$"), base, "K_midpoint_DE")
    cases["wrong_tangent_branch"] = (code.replace(r"{\RadiusP*\NormalY}", r"{-\RadiusP*\NormalY}"), base, "tangent_at_C")
    cases["supplied_figure"] = (original, base, "three_circles")
    cases["layout_repaired"] = (code.replace(r"label={below:$K$}", r"label={below left:$K$}"), base, "ready")
    sweep = []
    for R in (1.25, 2., 3., 4.5):
        for ratio in (0.2, 0.35, 0.5, 0.8, 1., 1.25, 2., 3.5):
            params = {"R": R, "r": R * ratio}
            checked = check_math(realize(**params), params, tolerance=1e-9)
            sweep.append({**params, "pass": all(row["pass"] for row in checked.values()),
                          "maximum_residual": max(row["residual"] for row in checked.values())})
    files = [Path(__file__), *(EXAMPLE / name for name in ("spec.json", "instruction-template.txt", "constructive-template.tikz"))]
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "complete": False, "model_calls": 0,
              "preparation": spec["preparation"], "unrendered_numeric_sweep": sweep, "cases": {},
              "file_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    drawing.save_json(EXAMPLE / "results.json", report)
    with drawing.CompilerClient(concurrency=1, base_url=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"), timeout=200, trust_env=False) as compiler:
        reference = None
        for name, (tikz, parameters, expectation) in cases.items():
            folder = EXAMPLE / "cases" / name
            folder.mkdir(parents=True, exist_ok=True)
            instruction = template.format(**parameters)
            (folder / "instruction.txt").write_text(instruction, encoding="utf-8")
            (folder / "target.tikz").write_text(tikz, encoding="utf-8")
            print(f"Compiling {name}", flush=True)
            observation = compile_observe(tikz, folder, compiler, preview=True)
            drawing.save_json(folder / "observations.json", observation)
            result = check_render(observation, parameters, spec)
            failures = [key for key, value in result["checks"].items() if not value["pass"]]
            if name == "reference":
                reference = observation
            # Changed-radius pairs have different instructions, so do not compare them with the base target.
            metrics = _score_observations(reference, observation) if parameters == base else None
            expectation_met = result["pass"] if expectation == "ready" else result["construction_pass"] if expectation == "valid" else expectation in failures
            row = {"parameters": parameters, "gate": result, "failures": failures, "shared_metrics_against_base": metrics,
                   "expectation": expectation, "expectation_met": expectation_met,
                   "image_path": observation["image_path"], "toolchain_id": observation["metadata"].get("toolchain_id")}
            report["cases"][name] = row
            drawing.save_json(EXAMPLE / "results.json", report)
            print(json.dumps({"case": name, "failures": failures, "metrics": metrics, "expectation_met": row["expectation_met"]}), flush=True)
    report["complete"] = True
    report["all_expectations_met"] = all(row["expectation_met"] for row in report["cases"].values()) and all(row["pass"] for row in sweep)
    drawing.save_json(EXAMPLE / "results.json", report)
    if not report["all_expectations_met"]:
        raise RuntimeError("Some cases need review; retain the actual failures in results.json")


if __name__ == "__main__":
    main()
