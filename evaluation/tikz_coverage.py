"""Compare emitted content after similarity alignment of resolved mathematical points."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
from shapely import affinity
from shapely.geometry import Point
from shapely.ops import unary_union

PATH_TOLERANCE = 0.006
COVERAGE_MINIMUM = 0.985


def _alignment(target: np.ndarray, output: np.ndarray, *, allow_reflection: bool = False) -> tuple[list[float], float, bool]:
    a, b = output - output.mean(axis=0), target - target.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    rotation = u @ vt
    reflected = bool(np.linalg.det(rotation) < 0)
    if reflected and not allow_reflection:
        u[:, -1] *= -1
        rotation = u @ vt
    scale = float(np.sum((a @ rotation) * b) / np.sum(a * a))
    if scale <= 0 or not math.isfinite(scale):
        raise ValueError("No positive similarity alignment")
    shift = target.mean(axis=0) - scale * output.mean(axis=0) @ rotation
    matrix = [scale * rotation[0, 0], scale * rotation[1, 0], scale * rotation[0, 1], scale * rotation[1, 1], shift[0], shift[1]]
    error = float(np.linalg.norm(scale * output @ rotation + shift - target, axis=1).max())
    return [float(x) for x in matrix], error, reflected


def _compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return max(abs(x - y) for x, y in zip(a["color"], b["color"])) < 0.05 and a.get("dashed") == b.get("dashed") and abs(a.get("opacity", 1) - b.get("opacity", 1)) < 0.05


def _coverage(source: list[dict[str, Any]], other: list[dict[str, Any]], tolerance: float, *, filled: bool = False) -> tuple[list[dict[str, Any]], float | None]:
    results = []
    for item in source:
        geometry = item["geometry"]
        support = unary_union([o["geometry"] for o in other if _compatible(item, o)])
        parts = [geometry] if filled else item.get("components", [geometry])
        fractions = []
        tolerances = []
        for part in parts:
            amount = part.area if filled else part.length
            # Protect a short edge even when emitted inside one long PDF path.
            local_tolerance = tolerance if filled else min(tolerance, max(0.02, part.length * 0.02))
            covered = part.intersection(support.buffer(local_tolerance))
            fraction = (covered.area if filled else covered.length) / amount if amount > 1e-9 else 1.0
            fractions.append(min(1.0, fraction))
            tolerances.append(local_tolerance)
        fraction = min(fractions, default=1.0)
        results.append({"path": item["path"], "covered_fraction": fraction, "component_coverage": fractions, "component_tolerance_pt": tolerances, "matched": fraction >= COVERAGE_MINIMUM})
    # Union equal paint styles before measuring so splitting or repeating a PDF
    # path cannot change its weight. Component minima remain the defect guard.
    styles: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for item in source:
        key = (tuple(item["color"]), item.get("dashed"), item.get("opacity", 1))
        styles.setdefault(key, []).append(item)
    total, covered_total = 0.0, 0.0
    for items in styles.values():
        geometry = unary_union([item["geometry"] for item in items])
        support = unary_union([item["geometry"] for item in other if _compatible(items[0], item)])
        covered = geometry.intersection(support.buffer(tolerance))
        total += geometry.area if filled else geometry.length
        covered_total += covered.area if filled else covered.length
    return results, min(100.0, 100 * covered_total / total) if total > 1e-9 else None


def _path_visibility(scene: dict[str, Any], geometry: Any, color: tuple[float, ...], width: float = 1.0) -> float:
    if geometry.is_empty or geometry.length <= 0:
        return 0.0
    paths = list(geometry.geoms) if hasattr(geometry, "geoms") else [geometry]
    seen, count = 0, 0
    pixels, scale = scene["pixels"], scene["raster_scale"]
    expected = np.asarray(color) * 255
    radius = max(1, min(5, math.ceil(width * scale / 2)))
    for line in paths:
        for distance in np.linspace(0, line.length, max(5, min(800, math.ceil(line.length * scale)))):
            point = line.interpolate(float(distance))
            x, y = int(point.x * scale), int(point.y * scale)
            patch = pixels[max(0, y - radius):min(pixels.shape[0], y + radius + 1), max(0, x - radius):min(pixels.shape[1], x + radius + 1)]
            count += 1
            if patch.size and np.any(np.max(np.abs(patch.astype(float) - expected), axis=2) < 90):
                seen += 1
    return seen / count if count else 0.0


def compare_content(
    target: dict[str, Any], output: dict[str, Any], *,
    allow_reflection: bool = False, distance_tolerance: float = 0.005,
) -> dict[str, Any]:
    """Compare required labels, actual painted paths and sampled visibility."""
    t, o = target, output
    tc, oc = Counter(label["text"] for label in t["text"]), Counter(label["text"] for label in o["text"])
    checks = {name: {"status": "unknown", "reason": "Resolved point correspondence is required for alignment"}
              for name in ("strokes", "fills", "point_markers", "orientation", "annotations", "visibility")}
    checks["text"] = {"status": "match" if tc == oc else "different",
                      "missing": list((tc - oc).elements()), "extra": list((oc - tc).elements())}
    labels = sorted(label for label in t["points"].keys() & o["points"].keys()
                    if t["points"][label] is not None and o["points"][label] is not None)
    if len(labels) < 2:
        return {"checks": checks, "alignment": None, "limitations": ["At least two resolved labeled points are required for path alignment"]}
    try:
        tp = np.asarray([t["points"][label] for label in labels], dtype=float)
        op = np.asarray([o["points"][label] for label in labels], dtype=float)
        extent = float(np.linalg.norm(tp[:, None] - tp[None, :], axis=2).max())
        if extent <= 0 or not np.isfinite(tp).all() or not np.isfinite(op).all():
            raise ValueError("No finite nondegenerate point configuration for path alignment")
        matrix, alignment_error, reflected = _alignment(tp, op, allow_reflection=True)
    except (ValueError, np.linalg.LinAlgError) as error:
        return {"checks": checks, "alignment": None, "limitations": [str(error)]}
    rank = min(np.linalg.matrix_rank(tp - tp.mean(axis=0)), np.linalg.matrix_rank(op - op.mean(axis=0)))
    checks["orientation"] = {
        "status": "different" if reflected and rank == 2 and not allow_reflection else "match",
        "reflected_best_fit": reflected if rank == 2 else None,
        "reflection_allowed": allow_reflection,
        "meaning": "Chirality under similarity alignment; collinear configurations have no planar chirality",
    }
    alignment = {"output_pdf_to_target_pdf": matrix, "reference_extent_pt": extent, "similarity_residual": alignment_error / extent}
    aligned = {kind: [{**item, "geometry": affinity.affine_transform(item["geometry"], matrix), "components": [affinity.affine_transform(part, matrix) for part in item.get("components", [])]} for item in o[kind]] for kind in ("strokes", "fills")}
    # Only uniquely matched, executed annotation paths get a local glyph scale.
    # Construction strokes and nonstandard/manual glyphs retain strict coverage.
    annotation_matches = []
    target_keys = Counter(item.get("annotation_key") for item in t["strokes"] if item.get("annotation_key"))
    output_keys = Counter(item.get("annotation_key") for item in aligned["strokes"] if item.get("annotation_key"))
    for item in aligned["strokes"]:
        key = item.get("annotation_key")
        if not key or target_keys[key] != 1 or output_keys[key] != 1:
            continue
        reference = next(other for other in t["strokes"] if other.get("annotation_key") == key)
        vertex = reference["annotation_vertex"]
        output_vertex = affinity.affine_transform(Point(item["annotation_vertex"]), matrix)
        if output_vertex.distance(Point(vertex)) > extent * distance_tolerance:
            continue
        radius = max(Point(vertex).distance(Point(xy)) for part in reference["components"] for xy in part.coords)
        observed_radius = max(output_vertex.distance(Point(xy)) for part in item["components"] for xy in part.coords)
        if min(radius, observed_radius) <= 0:
            continue
        factor = radius / observed_radius
        # Translation here is bounded by the same observed point alignment; the
        # separate point geometry check still detects changes to the anchors.
        glyph_matrix = [factor, 0, 0, factor, vertex[0] - factor * output_vertex.x, vertex[1] - factor * output_vertex.y]
        item["geometry"] = affinity.affine_transform(item["geometry"], glyph_matrix)
        item["components"] = [affinity.affine_transform(part, glyph_matrix) for part in item["components"]]
        item["reference_annotation_path"] = reference["path"]
        annotation_matches.append({"key": key, "target_path": reference["path"], "output_path": item["path"], "local_positive_scale": factor})
    checks["annotations"] = {"status": "observed", "same_runtime_annotations": target_keys == output_keys, "target": t["annotations"], "output": o["annotations"], "matches": annotation_matches, "meaning": "Runtime provenance permits local angle-glyph scaling; emitted-path coverage still determines presence and wedge, including equivalent manual paths"}
    for kind in ("strokes", "fills"):
        forward, forward_pct = _coverage(t[kind], aligned[kind], extent * PATH_TOLERANCE, filled=kind == "fills")
        reverse, reverse_pct = _coverage(aligned[kind], t[kind], extent * PATH_TOLERANCE, filled=kind == "fills")
        checks[kind] = {"status": "match" if all(r["matched"] for r in forward + reverse) else "different", "target_coverage": forward, "output_coverage": reverse,
                        "target_coverage_pct": forward_pct, "output_coverage_pct": reverse_pct,
                        "measurement": "Covered union length/area divided by total union length/area, summed over paint styles"}
    marker_matches = []
    for source, other, transform_marker in ((t, o, True), (o, t, False)):
        for marker in source["markers"]:
            point = marker["geometry"] if transform_marker else affinity.affine_transform(marker["geometry"], matrix)
            distances = [point.distance(affinity.affine_transform(m["geometry"], matrix) if transform_marker else m["geometry"]) for m in other["markers"] if _compatible(marker, m)]
            marker_matches.append(bool(distances and min(distances) <= extent * PATH_TOLERANCE))
    checks["point_markers"] = {"status": "observed", "same_markers": len(t["markers"]) == len(o["markers"]) and all(marker_matches), "meaning": "Point dots are optional glyphs, not mathematical point identities", "target_count": len(t["markers"]), "output_count": len(o["markers"])}
    transform = np.array([[matrix[0], matrix[1], matrix[4]], [matrix[2], matrix[3], matrix[5]], [0, 0, 1]])
    inverse = np.linalg.inv(transform)
    inv = [inverse[0, 0], inverse[0, 1], inverse[1, 0], inverse[1, 1], inverse[0, 2], inverse[1, 2]]
    visibility = []
    for stroke in t["strokes"]:
        baseline = _path_visibility(t, stroke["geometry"], stroke["color"], stroke["width"])
        matching_glyph = next((item for item in aligned["strokes"] if item.get("reference_annotation_path") == stroke["path"]), None)
        if matching_glyph is not None:
            native = next(item for item in o["strokes"] if item["path"] == matching_glyph["path"])
            observed = _path_visibility(o, native["geometry"], native["color"], native["width"])
        else:
            observed = _path_visibility(o, affinity.affine_transform(stroke["geometry"], inv), stroke["color"], stroke["width"])
        visibility.append({"target_path": stroke["path"], "target_ink_fraction": baseline, "output_ink_fraction": observed,
                           "graded": not stroke["dashed"], "matched": observed >= baseline - 0.18})
    checks["visibility"] = {"status": "match" if all(v["matched"] for v in visibility if v["graded"]) else "different", "paths": visibility,
                            "meaning": "Sampled solid-stroke raster support; dashed paths are diagnostic because cadence and phase are ungraded; fill compositing is unmeasured"}
    for kind in ("strokes", "fills"):
        check = checks[kind]
        components = []
        for side in ("target", "output"):
            records = check[side + "_coverage"]
            components.extend(value for record in records for value in record["component_coverage"])
        check["worst_component_coverage_pct"] = 100 * min(components) if components else None
    return {"checks": checks, "alignment": alignment, "limitations": []}
