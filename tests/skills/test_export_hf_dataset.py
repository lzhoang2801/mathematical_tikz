import json
import tempfile
import unittest
from collections import Counter
from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

from tools.export_hf_dataset import COLUMNS, SPLITS, assign_splits, digest, export, file_digest


def png(color):
    stream = BytesIO()
    Image.new("RGB", (4, 3), color).save(stream, format="PNG")
    return {"bytes": stream.getvalue(), "path": None}


def reviewed_row(row, image_path: Path, color: str, current_color: str | None = None):
    from tools import draw_instruction as drawing

    payload = png(color)["bytes"]
    image_path.write_bytes(payload)
    row.update(rendered_png_path=str(image_path),
        rendered_png_sha256=digest(payload),
        rendered_tikz_sha256=digest(row["target_tikz"].encode("utf-8")))
    if row["task"] == "Edit":
        current_payload = png(current_color or "white")["bytes"]
        current_path = image_path.with_name(image_path.stem + "-current.png")
        current_path.write_bytes(current_payload)
        row["current_render"] = {
            "rendered_png_path": str(current_path),
            "rendered_png_sha256": digest(current_payload),
            "rendered_tikz_sha256": digest(row["current_tikz"].encode("utf-8")),
        }
        row["review_evidence"] = {
            "source": "Compared with the supplied source statement.",
            "instruction": "The requested edit is stated completely.",
            "mathematics": "All constructed relations were checked.",
            "content": "Required visible objects are present.",
            "readability": "Labels and constructions have clear spacing.",
            "edit_change": "Added segment AB and point B.",
            "edit_preservation": "The original point A and its geometry remain unchanged.",
            "unresolved": [],
        }
    else:
        row["review_evidence"] = {
            "source": "Compared with the supplied source statement.",
            "instruction": "The construction scope is complete.",
            "mathematics": "All constructed relations were checked.",
            "content": "Required visible objects are present.",
            "readability": "Labels and constructions have clear spacing.",
            "unresolved": [],
        }
    row["verification"] = {
        "status": "ready",
        "reviewed_by": "human:test-fixture",
        "method": "independent_source_render_review",
    }
    row["verification"]["reviewed_input_sha256"] = drawing.review_digest(row)
    return row


class ExportTest(unittest.TestCase):
    def test_transitive_links_keep_held_out_and_saved_assignments(self):
        rows = [
            {"_task": "generate", "_keys": {"family:A", "code:base"}, "_pinned": None},
            {"_task": "edit", "_keys": {"code:base", "code:edited"}, "_pinned": None},
            {"_task": "generate", "_keys": {"code:edited", "family:B"}, "_pinned": "test"},
        ]
        splits, remembered, groups = assign_splits(rows, 42)
        self.assertEqual(splits, ["test"] * 3)
        self.assertEqual(groups, 1)
        replacement = [{"_task": "edit", "_keys": {"family:A", "code:new"}, "_pinned": None}]
        self.assertEqual(assign_splits(replacement, 42, remembered)[0], ["test"])

    def test_group_assignment_is_balanced_and_order_independent(self):
        rows = []
        for family in range(40):
            for task in ("generate", "edit"):
                for variant in range(family % 4 + 1):
                    rows.append({"_task": task, "_keys": {f"family:{family}", f"record:{task}:{family}:{variant}"},
                                 "_pinned": None})
        splits, _, _ = assign_splits(rows, 42)
        reverse, _, _ = assign_splits(list(reversed(rows)), 42)
        self.assertEqual(splits, list(reversed(reverse)))
        by_key = {}
        for row, split in zip(rows, splits):
            for key in row["_keys"]:
                self.assertEqual(by_key.setdefault(key, split), split)
        for task in ("generate", "edit"):
            counts = Counter(split for row, split in zip(rows, splits) if row["_task"] == task)
            for split, fraction in zip(SPLITS, (0.8, 0.1, 0.1)):
                self.assertLessEqual(abs(counts[split] - 100 * fraction), 4)

    def test_export_retains_rows_exact_fields_images_nulls_and_duplicate_hash_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            geo, synthetic, output = root / "geo", root / "synthetic", root / "out"
            geo.mkdir()
            synthetic.mkdir()
            image, other = png("white"), png("blue")
            raw_code = "\\usetikzlibrary{calc}\n\\begin{tikzpicture}\n% unchanged text\n\\end{tikzpicture}"
            image_type = pa.struct([("bytes", pa.binary()), ("path", pa.string())])
            schema = pa.schema([("rendered_image", image_type), ("code", pa.string()), ("image", image_type)])
            upstream = {
                "train": [{"rendered_image": image, "code": raw_code, "image": image},
                          {"rendered_image": None, "code": "missing-render-code", "image": other}],
                "validation": [{"rendered_image": other, "code": "other-code", "image": other}],
                "test": [{"rendered_image": image, "code": raw_code + "\n% alternate", "image": image}],
            }
            for split, rows in upstream.items():
                pq.write_table(pa.Table.from_pylist(rows, schema=schema), geo / f"{split}-00000-of-00001.parquet")
            base_code = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
            edited_code = r"\begin{tikzpicture}\coordinate (A) at (0,0);\coordinate (B) at (1,0);\draw (A)--(B);\end{tikzpicture}"
            generated = [
                reviewed_row({"id": "base", "task": "Generate", "instruction": "Base instruction", "current_tikz": None,
                 "target_tikz": base_code, "source": "Base source", "source_group": "A", "grade": 8,
                 "provenance": {"parents": ["parent"]}}, root / "base.png", "red"),
                reviewed_row({"id": "derived", "task": "Generate", "instruction": "Complete instruction", "current_tikz": None,
                 "target_tikz": edited_code, "source": "Derived source", "provenance": {"derived_from_edit": "edit"}},
                 root / "derived.png", "green"),
            ]
            edited = [reviewed_row({"id": "edit", "task": "Edit", "instruction": "Add median", "current_tikz": base_code,
                       "target_tikz": edited_code, "source": "Edit source", "split": "test",
                       "provenance": {"starting_record_id": "base"}}, root / "edit.png", "green")]
            for task, rows in (("generate", generated), ("edit", edited)):
                (synthetic / f"{task}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            before = {path: file_digest(path) for path in list(geo.glob("*.parquet")) + list(synthetic.glob("*.jsonl"))}
            report = export(geo, synthetic, output, seed=42)
            self.assertEqual(report["rows"], 7)
            self.assertTrue(report["all_input_rows_retained"])
            self.assertEqual(report["training_ready_rows"], 7)
            self.assertEqual(report["withheld_nonready_candidates"]["generate"]["count"], 0)
            self.assertEqual(report["withheld_nonready_candidates"]["edit"]["count"], 0)
            self.assertEqual(report["cross_split_lineage_or_exact_duplicates"], 0)
            self.assertEqual(report["missing_rendered_images"], ["geo3k/train-00000-of-00001.parquet:1"])
            reconstruct = []
            for path in (output / "reconstruct").glob("*.parquet"):
                table = pq.read_table(path)
                self.assertEqual(table.schema.names, list(COLUMNS["reconstruct"]))
                features = json.loads(table.schema.metadata[b"huggingface"])["info"]["features"]
                self.assertEqual(features["image"], {"_type": "Image"})
                reconstruct.extend(table.to_pylist())
            duplicate = [row for row in reconstruct if row["id"] == digest(image["bytes"])]
            self.assertEqual(len(duplicate), 2)
            self.assertEqual({row["target_tikz"] for row in duplicate}, {raw_code, raw_code + "\n% alternate"})
            self.assertTrue(all(row["image"] == image for row in duplicate))
            self.assertEqual(sum(row["id"] is None and row["image"] is None for row in reconstruct), 1)
            self.assertEqual(pq.read_table(output / "reconstruct/test.parquet").num_rows, 2)
            for task, expected in (("generate", generated), ("edit", edited)):
                table = pq.read_table(output / task / "test.parquet")
                self.assertEqual(table.schema.names, list(COLUMNS[task]))
                self.assertEqual(table.schema.field("current_tikz").type, pa.string())
                self.assertEqual(table.to_pylist(), [{k: row.get(k) for k in COLUMNS[task]} for row in expected])
            again = export(geo, synthetic, output, seed=42)
            self.assertEqual(again["output_sha256"], report["output_sha256"])
            self.assertEqual(before, {path: file_digest(path) for path in before})
            with self.assertRaisesRegex(ValueError, "different seed"):
                export(geo, synthetic, output, seed=43)
            reviewed = export(None, synthetic, root / "reviewed", seed=42)
            self.assertEqual(reviewed["rows"], 3)
            self.assertEqual(sum(reviewed["counts"]["reconstruct"].values()), 0)
            self.assertTrue(all("geo3k" not in path for path in reviewed["input_sha256"]))

    def test_unreviewed_pairs_are_withheld_and_invalid_ready_evidence_fails(self):
        from tools import draw_instruction as drawing

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            synthetic, output = root / "synthetic", root / "out"
            synthetic.mkdir()
            base_code = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
            edit_code = r"\begin{tikzpicture}\coordinate (A) at (0,0);\coordinate (B) at (1,0);\draw (A)--(B);\end{tikzpicture}"
            candidates = {
                "generate": [{"id": "candidate-g", "task": "Generate", "instruction": "Draw A.",
                              "current_tikz": None, "target_tikz": base_code,
                              "verification": {"status": "candidate"}}],
                "edit": [{"id": "candidate-e", "task": "Edit", "instruction": "Add B.",
                          "current_tikz": base_code, "target_tikz": edit_code,
                          "verification": {"status": "needs_revision"}}],
            }
            for task, rows in candidates.items():
                (synthetic / f"{task}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

            report = export(None, synthetic, output, seed=7)

            self.assertEqual(report["training_ready_rows"], 0)
            self.assertFalse(report["all_input_rows_retained"])
            self.assertEqual(report["counts"]["generate"], {"train": 0, "validation": 0, "test": 0})
            self.assertEqual(report["counts"]["edit"], {"train": 0, "validation": 0, "test": 0})
            self.assertEqual(report["withheld_nonready_candidates"]["generate"]["ids"], ["candidate-g"])
            self.assertEqual(report["withheld_nonready_candidates"]["generate"]["statuses"], {"candidate": 1})
            self.assertEqual(report["withheld_nonready_candidates"]["edit"]["ids"], ["candidate-e"])
            self.assertEqual(report["withheld_nonready_candidates"]["edit"]["statuses"], {"needs_revision": 1})

            invalid = reviewed_row({"id": "forged-ready", "task": "Generate", "instruction": "Draw A.",
                "current_tikz": None, "target_tikz": base_code, "source": "Source"}, root / "ready.png", "white")
            invalid["review_evidence"].pop("source")
            invalid["verification"]["reviewed_input_sha256"] = drawing.review_digest(invalid)
            (synthetic / "generate.jsonl").write_text(json.dumps(invalid) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "independent source/render review evidence"):
                export(None, synthetic, root / "invalid-out", seed=7)


if __name__ == "__main__":
    unittest.main()


def test_source_reference_alone_keeps_variants_in_frozen_held_out_split(tmp_path):
    synthetic = tmp_path / "synthetic"
    synthetic.mkdir()
    (synthetic / "edit.jsonl").write_text("", encoding="utf-8")
    rows = []
    for index, color in enumerate(("red", "blue", "green")):
        rows.append(reviewed_row({
            "id": f"variant-{index}", "task": "Generate",
            "instruction": f"Configuration {index}", "current_tikz": None,
            "target_tikz": f"\\begin{{tikzpicture}}\\coordinate (A) at ({index},0);\\end{{tikzpicture}}",
            "source": "source.tex#problem=7", "split": "test" if index == 0 else None,
        }, tmp_path / f"{index}.png", color))
    def save(selected):
        (synthetic / "generate.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in selected), encoding="utf-8")
    save(rows[:2])
    output = tmp_path / "export"
    first = export(None, synthetic, output, seed=42)
    frozen = json.loads((output / "split_assignments.json").read_text(encoding="utf-8"))["keys"]
    assert first["counts"]["generate"] == {"train": 0, "validation": 0, "test": 2}
    save(rows)
    second = export(None, synthetic, output, seed=42)
    current = json.loads((output / "split_assignments.json").read_text(encoding="utf-8"))["keys"]
    assert second["counts"]["generate"] == {"train": 0, "validation": 0, "test": 3}
    assert all(current[key] == split for key, split in frozen.items())
    table = pq.read_table(output / "generate/test.parquet")
    assert table.column_names == list(COLUMNS["generate"])


def test_export_retries_short_windows_parquet_reader_lock(tmp_path, monkeypatch):
    synthetic = tmp_path / "synthetic"
    synthetic.mkdir()
    row = reviewed_row({
        "id": "lock-safe", "task": "Generate", "instruction": "Configuration A",
        "current_tikz": None, "target_tikz": "\\begin{tikzpicture}\\coordinate (A) at (0,0);\\end{tikzpicture}",
        "source": "source.tex#problem=lock", "split": "train",
    }, tmp_path / "target.png", "black")
    (synthetic / "generate.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (synthetic / "edit.jsonl").write_text("", encoding="utf-8")
    original_replace = Path.replace
    attempts = []
    def locked_once(path, target):
        if path.name == "val.parquet.tmp" and path.parent.name == "edit":
            attempts.append(path)
            if len(attempts) == 1:
                raise PermissionError("short Windows reader lock")
        return original_replace(path, target)
    monkeypatch.setattr(Path, "replace", locked_once)
    output = tmp_path / "export"
    report = export(None, synthetic, output, seed=42)
    assert len(attempts) == 2
    assert report["training_ready_rows"] == 1
    assert pq.read_table(output / "generate/train.parquet").to_pylist()[0]["id"] == row["id"]
    assert json.loads((output / "split_assignments.json").read_text(encoding="utf-8"))["keys"]["record:lock-safe"] == "train"
