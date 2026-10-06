"""Runtime provenance for standard TikZ angle annotation pics.

The probe is inserted into a compiled document after TikZ libraries are loaded.
It hooks the standard ``angles`` library helpers and PGF softpath construction
primitives while those helpers execute. It does not inspect TikZ source text or
classify paths by their size.
"""

from __future__ import annotations

import math
import re
from typing import Any

_MAX_PICS = 64
_MAX_OPERATIONS = 4096
_DIMENSION = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))pt$")
_INTEGER = re.compile(r"^\d+$")

# This fragment is deliberately runtime-only. The angles library has already
# loaded by the time standalone_tikz_document reaches \begin{document}.
PROBE_TEX = rf"""
\makeatletter
\newcount\PTKZAnnPicCount
\newcount\PTKZAnnOperationCount
\newcount\PTKZAnnPathOperationCount
\newif\ifPTKZAnnCapture
\newif\ifPTKZAnnTruncated
\newif\ifPTKZAnnPathOpen
\PTKZAnnCapturefalse
\PTKZAnnTruncatedfalse
\PTKZAnnPathOpenfalse

\def\PTKZAnnDimension#1{{\the\dimexpr#1\relax}}
\def\PTKZAnnLogAnchor#1#2{{%
  \begingroup
    \pgftransformreset
    \pgfpointanchor{{#2}}{{center}}%
    \pgfgetlastxy{{\PTKZAnnX}}{{\PTKZAnnY}}%
    \typeout{{PTKZANN|ANCHOR|\the\PTKZAnnPicCount|#1|\PTKZAnnX|\PTKZAnnY|\detokenize{{#2}}}}%
  \endgroup
}}
\let\PTKZAnnOriginalAngleParse\tikz@lib@angle@parse
\def\tikz@lib@angle@parse#1--#2--#3\pgf@stop{{%
  \global\advance\PTKZAnnPicCount by 1\relax
  \PTKZAnnOriginalAngleParse#1--#2--#3\pgf@stop
  \ifnum\PTKZAnnPicCount>{_MAX_PICS}\relax
    \ifPTKZAnnTruncated\else
      \global\PTKZAnnTruncatedtrue
      \typeout{{PTKZANN|TRUNCATED|pics}}%
    \fi
  \else
    \PTKZAnnLogAnchor{{first}}{{#1}}%
    \PTKZAnnLogAnchor{{vertex}}{{#2}}%
    \PTKZAnnLogAnchor{{second}}{{#3}}%
    \typeout{{PTKZANN|META|\the\PTKZAnnPicCount|\tikz@lib@angle@rad|\tikz@start@angle@temp|\tikz@end@angle@temp}}%
  \fi
}}

\def\PTKZAnnBeginPath#1#2{{%
  \global\PTKZAnnPathOperationCount=0\relax
  \ifnum\PTKZAnnPicCount>{_MAX_PICS}\relax
    \global\PTKZAnnCapturefalse
    \global\PTKZAnnPathOpenfalse
  \else
    \typeout{{PTKZANN|PATH|\the\PTKZAnnPicCount|#1|#2}}%
    \global\PTKZAnnCapturetrue
    \global\PTKZAnnPathOpentrue
  \fi
}}
\def\PTKZAnnEndPath{{%
  \global\PTKZAnnCapturefalse
  \ifPTKZAnnPathOpen
    \typeout{{PTKZANN|PATHEND|\the\PTKZAnnPicCount}}%
    \global\PTKZAnnPathOpenfalse
  \fi
}}
\def\PTKZAnnBeginOperation#1{{%
  \ifPTKZAnnCapture
    \global\advance\PTKZAnnOperationCount by 1\relax
    \global\advance\PTKZAnnPathOperationCount by 1\relax
    \ifnum\PTKZAnnOperationCount>{_MAX_OPERATIONS}\relax
      \ifPTKZAnnTruncated\else
        \global\PTKZAnnTruncatedtrue
        \typeout{{PTKZANN|TRUNCATED|operations}}%
      \fi
    \else
      \xdef\PTKZAnnCurrentOperation{{\the\PTKZAnnPathOperationCount}}%
      \typeout{{PTKZANN|OP|\the\PTKZAnnPicCount|\PTKZAnnCurrentOperation|#1}}%
    \fi
  \fi
}}
\def\PTKZAnnLogArgument#1#2{{%
  \ifPTKZAnnCapture
    \ifnum\PTKZAnnOperationCount>{_MAX_OPERATIONS}\relax\else
      \typeout{{PTKZANN|ARG|\the\PTKZAnnPicCount|\PTKZAnnCurrentOperation|#1|#2}}%
    \fi
  \fi
}}
\def\PTKZAnnLogPaint#1{{%
  \ifPTKZAnnCapture
    \typeout{{PTKZANN|PAINT|\the\PTKZAnnPicCount|#1}}%
  \fi
}}

\let\PTKZAnnOriginalAngleBackground\tikz@lib@angle@background
\def\tikz@lib@angle@background#1--#2--#3\pgf@stop{{%
  \PTKZAnnBeginPath{{angle}}{{background}}%
  \PTKZAnnOriginalAngleBackground#1--#2--#3\pgf@stop
  \PTKZAnnEndPath
}}
\let\PTKZAnnOriginalAngleForeground\tikz@lib@angle@foreground
\def\tikz@lib@angle@foreground#1--#2--#3\pgf@stop{{%
  \PTKZAnnBeginPath{{angle}}{{foreground}}%
  \PTKZAnnOriginalAngleForeground#1--#2--#3\pgf@stop
  \PTKZAnnEndPath
}}
\let\PTKZAnnOriginalRightBackground\tikz@lib@rightangle@background
\def\tikz@lib@rightangle@background#1--#2--#3\pgf@stop{{%
  \PTKZAnnBeginPath{{right_angle}}{{background}}%
  \PTKZAnnOriginalRightBackground#1--#2--#3\pgf@stop
  \PTKZAnnEndPath
}}
\let\PTKZAnnOriginalRightForeground\tikz@lib@rightangle@foreground
\def\tikz@lib@rightangle@foreground#1--#2--#3\pgf@stop{{%
  \PTKZAnnBeginPath{{right_angle}}{{foreground}}%
  \PTKZAnnOriginalRightForeground#1--#2--#3\pgf@stop
  \PTKZAnnEndPath
}}

\let\PTKZAnnOriginalMove\pgfsyssoftpath@moveto
\def\pgfsyssoftpath@moveto#1#2{{%
  \PTKZAnnBeginOperation{{M}}%
  \PTKZAnnLogArgument{{0}}{{\PTKZAnnDimension{{#1}}}}%
  \PTKZAnnLogArgument{{1}}{{\PTKZAnnDimension{{#2}}}}%
  \PTKZAnnOriginalMove{{#1}}{{#2}}%
}}
\let\PTKZAnnOriginalLine\pgfsyssoftpath@lineto
\def\pgfsyssoftpath@lineto#1#2{{%
  \PTKZAnnBeginOperation{{L}}%
  \PTKZAnnLogArgument{{0}}{{\PTKZAnnDimension{{#1}}}}%
  \PTKZAnnLogArgument{{1}}{{\PTKZAnnDimension{{#2}}}}%
  \PTKZAnnOriginalLine{{#1}}{{#2}}%
}}
\let\PTKZAnnOriginalCurve\pgfsyssoftpath@curveto
\def\pgfsyssoftpath@curveto#1#2#3#4#5#6{{%
  \PTKZAnnBeginOperation{{C}}%
  \PTKZAnnLogArgument{{0}}{{\PTKZAnnDimension{{#1}}}}%
  \PTKZAnnLogArgument{{1}}{{\PTKZAnnDimension{{#2}}}}%
  \PTKZAnnLogArgument{{2}}{{\PTKZAnnDimension{{#3}}}}%
  \PTKZAnnLogArgument{{3}}{{\PTKZAnnDimension{{#4}}}}%
  \PTKZAnnLogArgument{{4}}{{\PTKZAnnDimension{{#5}}}}%
  \PTKZAnnLogArgument{{5}}{{\PTKZAnnDimension{{#6}}}}%
  \PTKZAnnOriginalCurve{{#1}}{{#2}}{{#3}}{{#4}}{{#5}}{{#6}}%
}}
\let\PTKZAnnOriginalClose\pgfsyssoftpath@closepath
\def\pgfsyssoftpath@closepath{{%
  \PTKZAnnBeginOperation{{Z}}%
  \PTKZAnnOriginalClose
}}
\let\PTKZAnnOriginalRectangle\pgfsyssoftpath@rect
\def\pgfsyssoftpath@rect#1#2#3#4{{%
  \PTKZAnnBeginOperation{{R}}%
  \PTKZAnnLogArgument{{0}}{{\PTKZAnnDimension{{#1}}}}%
  \PTKZAnnLogArgument{{1}}{{\PTKZAnnDimension{{#2}}}}%
  \PTKZAnnLogArgument{{2}}{{\PTKZAnnDimension{{#3}}}}%
  \PTKZAnnLogArgument{{3}}{{\PTKZAnnDimension{{#4}}}}%
  \PTKZAnnOriginalRectangle{{#1}}{{#2}}{{#3}}{{#4}}%
}}
\let\PTKZAnnOriginalStroke\pgfsys@stroke
\def\pgfsys@stroke{{\PTKZAnnLogPaint{{stroke}}\PTKZAnnOriginalStroke}}
\let\PTKZAnnOriginalFill\pgfsys@fill
\def\pgfsys@fill{{\PTKZAnnLogPaint{{fill}}\PTKZAnnOriginalFill}}
\let\PTKZAnnOriginalFillStroke\pgfsys@fillstroke
\def\pgfsys@fillstroke{{\PTKZAnnLogPaint{{fillstroke}}\PTKZAnnOriginalFillStroke}}
\makeatother
"""


def parse_annotations(log_text: str) -> dict[str, Any]:
    """Parse angle-pic events and exact PGF softpath operations from a TeX log.

    Coordinates remain in the PGF runtime's TeX-point frame. This function does
    not transform them into PDF pixels or decide whether paths are visible.
    """
    if not isinstance(log_text, str):
        raise TypeError("log_text must be a string")

    records: dict[int, dict[str, Any]] = {}
    diagnostics: list[str] = []
    truncated = False

    def record_for(raw_id: str) -> dict[str, Any] | None:
        if not _INTEGER.fullmatch(raw_id):
            diagnostics.append("invalid_pic_id")
            return None
        pic_id = int(raw_id)
        if pic_id < 1 or pic_id > _MAX_PICS:
            diagnostics.append("pic_id_out_of_range")
            return None
        return records.setdefault(
            pic_id,
            {
                "pic_id": pic_id,
                "kind": None,
                "anchors": {},
                "radius_pt": None,
                "start_angle_deg": None,
                "end_angle_deg": None,
                "paths": [],
            },
        )

    def dimension(raw: str) -> float | None:
        match = _DIMENSION.fullmatch(raw.strip())
        if not match:
            return None
        value = float(match.group(1))
        return value if math.isfinite(value) else None

    current_path: dict[str, Any] | None = None
    for raw_line in log_text.splitlines():
        marker = raw_line.find("PTKZANN|")
        if marker < 0:
            continue
        fields = raw_line[marker:].strip().split("|")
        if len(fields) < 3 or fields[0] != "PTKZANN":
            diagnostics.append("malformed_record")
            current_path = None
            continue

        event = fields[1]
        if event == "TRUNCATED":
            truncated = True
            diagnostics.append("truncated_" + (fields[2] if len(fields) > 2 else "unknown"))
            current_path = None
            continue

        if event == "ANCHOR":
            if len(fields) < 7:
                diagnostics.append("malformed_anchor")
                continue
            item = record_for(fields[2])
            x, y = dimension(fields[4]), dimension(fields[5])
            role = fields[3]
            if item is None or x is None or y is None or role not in {"first", "vertex", "second"}:
                diagnostics.append("invalid_anchor")
                continue
            item["anchors"][role] = {"name": "|".join(fields[6:]), "x_pt": x, "y_pt": y}
            continue

        if event == "META":
            if len(fields) != 6:
                diagnostics.append("malformed_meta")
                continue
            item = record_for(fields[2])
            radius = dimension(fields[3] + "pt") if not fields[3].endswith("pt") else dimension(fields[3])
            try:
                start, end = float(fields[4]), float(fields[5])
            except ValueError:
                start = end = math.nan
            if item is None or radius is None or not math.isfinite(start) or not math.isfinite(end):
                diagnostics.append("invalid_meta")
                continue
            item.update(radius_pt=radius, start_angle_deg=start, end_angle_deg=end)
            continue

        if event == "PATH":
            if len(fields) != 5:
                diagnostics.append("malformed_path")
                current_path = None
                continue
            item = record_for(fields[2])
            kind, part = fields[3], fields[4]
            if item is None or kind not in {"angle", "right_angle"} or part not in {"background", "foreground"}:
                diagnostics.append("invalid_path")
                current_path = None
                continue
            if item["kind"] not in (None, kind):
                diagnostics.append("conflicting_kind")
                current_path = None
                continue
            item["kind"] = kind
            current_path = {
                "pic_id": int(fields[2]),
                "part": part,
                "operations": [],
                "paint_actions": [],
                "record_complete": False,
            }
            item["paths"].append(current_path)
            continue

        if event == "OP":
            if len(fields) != 5 or current_path is None:
                diagnostics.append("orphan_operation")
                continue
            if fields[2] != str(current_path["pic_id"]):
                diagnostics.append("operation_pic_mismatch")
                continue
            if current_path.get("pending") is not None:
                diagnostics.append("incomplete_operation")
            op_id, operation = fields[3], fields[4]
            expected = {"M": 2, "L": 2, "C": 6, "Z": 0, "R": 4}.get(operation)
            if not _INTEGER.fullmatch(op_id) or expected is None:
                diagnostics.append("invalid_operation")
                continue
            pending = {"op_id": op_id, "op": operation, "expected": expected, "values_pt": []}
            current_path["pending"] = pending
            if expected == 0:
                current_path["operations"].append({"op": operation, "values_pt": []})
                current_path["pending"] = None
            continue

        if event == "ARG":
            if len(fields) != 6 or current_path is None:
                diagnostics.append("orphan_argument")
                continue
            pending = current_path.get("pending")
            if fields[2] != str(current_path["pic_id"]) or pending is None or fields[3] != pending["op_id"]:
                diagnostics.append("argument_operation_mismatch")
                continue
            if not _INTEGER.fullmatch(fields[4]) or int(fields[4]) != len(pending["values_pt"]):
                diagnostics.append("invalid_argument_index")
                continue
            value = dimension(fields[5])
            if value is None:
                diagnostics.append("invalid_argument")
                continue
            pending["values_pt"].append(value)
            if len(pending["values_pt"]) == pending["expected"]:
                current_path["operations"].append({"op": pending["op"], "values_pt": pending["values_pt"]})
                current_path["pending"] = None
            continue

        if event == "PAINT":
            if len(fields) != 4 or current_path is None:
                diagnostics.append("orphan_paint_action")
                continue
            if fields[2] != str(current_path["pic_id"]) or fields[3] not in {"stroke", "fill", "fillstroke"}:
                diagnostics.append("invalid_paint_action")
                continue
            current_path["paint_actions"].append(fields[3])
            continue

        if event == "PATHEND":
            if current_path is None or len(fields) != 3 or fields[2] != str(current_path["pic_id"]):
                diagnostics.append("unmatched_path_end")
            else:
                if current_path.get("pending") is not None:
                    diagnostics.append("incomplete_operation")
                else:
                    current_path["record_complete"] = True
                current_path.pop("pending", None)
                current_path = None
            continue

        diagnostics.append("unknown_event")
        current_path = None

    if current_path is not None:
        diagnostics.append("unterminated_path")

    annotations = []
    for pic_id in sorted(records):
        item = records[pic_id]
        if item["kind"] is None:
            continue
        item["complete"] = (
            len(item["anchors"]) == 3
            and item["radius_pt"] is not None
            and bool(item["paths"])
            and all(path["operations"] and path["record_complete"] for path in item["paths"])
        )
        item["painted_by_pgf"] = any(path["paint_actions"] for path in item["paths"])
        annotations.append(item)

    status = "truncated" if truncated else ("partial" if diagnostics or any(not a["complete"] for a in annotations) else "ok")
    return {
        "status": status,
        "annotations": annotations,
        "truncated": truncated,
        "diagnostics": sorted(set(diagnostics)),
        "coordinate_unit": "TeX pt",
        "coordinate_frame": "PGF runtime softpath; map with compile_observe frame",
        "meaning": "constructed standard-angle softpaths and PGF paint actions; this does not establish final pixel visibility or instruction fidelity",
    }


