import xml.etree.ElementTree as ET

import pymupdf
import pytest
from shapely.geometry import LineString, box

from evaluation.tikz_readability import (
    attach_glyph_ink,
    inspect_readability,
    extract_glyph_outlines,
    glyph_ink,
)


def test_font_outline_distinguishes_open_c_aperture_from_ink_stem():
    with pymupdf.open() as document:
        page = document.new_page(width=250, height=180)
        page.insert_text((113.222, 41.095), "C H", fontsize=7.9701)

        result = extract_glyph_outlines(page)

    assert result["status"] == "ok", result
    assert [glyph["text"] for glyph in result["glyphs"]] == ["C", "H"]
    glyph = result["glyphs"][0]
    label = {
        "size": 7.9701,
        "glyphs": [{"text": glyph["text"], "bbox": glyph["bbox_pt"]}],
    }
    assert attach_glyph_ink([label], result) == []
    assert label["glyphs"][0]["evidence_id"] == glyph["evidence_id"]
    ink = glyph_ink(glyph["drawings"])
    outline = glyph["drawings"][0]["rect"]
    y = (outline.y0 + outline.y1) / 2

    aperture = LineString([(outline.x1 - 0.8, y), (outline.x1 + 0.2, y)])
    assert aperture.intersection(box(*glyph["bbox_pt"])).length > 0.8
    assert aperture.intersection(ink).length == pytest.approx(0.0, abs=1e-6)

    stem = LineString([(outline.x0 + 0.4, y), (outline.x0 + 1.4, y)])
    assert stem.intersection(ink).length > 0.1


def test_extract_glyph_outlines_uses_supplied_page_char_records():
    with pymupdf.open() as document:
        page = document.new_page(width=100, height=80)
        page.insert_text((20, 30), "A", fontsize=10)

        result = extract_glyph_outlines(page, [{"c": "Z", "bbox": [10, 10, 20, 20]}])

    assert result["status"] == "unknown"
    assert result["reason"] == "SVG glyph order does not match PDF text extraction order"


def test_output_readability_retains_actual_collision_evidence():
    from shapely.geometry import LineString, box

    text = [{
        "text": "A",
        "bbox": [4, 4, 6, 6],
        "glyphs": [
            {
                "text": "A",
                "bbox": [4, 4, 6, 6],
                "ink": box(4, 4, 6, 6),
                "evidence_id": "glyph:A",
            }
        ],
    }]
    target = {"strokes": [], "text": text, "bounds": [0, 0, 10, 10], "ink_issues": []}
    output = {
        **target,
        "strokes": [{"geometry": LineString([(0, 5), (10, 5)]), "width": 0.5}],
    }

    result = inspect_readability(output)

    assert result["labels"][0]["status"] == "fail"
    issue = result["labels"][0]["issues"][0]
    assert issue == {"kind": "stroke_collision", "area_pdf_pt2": 1.0, "basis": "font_outline"}
    assert inspect_readability(target)["labels"][0]["status"] == "pass"


def test_nonspace_glyphs_still_match_when_svg_omits_inferred_spaces(monkeypatch):
    original = pymupdf.Page.get_svg_image

    def omit_space_uses(page, *args, **kwargs):
        source = original(page, *args, **kwargs)
        root = ET.fromstring(source)
        parents = {child: parent for parent in root.iter() for child in list(parent)}
        for use in [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "use"]:
            if (use.get("data-text") or "").isspace():
                parents[use].remove(use)
        return ET.tostring(root, encoding="unicode")

    monkeypatch.setattr(pymupdf.Page, "get_svg_image", omit_space_uses)
    with pymupdf.open() as document:
        page = document.new_page(width=250, height=180)
        page.insert_text((30, 60), "6 cmx8 cmOAB", fontsize=10)

        result = extract_glyph_outlines(page)

    assert result["status"] == "ok", result
    assert "".join(glyph["text"] for glyph in result["glyphs"]) == "6cmx8cmOAB"


def test_unresolved_outlines_cannot_earn_credit_and_overlaps_count_each_label_once():
    from shapely.geometry import LineString, box
    label = {"text": "A", "bbox": [4, 4, 6, 6], "glyphs": [{"text": "A", "bbox": [4, 4, 6, 6], "ink": box(4, 4, 6, 6)}]}
    scene = {"text": [label, label], "strokes": [{"geometry": LineString([(0, 5), (10, 5)]), "width": 0.5}],
             "bounds": [0, 0, 10, 10], "ink_issues": []}
    measured = inspect_readability(scene)
    assert [row["status"] for row in measured["labels"]] == ["fail", "fail"]
    assert len(measured["labels"][0]["issues"]) == 2
    scene["text"] = [{"text": "A", "bbox": [4, 4, 6, 6], "glyphs": []}]
    assert inspect_readability(scene)["labels"][0]["status"] == "unknown"
