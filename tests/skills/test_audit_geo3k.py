import unittest

from tools.audit_geo3k import duplicate_summary, stratified_indices


class Geo3KAuditTests(unittest.TestCase):
    def test_sampling_and_cross_split_duplicate_lineage(self):
        counts = {"train": 50, "validation": 12, "test": 30}
        first = stratified_indices(counts, 20, 20261008)
        self.assertEqual(first, stratified_indices(counts, 20, 20261008))
        self.assertEqual({split: len(indices) for split, indices in first.items()},
                         {"train": 20, "validation": 12, "test": 20})
        self.assertTrue(all(indices == sorted(set(indices)) for indices in first.values()))

        rows = [
            {"upstream_split": "train", "upstream_row_index": 1, "image_sha256": "same"},
            {"upstream_split": "test", "upstream_row_index": 7, "image_sha256": "same"},
            {"upstream_split": "train", "upstream_row_index": 2, "image_sha256": "unique"},
        ]
        summary = duplicate_summary(rows, "image_sha256")
        self.assertEqual(summary["unique_values"], 2)
        self.assertEqual(summary["duplicate_groups"], summary["cross_split_groups"])
        self.assertEqual(summary["excess_rows"], summary["cross_split_excess_rows"])


if __name__ == "__main__":
    unittest.main()
