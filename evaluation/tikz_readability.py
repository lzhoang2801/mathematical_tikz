"""Native PDF glyph outlines for local text-collision screening.

PyMuPDF's SVG export already describes text as glyph ``<use>`` elements. This
module resolves those references in a copy of that SVG, tags each glyph with a
unique fill, and lets MuPDF's SVG importer return the actual painted outlines.
No source-TikZ parsing or font parser is involved.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from itertools import pairwise
from typing import Any

import pymupdf
from shapely.geometry import Polygon, box
from shapely.ops import polygonize, unary_union

from evaluation.tikz_geometry import path_parts

_MAX_SVG_BYTES = 10_000_000
_MAX_GLYPHS = 4096
_MAX_DRAWINGS = 20_000
_XHTML = "http://www.w3.org/2000/svg"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _unknown(reason: str) -> dict[str, Any]:
    return {"status": "unknown", "reason": reason, "glyphs": []}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _color_key(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) < 3:
        return None
    try:
        rgb = tuple(max(0, min(255, round(float(channel) * 255))) for channel in value[:3])
    except (TypeError, ValueError, OverflowError):
        return None
    return rgb  # type: ignore[return-value]


def _used_fill_colors(drawings: list[dict[str, Any]]) -> set[tuple[int, int, int]]:
    used: set[tuple[int, int, int]] = set()
    for drawing in drawings:
        key = _color_key(drawing.get("fill"))
        if key is not None:
            used.add(key)
    return used


def _marker_colors(count: int, used: set[tuple[int, int, int]]) -> list[str] | None:
    """Choose exact 24-bit colors absent from the source page's fill palette."""
    colors: list[str] = []
    # A simple bijection over the 24-bit RGB space, with an odd multiplier.
    # The loop is bounded by the finite palette and stops as soon as enough
    # colors have been found.
    value = 1
    while len(colors) < count and value < 0x1000000:
        rgb_value = (value * 0x5BD1E995) & 0xFFFFFF
        rgb = (rgb_value >> 16, (rgb_value >> 8) & 0xFF, rgb_value & 0xFF)
        if rgb not in used:
            colors.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
            used.add(rgb)
        value += 1
    return colors if len(colors) == count else None


def _style_without_paint(style: str) -> str:
    retained = []
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        if name.strip().lower() in {"fill", "stroke", "color"}:
            continue
        if name.strip() and value.strip():
            retained.append(f"{name.strip()}:{value.strip()}")
    return ";".join(retained)


def _inline_glyphs(root: ET.Element, page_chars: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    elements = list(root.iter())
    parents = {child: parent for parent in elements for child in list(parent)}
    paths: dict[str, ET.Element] = {}
    duplicate_ids: set[str] = set()
    for element in elements:
        identifier = element.get("id")
        if identifier:
            if identifier in paths:
                duplicate_ids.add(identifier)
            else:
                paths[identifier] = element
    if duplicate_ids:
        return [], "duplicate SVG ids make glyph references ambiguous"

    uses = [element for element in elements if _local_name(element.tag) == "use"]
    if len(uses) > _MAX_GLYPHS:
        return [], "glyph count exceeds the extraction limit"
    nonspace_chars = [char for char in page_chars if not char.get("c", "").isspace()]
    nonspace_uses: list[tuple[int, ET.Element]] = []
    for index, use in enumerate(uses):
        text = use.get("data-text")
        if not isinstance(text, str):
            return [], f"glyph {index} has no extracted text"
        if text.isspace():
            # MuPDF sometimes omits spaces from its SVG path export. If present,
            # remove whitespace uses and match the ordered non-space streams.
            parent = parents.get(use)
            if parent is None:
                return [], f"whitespace glyph {index} has no SVG parent"
            parent.remove(use)
        else:
            nonspace_uses.append((index, use))
    if len(nonspace_uses) != len(nonspace_chars):
        return [], "SVG non-space glyph count does not match PDF text characters"

    glyphs: list[dict[str, Any]] = []
    for (index, use), char in zip(nonspace_uses, nonspace_chars, strict=True):
        text = use.get("data-text")
        href = use.get(_XLINK_HREF) or use.get("href")
        if not isinstance(text, str) or text != char.get("c"):
            return [], "SVG glyph order does not match PDF text extraction order"
        if not href or not href.startswith("#"):
            return [], f"glyph {index} has no local SVG path reference"
        source_path = paths.get(href[1:])
        if source_path is None or _local_name(source_path.tag) != "path" or not source_path.get("d"):
            return [], f"glyph {index} does not reference a resolvable path"
        if use.get("x") not in (None, "0", "0px") or use.get("y") not in (None, "0", "0px"):
            return [], f"glyph {index} uses unsupported x/y placement"

        parent = parents.get(use)
        if parent is None:
            return [], f"glyph {index} has no SVG parent"
        glyphs.append({
            "text": text,
            "bbox_pt": [float(value) for value in char["bbox"]],
            "transform": use.get("transform"),
            "source_use_index": index,
            "evidence_id": f"pdf-svg-glyph:{index}",
            "_use": use,
            "_path": source_path,
            "_parent": parent,
            "_color": None,
        })
    return glyphs, None


def _replace_uses(glyphs: list[dict[str, Any]], root: ET.Element, colors: list[str]) -> str | None:
    for glyph, color in zip(glyphs, colors, strict=True):
        use: ET.Element = glyph.pop("_use")
        source_path: ET.Element = glyph.pop("_path")
        parent: ET.Element = glyph.pop("_parent")
        glyph["_color"] = color
        # Keep the original parent chain, transform and clipping properties.
        # Replacing <use> with <g> also preserves its position in paint order.
        group = ET.Element(f"{{{_XHTML}}}g")
        for key, value in use.attrib.items():
            if key in {_XLINK_HREF, "href", "id", "data-text"}:
                continue
            if key == "style":
                value = _style_without_paint(value)
                if not value:
                    continue
            group.set(key, value)

        path = ET.SubElement(group, f"{{{_XHTML}}}path")
        for key, value in source_path.attrib.items():
            if key in {"id", "style", "fill", "stroke", "opacity"}:
                continue
            path.set(key, value)
        path.set("d", source_path.get("d", ""))
        # Direct important paint overrides make the marker reliable even when
        # an SVG stylesheet contains inherited fill/stroke declarations.
        path.set("style", f"fill:{color} !important;stroke:none !important")
        try:
            child_index = list(parent).index(use)
        except ValueError:
            return "SVG glyph moved during outline extraction"
        parent.remove(use)
        parent.insert(child_index, group)

    # ElementTree may omit namespace declarations used only by attributes.
    # Keep the SVG namespace explicit for MuPDF's SVG document loader.
    if _local_name(root.tag) != "svg":
        return "MuPDF SVG export has no svg root"
    return None


def _raw_chars(page: Any) -> list[dict[str, Any]]:
    chars: list[dict[str, Any]] = []
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                chars.extend(span.get("chars", []))
    return chars


def extract_glyph_outlines(
    page: Any, chars: list[dict[str, Any]] | None = None, drawings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Return execution-grounded vector outlines for every non-space PDF glyph.

    Result shape is ``{status, reason, glyphs}``. On success, each glyph has
    ``text``, its raw PDF text ``bbox_pt``, source SVG ``transform`` and
    ``source_use_index``, a stable ``evidence_id``, and the exact PyMuPDF
    ``drawings`` whose fill color uniquely identifies that glyph. Any missing,
    ambiguous or unsupported non-space glyph makes the whole result unknown.
    Drawing coordinates are in the original page's PDF-point frame.
    """
    try:
        chars = _raw_chars(page) if chars is None else chars
        svg = page.get_svg_image(text_as_path=True)
        encoded = svg.encode("utf-8")
        if len(encoded) > _MAX_SVG_BYTES:
            return _unknown("SVG export exceeds the extraction size limit")
        root = ET.fromstring(encoded)
        glyphs, issue = _inline_glyphs(root, chars)
        if issue:
            return _unknown(issue)
        if not glyphs:
            if chars:
                return _unknown("PDF text has no extractable non-space glyph paths")
            return {"status": "ok", "reason": None, "glyphs": []}

        colors = _marker_colors(len(glyphs), _used_fill_colors(page.get_drawings() if drawings is None else drawings))
        if colors is None:
            return _unknown("could not assign unique marker colors")
        issue = _replace_uses(glyphs, root, colors)
        if issue:
            return _unknown(issue)

        analysis_svg = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with pymupdf.open(stream=analysis_svg, filetype="svg") as svg_document:
            converted = svg_document.convert_to_pdf()
        with pymupdf.open(stream=converted, filetype="pdf") as outline_document:
            if len(outline_document) != 1:
                return _unknown("SVG outline import did not produce exactly one page")
            drawings = outline_document[0].get_drawings()
        if len(drawings) > _MAX_DRAWINGS:
            return _unknown("outline drawing count exceeds the extraction limit")

        by_color: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
        for drawing in drawings:
            key = _color_key(drawing.get("fill"))
            if key is not None:
                by_color.setdefault(key, []).append(drawing)
        for glyph, color in zip(glyphs, colors, strict=True):
            marker = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
            matched = by_color.get(marker, [])
            if not matched:
                return _unknown(f"glyph {glyph['source_use_index']} produced no measurable outline")
            glyph["drawings"] = matched
            glyph["status"] = "ok"
            glyph.pop("_color", None)
        return {"status": "ok", "reason": None, "glyphs": glyphs}
    except (ET.ParseError, OSError, RuntimeError, TypeError, ValueError, pymupdf.FileDataError) as error:
        return _unknown(f"native glyph outline extraction failed: {type(error).__name__}: {error}")


def glyph_ink(drawings: list[dict[str, Any]]) -> Any:
    """Recover font fill contours, including holes, from native PDF paths."""
    ink = []
    for drawing in drawings:
        rings = []
        for raw_part in path_parts(drawing):
            part = list(raw_part)
            if len(part) < 3:
                continue
            if part[-1] != part[0]:
                part.append(part[0])
            ring = Polygon(part)
            if not ring.is_valid:
                raise ValueError("Unsupported self-intersecting font contour")
            signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in pairwise(part))
            rings.append((ring, 1 if signed > 0 else -1))
        faces = polygonize(unary_union([ring.boundary for ring, _ in rings]))
        for face in faces:
            point = face.representative_point()
            winding = sum(sign for ring, sign in rings if ring.contains(point))
            has_ink = (
                abs(winding) % 2 != 0
                if drawing.get("even_odd")
                else winding != 0
            )
            if has_ink:
                ink.append(face)
    return unary_union(ink)


def _normalize_text(value: str) -> str:
    return "".join(value.split()).replace("\u2032", "'").replace("\u2019", "'")


def attach_glyph_ink(
    text: list[dict[str, Any]], outline_capture: dict[str, Any]
) -> list[str]:
    """Attach uniquely matched extracted glyph ink to PDF text records."""
    outlines = outline_capture.get("glyphs", [])
    issues = []
    used_glyphs = set()
    for label in text:
        for glyph in label.get("glyphs", []):
            candidates = [
                (index, outline)
                for index, outline in enumerate(outlines)
                if index not in used_glyphs
                and _normalize_text(outline["text"]) == _normalize_text(glyph["text"])
                and box(*glyph["bbox"]).buffer(label["size"] * 0.2).covers(
                    box(*outline["bbox_pt"])
                )
            ]
            if outline_capture.get("status") != "ok" or len(candidates) != 1:
                issues.append("Unresolved font outline for " + glyph["text"])
                continue
            index, outline = candidates[0]
            try:
                ink = glyph_ink(outline["drawings"])
            except ValueError as error:
                issues.append(str(error))
                continue
            if ink.is_empty:
                issues.append("Empty font outline for " + glyph["text"])
                continue
            used_glyphs.add(index)
            glyph.update(ink=ink, evidence_id=outline["evidence_id"])
    if outline_capture.get("status") != "ok":
        issues.append(outline_capture.get("reason", "Font outline extraction unavailable"))
    return issues


def inspect_readability(scene: dict[str, Any]) -> dict[str, Any]:
    """Screen text against painted strokes and other text in a PDF scene."""
    painted_strokes = unary_union(
        [stroke["geometry"].buffer(stroke["width"] / 2) for stroke in scene["strokes"]]
    )
    collisions, collision_evidence, clipped = [], [], []
    glyph_overlaps, overlaps = [], []
    page = box(*scene["bounds"])
    label_inks = []
    resolved_labels, resolved_ink_area, collision_ink_area = 0, 0.0, 0.0
    for label in scene["text"]:
        glyphs = label.get("glyphs", [])
        resolved = all("ink" in glyph for glyph in glyphs) and bool(glyphs)
        ink = (
            unary_union([glyph["ink"] for glyph in glyphs])
            if resolved
            else box(*label["bbox"]).buffer(-0.6)
        )
        label_inks.append(ink)
        intersection = ink.intersection(painted_strokes)
        if resolved:
            resolved_labels += 1
            resolved_ink_area += ink.area
            collision_ink_area += intersection.area
        if intersection.area > 0.02:
            collisions.append(label["text"])
            collision_evidence.append(
                {
                    "text": label["text"],
                    "intersection_area_pdf_pt2": intersection.area,
                    "label_ink_area_pdf_pt2": ink.area,
                    "basis": "font_outline" if resolved else "bbox_fallback",
                    "glyph_evidence": [glyph.get("evidence_id") for glyph in glyphs],
                }
            )
        if not page.covers(ink):
            clipped.append(label["text"])
        for index, first in enumerate(glyphs):
            for second in glyphs[index + 1 :]:
                a = first.get("ink", box(*first["bbox"]))
                b = second.get("ink", box(*second["bbox"]))
                if a.intersection(b).area > 0.02:
                    glyph_overlaps.append(
                        {"text": label["text"], "characters": [first["text"], second["text"]]}
                    )
    for index, first in enumerate(label_inks):
        for other_index, second in enumerate(label_inks[index + 1 :], start=index + 1):
            if first.intersection(second).area > 0.02:
                overlaps.append(
                    [scene["text"][index]["text"], scene["text"][other_index]["text"]]
                )
    return {
        "glyph_overlap_candidates": glyph_overlaps,
        "stroke_collision_candidates": collisions,
        "stroke_collision_evidence": collision_evidence,
        "text_overlap_candidates": overlaps,
        "text_count": len(scene["text"]),
        "resolved_outline_label_count": resolved_labels,
        "resolved_label_ink_area_pdf_pt2": resolved_ink_area,
        "resolved_stroke_collision_area_pdf_pt2": collision_ink_area,
        "clipped_text": clipped,
        "outline_issues": scene["ink_issues"],
        "approximation": "Font and stroke curves flattened to 0.08 PDF pt; 0.02 square PDF pt intersection screen; dash gaps and final compositing are not certified",
    }


def compare_readability(
    target_scene: dict[str, Any], output_scene: dict[str, Any]
) -> dict[str, Any]:
    """Compare existing readability screens and retain their diagnostic fields."""
    target = inspect_readability(target_scene)
    output = inspect_readability(output_scene)
    new_collisions = list(
        (Counter(output["stroke_collision_candidates"])
         - Counter(target["stroke_collision_candidates"])).elements()
    )
    status = (
        "review"
        if new_collisions
        or len(output["glyph_overlap_candidates"]) > len(target["glyph_overlap_candidates"])
        or len(output["text_overlap_candidates"]) > len(target["text_overlap_candidates"])
        or output["clipped_text"]
        else "unknown"
        if target["outline_issues"] or output["outline_issues"]
        else "no_new_warning"
    )
    ink_area = output["resolved_label_ink_area_pdf_pt2"]
    output_status = (
        "review" if output["stroke_collision_candidates"] or output["glyph_overlap_candidates"]
        or output["text_overlap_candidates"] or output["clipped_text"] else
        "unknown" if output["outline_issues"] or output_scene.get("unsupported") else "match"
    )
    collision_ink_pct = (
        100 * output["resolved_stroke_collision_area_pdf_pt2"] / ink_area
        if ink_area
        else None
    )
    return {
        "status": status,
        "output_status": output_status,
        "target": target,
        "output": output,
        "new_stroke_collision_candidates": new_collisions,
        "collision_ink_pct": collision_ink_pct,
        "collision_measurement_complete": not output["outline_issues"] and not output_scene.get("unsupported"),
        "meaning": "Output-only geometric collision screen; status/new candidates describe change from target, not absolute readability; dash gaps, fills and final compositing are unmeasured",
    }
