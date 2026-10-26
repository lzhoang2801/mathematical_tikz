"""One source-grounded worked example; run real compiler checks, without model calls."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import draw_instruction as drawing  # isort: skip -- sets the existing MathPaper import path

from evaluation.evaluator import _score_observations
from evaluation.tikz_coverage import connections
from evaluation.tikz_marks import right_angles as _right_angles
from evaluation.tikz_observations import compile_observe, read_scene
from evaluation.tikz_readability import inspect_readability

EXAMPLE = ROOT / "docs/examples/spec-first-altitude"


def check_geometry(points: dict, spec: dict) -> dict:
    """Test instruction facts on measured points, independent of the target's coordinates."""
    required = spec["display"]["points"]
    known = all(points.get(name) is not None and len(points[name]) == 2
                and all(math.isfinite(v) for v in points[name]) for name in required)
    checks = {"measured_points": {"pass": known}}
    if not known:
        return checks
    a, b, c, h = (points[name] for name in "ABCH")
    ab, ac, bc, ah = math.dist(a, b), math.dist(a, c), math.dist(b, c), math.dist(a, h)
    atol = spec["check_tolerances"]["normalized_geometry_atol"]
    distinct = max(ab, ac, bc) > 0 and min(math.dist(p, q) for p, q in combinations((a, b, c, h), 2)) > atol * max(ab, ac, bc)
    checks["distinct_points"] = {"pass": distinct}
    if not distinct:
        return checks
    lengths = spec["source_givens"]["lengths_cm"]
    for name, value in (("AC", ac), ("BC", bc)):
        expected, actual = lengths[name] / lengths["AB"], value / ab
        checks[f"ratio_{name}_AB"] = {"pass": math.isclose(actual, expected, rel_tol=spec["check_tolerances"]["ratio_rtol"]),
                                     "observed": actual, "expected": expected}
    u = (b[0] - a[0], b[1] - a[1])
    v = (c[0] - a[0], c[1] - a[1])
    base = (c[0] - b[0], c[1] - b[1])
    offset = (h[0] - b[0], h[1] - b[1])
    altitude = (h[0] - a[0], h[1] - a[1])
    measurements = {
        "AB_perpendicular_AC": abs(u[0] * v[0] + u[1] * v[1]) / (ab * ac),
        "H_on_BC": abs(base[0] * offset[1] - base[1] * offset[0]) / bc**2,
        "AH_perpendicular_BC": abs(altitude[0] * base[0] + altitude[1] * base[1]) / (ah * bc),
    }
    checks.update({name: {"pass": value <= atol, "observed": value, "maximum": atol}
                   for name, value in measurements.items()})
    t = (offset[0] * base[0] + offset[1] * base[1]) / bc**2
    checks["H_inside_BC"] = {"pass": atol < t < 1 - atol, "observed_t": t}
    return checks


def check_spec(observation: dict, spec: dict) -> dict:
    checks = {"compile": {"pass": observation["compile_success"]},
              "raster": {"pass": observation["raster_success"]}}
    if not all(row["pass"] for row in checks.values()):
        return {"pass": False, "checks": checks}
    scene = read_scene(observation)
    checks["resolved_evidence"] = {"pass": not scene["unsupported"] and not scene["unresolved"],
                                   "unsupported": scene["unsupported"], "unresolved": scene["unresolved"]}
    checks.update(check_geometry(scene["points"], spec))
    checks["point_names"] = {"pass": set(scene["points"]) == set(spec["display"]["points"])}
    if checks["measured_points"]["pass"] and not scene["unresolved"]:
        edges = connections(scene)
        observed = sorted("".join(edge["points"]) for edge in edges if not edge["dashed"])
        expected = sorted(spec["display"]["solid_segments"])
        checks["visible_segments"] = {"pass": observed == expected and not any(edge["dashed"] for edge in edges),
                                      "observed": observed, "expected": expected}
        angles = _right_angles(scene, edges)
        checks["right_angle_marks"] = {"pass": ("B", "A", "C") in angles
                                       and bool({("A", "H", "B"), ("A", "H", "C")} & angles),
                                       "observed": sorted(angles)}
        checks["no_extra_curves"] = {"pass": not scene["curves"]}
        readable = inspect_readability(scene)
        checks["label_readability"] = {"pass": bool(readable["labels"]) and all(row["status"] == "pass" for row in readable["labels"]),
                                       "labels": readable["labels"]}
        separation = min(math.dist(a, b) for a, b in combinations(scene["points"].values(), 2))
        threshold = spec["check_tolerances"]["minimum_point_separation_in_em"] * max(row["size"] for row in scene["text"])
        checks["point_spacing"] = {"pass": separation >= threshold, "minimum_tex_pt": separation, "threshold_tex_pt": threshold}
    return {"pass": all(row["pass"] for row in checks.values()), "checks": checks, "points_tex_pt": scene["points"]}


def calibration_cases(target: str) -> dict[str, tuple[str, set[str]]]:
    def change(old: str, new: str) -> str:
        if target.count(old) != 1:
            raise ValueError(f"Calibration mutation is stale: {old}")
        return target.replace(old, new)

    return {
        "target": (target, set()),
        "valid_scaled": (change("[thick,", "[scale=1.35,xshift=7mm,yshift=-4mm,thick,"), set()),
        "wrong_side_ratio": (change("(C) at (0,3)", "(C) at (0,2.5)"), {"ratio_AC_AB", "ratio_BC_AB"}),
        "wrong_altitude_foot": (change("$(B)!(A)!(C)$", "$(B)!0.5!(C)$"), {"AH_perpendicular_BC"}),
        "missing_altitude": (change(r"\draw (A) -- (H);", ""), {"visible_segments"}),
        "missing_right_mark": (change(r"\pic[draw,angle radius=6pt] {right angle=A--H--C};", ""), {"right_angle_marks"}),
        "colliding_label": (change(r"\node[circle,fill,inner sep=1.3pt,label={above right:$H$}] at (H) {};",
                                   r"\node[circle,fill,inner sep=1.3pt] at (H) {};" + "\n" + r"  \node[inner sep=0pt] at (H) {$H$};"), {"label_readability"}),
        "broken_tex": (change(r"\draw (A) -- (H);", r"\SpecFirstDeliberateUndefinedCommand"), {"compile"}),
    }


def main() -> None:
    from agent.prompts.tikz import TIKZ_PROMPT_VERSION

    from tools.generate_instruction import CORPUS, load_pool

    spec = json.loads((EXAMPLE / "spec.json").read_text(encoding="utf-8"))
    sources, _, _ = load_pool()
    source = sources[spec["source_id"]]
    row = next(row for row in drawing.load_rows(ROOT / "dataset/synthetic/generate.jsonl") if row["id"] == spec["sample_id"])
    instruction = (EXAMPLE / "instruction.txt").read_text(encoding="utf-8").strip()
    target = (EXAMPLE / "target.tikz").read_text(encoding="utf-8").strip()
    if row["instruction"] != instruction or row["target_tikz"].strip() != target:
        raise ValueError("Frozen example no longer matches the selected dataset candidate")
    if row["task"] != "Generate" or row["source_group"] != source["source_group"]:
        raise ValueError("Example source lineage does not match the candidate")
    parent = row["provenance"]["parent_sources"][spec["source_id"]]
    if any(parent[key] != source[key] for key in ("source_sha256", "source_text_sha256")):
        raise ValueError("Candidate source hashes are stale")
    for path in source.get("image_paths", []):
        if not (CORPUS / path).is_file():
            raise FileNotFoundError(path)
    drawing.save_json(EXAMPLE / "original-record.json", row)
    drawing.save_json(EXAMPLE / "source.json", source)

    files = [EXAMPLE / name for name in ("instruction.txt", "spec.json", "target.tikz")]
    files += [Path(__file__), *sorted((ROOT / "evaluation").glob("*.py"))]
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "sample_id": row["id"],
              "preparation": spec["preparation"], "model_calls_this_run": 0,
              "prompt_version": TIKZ_PROMPT_VERSION,
              "file_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
              "cases": {}}
    with drawing.CompilerClient(concurrency=1, base_url=os.environ.get("COMPILER_URL", "http://127.0.0.1:18080"), timeout=200, trust_env=False) as compiler:
        reference = None
        for name, (tikz, expected_failures) in calibration_cases(target).items():
            folder = EXAMPLE / "cases" / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "input.tikz").write_text(tikz + "\n", encoding="utf-8")
            print(f"Compiling {name}", flush=True)
            observation = compile_observe(tikz, folder, compiler, preview=True)
            drawing.save_json(folder / "observations.json", observation)
            checked = check_spec(observation, spec)
            if name == "target":
                if not checked["pass"]:
                    drawing.save_json(folder / "checks.json", checked)
                    raise RuntimeError("Target failed its specification; inspect cases/target/checks.json")
                reference = observation
            metrics = _score_observations(reference, observation)
            failures = {key for key, value in checked["checks"].items() if not value["pass"]}
            calibration_pass = expected_failures <= failures if expected_failures else checked["pass"]
            result = {"spec": checked, "metrics": metrics, "expected_failures": sorted(expected_failures),
                      "failed_checks": sorted(failures), "calibration_pass": calibration_pass,
                      "image_path": observation["image_path"], "toolchain_id": observation["metadata"].get("toolchain_id")}
            drawing.save_json(folder / "checks.json", result)
            report["cases"][name] = result
            drawing.save_json(EXAMPLE / "results.json", report)
            print(json.dumps({"case": name, "metrics": metrics, "spec_pass": checked["pass"], "failed": sorted(failures), "calibration_pass": calibration_pass}), flush=True)
    if not all(row["calibration_pass"] for row in report["cases"].values()):
        raise RuntimeError("Calibration failed; inspect results.json")


if __name__ == "__main__":
    main()
