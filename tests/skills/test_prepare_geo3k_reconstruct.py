import hashlib
from io import BytesIO

from PIL import Image

from tools import draw_instruction as drawing
from tools.prepare_geo3k_reconstruct import compile_candidate, normalize_code, successful, unique_candidates


def test_only_calc_preamble_is_removed_and_duplicate_origins_are_preserved():
    picture = "\\begin{tikzpicture}\n\\draw (A) -- (B);\n\\end{tikzpicture}"
    with_preamble = "\\usetikzlibrary{calc}\n" + picture
    rows = [
        ("train", 3, with_preamble, "source-image-a"),
        ("validation", 7, picture, "source-image-a"),
        ("test", 1, picture.replace("(A)", "(C)"), "source-image-b"),
    ]
    file_hashes = {split: f"{split}-hash" for split in ("train", "validation", "test")}

    assert normalize_code(with_preamble) == picture
    assert normalize_code(picture) == picture
    candidates, invalid = unique_candidates(rows, file_hashes)

    assert invalid == []
    assert len(candidates) == 2
    first = candidates[0]
    assert first["target_tikz"] == picture
    assert first["provenance"]["upstream_split"] == "train"
    assert first["provenance"]["upstream_row_index"] == 3
    assert first["provenance"]["upstream_code_sha256"] == hashlib.sha256(with_preamble.encode()).hexdigest()
    assert first["provenance"]["upstream_original_image_sha256"] == "source-image-a"
    assert first["provenance"]["duplicate_origins"][0]["upstream_split"] == "validation"
    assert first["source_group"] == "geo3k-image:source-image-a"
    assert all(row["instruction"] is None and "grade" not in row and "diagram_types" not in row
               for row in candidates)


def test_shared_compile_success_requires_exact_complete_one_page_raster(tmp_path):
    png = tmp_path / "page-1.png"
    png.write_bytes(b"compiled fixture")
    result = {"status": "needs_review", "compile": {"outcome": "ok"},
              "raster": {"outcome": "ok"}, "page_count": 1,
              "artifacts": {"page-1.png": {"path": str(png), "complete": True}}}

    assert successful(result)
    assert not successful({**result, "raster": {"outcome": "failed"}})
    assert not successful({**result, "page_count": 2})


def test_successful_compile_prepares_digest_bound_synthetic_input(tmp_path):
    code = "\\begin{tikzpicture}\n\\draw (A) -- (B);\n\\end{tikzpicture}"
    candidate, _ = unique_candidates(
        [("train", 3, code, "original-image-hash")],
        {split: f"{split}-hash" for split in ("train", "validation", "test")},
    )

    def compile_one(target_tikz, attempt, _compiler):
        attempt.mkdir(parents=True)
        buffer = BytesIO()
        Image.new("RGB", (3, 2), "white").save(buffer, format="PNG")
        png = buffer.getvalue()
        path = attempt / "page-1.png"
        path.write_bytes(png)
        return {
            "status": "needs_review",
            "input_tikz_sha256": hashlib.sha256(target_tikz.encode()).hexdigest(),
            "compile": {"outcome": "ok"},
            "raster": {"outcome": "ok"},
            "page_count": 1,
            "artifacts": {"page-1.png": {
                "path": str(path), "sha256": hashlib.sha256(png).hexdigest(), "complete": True,
            }},
        }

    row, _ = compile_candidate(candidate[0], tmp_path / "out", None, compile_one)
    source = drawing.source_image(row)
    preview = drawing.target_image(row)

    assert row["success"] is True
    assert row["drawing_status"] == "prepared"
    assert row["verification"]["status"] == "ready"
    assert row["verification"]["reviewed_by"] == "deterministic-code-render-binding"
    assert row["verification"]["reviewed_input_sha256"] == drawing.review_digest(row)
    assert source is not None and preview is not None
    assert source["bytes"] == preview["bytes"]
