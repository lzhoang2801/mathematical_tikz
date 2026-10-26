"""Export all requested rows to minimal, jointly split Hugging Face Parquet configs."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_geo3k import digest, file_digest, image_payload
from tools.draw_instruction import replace_snapshot

TASKS = ("reconstruct", "generate", "edit")
SPLITS = ("train", "validation", "test")
FILES = {"train": "train", "validation": "val", "test": "test"}
COLUMNS = {
    "reconstruct": ("id", "image", "target_tikz"),
    "generate": ("id", "instruction", "current_tikz", "target_tikz"),
    "edit": ("id", "instruction", "current_tikz", "target_tikz"),
}


def load_inputs(geo3k: Path | None, synthetic: Path,
                withheld: dict[str, list[dict]] | None = None) -> tuple[list[dict], dict]:
    rows, inputs = [], {}
    for split in SPLITS if geo3k is not None else ():
        paths = sorted(geo3k.glob(f"{split}-*.parquet"))
        if not paths:
            raise FileNotFoundError(f"No Geo3K {split} Parquet files in {geo3k}")
        for path in paths:
            inputs[str(path.resolve())] = file_digest(path)
            table = pq.read_table(path, columns=["code", "rendered_image", "image"])
            for index, source in enumerate(table.to_pylist()):
                image = source["rendered_image"]
                payload = image_payload(image)
                image_id = digest(payload) if payload else None
                original = image_payload(source["image"])
                keys = set()
                if image_id:
                    keys.add("image:" + image_id)
                if original:
                    keys.add("geo3k-original:" + digest(original))
                rows.append({"id": image_id, "image": image if payload else None,
                    "target_tikz": source["code"], "_task": "reconstruct", "_keys": keys,
                    "_origin": f"geo3k/{path.name}:{index}", "_pinned": split})
    for task in (("generate", "edit") if geo3k is not None else TASKS):
        path = synthetic / ("reconstruct/candidates.jsonl" if task == "reconstruct" else f"{task}.jsonl")
        if task == "reconstruct" and not path.is_file():
            continue
        inputs[str(path.resolve())] = file_digest(path)
        seen = set()
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            source = json.loads(line)
            key = source.get("id")
            if not isinstance(key, str) or not key or key in seen:
                raise ValueError(f"{path}: missing or duplicate ID {key!r}")
            seen.add(key)
            if source.get("task", "").lower() != task:
                raise ValueError(f"{path}: task mismatch for {key}")
            provenance = source.get("provenance") or {}
            keys = {"record:" + key}
            if source.get("source"):
                keys.add("source:" + source["source"])
            if source.get("source_group"):
                keys.add("family:" + source["source_group"])
            keys.update("parent:" + parent for parent in provenance.get("parents", []))
            keys.update("family:" + group for group in provenance.get("source_groups", []))
            keys.update("record:" + record for record in provenance.get("moved_from", []))
            for name in ("starting_record_id", "derived_from_edit"):
                if provenance.get(name):
                    keys.add("record:" + provenance[name])
            if source.get("current_tikz"):
                keys.add("code:" + digest(source["current_tikz"].encode("utf-8")))
            if source.get("rendered_png_sha256"):
                keys.add("image:" + source["rendered_png_sha256"])
            if task in ("generate", "edit"):
                review = source.get("verification")
                review = review if isinstance(review, dict) else {}
                if review.get("status") != "ready":
                    if withheld is not None:
                        status = review.get("status")
                        withheld[task].append({"id": key, "status": status if isinstance(status, str)
                                               else "missing" if status is None else "invalid"})
                    continue
                from tools import draw_instruction as drawing
                drawing.validate_ready_pair(source)
            if task == "reconstruct":
                from tools import draw_instruction as drawing
                review = source.get("verification", {})
                image = drawing.source_image(source)
                target = drawing.target_image(source)
                if (review.get("method") != "manual_reconstruct_review" or review.get("status") != "ready"
                        or review.get("original_instruction_match") is not False
                        or review.get("reviewed_input_sha256") != drawing.review_digest(source)
                        or image is None or target is None or image["bytes"] != target["bytes"]):
                    raise ValueError(f"{path}: {key} needs a valid manual Reconstruct review and exact image/target binding")
                source = {**source, "image": image}
            rows.append({**{name: source.get(name) for name in COLUMNS[task]},
                "_task": task, "_keys": keys, "_origin": task + "/" + key,
                "_pinned": source.get("split")})
    for row in rows:
        if not isinstance(row["target_tikz"], str) or not row["target_tikz"].strip():
            raise ValueError(f"{row['_origin']}: missing target TikZ")
        if row["_task"] != "reconstruct":
            if not isinstance(row["instruction"], str) or not row["instruction"].strip():
                raise ValueError(f"{row['_origin']}: missing instruction")
            if row["_task"] == "edit" and not row["current_tikz"]:
                raise ValueError(f"{row['_origin']}: missing starting TikZ")
            if row["_task"] == "generate" and row["current_tikz"] is not None:
                raise ValueError(f"{row['_origin']}: Generate has starting TikZ")
        if row["_pinned"] not in (None, *SPLITS):
            raise ValueError(f"{row['_origin']}: unknown split {row['_pinned']!r}")
        row["_keys"].add("code:" + digest(row["target_tikz"].encode("utf-8")))
    return rows, inputs


def assign_splits(rows: list[dict], seed: int, saved: dict[str, str] | None = None) -> tuple[list[str], dict, int]:
    """Join related rows before assignment; held-out assignments take precedence."""
    roots = list(range(len(rows)))

    def find(index):
        while roots[index] != index:
            roots[index] = roots[roots[index]]
            index = roots[index]
        return index

    owners = {}
    for index, row in enumerate(rows):
        for key in sorted(row["_keys"]):
            if key in owners:
                roots[find(index)] = find(owners[key])
            owners[key] = index
    components = defaultdict(list)
    for index in range(len(rows)):
        components[find(index)].append(index)
    remembered = dict(saved or {})
    assigned = [""] * len(rows)
    totals = Counter(row["_task"] for row in rows)
    counts = {split: Counter() for split in SPLITS}
    pending = []

    def assign(members, keys, split):
        for index in members:
            assigned[index] = split
            counts[split][rows[index]["_task"]] += 1
        remembered.update(dict.fromkeys(keys, split))

    for members in components.values():
        keys = set().union(*(rows[index]["_keys"] for index in members))
        pinned = {rows[index]["_pinned"] for index in members} - {None}
        pinned.update(remembered[key] for key in keys if key in remembered)
        if pinned:
            assign(members, keys, max(pinned, key=SPLITS.index))
        else:
            families = [key for key in keys if key.startswith(("family:", "parent:"))]
            group = min(families or keys)
            pending.append((members, keys, digest(f"{seed}:{group}".encode("utf-8"))))
    for members, keys, _ in sorted(pending, key=lambda item: (-len(item[0]), item[2])):
        sizes = Counter(rows[index]["_task"] for index in members)

        def cost(split):
            fraction = 0.8 if split == "train" else 0.1
            return sum(((counts[split][task] + size - totals[task] * fraction) ** 2
                        - (counts[split][task] - totals[task] * fraction) ** 2)
                       / max(totals[task] * fraction, 1) for task, size in sizes.items())

        assign(members, keys, min(SPLITS, key=cost))
    return assigned, remembered, len(components)


def arrow_schema(task: str) -> pa.Schema:
    image_type = pa.struct([("bytes", pa.binary()), ("path", pa.string())])
    fields = [(name, image_type if name == "image" else pa.string()) for name in COLUMNS[task]]
    features = {name: {"_type": "Image"} if name == "image" else {"_type": "Value", "dtype": "string"}
                for name in COLUMNS[task]}
    return pa.schema(fields, metadata={"huggingface": json.dumps({"info": {"features": features}})})


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    replace_snapshot(temporary, path)


def export(geo3k: Path | None, synthetic: Path, output: Path, seed: int = 20261009) -> dict:
    withheld = {task: [] for task in ("generate", "edit")}
    rows, inputs = load_inputs(geo3k, synthetic, withheld)
    assignments_path = output / "split_assignments.json"
    previous = json.loads(assignments_path.read_text(encoding="utf-8")) if assignments_path.is_file() else {}
    if previous and previous["seed"] != seed:
        raise ValueError("This export already has frozen split assignments with a different seed")
    assigned, remembered, groups = assign_splits(rows, seed, previous.get("keys"))
    output.mkdir(parents=True, exist_ok=True)
    # Persist before writing shards so an interrupted export cannot reshuffle existing groups.
    write_json(assignments_path, {"seed": seed, "keys": remembered})
    counts, files = {}, {}
    for task in TASKS:
        directory = output / task
        directory.mkdir(exist_ok=True)
        counts[task] = {}
        for split in SPLITS:
            selected = [{name: row[name] for name in COLUMNS[task]}
                        for row, assigned_split in zip(rows, assigned)
                        if row["_task"] == task and assigned_split == split]
            table = pa.Table.from_pylist(selected, schema=arrow_schema(task))
            path = directory / f"{FILES[split]}.parquet"
            temporary = path.with_suffix(".parquet.tmp")
            pq.write_table(table, temporary, compression="zstd", row_group_size=100,
                           use_content_defined_chunking=True, write_page_index=True)
            if not table.equals(pq.read_table(temporary), check_metadata=True):
                raise RuntimeError(f"Parquet round-trip mismatch: {path}")
            replace_snapshot(temporary, path)
            counts[task][split] = len(selected)
            files[str(path.relative_to(output)).replace("\\", "/")] = file_digest(path)
    key_splits = defaultdict(set)
    for row, split in zip(rows, assigned):
        for key in row["_keys"]:
            key_splits[key].add(split)
    if any(len(values) != 1 for values in key_splits.values()):
        raise RuntimeError("A source family or exact duplicate crosses output splits")
    changed = [{"origin": row["_origin"], "id": row["id"], "from": row["_pinned"], "to": split}
               for row, split in zip(rows, assigned) if row["_pinned"] and row["_pinned"] != split]
    missing = [row["_origin"] for row in rows if row["_task"] == "reconstruct" and row["image"] is None]
    report = {"seed": seed, "counts": counts, "input_sha256": inputs, "output_sha256": files,
        "all_input_rows_retained": not any(withheld.values()) and
            len(rows) == sum(sum(value.values()) for value in counts.values()),
        "training_ready_rows": len(rows),
        "withheld_nonready_candidates": {task: {
            "count": len(candidates),
            "ids": [candidate["id"] for candidate in candidates],
            "statuses": dict(Counter(candidate["status"] for candidate in candidates)),
        } for task, candidates in withheld.items()},
        "rows": len(rows), "groups": groups, "unique_reconstruct_image_ids": len({
            row["id"] for row in rows if row["_task"] == "reconstruct" and row["id"] is not None}),
        "missing_rendered_images": missing, "upstream_split_changes": changed,
        "cross_split_lineage_or_exact_duplicates": 0,
        "synthetic_split_policy": "Deterministic whole-group allocation targeting 80/10/10 per task; assignments persisted.",
        "existing_split_policy": "Keep existing assignments, promoting connected duplicate groups to test > validation > train.",
        "verification": "All requested fields round-trip exactly through Parquet; no model calls, recompilation or semantic review."}
    write_json(output / "export_report.json", report)
    card = ["---", "configs:"]
    for task in TASKS:
        card += [f"- config_name: {task}", "  data_files:"]
        for split in SPLITS:
            card += [f"  - split: {split}", f"    path: {task}/{FILES[split]}.parquet"]
    card += ["---", "", "# TikZ dataset export", "",
        "Upload this folder to one Hugging Face dataset repository. Choose the reconstruct, generate, or edit configuration.",
        "", "| Configuration | Train | Validation | Test | Total |", "|---|---:|---:|---:|---:|"]
    for task in TASKS:
        values = counts[task]
        card.append(f"| {task} | {values['train']} | {values['validation']} | {values['test']} | {sum(values.values())} |")
    card += ["", "Reconstruct columns: id, image, target_tikz. Images and target code are preserved exactly.",
        ("Generate/Edit columns: id, instruction, current_tikz, target_tikz. Existing IDs and text are unchanged. "
         "Generate current_tikz is null."), "",
        ("Legacy Geo3K export was explicitly requested. All upstream rows, including duplicates and missing images, are retained."
         if geo3k is not None else
         "Reconstruct contains only manually moved Generate/Edit targets: usable diagrams that fail their original instruction. "
         "Exact image/code pairs are deduplicated by the reviewer; original rows remain in its recovery archive."),
        f"{len(missing)} row(s) lack an image.", "",
        ("Existing split assignments are preserved, promoting connected groups toward test > validation > train where needed. "
         "export_report.json lists changes."),
        ("Synthetic rows target 80/10/10 per task with a fixed seed while keeping whole groups together, so proportions can differ. "
         "Original parents, source families, linked Generate/Edit rows, matching current/target code, and image hashes "
         "stay in one split. split_assignments.json freezes assignments for subsequent exports."), "",
        ("Only Generate/Edit rows with current independent source/render review evidence are exported. "
         "Nonready candidates and their statuses are listed in export_report.json. The export validates recorded evidence bindings; it does not conduct the mathematical or visual review."),
        "", ("Source snapshot: dataset/synthetic/{generate,edit}.jsonl and reconstruct/candidates.jsonl "
               "(or explicitly requested legacy Geo3K inputs)."),
        ("Format: [HF configurations](https://huggingface.co/docs/hub/datasets-manual-configuration) and "
         "[embedded images](https://huggingface.co/docs/hub/datasets-pyarrow#embed-images-inside-parquet)."),
        "Group separation: [cross-validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).", ""]
    (output / "README.md").write_text("\n".join(card), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geo3k", type=Path, help="Explicit legacy import; by default use manually reviewed synthetic Reconstruct pairs")
    parser.add_argument("--synthetic", type=Path, default=ROOT / "dataset/synthetic")
    parser.add_argument("--output", type=Path, default=ROOT / "dataset/synthetic/hf")
    parser.add_argument("--seed", type=int, default=20261009)
    args = parser.parse_args()
    report = export(args.geo3k, args.synthetic, args.output, args.seed)
    print(json.dumps({key: report[key] for key in ("counts", "rows", "groups", "missing_rendered_images")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
