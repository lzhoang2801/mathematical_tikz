"""Acquire original compiler artifacts and resolve executed PGF evidence into PDF coordinates."""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pymupdf
from agent.latex.tikz import standalone_tikz_document, validate_tikz
from latex_compiler.client import compile as compile_latex
from latex_compiler.schemas import CompileRequest, Images, Outputs
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from evaluation.tikz_annotations import PROBE_TEX, parse_annotations
from evaluation.tikz_geometry import path_parts
from evaluation.tikz_readability import attach_glyph_ink, extract_glyph_outlines

SCHEMA_VERSION = "tikz-observations:v3"


_PGF_DIMENSION = r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))pt"
_BBOX_LOG = re.compile(
    rf"PTKZBBOX\|([^|\r\n]+)\|{_PGF_DIMENSION}\|{_PGF_DIMENSION}\|"
    rf"{_PGF_DIMENSION}\|{_PGF_DIMENSION}"
)
_POINT_LABEL = re.compile(r"[A-Z](?:[0-9]+|['′]+)?\Z")
_MAX_PDF_ITEMS = 4000
_MAX_DISCOVERY_ITEMS = 512
_STANDALONE_BORDER_TEX_PT = 4.0
_PDF_COORDINATE_ERROR_BOUND_PT = 2e-5


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_records(response: Any, directory: Path) -> dict[str, dict[str, Any]]:
    """Persist returned bytes and retain each artifact's compiler identity."""
    directory.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    for artifact in response.artifacts:
        data = artifact.data
        path = directory / artifact.name
        path.write_bytes(data)
        records[artifact.name] = {
            "path": str(path.resolve()),
            "sha256": _sha256(data),
            "complete": artifact.complete,
            "size_bytes": len(data),
        }
    return records


def _stage_record(stage: Any) -> dict[str, Any]:
    return {
        "outcome": stage.outcome,
        "success": stage.success,
        "exit_code": stage.exit_code,
        "failure_code": stage.failure_code,
        "diagnostic": stage.diagnostic,
    }


def _empty_annotations(status: str, reason: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "annotations": [],
        "truncated": False,
        "diagnostics": [reason] if reason else [],
        "coordinate_unit": "TeX pt",
        "coordinate_frame": "PGF runtime softpath; map with discovery frame_mapping",
    }


_DISCOVERY_HOOKS = rf"""
\makeatletter
\newcount\PTKZ@nodecount
\newif\ifPTKZ@truncated
\newif\ifPTKZ@labelpending
\newif\ifPTKZ@inNode
\def\PTKZ@logcircle#1#2{{%
  \begingroup
    \pgf@process{{\pgfpointtransformed{{#1}}}}%
    \edef\PTKZ@cx{{\the\pgf@x}}\edef\PTKZ@cy{{\the\pgf@y}}%
    \pgf@process{{\pgfpointtransformed{{\pgfpointadd{{#1}}{{\pgfpoint{{#2}}{{0pt}}}}}}}}%
    \edef\PTKZ@xx{{\the\pgf@x}}\edef\PTKZ@xy{{\the\pgf@y}}%
    \pgf@process{{\pgfpointtransformed{{\pgfpointadd{{#1}}{{\pgfpoint{{0pt}}{{#2}}}}}}}}%
    \edef\PTKZ@yx{{\the\pgf@x}}\edef\PTKZ@yy{{\the\pgf@y}}%
    \typeout{{PTKZCIRC|\pgfpictureid|\PTKZ@activeindex|\PTKZ@cx|\PTKZ@cy}}%
    \typeout{{PTKZCRX|\pgfpictureid|\PTKZ@activeindex|\PTKZ@xx|\PTKZ@xy}}%
    \typeout{{PTKZCRY|\pgfpictureid|\PTKZ@activeindex|\PTKZ@yx|\PTKZ@yy}}%
  \endgroup
}}
\let\PTKZ@originalpathcircle\pgfpathcircle
\def\pgfpathcircle#1#2{{%
  \ifPTKZ@inNode
    \ifcsname pgf@sh@ns@\pgf@node@name\endcsname
      \edef\PTKZ@shapename{{\csname pgf@sh@ns@\pgf@node@name\endcsname}}%
      \def\PTKZ@circleshape{{circle}}%
      \ifx\PTKZ@shapename\PTKZ@circleshape\PTKZ@logcircle{{#1}}{{#2}}\fi
    \fi
  \fi
  \PTKZ@originalpathcircle{{#1}}{{#2}}%
}}
\def\PTKZ@capturelabelparent{{%
  \begingroup
    \pgftransformreset
    \pgfpointanchor{{\tikzlastnode}}{{center}}%
    \global\edef\PTKZ@pendingx{{\the\pgf@x}}%
    \global\edef\PTKZ@pendingy{{\the\pgf@y}}%
    \global\PTKZ@labelpendingtrue
  \endgroup
}}
\tikzset{{tikz@label@post/.append code={{\PTKZ@capturelabelparent}}}}
\let\PTKZ@originalnodebegin\tikz@node@begin@hook
\def\tikz@node@begin@hook{{%
  \tikz@fig@mustbenamed%
  \global\edef\PTKZ@activeindex{{\number\numexpr\PTKZ@nodecount+1\relax}}%
  \global\PTKZ@inNodetrue%
  \PTKZ@originalnodebegin
  \ifPTKZ@labelpending
    \let\PTKZ@attachx\PTKZ@pendingx
    \let\PTKZ@attachy\PTKZ@pendingy
    \def\PTKZ@attachkind{{label-parent-center}}%
    \global\PTKZ@labelpendingfalse
  \else
    \pgf@process{{\pgfpointtransformed{{\tikz@node@at}}}}%
    \edef\PTKZ@attachx{{\the\pgf@x}}%
    \edef\PTKZ@attachy{{\the\pgf@y}}%
    \def\PTKZ@attachkind{{node-position}}%
  \fi
}}
\def\PTKZ@lognode{{%
  \ifnum\PTKZ@nodecount<{_MAX_DISCOVERY_ITEMS}\relax
    \global\advance\PTKZ@nodecount by1\relax
    \edef\PTKZ@name{{\tikz@fig@name}}%
    \edef\PTKZ@shape{{\tikz@shape}}%
    \ifcsname pgf@sh@ns@\PTKZ@name\endcsname
      \begingroup
        \pgftransformreset
        \pgfpointanchor{{\PTKZ@name}}{{center}}%
        \pgfgetlastxy{{\PTKZ@cx}}{{\PTKZ@cy}}%
        \ifcsname pgf@anchor@\PTKZ@shape @north west\endcsname
          \pgfpointanchor{{\PTKZ@name}}{{north west}}%
          \pgfgetlastxy{{\PTKZ@nwX}}{{\PTKZ@nwY}}%
          \pgfpointanchor{{\PTKZ@name}}{{north east}}%
          \pgfgetlastxy{{\PTKZ@neX}}{{\PTKZ@neY}}%
          \pgfpointanchor{{\PTKZ@name}}{{south west}}%
          \pgfgetlastxy{{\PTKZ@swX}}{{\PTKZ@swY}}%
          \pgfpointanchor{{\PTKZ@name}}{{south east}}%
          \pgfgetlastxy{{\PTKZ@seX}}{{\PTKZ@seY}}%
          \typeout{{PTKZNODE|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@shape|ok|\PTKZ@attachkind}}%
          \typeout{{PTKZNPOS|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@attachx|\PTKZ@attachy|\PTKZ@cx|\PTKZ@cy}}%
          \typeout{{PTKZNBBOX|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@nwX|\PTKZ@nwY|\PTKZ@neX|\PTKZ@neY}}%
          \typeout{{PTKZNSBOX|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@swX|\PTKZ@swY|\PTKZ@seX|\PTKZ@seY}}%
        \else
          \typeout{{PTKZNODE|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@shape|unsupported-bounds|\PTKZ@attachkind}}%
          \typeout{{PTKZNPOS|\pgfpictureid|\the\PTKZ@nodecount|\PTKZ@attachx|\PTKZ@attachy|\PTKZ@cx|\PTKZ@cy}}%
        \fi
      \endgroup
    \else
      \relax
    \fi
  \else
    \ifPTKZ@truncated\else
      \global\PTKZ@truncatedtrue
      \typeout{{PTKZTRUNCATED|nodes}}
    \fi
  \fi
}}
\let\PTKZ@originalnodefinish\tikz@node@finish
\def\tikz@node@finish{{%
  \PTKZ@lognode
  \global\PTKZ@inNodefalse\global\let\PTKZ@activeindex\relax
  \PTKZ@originalnodefinish
}}
\def\PTKZ@logbbox{{%
  \typeout{{PTKZBBOX|\pgfpictureid|\the\pgf@picminx|\the\pgf@picminy|\the\pgf@picmaxx|\the\pgf@picmaxy}}%
}}
\let\TikzEvalLogBbox\PTKZ@logbbox
\makeatother
"""


def _discovery_wrapper(tikz: str) -> str:
    """Instrument executed coordinates and node attachments without drawing."""
    source = standalone_tikz_document(tikz)
    document_start = r"\begin{document}"
    if document_start not in source:
        raise ValueError("standalone wrapper has no document start")
    source = source.replace(
        document_start,
        document_start + "\n" + _DISCOVERY_HOOKS + "\n" + PROBE_TEX,
        1,
    )
    return source.replace(r"\end{tikzpicture}", r"\TikzEvalLogBbox\end{tikzpicture}")


def _dimension(value: str) -> float:
    if not value.endswith("pt"):
        raise ValueError("PGF dimension has no pt unit")
    result = float(value[:-2])
    if not math.isfinite(result):
        raise ValueError("PGF dimension is not finite")
    return result


def _map_picture_to_pdf(
    bbox: tuple[float, float, float, float], pdf_rect: Sequence[Any], *, border_pt: float = _STANDALONE_BORDER_TEX_PT
) -> dict[str, Any]:
    """Map ordinary PGF picture coordinates through the fixed standalone crop."""
    if len(pdf_rect) != 4:
        return {"status": "unknown", "reason": "pdf_page_rect_unavailable"}
    x0, y0, x1, y1 = (float(value) for value in pdf_rect)
    min_x, min_y, max_x, max_y = bbox
    if max_x <= min_x or max_y <= min_y:
        return {"status": "unknown", "reason": "degenerate_picture_bbox"}
    tex_to_pdf = 72.0 / 72.27
    expected_width = (max_x - min_x + 2 * border_pt) * tex_to_pdf
    expected_height = (max_y - min_y + 2 * border_pt) * tex_to_pdf
    page_width, page_height = x1 - x0, y1 - y0
    residual = max(abs(expected_width - page_width), abs(expected_height - page_height))
    if residual > 0.1:
        return {
            "status": "unknown",
            "reason": "picture_bbox_page_size_mismatch",
            "expected_page_size_pt": [expected_width, expected_height],
            "observed_page_size_pt": [page_width, page_height],
            "size_residual_pt": residual,
        }
    return {
        "status": "verified_dimensions",
        "frame": "pdf-page-top-left",
        "unit": "PDF pt",
        "pgf_bbox_pt": [min_x, min_y, max_x, max_y],
        "pdf_rect_pt": [x0, y0, x1, y1],
        "border_tex_pt": border_pt,
        "tex_pt_to_pdf_pt": tex_to_pdf,
        "size_residual_pt": residual,
        "limitations": [
            "Dimension agreement verifies the standalone crop scale, not every custom canvas transform.",
            "Custom PGF/system transforms that bypass tracked coordinates make this mapping unsupported.",
        ],
    }


def _pdf_point(x: float, y: float, frame: Mapping[str, Any]) -> tuple[float, float] | None:
    if frame.get("status") != "verified_dimensions":
        return None
    min_x, _, _, max_y = frame["pgf_bbox_pt"]
    page_x0, page_y0, _, _ = frame["pdf_rect_pt"]
    border = frame["border_tex_pt"]
    factor = frame["tex_pt_to_pdf_pt"]
    return (page_x0 + (x - min_x + border) * factor, page_y0 + (max_y - y + border) * factor)


def _point_label(text: str) -> str | None:
    normalized = "".join(text.split()).replace("′", "'")
    normalized = normalized.replace("\u2032", "'").replace("\u2019", "'")
    return normalized if _POINT_LABEL.fullmatch(normalized) else None


def _overlapping_glyph_labels(span: Mapping[str, Any]) -> set[str]:
    """Find single-letter point labels merged into one overlapping PDF span."""
    glyphs = [
        (label, glyph["bbox_pt"])
        for glyph in span.get("glyphs", [])
        if isinstance(glyph, Mapping)
        and isinstance(glyph.get("bbox_pt"), list)
        and len(glyph["bbox_pt"]) == 4
        and (label := _point_label(str(glyph.get("text", "")))) is not None
        and len(label) == 1
    ]
    for index, (_, first) in enumerate(glyphs):
        for _, second in glyphs[index + 1 :]:
            width = max(0.0, min(float(first[2]), float(second[2])) - max(float(first[0]), float(second[0])))
            height = max(0.0, min(float(first[3]), float(second[3])) - max(float(first[1]), float(second[1])))
            first_area = max(0.0, float(first[2]) - float(first[0])) * max(0.0, float(first[3]) - float(first[1]))
            second_area = max(0.0, float(second[2]) - float(second[0])) * max(0.0, float(second[3]) - float(second[1]))
            smaller_area = min(first_area, second_area)
            if smaller_area > 0 and width * height / smaller_area > 0.6:
                return {label for label, _ in glyphs}
    return set()


def _distance_to_rect(x: float, y: float, rect: Sequence[Any]) -> float:
    x0, y0, x1, y1 = (float(value) for value in rect)
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


def _parse_discovery_log(
    log_text: str, pdf_observations: Mapping[str, Any], canonical_tikz: str
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    unsupported: list[str] = []
    bbox_records = [
        {
            "picture_id": match.group(1),
            "bbox_pt": tuple(float(match.group(index)) for index in range(2, 6)),
        }
        for match in _BBOX_LOG.finditer(log_text)
    ]
    frame: dict[str, Any] = {"status": "unknown", "reason": "picture_bbox_unavailable"}
    if len(bbox_records) == 1:
        pages = pdf_observations.get("pages", [])
        if len(pages) == 1:
            frame = _map_picture_to_pdf(
                bbox_records[0]["bbox_pt"], pages[0].get("rect_pt", [])
            )
            frame["picture_id"] = bbox_records[0]["picture_id"]
        else:
            frame = {"status": "unknown", "reason": "single_pdf_page_required_for_frame_mapping"}
    elif bbox_records:
        frame = {"status": "unknown", "reason": "multiple_picture_frames"}

    canvas_transform_hint = bool(
        re.search(r"transform\s+canvas|\\pgflowlevel", canonical_tikz, re.IGNORECASE)
    )
    if canvas_transform_hint:
        frame = {
            "status": "unknown",
            "reason": "canvas_transform_may_bypass_pgf_coordinate_tracking",
            "picture_id": frame.get("picture_id"),
            "dimension_check": frame,
        }

    node_events: dict[tuple[str, str], dict[str, list[str]]] = {}
    circle_events: dict[tuple[str, str], dict[str, list[list[str]]]] = {}
    node_markers = {"PTKZNODE", "PTKZNPOS", "PTKZNBBOX", "PTKZNSBOX"}
    circle_markers = {"PTKZCIRC", "PTKZCRX", "PTKZCRY"}
    for line in log_text.splitlines():
        marker_positions = [
            (line.find(f"{marker}|"), marker) for marker in node_markers | circle_markers
        ]
        marker_positions = [(position, marker) for position, marker in marker_positions if position >= 0]
        if not marker_positions:
            continue
        position, marker = min(marker_positions)
        fields = line[position:].strip().split("|")
        if len(fields) < 4:
            unsupported.append("malformed_node_record")
            continue
        _, picture_id, index_text, *values = fields
        key = (picture_id, index_text)
        if marker in node_markers:
            node_events.setdefault(key, {})[marker] = values
        else:
            circle_events.setdefault(key, {}).setdefault(marker, []).append(values)

    nodes: list[dict[str, Any]] = []
    for (picture_id, index_text), event in node_events.items():
        try:
            node_index = int(index_text)
            header = event["PTKZNODE"]
            if len(header) != 3:
                raise ValueError("malformed node header")
            shape, bounds_status, attachment = header
            position = event["PTKZNPOS"]
            if len(position) != 4:
                raise ValueError("malformed node position")
            attachment_pt = [_dimension(position[0]), _dimension(position[1])]
            center_pt = [_dimension(position[2]), _dimension(position[3])]
        except (KeyError, ValueError):
            unsupported.append("malformed_node_coordinates")
            continue

        corners_pt = None
        if bounds_status == "ok":
            try:
                north = event["PTKZNBBOX"]
                south = event["PTKZNSBOX"]
                if len(north) != 4 or len(south) != 4:
                    raise ValueError("malformed node bounds")
                north_points = [_dimension(value) for value in north]
                south_points = [_dimension(value) for value in south]
                corners_pt = [
                    north_points[0:2],
                    north_points[2:4],
                    south_points[0:2],
                    south_points[2:4],
                ]
            except (KeyError, ValueError):
                bounds_status = "unknown"
                unsupported.append("malformed_node_bounds")
        node: dict[str, Any] = {
            "status": "measured",
            "picture_id": picture_id,
            "node_index": node_index,
            "shape": shape,
            "attachment": attachment,
            "attachment_pt": attachment_pt,
            "center_pt": center_pt,
            "bounds_status": bounds_status,
            "corners_pt": corners_pt,
            "evidence_id": f"node-log:{picture_id}:{index_text}",
        }
        if shape == "circle":
            circle_rows = circle_events.get((picture_id, index_text), {})
            required_circle_rows = {"PTKZCIRC", "PTKZCRX", "PTKZCRY"}
            circle_path: dict[str, Any] = {
                "status": "unknown",
                "reason": "circle_path_event_incomplete",
                "evidence_id": f"circle-path-log:{picture_id}:{index_text}",
            }
            if set(circle_rows) == required_circle_rows and all(
                len(circle_rows[marker]) == 1 for marker in required_circle_rows
            ):
                try:
                    center = [_dimension(item) for item in circle_rows["PTKZCIRC"][0]]
                    x_endpoint = [_dimension(item) for item in circle_rows["PTKZCRX"][0]]
                    y_endpoint = [_dimension(item) for item in circle_rows["PTKZCRY"][0]]
                    if any(len(value) != 2 for value in (center, x_endpoint, y_endpoint)):
                        raise ValueError("malformed circle path coordinates")
                    circle_path.update(
                        picture_center_pt=center,
                        picture_x_radius_endpoint_pt=x_endpoint,
                        picture_y_radius_endpoint_pt=y_endpoint,
                    )
                    if frame.get("status") == "verified_dimensions" and frame.get("picture_id") == picture_id:
                        pdf_center = _pdf_point(center[0], center[1], frame)
                        pdf_x_endpoint = _pdf_point(x_endpoint[0], x_endpoint[1], frame)
                        pdf_y_endpoint = _pdf_point(y_endpoint[0], y_endpoint[1], frame)
                        if pdf_center and pdf_x_endpoint and pdf_y_endpoint:
                            circle_path.update(
                                status="measured",
                                coordinate_frame=frame["frame"],
                                unit="PDF pt",
                                center_pdf_pt=list(pdf_center),
                                x_radius_endpoint_pdf_pt=list(pdf_x_endpoint),
                                y_radius_endpoint_pdf_pt=list(pdf_y_endpoint),
                                axis_radii_pdf_pt=[
                                    math.dist(pdf_center, pdf_x_endpoint),
                                    math.dist(pdf_center, pdf_y_endpoint),
                                ],
                                pdf_coordinate_error_bound_pt=_PDF_COORDINATE_ERROR_BOUND_PT,
                                capture="pgfpathcircle_argument_after_outer_separation",
                            )
                            circle_path.pop("reason", None)
                        else:
                            circle_path["reason"] = "circle_path_pdf_frame_mapping_failed"
                    else:
                        circle_path["reason"] = "circle_path_pdf_frame_unavailable"
                except ValueError:
                    circle_path["reason"] = "malformed_circle_path_coordinates"
                    unsupported.append("malformed_circle_path_coordinates")
            elif circle_rows:
                circle_path["reason"] = "duplicate_or_incomplete_circle_path_events"
                unsupported.append("duplicate_or_incomplete_circle_path_events")
            else:
                unsupported.append("circle_path_event_missing")
            node["circle_path_pdf"] = circle_path
        if frame.get("status") == "verified_dimensions" and frame.get("picture_id") == picture_id:
            node_center = _pdf_point(center_pt[0], center_pt[1], frame)
            node_attachment = _pdf_point(attachment_pt[0], attachment_pt[1], frame)
            node.update(
                center_pdf_pt=list(node_center) if node_center else None,
                attachment_pdf_pt=list(node_attachment) if node_attachment else None,
            )
            if corners_pt:
                mapped = [_pdf_point(x, y, frame) for x, y in corners_pt]
                if all(item is not None for item in mapped):
                    mapped_points = [item for item in mapped if item is not None]
                    xs = [item[0] for item in mapped_points]
                    ys = [item[1] for item in mapped_points]
                    pdf_bbox = [min(xs), min(ys), max(xs), max(ys)]
                    node["pdf_bbox_pt"] = pdf_bbox
                    node["area_pt2"] = (pdf_bbox[2] - pdf_bbox[0]) * (pdf_bbox[3] - pdf_bbox[1])
        nodes.append(node)

    if "PTKZTRUNCATED|nodes" in log_text:
        unsupported.append("instrumented_evidence_truncated")
    return nodes, frame, unsupported


def _bind_text_labels(
    pdf_observations: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
    frame: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bind extractable point labels to uniquely containing instrumented TikZ nodes."""
    result: dict[str, dict[str, Any]] = {}
    if frame.get("status") != "verified_dimensions":
        reason = str(frame.get("reason", "pdf_frame_unavailable"))
        for page in pdf_observations.get("pages", []):
            for span_index, span in enumerate(page.get("text_spans", [])):
                label = _point_label(str(span.get("text", "")))
                if label:
                    result[label] = {"status": "unknown", "reason": reason, "evidence_id": f"pdf-text:{page.get('page_number', 1)}:{span_index}"}
        return result

    page = next(iter(pdf_observations.get("pages", [])), None)
    if not isinstance(page, Mapping):
        return result
    converted_nodes = [
        node for node in node_records
        if node.get("picture_id") == frame.get("picture_id")
        and node.get("pdf_bbox_pt") and node.get("attachment_pdf_pt")
    ]

    span_records: dict[str, list[tuple[int, Mapping[str, Any], bool]]] = {}
    for span_index, span in enumerate(page.get("text_spans", [])):
        label = _point_label(str(span.get("text", "")))
        if label:
            span_records.setdefault(label, []).append((span_index, span, False))
        else:
            for merged_label in _overlapping_glyph_labels(span):
                span_records.setdefault(merged_label, []).append((span_index, span, True))
    for label, spans in span_records.items():
        if len(spans) != 1 or spans[0][2]:
            result[label] = {
                "status": "unknown",
                "reason": "merged_or_duplicate_ambiguous_pdf_label",
                "span_count": len(spans),
                "evidence_ids": [
                    f"pdf-text:{page.get('page_number', 1)}:{item[0]}"
                    for item in spans
                ],
            }
            continue
        span_index, span, _ = spans[0]
        span_bbox = span.get("bbox_pt")
        if not isinstance(span_bbox, list) or len(span_bbox) != 4:
            result[label] = {"status": "unknown", "reason": "pdf_label_bbox_unavailable"}
            continue
        center_x = (float(span_bbox[0]) + float(span_bbox[2])) / 2
        center_y = (float(span_bbox[1]) + float(span_bbox[3])) / 2
        matches = sorted(
            (_distance_to_rect(center_x, center_y, node["pdf_bbox_pt"]), index, node)
            for index, node in enumerate(converted_nodes)
        )
        within = [entry for entry in matches if entry[0] <= 1.0 and entry[2].get("area_pt2", 0) > 0.05]
        if not within:
            result[label] = {"status": "unknown", "reason": "no_instrumented_node_contains_pdf_label", "evidence_id": f"pdf-text:{page.get('page_number', 1)}:{span_index}"}
            continue
        # Prefer the smallest containing text box. If equally plausible node boxes
        # remain, retain uncertainty rather than arbitrarily choosing an origin.
        ranked = sorted(within, key=lambda entry: (entry[2]["area_pt2"], entry[0]))
        if len(ranked) > 1 and abs(ranked[1][2]["area_pt2"] - ranked[0][2]["area_pt2"]) < 0.05 and ranked[1][0] <= 1.0:
            result[label] = {"status": "unknown", "reason": "ambiguous_instrumented_node_attachment", "candidate_node_ids": [ranked[0][2]["evidence_id"], ranked[1][2]["evidence_id"]]}
            continue
        distance, _, node = ranked[0]
        ax, ay = node["attachment_pdf_pt"]
        result[label] = {
            "status": "measured",
            "pdf_x": ax,
            "pdf_y": ay,
            "pdf_coordinate_error_bound_pt": _PDF_COORDINATE_ERROR_BOUND_PT,
            "executed_origin": node["attachment_pt"],
            "node_shape": node.get("shape"),
            "attachment": node.get("attachment"),
            "node_evidence_id": node["evidence_id"],
            "evidence_id": f"pdf-text:{page.get('page_number', 1)}:{span_index}",
            "text_bbox_pt": span_bbox,
            "node_text_distance_pt": distance,
            "binding_method": "pdf_text_inside_executed_tikz_node_bounds",
        }
    return result


def _json_value(value: Any) -> Any:
    """Convert PyMuPDF geometry values into small JSON-safe coordinate arrays."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "x") and hasattr(value, "y"):
        return [float(value.x), float(value.y)]
    if all(hasattr(value, key) for key in ("x0", "y0", "x1", "y1")):
        return [float(value.x0), float(value.y0), float(value.x1), float(value.y1)]
    if all(hasattr(value, key) for key in ("ul", "ur", "ll", "lr")):
        return [_json_value(getattr(value, key)) for key in ("ul", "ur", "ll", "lr")]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return str(value)


def _pdf_text_line_observation(line: Mapping[str, Any]) -> dict[str, Any] | None:
    """Join font-split glyph spans on one PDF text line for label extraction."""
    source_spans = line.get("spans", [])
    glyphs = [
        {
            "text": str(char.get("c", "")),
            "bbox_pt": _json_value(char.get("bbox")),
        }
        for span in source_spans
        for char in span.get("chars", [])
    ]
    text = "".join(glyph["text"] for glyph in glyphs)
    if not text.strip():
        return None
    boxes = [
        glyph["bbox_pt"]
        for glyph in glyphs
        if isinstance(glyph["bbox_pt"], list) and len(glyph["bbox_pt"]) == 4
    ]
    if boxes:
        bbox = [
            min(float(box[0]) for box in boxes),
            min(float(box[1]) for box in boxes),
            max(float(box[2]) for box in boxes),
            max(float(box[3]) for box in boxes),
        ]
    else:
        bbox = _json_value(line.get("bbox"))
    fonts = sorted({str(span["font"]) for span in source_spans if span.get("font")})
    sizes = [float(span["size"]) for span in source_spans if span.get("size") is not None]
    return {
        "text": text,
        "bbox_pt": bbox,
        "glyphs": glyphs,
        "font": fonts[0] if len(fonts) == 1 else None,
        "fonts": fonts,
        "size_pt": max(sizes) if sizes else None,
        "source_span_count": len(source_spans),
    }


def _page_observation(page: Any, page_index: int) -> dict[str, Any]:
    """Extract paths, text and glyph outlines once from an original PDF page."""
    drawings = page.get_drawings(extended=True)
    spans = []
    for block in page.get_text("rawdict").get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                span = _pdf_text_line_observation(line)
                if span is not None:
                    spans.append(span)
    chars = [{"c": glyph["text"], "bbox": glyph["bbox_pt"]} for span in spans for glyph in span["glyphs"]]
    return {
        "page_number": page_index + 1,
        "rect_pt": list(page.rect),
        "drawings": [_json_value(drawing) for drawing in drawings[:_MAX_PDF_ITEMS]],
        "drawing_count": len(drawings),
        "drawings_truncated": len(drawings) > _MAX_PDF_ITEMS,
        "text_spans": spans[:_MAX_PDF_ITEMS],
        "text_truncated": len(spans) > _MAX_PDF_ITEMS,
        "glyph_outlines": _json_value(extract_glyph_outlines(page, chars=chars, drawings=drawings)),
    }


def _pdf_observations(pdf: bytes, pdf_sha256: str, source_digest: str) -> dict[str, Any]:
    """Capture serializable emitted objects; leave evaluation decisions to callers."""
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        pages = [_page_observation(page, index) for index, page in enumerate(document)]
    return {
        "producer": "PyMuPDF Page.get_drawings(extended=True) and get_text(rawdict)",
        "meaning": "PDF-emitted paths, extractable text and native glyph outlines; not semantic correctness",
        "pdf_sha256": pdf_sha256,
        "source_digest": source_digest,
        "pages": pages,
    }


def compile_observe(tikz: str, artifact_dir: Path, compiler_http: httpx.Client) -> dict[str, Any]:
    """Compile the original, then accept runtime discovery only when its render is unchanged."""
    metadata = {"schema_version": SCHEMA_VERSION, "input_tikz_sha256": _sha256(tikz.encode("utf-8"))}
    result = {
        "compile_success": False, "raster_success": False,
        "image_path": None, "pdf_path": None, "log_path": None,
        "nodes": [], "labeled_points": {},
        "annotations": _empty_annotations("unknown"),
        "pdf_observations": None, "artifacts": {}, "metadata": metadata,
    }
    try:
        canonical = validate_tikz(tikz)
    except ValueError as error:
        result["compile"] = {"outcome": "validation_failed", "success": False, "diagnostic": str(error)}
        return result
    root = Path(artifact_dir).resolve()
    source = standalone_tikz_document(canonical)
    source_path = root / "original" / "main.tex"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")
    result["source_path"] = str(source_path)
    metadata.update(canonical_tikz_sha256=_sha256(canonical.encode()), wrapper_sha256=_sha256(source.encode()))
    try:
        original = compile_latex(compiler_http, CompileRequest(source=source, outputs=Outputs(pdf=True, images=Images())))
    except (httpx.HTTPError, ValueError) as error:
        result.update(
            compile={"outcome": "unknown", "success": False, "diagnostic": str(error)},
            raster={"outcome": "unknown", "success": False},
            compile_error={"type": type(error).__name__, "message": str(error)},
        )
        return result
    artifacts = _artifact_records(original, root / "original")
    metadata.update(toolchain_id=original.toolchain_id, source_digest=original.source_digest, page_count=original.page_count)
    result.update(
        compile_success=original.compile.success, raster_success=original.raster.success,
        compile=_stage_record(original.compile), raster=_stage_record(original.raster),
        artifacts={"original": artifacts},
    )
    for name, key in (("result.pdf", "pdf_path"), ("result.log", "log_path"), ("page-1.png", "image_path")):
        artifact = artifacts.get(name)
        if artifact and artifact["complete"] and (key != "image_path" or original.raster.success):
            result[key] = artifact["path"]
    if not original.compile.success:
        metadata["discovery"] = {"status": "not_run_original_compile_failed"}
        return result
    pdf = next((artifact for artifact in original.artifacts if artifact.name == "result.pdf" and artifact.complete), None)
    if pdf is not None:
        try:
            result["pdf_observations"] = _pdf_observations(pdf.data, artifacts["result.pdf"]["sha256"], original.source_digest)
        except (ValueError, RuntimeError, pymupdf.FileDataError) as error:
            result["pdf_observations"] = {"status": "extraction_error", "error": str(error)}
    nodes, labels, discovery, annotations = _discover_executed_geometry(
        canonical, root, compiler_http, original, artifacts, result["pdf_observations"]
    )
    result.update(nodes=nodes, labeled_points=labels, annotations=annotations)
    metadata["discovery"] = discovery
    return result


def _discover_executed_geometry(
    canonical_tikz: str,
    root: Path,
    compiler_http: httpx.Client,
    original: Any,
    original_artifacts: Mapping[str, Mapping[str, Any]],
    pdf_observations: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    wrapper = _discovery_wrapper(canonical_tikz)
    source_path = root / "discovery" / "main.tex"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(wrapper, encoding="utf-8")
    metadata: dict[str, Any] = {
        "status": "running",
        "input_tikz_sha256": _sha256(canonical_tikz.encode("utf-8")),
        "instrumented_wrapper_sha256": _sha256(wrapper.encode("utf-8")),
        "source_path": str(source_path.resolve()),
    }
    request = CompileRequest(source=wrapper, outputs=Outputs(pdf=True, images=Images()))
    try:
        response = compile_latex(compiler_http, request)
    except (httpx.HTTPError, ValueError) as error:
        metadata.update(status="request_error", error=f"{type(error).__name__}: {error}")
        return [], {}, metadata, _empty_annotations("unknown", "instrumented_compile_request_failed")

    artifact_records = _artifact_records(response, root / "discovery")
    original_png = original_artifacts.get("page-1.png", {})
    probe_png = artifact_records.get("page-1.png", {})
    render_identity_match = bool(
        original_png.get("complete")
        and probe_png.get("complete")
        and original_png.get("sha256") == probe_png.get("sha256")
    )
    probe_log = next((item for item in response.artifacts if item.name == "result.log"), None)
    probe_pdf = next((item for item in response.artifacts if item.name == "result.pdf"), None)
    same_toolchain = response.toolchain_id == original.toolchain_id
    metadata.update(
        {
            "source_digest": response.source_digest,
            "toolchain_id": response.toolchain_id,
            "same_toolchain": same_toolchain,
            "compile": _stage_record(response.compile),
            "raster": _stage_record(response.raster),
            "artifacts": artifact_records,
            "render_identity": {
                "status": "identical_png_bytes" if render_identity_match else "mismatch_or_unavailable",
                "original_png_sha256": original_png.get("sha256"),
                "instrumented_png_sha256": probe_png.get("sha256"),
                "instrumented_pdf_sha256": _sha256(probe_pdf.data) if probe_pdf and probe_pdf.complete else None,
                "original_pdf_sha256": original_artifacts.get("result.pdf", {}).get("sha256"),
                "pdf_bytes_identical": bool(
                    probe_pdf
                    and probe_pdf.complete
                    and _sha256(probe_pdf.data) == original_artifacts.get("result.pdf", {}).get("sha256")
                ),
            },
        }
    )
    invalid_reason = None
    if not response.compile.success:
        invalid_reason = "instrumented_compile_failed"
    elif not same_toolchain:
        invalid_reason = "toolchain_mismatch"
    elif not probe_log or not probe_log.complete:
        invalid_reason = "instrumented_log_missing"
    elif not render_identity_match:
        invalid_reason = "instrumentation_render_mismatch"
    if invalid_reason:
        metadata.update(status="unknown", reason=invalid_reason)
        return [], {}, metadata, _empty_annotations("unknown", invalid_reason)

    if pdf_observations is None:
        pdf_observations = {"pages": []}
    log_text = probe_log.data.decode("utf-8", errors="replace")
    annotations = parse_annotations(log_text)
    nodes, frame, unsupported = _parse_discovery_log(
        log_text, pdf_observations, canonical_tikz
    )
    for node in nodes:
        bounds = node.get("pdf_bbox_pt")
        if not bounds:
            node["pdf_text_observation"] = "unavailable_without_verified_bounds"
            continue
        spans = []
        for page in (pdf_observations or {}).get("pages", []):
            for span_index, span in enumerate(page.get("text_spans", [])):
                span_bbox = span.get("bbox_pt")
                if isinstance(span_bbox, list) and len(span_bbox) == 4:
                    center_x = (float(span_bbox[0]) + float(span_bbox[2])) / 2
                    center_y = (float(span_bbox[1]) + float(span_bbox[3])) / 2
                    if _distance_to_rect(center_x, center_y, bounds) <= 1.0:
                        spans.append(f"pdf-text:{page.get('page_number', 1)}:{span_index}")
        node["extractable_text_evidence"] = spans
        node["pdf_text_observation"] = "span_inside_node_bounds" if spans else "no_extractable_span_inside_node_bounds"
    labeled_points = _bind_text_labels(pdf_observations, nodes, frame)
    if unsupported:
        metadata["status"] = "partial"
        metadata["unsupported"] = unsupported
    elif nodes:
        metadata["status"] = "ok"
    else:
        metadata["status"] = "empty"
    metadata["labeled_point_count"] = sum(point["status"] == "measured" for point in labeled_points.values())
    metadata["node_count"] = len(nodes)
    metadata["frame_mapping"] = frame
    metadata["label_binding_status"] = "partial" if any(v.get("status") != "measured" for v in labeled_points.values()) else "ok"
    metadata["annotation_status"] = annotations["status"]
    metadata["annotation_count"] = len(annotations["annotations"])
    return nodes, labeled_points, metadata, annotations


def _point_dot_evidence(drawing: dict[str, Any], observation: dict[str, Any], font_size: float) -> str | None:
    """Recognize optional empty circle-node glyphs at bound labeled points."""
    x0, y0, x1, y1 = drawing["rect"]
    width, height = x1 - x0, y1 - y0
    if not (drawing.get("fill") is not None and drawing.get("fill_opacity", 1) > 0
            and drawing.get("items") and all(item[0] == "c" for item in drawing["items"])
            and 0 < max(width, height) <= font_size * 1.2):
        return None
    center = ((x0 + x1) / 2, (y0 + y1) / 2)
    points = [(point["pdf_x"], point["pdf_y"]) for point in observation.get("labeled_points", {}).values()
              if point.get("status") == "measured" and "pdf_x" in point and "pdf_y" in point]
    point_text_ids = {f"pdf-text:{page.get('page_number', 1)}:{index}" for page in observation.get("pdf_observations", {}).get("pages", []) for index, span in enumerate(page.get("text_spans", [])) if _POINT_LABEL.fullmatch(_normalize_text(span.get("text", "")))}
    # A duplicated label makes point identity unresolved, but does not turn its
    # executed empty circle-node glyph into a newly required filled object.
    points.extend(node["attachment_pdf_pt"] for node in observation.get("nodes", []) if node.get("attachment") == "label-parent-center" and node.get("attachment_pdf_pt") and point_text_ids.intersection(node.get("extractable_text_evidence", [])))
    if not any(math.dist(center, point) <= 0.1 for point in points):
        return None
    matches = []
    for node in observation.get("nodes", []):
        circle = node.get("circle_path_pdf", {})
        nc = circle.get("center_pdf_pt")
        if (node.get("shape") != "circle" or circle.get("status") != "measured" or not nc
                or node.get("pdf_text_observation") != "no_extractable_span_inside_node_bounds"
                or math.dist(center, nc) > 0.02):
            continue
        # Runtime circle-path radii exclude outer separation. Transformed axis
        # endpoints also describe an elliptical point glyph without guessing
        # its radius from node anchors or adding a scale-dependent allowance.
        ex, ey = circle.get("x_radius_endpoint_pdf_pt"), circle.get("y_radius_endpoint_pdf_pt")
        if not ex or not ey:
            continue
        rx = math.hypot(ex[0] - nc[0], ey[0] - nc[0])
        ry = math.hypot(ex[1] - nc[1], ey[1] - nc[1])
        if abs(rx - width / 2) <= 0.02 and abs(ry - height / 2) <= 0.02:
            matches.append(circle["evidence_id"])
    return matches[0] if len(matches) == 1 else None


def _annotation_paths(observation: dict[str, Any], strokes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Associate executed standard angle paths with unique emitted PDF paths."""
    capture = observation.get("annotations", {})
    frame = observation.get("metadata", {}).get("discovery", {}).get("frame_mapping", {})
    if capture and capture.get("status") not in {"ok", "not_requested"}:
        return [], ["Angle annotation capture is incomplete; paths remain strict"]
    if not capture.get("annotations"):
        return [], []
    if capture.get("status") != "ok" or frame.get("status") != "verified_dimensions":
        return [], ["Angle annotation provenance is incomplete; paths remain strict"]
    annotations, issues, used = [], [], set()
    for annotation in capture["annotations"]:
        if not annotation.get("complete"):
            issues.append("Incomplete executed angle annotation")
            continue
        anchor_labels, anchors = [], []
        for role in ("first", "vertex", "second"):
            raw = annotation["anchors"][role]
            xy = _pdf_point(raw["x_pt"], raw["y_pt"], frame)
            labels = [label for label, point in observation.get("labeled_points", {}).items()
                      if point.get("status") == "measured" and xy is not None
                      and math.dist(xy, (point["pdf_x"], point["pdf_y"])) <= 0.1]
            anchor_labels.append(labels[0] if len(labels) == 1 else None)
            anchors.append(xy)
        for path in annotation["paths"]:
            if "stroke" not in path.get("paint_actions", []):
                continue
            if None in anchor_labels or any(xy is None for xy in anchors):
                issues.append("Angle annotation has an unresolved labeled anchor")
                continue
            items, current = [], None
            for operation in path["operations"]:
                values, op = operation["values_pt"], operation["op"]
                xy = [_pdf_point(values[i], values[i + 1], frame) for i in range(0, len(values), 2)]
                if any(point is None for point in xy):
                    items = []
                    break
                if op == "M":
                    current = first_point = xy[0]
                elif op == "L" and current is not None:
                    items.append(("l", current, xy[0]))
                    current = xy[0]
                elif op == "C" and current is not None:
                    items.append(("c", current, *xy))
                    current = xy[-1]
                elif op == "Z" and current is not None:
                    items.append(("l", current, first_point))
                    current = first_point
                else:
                    items = []
                    break
            parts = [LineString(part) for part in path_parts({"items": items})]
            if not parts:
                issues.append("Unsupported angle softpath")
                continue
            geometry = unary_union(parts)
            matches = [item for item in strokes if item["path"] not in used
                       and geometry.hausdorff_distance(item["geometry"]) <= 0.1
                       and abs(geometry.length - item["geometry"].length) <= 0.2]
            if len(matches) != 1:
                issues.append("Executed angle softpath does not uniquely identify a painted PDF stroke")
                continue
            item = matches[0]
            used.add(item["path"])
            first, vertex, second = anchor_labels
            rays = tuple(sorted((first, second))) if annotation["kind"] == "right_angle" else (first, second)
            key = (annotation["kind"], vertex, *rays, path["part"])
            item["annotation_key"] = key
            item["annotation_vertex"] = anchors[1]
            annotations.append({"pic_id": annotation["pic_id"], "path": item["path"], "key": key,
                                "anchors": anchor_labels, "vertex_pdf_pt": anchors[1]})
    return annotations, issues


def _normalize_text(value: str) -> str:
    return "".join(value.split()).replace("\u2032", "'").replace("\u2019", "'")


def read_scene(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one original-PDF scene; downstream checks never interpret PGF coordinates."""
    if not observation.get("compile_success") or not observation.get("pdf_path"):
        raise ValueError("No successfully compiled original PDF")
    pdf = Path(observation["pdf_path"]).read_bytes()
    digest = _sha256(pdf)
    artifact = observation.get("artifacts", {}).get("original", {}).get("result.pdf")
    if artifact and (not artifact.get("complete", True) or artifact.get("sha256") != digest):
        raise ValueError("Original PDF artifact is incomplete or changed")
    capture = observation.get("pdf_observations") or {}
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        if len(document) != 1:
            raise ValueError("Exactly one PDF page is required")
        page = document[0]
        records = capture.get("pages", [])
        cached = capture.get("pdf_sha256") == digest and len(records) == 1 and "drawings" in records[0]
        emitted = records[0] if cached else _page_observation(page, 0)
        if emitted.get("drawings_truncated") or emitted.get("text_truncated"):
            raise ValueError("PDF observation limit exceeded")
        text = [{
            "text": _normalize_text(span["text"]), "bbox": span["bbox_pt"], "size": span["size_pt"] or 10.0,
            "glyphs": [{"text": glyph["text"], "bbox": glyph["bbox_pt"]} for glyph in span["glyphs"] if not glyph["text"].isspace()],
        } for span in emitted["text_spans"] if _normalize_text(span["text"])]
        outlines = emitted.get("glyph_outlines")
        if outlines is None:
            chars = [{"c": glyph["text"], "bbox": glyph["bbox_pt"]} for span in emitted["text_spans"] for glyph in span["glyphs"]]
            outlines = extract_glyph_outlines(page, chars=chars, drawings=emitted["drawings"])
        ink_issues = attach_glyph_ink(text, outlines)
        raster_scale = min(2.0, 1800 / max(page.rect.width, page.rect.height))
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(raster_scale, raster_scale), colorspace=pymupdf.csRGB, alpha=False)
        pixels = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
        bounds = list(page.rect)
    font_size = float(np.median([label["size"] for label in text])) if text else 10.0
    markers, strokes, fills, unsupported = [], [], [], []
    for index, drawing in enumerate(emitted["drawings"]):
        if drawing["type"] in {"clip", "group"}:
            unsupported.append("Clip/group geometry is assessed by rendered visibility; no exact compositing proof")
            continue
        try:
            parts = path_parts(drawing)
        except ValueError as error:
            unsupported.append(str(error))
            continue
        x0, y0, x1, y1 = drawing["rect"]
        marker_evidence = _point_dot_evidence(drawing, dict(observation), font_size)
        if marker_evidence:
            center = ((x0 + x1) / 2, (y0 + y1) / 2)
            markers.append({"evidence_id": marker_evidence, "xy": center, "path": index,
                            "fill": drawing.get("fill"), "radius": max(x1 - x0, y1 - y0) / 2,
                            "color": drawing["fill"], "opacity": drawing.get("fill_opacity", 1), "geometry": Point(center)})
            continue
        lines = [LineString(part) for part in parts if len(part) >= 2 and LineString(part).length > 1e-8]
        if drawing.get("color") is not None and drawing.get("stroke_opacity", 1) > 0:
            components = [LineString(part) for item in drawing["items"] for part in path_parts({"items": [item]}) if len(part) >= 2]
            components += [LineString(part[-2:]) for part in parts if drawing.get("closePath") and len(part) >= 3]
            strokes.append({
                "components": components, "geometry": unary_union(lines), "color": drawing["color"],
                "dashed": drawing.get("dashes", "[] 0").split("]")[0].strip() != "[",
                "path": index, "width": drawing.get("width", 1), "opacity": drawing.get("stroke_opacity", 1),
            })
        if drawing.get("fill") is not None and drawing.get("fill_opacity", 1) > 0:
            polygons = [Polygon(part) for part in parts if len(part) >= 3]
            if any(not polygon.is_valid for polygon in polygons) or len(polygons) > 1:
                unsupported.append(f"Complex fill path {index} needs winding-rule handling")
            elif polygons:
                fills.append({"geometry": polygons[0], "color": drawing["fill"], "path": index, "opacity": drawing.get("fill_opacity", 1)})
    points, bindings, unresolved = {}, {}, []
    measured = observation.get("labeled_points", {})
    visible_labels = {label["text"] for label in text if _POINT_LABEL.fullmatch(label["text"])}
    for label in sorted(visible_labels | measured.keys()):
        point = measured.get(label, {})
        x, y = point.get("pdf_x"), point.get("pdf_y")
        if point.get("status") == "measured" and isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y):
            points[label], bindings[label] = (x, y), point
        else:
            points[label] = None
            unresolved.append(label)
            bindings[label] = {**point, "status": "unknown", "reason": point.get("reason", "No execution-grounded label attachment")}
    annotations, issues = _annotation_paths(dict(observation), strokes)
    unsupported.extend(issues)
    unsupported.extend(issue for issue in observation.get("metadata", {}).get("discovery", {}).get("unsupported", []) if not issue.startswith("coordinate_name:"))
    return {
        "frame": "original_pdf", "unit": "pdf_pt", "pdf_sha256": digest,
        "annotations": annotations, "points": points, "bindings": bindings, "unresolved": unresolved,
        "text": text, "ink_issues": sorted(set(ink_issues)), "markers": markers, "strokes": strokes, "fills": fills,
        "unsupported": sorted(set(unsupported)), "pixels": pixels, "raster_scale": raster_scale, "bounds": bounds,
    }

