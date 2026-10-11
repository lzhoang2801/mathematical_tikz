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
            generated = [
                {"id": "base", "task": "Generate", "instruction": "Base instruction", "current_tikz": None,
                 "target_tikz": "base-code", "source_group": "A", "provenance": {"parents": ["parent"]}},
                {"id": "derived", "task": "Generate", "instruction": "Complete instruction", "current_tikz": None,
                 "target_tikz": "edited-code", "provenance": {"derived_from_edit": "edit"}},
            ]
            edited = [{"id": "edit", "task": "Edit", "instruction": "Add median", "current_tikz": "base-code",
                       "target_tikz": "edited-code", "split": "test", "provenance": {"starting_record_id": "base"}}]
            for task, rows in (("generate", generated), ("edit", edited)):
                (synthetic / f"{task}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            before = {path: file_digest(path) for path in list(geo.glob("*.parquet")) + list(synthetic.glob("*.jsonl"))}
            report = export(geo, synthetic, output, seed=42)
            self.assertEqual(report["rows"], 7)
            self.assertTrue(report["all_input_rows_retained"])
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


if __name__ == "__main__":
    unittest.main()
