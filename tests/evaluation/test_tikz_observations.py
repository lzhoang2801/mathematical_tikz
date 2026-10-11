import base64
from pathlib import Path

import httpx
import pymupdf
import pytest
from latex_compiler.schemas import (
    Artifact,
    CompileRequest,
    CompileResponse,
    StageResult,
)

from evaluation.tikz_observations import (
    _bind_text_labels,
    _pdf_text_line_observation,
    _point_label,
    compile_observe,
    read_scene,
)

TIKZ = r"""\begin{tikzpicture}
\coordinate (A) at (0,1);
\coordinate (H) at (0,0);
\coordinate (B) at (-1,0);
\coordinate (C) at (1,0);
\draw (A)--(H);
\draw (B)--(C);
\end{tikzpicture}"""


def _pdf_and_png() -> tuple[bytes, bytes]:
    document = pymupdf.open()
    page = document.new_page(width=120, height=90)
    page.draw_line((10, 30), (80, 30))
    page.insert_text((12, 20), "A")
    pdf = document.tobytes()
    png = page.get_pixmap().tobytes("png")
    document.close()
    return pdf, png


def _artifact(name: str, data: bytes) -> Artifact:
    return Artifact(name=name, data_base64=base64.b64encode(data).decode("ascii"))







def test_point_label_normalizes_primes_and_keeps_duplicates_unknown():
    assert _point_label("A\u2032") == "A'"
    assert _point_label(" A \u2019 ") == "A'"
    pdf = {
        "pages": [
            {
                "page_number": 1,
                "text_spans": [
                    {"text": "A\u2032", "bbox_pt": [1, 1, 5, 5]},
                    {"text": "A\u2019", "bbox_pt": [8, 1, 12, 5]},
                ],
            }
        ]
    }
    labels = _bind_text_labels(pdf, [], {"status": "verified_dimensions", "picture_id": "pgfid1"})
    assert labels["A'"]["status"] == "unknown"
    assert labels["A'"]["reason"] == "merged_or_duplicate_ambiguous_pdf_label"


def test_pdf_line_joins_font_split_superscript_prime_and_keeps_glyph_boxes():
    line = {
        "bbox": (10, 10, 20, 20),
        "spans": [
            {
                "chars": [{"c": "A", "bbox": (10, 12, 17, 20)}],
                "font": "MathFont-Regular",
                "size": 10,
            },
            {
                "chars": [{"c": "′", "bbox": (16, 10, 20, 15)}],
                "font": "MathFont-Symbol",
                "size": 6,
            },
        ],
    }

    observation = _pdf_text_line_observation(line)

    assert observation is not None
    assert observation["text"] == "A′"
    assert _point_label(observation["text"]) == "A'"
    assert observation["bbox_pt"] == [10.0, 10.0, 20.0, 20.0]
    assert observation["size_pt"] == 10
    assert observation["source_span_count"] == 2
    assert len(observation["glyphs"]) == 2


def test_overlapping_merged_pdf_labels_remain_unknown():
    pdf = {
        "pages": [
            {
                "page_number": 1,
                "text_spans": [
                    {
                        "text": "AB",
                        "bbox_pt": [1, 1, 10, 10],
                        "glyphs": [
                            {"text": "A", "bbox_pt": [1, 1, 7, 10]},
                            {"text": "B", "bbox_pt": [1, 1, 7, 10]},
                        ],
                    }
                ],
            }
        ]
    }
    labels = _bind_text_labels(pdf, [], {"status": "verified_dimensions", "picture_id": "pgfid1"})
    assert labels["A"]["status"] == "unknown"
    assert labels["B"]["status"] == "unknown"
    assert labels["A"]["reason"] == "merged_or_duplicate_ambiguous_pdf_label"


def _discovery_compiler(*, same_render: bool = True):
    pdf, png = _pdf_and_png()
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        page = document[0]
        label_bbox = next(
            span["bbox"]
            for block in page.get_text("dict")["blocks"]
            if block.get("type") == 0
            for line in block["lines"]
            for span in line["spans"]
            if span.get("text") == "A"
        )
        page_rect = page.rect
    conversion = 72.0 / 72.27
    border = 4.0
    min_x, min_y = -5.0, -5.0
    max_x = min_x + page_rect.width / conversion - 2 * border
    max_y = min_y + page_rect.height / conversion - 2 * border

    def pgf_point(pdf_x: float, pdf_y: float) -> tuple[float, float]:
        return (
            min_x + pdf_x / conversion - border,
            max_y + border - pdf_y / conversion,
        )

    left, top, right, bottom = label_bbox
    # The label node is intentionally displaced from the point it annotates.
    point_pdf = (42.0, 38.0)
    point_x, point_y = pgf_point(*point_pdf)
    node_pdf_box = (left - 2, top - 2, right + 2, bottom + 2)
    north_west = pgf_point(node_pdf_box[0], node_pdf_box[1])
    north_east = pgf_point(node_pdf_box[2], node_pdf_box[1])
    south_west = pgf_point(node_pdf_box[0], node_pdf_box[3])
    south_east = pgf_point(node_pdf_box[2], node_pdf_box[3])
    discovery_log = (
        "PTKZNODE|pgfid1|1|circle|ok|node-position\n"
        f"PTKZNPOS|pgfid1|1|{point_x}pt|{point_y}pt|{point_x}pt|{point_y}pt\n"
        f"PTKZNBBOX|pgfid1|1|{north_west[0]}pt|{north_west[1]}pt|{north_east[0]}pt|{north_east[1]}pt\n"
        f"PTKZNSBOX|pgfid1|1|{south_west[0]}pt|{south_west[1]}pt|{south_east[0]}pt|{south_east[1]}pt\n"
        f"PTKZBBOX|pgfid1|{min_x}pt|{min_y}pt|{max_x}pt|{max_y}pt\n"
    ).encode()
    requests: list[CompileRequest] = []

    def handle(request: httpx.Request) -> httpx.Response:
        compile_request = CompileRequest.model_validate_json(request.content)
        requests.append(compile_request)
        is_discovery = "PTKZNODE" in compile_request.source
        artifacts = [_artifact("result.log", discovery_log if is_discovery else b"")]
        if compile_request.outputs.pdf:
            artifacts.append(_artifact("result.pdf", pdf))
        if compile_request.outputs.images is not None:
            artifacts.append(_artifact("page-1.png", png if same_render or not is_discovery else b"different render"))
        result = CompileResponse(
            source_digest=compile_request.digest("test-toolchain"),
            toolchain_id="test-toolchain",
            page_count=1,
            compile=StageResult(outcome="ok", exit_code=0),
            raster=StageResult(
                outcome="not_requested"
                if compile_request.outputs.images is None
                else "ok",
                exit_code=0,
            ),
            artifacts=artifacts,
        )
        return httpx.Response(200, json=result.model_dump(mode="json"))

    client = httpx.Client(base_url="http://compiler.test", transport=httpx.MockTransport(handle))
    return client, requests


def test_discovery_binds_moved_label_to_executed_origin_without_filled_marker(tmp_path: Path):
    client, requests = _discovery_compiler()
    try:
        observed = compile_observe(TIKZ, tmp_path / "discovery", client)
    finally:
        client.close()

    assert len(requests) == 2
    assert "PTKZDISC" not in requests[1].source and "PTKZPOINT" not in requests[1].source
    assert "tikz@label@post/.append code" in requests[1].source
    assert "PTKZANN|" not in requests[1].source
    assert Path(observed["source_path"]).is_file()
    assert Path(observed["metadata"]["discovery"]["source_path"]).is_file()
    assert observed["metadata"]["discovery"]["render_identity"]["status"] == "identical_png_bytes"
    assert observed["metadata"]["discovery"]["frame_mapping"]["status"] == "verified_dimensions"
    assert observed["labeled_points"]["A"]["status"] == "measured"
    assert observed["labeled_points"]["A"]["pdf_x"] == pytest.approx(42.0)
    assert observed["labeled_points"]["A"]["pdf_y"] == pytest.approx(38.0)
    assert observed["labeled_points"]["A"]["pdf_coordinate_error_bound_pt"] == 2e-5
    assert "circle_path_pdf" not in observed["nodes"][0]
    assert "annotations" not in observed


def test_discovery_render_mismatch_invalidates_instrumented_geometry(tmp_path: Path):
    client, _ = _discovery_compiler(same_render=False)
    try:
        observed = compile_observe(TIKZ, tmp_path / "mismatch", client)
    finally:
        client.close()

    assert observed["compile_success"] is True
    assert observed["metadata"]["discovery"]["status"] == "unknown"
    assert observed["metadata"]["discovery"]["reason"] == "instrumentation_render_mismatch"
    assert observed["nodes"] == []
    assert observed["labeled_points"] == {}


def test_compiled_pdf_capture_is_reused_without_extracting_paths_or_text_again(tmp_path, monkeypatch):
    client, requests = _discovery_compiler()
    with client:
        observed = compile_observe(TIKZ, tmp_path / "capture", client)
    assert len(requests) == 2
    assert observed["metadata"]["schema_version"] == "tikz-observations:v4"
    assert "measurement" not in observed["metadata"]
    assert observed["pdf_observations"]["pages"][0]["glyph_outlines"]["status"] == "ok"

    def unexpected_extraction(*args, **kwargs):
        raise AssertionError("Original paths/text must use the canonical saved PDF capture")

    monkeypatch.setattr(pymupdf.Page, "get_drawings", unexpected_extraction)
    monkeypatch.setattr(pymupdf.Page, "get_text", unexpected_extraction)
    scene = read_scene(observed)
    assert scene["frame"] == "original_pdf" and scene["unit"] == "pdf_pt"
    assert scene["points"]["A"] == pytest.approx((42, 38))
    assert scene["strokes"] and scene["text"][0]["glyphs"][0].get("ink") is not None


def test_compiler_transport_failure_remains_unavailable(tmp_path):
    def unavailable(request):
        raise httpx.ConnectError("compiler unavailable", request=request)

    with httpx.Client(base_url="http://compiler.test", transport=httpx.MockTransport(unavailable)) as client:
        observed = compile_observe(TIKZ, tmp_path / "unavailable", client)
    assert observed["compile"]["outcome"] == "unknown"
    assert observed["compile_success"] is False and observed["labeled_points"] == {}
    assert observed["pdf_path"] is None


def test_dataset_comments_and_shared_libraries_compile_without_rewriting_source(tmp_path):
    source = (
        "% Geo3K source; ignored example \\input{ignored}\n"
        "\\usetikzlibrary{calc, angles}\n"
        "% keep layout comments\n"
        + TIKZ.replace("\\coordinate (A)", "% original point\n\\coordinate (A)")
        + "\n% trailing comment"
    )
    client, requests = _discovery_compiler()
    with client:
        observed = compile_observe(source, tmp_path / "dataset", client)
    assert observed["compile_success"] is True
    assert len(requests) == 2
    assert source in requests[0].source
    assert "% original point" in requests[1].source
    assert Path(observed["source_path"]).read_text(encoding="utf-8") == requests[0].source


@pytest.mark.parametrize("source", [
    "surrounding prose\n" + TIKZ,
    "\\documentclass{standalone}\n" + TIKZ,
    "\\usetikzlibrary{external}\n" + TIKZ,
    TIKZ.replace("\\coordinate (A)", "\\input{secret}\n\\coordinate (A)"),
    TIKZ + "\n" + TIKZ,
    "% ^^ encoded characters\n" + TIKZ,
])
def test_evaluation_source_compatibility_retains_shared_safety_checks(tmp_path, source):
    client, requests = _discovery_compiler()
    with client:
        observed = compile_observe(source, tmp_path / "invalid", client)
    assert observed["compile_success"] is False
    assert observed["compile"]["outcome"] == "validation_failed"
    assert requests == []
