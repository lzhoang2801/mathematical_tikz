"""Frozen source checks for three reviewed synthetic_new pilot cases.

Targets and these checks stay outside the drawing model's context.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.requirements import Requirements, check_scene
from evaluation.tikz_geometry import measure_circular_path

CASES = {
    "isosceles": "356b9bf0-dd12-56f1-9e6e-9541cb158b3e",
    "tangency": "56defb1d-cefc-5a8b-a937-4fca32772c7a",
    "reflection": "1ac1499f-b917-5412-9d46-c0661b7c7d54",
}


def requirements(case: str) -> Requirements:
    def relation(kind, *points):
        return {"id": kind + ":" + "-".join(points), "kind": kind, "points": points}

    if case == "isosceles":
        points = ["A", "B", "M", "O"]
        relations = [relation("noncollinear", "M", "A", "B"), relation("midpoint", "O", "A", "B"),
                     relation("equal_length", "M", "A", "M", "B"), relation("perpendicular", "M", "O", "A", "B"),
                     relation("equal_angle", "A", "M", "O", "O", "M", "B")]
        segments = [("M", "A"), ("M", "B"), ("A", "B"), ("M", "O")]
        extra = {"right_angles": [("M", "O", "B")], "equal_segments": [[("M", "A"), ("M", "B")]]}
    elif case == "tangency":
        points = ["O", "M", "H", "K"]
        relations = [relation("inside_angle", "M", "O", "H", "K"),
                     relation("perpendicular", "M", "H", "O", "H"), relation("perpendicular", "M", "K", "O", "K"),
                     relation("equal_length", "M", "H", "M", "K"), relation("noncollinear", "O", "H", "K")]
        segments = [("O", "H"), ("O", "K"), ("M", "H"), ("M", "K")]
        extra = {"circles": [{"center": "M", "through": "H"}], "right_angles": [("O", "H", "M"), ("O", "K", "M")],
                 "equal_segments": [[("M", "H"), ("M", "K")]]}
    else:
        if case != "reflection":
            raise ValueError(case)
        points = ["A", "B", "B'", "C", "H", "M"]
        relations = [relation("same_side", "A", "B", "M", "H"), relation("midpoint", "H", "B", "B'"),
                     relation("perpendicular", "B", "B'", "M", "H"), relation("on_line", "C", "M", "H"),
                     relation("on_segment", "C", "A", "B'"), relation("distinct", "C", "M"),
                     relation("noncollinear", "M", "B", "B'"), relation("equal_length", "M", "B", "M", "B'")]
        segments = [("A", "C"), ("C", "B"), ("A", "M"), ("M", "B"), ("M", "B'"), ("B", "B'"), ("M", "H"), ("C", "H")]
        extra = {}
    return Requirements(points=points, relations=relations, segments=[{"points": edge} for edge in segments], **extra)


def matching_angle_arcs(scene: dict) -> bool:
    """Require both bisected sectors to have the same nonempty arc-radius pattern.

Measure PDF ink at observed radii; allow arbitrary valid arc sizes, unlike a
fixed 7 pt template. No construction program coordinates are used.
"""
    points = scene["points"]
    if any(points.get(name) is None for name in ("A", "M", "O", "B")):
        return False
    vertex = np.asarray(points["M"])
    ink = unary_union([curve["geometry"] for curve in scene["curves"] if not curve["dashed"]])
    radii = []
    for curve in scene["curves"]:
        arc = measure_circular_path(list(curve["geometry"].coords))
        if (arc and not arc["closed"] and math.dist(arc["center"], vertex) <= 0.3 and arc["radius"] > 1
                and not any(abs(arc["radius"] - value) <= 0.3 for value in radii)):
            radii.append(arc["radius"])
    patterns = []
    for a, b in (("A", "O"), ("O", "B")):
        u, v = np.asarray(points[a]) - vertex, np.asarray(points[b]) - vertex
        first, last = math.atan2(u[1], u[0]), math.atan2(v[1], v[0])
        span = (last - first) % math.tau
        if span > math.pi:
            first, span = last, math.tau - span
        pattern = []
        for index, radius in enumerate(radii):
            theta = np.linspace(first, first + span, 65)
            arc = LineString(vertex + radius * np.column_stack((np.cos(theta), np.sin(theta))))
            if arc.length > 0 and arc.intersection(ink.buffer(0.25)).length / arc.length >= 0.985:
                pattern.append(index)
        patterns.append(pattern)
    return bool(patterns[0] and patterns[0] == patterns[1])


def check_output(case: str, scene: dict) -> dict:
    req = requirements(case)
    checked = check_scene(req, scene)
    extra = []
    if case == "isosceles":
        extra.append({"id": "matching_bisector_arcs", "status": "pass" if matching_angle_arcs(scene) else "fail"})
    if case == "tangency":
        # Filled arrowheads are not exposed by the shared scene observer; review
        # their presence visually. Here check the painted support and ray label.
        points = scene["points"]
        for name, label in (("H", "x"), ("K", "y")):
            valid = False
            if points.get("O") is not None and points.get(name) is not None:
                origin, foot = np.asarray(points["O"]), np.asarray(points[name])
                vector = foot - origin
                squared = float(vector @ vector)
                for stroke in scene["strokes"]:
                    endpoints = list(stroke["geometry"].geoms) if hasattr(stroke["geometry"], "geoms") else [stroke["geometry"]]
                    tips = [np.asarray(p) for part in endpoints for p in (part.coords[0], part.coords[-1])]
                    tip = max(tips, key=lambda p: float((p - origin) @ vector))
                    offset = tip - origin
                    t = float(offset @ vector) / squared if squared else 0
                    error = np.linalg.norm(offset - t * vector) / math.sqrt(squared) if squared else math.inf
                    labels = [row for row in scene["text"] if row["text"] == label]
                    close = any(math.dist(tip, [(row["bbox"][0] + row["bbox"][2]) / 2,
                                                        (row["bbox"][1] + row["bbox"][3]) / 2]) < 3 * row["size"] for row in labels)
                    if t > 1 and error < 0.006 and close:
                        valid = True
            extra.append({"id": "ray_support_and_label:" + label, "status": "pass" if valid else "fail"})
    if case == "reflection":
        extra.append({"id": "line_label:d", "status": "pass" if any(row["text"] == "d" for row in scene["text"]) else "fail"})
    checked["checks"].extend(extra)
    checked["status"] = "pass" if all(row["status"] == "pass" for row in checked["checks"]) else "held"
    relation_ids = {relation.id for relation in req.relations}
    checked["mathematics_pass"] = all(row["status"] == "pass" for row in checked["checks"] if row["id"] in relation_ids)
    checked["failed_checks"] = [row["id"] for row in checked["checks"] if row["status"] != "pass"]
    return checked


def calibration_variants(case: str, target: str) -> dict[str, tuple[str, list[str]]]:
    """Freeze deliberate failures and a valid similarity transform before drawing."""
    old, new, failure = {
        "isosceles": ("$(A)!0.5!(B)$", "$(A)!0.35!(B)$", "midpoint:O-A-B"),
        "tangency": ("$(O)!(M)!(Y)$", "$(O)!0.3!(Y)$", "perpendicular:M-K-O-K"),
        "reflection": ("$(B)!2!(H)$", "$(B)!1.7!(H)$", "midpoint:H-B-B'"),
    }[case]
    if target.count(old) != 1:
        raise ValueError("Stale calibration mutation: " + case)
    variants = {"target": (target, []),
                "valid_similarity": (target.replace("[thick,", "[scale=1.2,rotate=15,xshift=5mm,thick,", 1), []),
                "wrong_geometry": (target.replace(old, new), [failure])}
    if case == "isosceles":
        line = r"  \pic[draw,angle radius=18pt] {angle=O--M--B};"
        if line not in target:
            raise ValueError("Stale missing-arc calibration")
        variants["missing_arc"] = (target.replace(line, ""), ["matching_bisector_arcs"])
    return variants
