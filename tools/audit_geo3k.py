"""Audit the local Geo3K Parquet snapshot without changing its source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "dataset" / "geo3k-tikz" / "data"
DEFAULT_OUTPUT = ROOT / "dataset" / "geo3k-audit-20261008"
SPLITS = ("train", "validation", "test")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def image_payload(value: object) -> bytes | None:
    if isinstance(value, dict):
        value = value.get("bytes")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    return None


def stratified_indices(counts: dict[str, int], per_split: int, seed: int) -> dict[str, list[int]]:
    rng = random.Random(seed)
    return {
        split: sorted(rng.sample(range(count), min(per_split, count)))
        for split, count in counts.items()
    }


def duplicate_summary(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        if value:
            groups[value].append((row["upstream_split"], row["upstream_row_index"]))
    duplicates = [(value, refs) for value, refs in groups.items() if len(refs) > 1]
    cross_split = [(value, refs) for value, refs in duplicates if len({s for s, _ in refs}) > 1]

    def sample(items: list[tuple[str, list[tuple[str, int]]]]) -> list[dict]:
        return [
            {"sha256": value, "rows": [{"split": split, "index": index} for split, index in refs[:8]]}
            for value, refs in items[:8]
        ]

    return {
        "unique_values": len(groups),
        "duplicate_groups": len(duplicates),
        "excess_rows": sum(len(refs) - 1 for _, refs in duplicates),
        "cross_split_groups": len(cross_split),
        "cross_split_excess_rows": sum(len(refs) - 1 for _, refs in cross_split),
        "examples": sample(duplicates),
        "cross_split_examples": sample(cross_split),
    }


def image_info(value: object) -> tuple[dict, bytes | None]:
    data = image_payload(value)
    if data is None:
        return {"sha256": None, "bytes": 0, "format": None, "width": None, "height": None, "decode_error": None}, None
    info = {"sha256": digest(data), "bytes": len(data), "format": None,
            "width": None, "height": None, "decode_error": None}
    try:
        with Image.open(BytesIO(data)) as image:
            info.update(format=image.format, width=image.width, height=image.height)
            image.verify()
    except Exception as error:  # retain malformed-image diagnostics instead of aborting the audit
        info["decode_error"] = type(error).__name__
    return info, data


def complexity(row: dict) -> tuple[int, int, int]:
    return (len(row.get("line_instances") or []),
            len(row.get("diagram_logic_form") or []),
            len(row.get("text_logic_form") or []))


def choose_visual_rows(rows: list[dict], sample: dict[str, list[int]]) -> list[dict]:
    chosen = []
    seen_pairs = set()
    for split, indices in sample.items():
        candidates = [row for row in rows if row["upstream_split"] == split
                      and row["upstream_row_index"] in indices
                      and row["source_image_sha256"] and row["rendered_image_sha256"]]
        candidates.sort(key=lambda row: (complexity(row), row["upstream_row_index"]))
        for fraction in (0.35, 0.8):
            if not candidates:
                break
            target = round((len(candidates) - 1) * fraction)
            order = sorted(range(len(candidates)), key=lambda i: abs(i - target))
            for position in order:
                row = candidates[position]
                pair = (row["source_image_sha256"], row["code_sha256"])
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    chosen.append(row)
                    break
            candidates = [row for row in candidates if row not in chosen]
    return chosen


def jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)


def audit(data_dir: Path, output_dir: Path, per_split: int = 20, seed: int = 20261008) -> dict:
    if per_split < 1:
        raise ValueError("per_split must be positive")
    data_dir = data_dir.resolve()
    output_dir = output_dir.resolve()
    tables, file_hashes = {}, {}
    for split in SPLITS:
        path = data_dir / f"{split}-00000-of-00001.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        tables[split] = pq.read_table(path)
        file_hashes[split] = {"path": path.as_posix(), "sha256": file_digest(path), "bytes": path.stat().st_size}

    counts = {split: table.num_rows for split, table in tables.items()}
    sample = stratified_indices(counts, per_split, seed)
    rows, rows_by_split = [], {split: [] for split in SPLITS}
    nulls, blanks, empty_lists = defaultdict(int), defaultdict(int), defaultdict(int)
    missing_rows, first_lines, malformed_code_rows = defaultdict(list), Counter(), []
    image_decode_errors, formats = defaultdict(int), defaultdict(int)
    schemas = {}

    for split, table in tables.items():
        schemas[split] = [{"name": field.name, "type": str(field.type)} for field in table.schema]
        source_path = data_dir / f"{split}-00000-of-00001.parquet"
        source_hash = file_hashes[split]["sha256"]
        for index, raw in enumerate(table.to_pylist()):
            for field, value in raw.items():
                nulls[field] += value is None
                blanks[field] += isinstance(value, str) and not value.strip()
                empty_lists[field] += isinstance(value, list) and not value
                if value is None and len(missing_rows[field]) < 20:
                    missing_rows[field].append(f"{split}:{index}")
            source_info, source_bytes = image_info(raw.get("image"))
            render_info, render_bytes = image_info(raw.get("rendered_image"))
            for name, info in (("image", source_info), ("rendered_image", render_info)):
                if info["decode_error"]:
                    image_decode_errors[name] += 1
                if info["format"]:
                    formats[f"{name}:{info['format']}"] += 1
            code = raw.get("code")
            lines = code.splitlines() if isinstance(code, str) else []
            first_lines[lines[0] if lines else "<empty>"] += 1
            if not isinstance(code, str) or not code.lstrip().startswith(r"\begin{tikzpicture}") or not code.rstrip().endswith(r"\end{tikzpicture}"):
                malformed_code_rows.append(f"{split}:{index}")
            code_hash = digest(code.encode("utf-8")) if isinstance(code, str) else None
            pair_hash = digest(f"{source_info['sha256']}:{code_hash}".encode()) if source_info["sha256"] and code_hash else None
            item = {
                "id": f"{split}:{index}", "upstream_split": split, "upstream_row_index": index,
                "source_parquet": source_path.as_posix(), "source_parquet_sha256": source_hash,
                "grade": None, "source_image_sha256": source_info["sha256"],
                "rendered_image_sha256": render_info["sha256"], "code_sha256": code_hash,
                "image_code_pair_sha256": pair_hash, "source_image_bytes": source_info["bytes"],
                "rendered_image_bytes": render_info["bytes"], "source_image_format": source_info["format"],
                "rendered_image_format": render_info["format"],
                "source_image_decode_error": source_info["decode_error"],
                "rendered_image_decode_error": render_info["decode_error"],
                "problem": raw.get("problem"), "answer": raw.get("answer"),
                "text_logic_form": raw.get("text_logic_form"),
                "diagram_logic_form": raw.get("diagram_logic_form"),
                "line_instances": raw.get("line_instances"),
                "point_positions": raw.get("point_positions"),
                "circle_instances": raw.get("circle_instances"), "code": code,
                "_source_bytes": source_bytes, "_render_bytes": render_bytes,
            }
            rows.append(item)
            rows_by_split[split].append(item)

    duplicate_fields = ("source_image_sha256", "rendered_image_sha256", "code_sha256", "image_code_pair_sha256")
    duplicates = {field: duplicate_summary(rows, field) for field in duplicate_fields}
    samples = [
        {key: value for key, value in rows_by_split[split][index].items()
         if not key.startswith("_")}
        for split in SPLITS
        for index in sample[split]
    ]
    visuals = choose_visual_rows(rows, sample)
    pair_dir = output_dir / "artifacts" / "pairs"
    pair_dir.mkdir(parents=True, exist_ok=True)
    visual_rows = []
    for row in visuals:
        # Input and render bytes are copied verbatim for visual audit; source Parquet is untouched.
        for role, payload in (("source", row["_source_bytes"]), ("rendered", row["_render_bytes"])):
            with Image.open(BytesIO(payload)) as image:
                extension = (image.format or "png").lower()
            name = f"{row['upstream_split']}-{row['upstream_row_index']:04d}-{role}.{extension}"
            path = pair_dir / name
            path.write_bytes(payload)
            row[f"{role}_image_artifact"] = path.relative_to(output_dir).as_posix()
        visual_rows.append({key: value for key, value in row.items() if not key.startswith("_")})

    report = {
        "source_repo": "https://huggingface.co/datasets/SunnyLin/geo3k-tikz",
        "source_revision": "5d12d94db6af2217827d103caa17b93804a7d8df",
        "data_dir": data_dir.as_posix(), "file_hashes": file_hashes,
        "counts": {**counts, "total": sum(counts.values())}, "schema": schemas,
        "null_counts": dict(nulls), "blank_string_counts": dict(blanks),
        "empty_list_counts": dict(empty_lists), "image_decode_errors": dict(image_decode_errors),
        "missing_value_rows": dict(missing_rows), "image_formats": dict(formats),
        "code_format": {
            "first_line_counts": dict(first_lines.most_common(8)),
            "starts_with_tikzpicture": sum(
                row["code"].lstrip().startswith(r"\begin{tikzpicture}")
                for row in rows if isinstance(row["code"], str)
            ),
            "ends_with_tikzpicture": sum(
                row["code"].rstrip().endswith(r"\end{tikzpicture}")
                for row in rows if isinstance(row["code"], str)
            ),
            "malformed_for_shared_validator_shape": len(malformed_code_rows),
            "malformed_row_examples": malformed_code_rows[:20],
        },
        "exact_duplicates": duplicates,
        "sample": {"method": "uniform random within each upstream split", "per_split": per_split,
                   "seed": seed, "indices": sample, "grade": None},
        "visual_selection": {"rows": len(visual_rows), "per_split": 2,
                             "method": "approximately 35th and 80th complexity percentiles of the random sample; exact image/code pairs deduplicated"},
        "visual_pairs": [{key: value for key, value in row.items() if not key.startswith("_")}
                         for row in visual_rows],
        "limitations": ["The source has no grade or source-family field; grade remains unknown.",
                        "Hashes detect byte-identical duplicates only, not near-duplicates.",
                        "Compile success and visual/source fidelity require separate review."],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "sample-60.jsonl").write_text(jsonl(samples), encoding="utf-8")
    (output_dir / "visual-pairs.jsonl").write_text(jsonl(report["visual_pairs"]), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--per-split", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261008)
    args = parser.parse_args()
    report = audit(args.data, args.output, args.per_split, args.seed)
    print(json.dumps({"counts": report["counts"], "output": str(args.output.resolve()),
                      "duplicate_summary": {key: {k: value[k] for k in
                          ("unique_values", "duplicate_groups", "excess_rows", "cross_split_groups", "cross_split_excess_rows")}
                          for key, value in report["exact_duplicates"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
