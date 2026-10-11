"""Validate source selections and write one reviewable list; never copies assets."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SELECTION = REPO / "docs/dataset-selection"
IMAGE_LISTS = ("grades-6-7.images.jsonl", "grades-8-9.images.jsonl",
               "grades-10-11.images.jsonl", "grade-12.images.jsonl")
PROBLEM_LISTS = ("grades-6-7.problems.jsonl", "grade-8.problems.jsonl", "grade-9.problems.jsonl")
TYPES = {f"G{i:02}" for i in range(1, 18)} | {f"A{i:02}" for i in range(1, 7)}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def source(root, relative):
    require(isinstance(relative, str) and relative, "Missing source path")
    path = (root / relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(root),
            f"Source outside corpus: {relative}")
    require(path.is_file(), f"Missing source: {relative}")
    return path

def common(row, root):
    require(type(row["grade"]) is int and 6 <= row["grade"] <= 12, "Only grades 6–12")
    path = source(root, row["source_md"])
    require(path.parts[-3] == str(row["grade"]), f"Grade mismatch: {path}")
    require(path.parent.name == row["book"], f"Book mismatch: {path}")
    require(row["book_role"] in {"sgk", "sgv", "sgk_cd", "sgv_cd"}, "Invalid book role")
    expected = "book.final.md" if row["grade"] <= 9 else "full.md"
    require(path.name == expected, f"Wrong source artifact: {path}")
    require(isinstance(row["diagram_types"], list) and
            set(row["diagram_types"]) <= TYPES, f"Unknown diagram types: {row}")
    return path

def rows(filename):
    path = SELECTION / filename
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{filename}:{number}: {error}") from error

def build(root):
    root = root.resolve()
    images, problems, ids = {}, [], set()
    decisions = {"images": Counter(), "problems": Counter()}
    text_cache = {}
    def lines(path):
        if path not in text_cache:
            text_cache[path] = path.read_text(encoding="utf-8-sig").splitlines()
        return text_cache[path]
    layout_cache = {}
    def layout_images(path):
        if path not in layout_cache:
            def names(node):
                if isinstance(node, dict):
                    if isinstance(node.get("image_path"), str):
                        yield Path(node["image_path"]).name
                    for value in node.values():
                        yield from names(value)
                elif isinstance(node, list):
                    for value in node:
                        yield from names(value)
            data = json.loads(path.read_text(encoding="utf-8"))
            layout_cache[path] = {
                page["page_idx"] + 1: set(names(page))
                for page in data["pdf_info"]
            }
        return layout_cache[path]
    seen_sources = set()
    for filename in IMAGE_LISTS:
        for row in rows(filename):
            require(type(row["grade"]) is int and 6 <= row["grade"] <= 12, "Only grades 6–12")
            require(row["decision"] in {"selected", "excluded", "needs_review"},
                    "Invalid image decision")
            decisions["images"][row["decision"]] += 1
            md = common(row, root)
            img = source(root, row["source_image"])
            require(img.parent == md.parent / "images", f"Image/book mismatch: {img}")
            require(row["source_image"] not in seen_sources, f"Duplicate source: {img}")
            seen_sources.add(row["source_image"])
            index = row["source_line"]
            anchor = row.get("source_anchor", "markdown")
            require(anchor in {"markdown", "layout"}, f"Unknown source anchor: {anchor}")
            if index is not None:
                require(type(index) is int and 1 <= index <= len(lines(md)),
                        f"Invalid image source line: {img}")
            if anchor == "layout":
                layout = source(root, row["source_layout"])
                expected_layout = "layout.final.json" if row["grade"] <= 9 else "layout.json"
                require(layout == md.parent / expected_layout, "Wrong layout artifact")
                page = row["pdf_page"]
                require(type(page) is int and img.name in layout_images(layout).get(page, set()),
                        f"Image absent on cited layout page: {img}")
            else:
                require(index is not None and img.name in lines(md)[index - 1],
                        f"Image absent at source line: {img}")
            require(row["visual_checked"] is True, f"Image without visual check: {img}")
            if row["decision"] != "selected":
                continue
            require(row["diagram_types"], f"Unclassified image: {img}")
            digest = hashlib.sha256(img.read_bytes()).hexdigest()
            item = images.setdefault(digest, {
                "id": "image-" + digest[:16], "sha256": digest,
                "asset_path": "assets/" + digest + img.suffix.lower(),
                "grades": [], "diagram_types": [], "sources": [],
            })
            item["grades"] = sorted(set(item["grades"]) | {row["grade"]})
            item["diagram_types"] = sorted(set(item["diagram_types"]) | set(row["diagram_types"]))
            item["sources"].append(row)
    for filename in PROBLEM_LISTS:
        for row in rows(filename):
            require(type(row["grade"]) is int and 6 <= row["grade"] <= 12, "Only grades 6–12")
            require(row["decision"] in {"prepared", "needs_review"}, "Invalid problem decision")
            decisions["problems"][row["decision"]] += 1
            if row["decision"] != "prepared":
                continue
            md = common(row, root)
            require(6 <= row["grade"] <= 9, "Problem selection is restricted to final grades 6–9")
            require(row["id"] not in ids, f"Duplicate problem id: {row['id']}")
            ids.add(row["id"])
            require(row["source_kind"] in {"example", "practice", "exercise"}, "Invalid source kind")
            start, end = row["start_line"], row["end_line"]
            require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines(md)),
                    f"Invalid problem range: {row['id']}")
            expected = "\n".join(lines(md)[start - 1:end]).strip()
            require(row["source_text"].strip() == expected, f"Source text differs: {row['id']}")
            require(len(expected) > 30 and row["diagram_types"], f"Incomplete/unclassified: {row['id']}")
            for relative in row["image_paths"]:
                source(root, relative)
            problems.append(row)
    for row in problems:
        require(set(row.get("context_ids", [])) <= ids,
                f"Missing prepared context: {row['id']}")
    image_list = sorted(images.values(), key=lambda x: (min(x["grades"]), x["sources"][0]["source_image"]))
    statistics = {
        "selected_images": len(image_list),
        "selected_source_crops": decisions["images"]["selected"],
        "prepared_problems": len(problems),
        "problem_kinds": dict(Counter(p["source_kind"] for p in problems)),
        "images_by_type": dict(sorted(Counter(t for im in image_list for t in im["diagram_types"]).items())),
        "decisions": {k: dict(v) for k, v in decisions.items()},
        "by_grade": {
            str(g): {"images": sum(g in im["grades"] for im in image_list),
                     **dict(Counter(p["source_kind"] for p in problems if p["grade"] == g))}
            for g in range(6, 13)
        },
    }
    copied = 0
    for item in image_list:
        asset = REPO / item["asset_path"]
        if asset.exists():
            require(asset.is_file() and hashlib.sha256(asset.read_bytes()).hexdigest() == item["sha256"],
                    f"Asset hash mismatch: {asset}")
            copied += 1
    asset_status = "copied" if copied == len(image_list) and copied else (
        "partially_copied" if copied else "listed_not_copied")
    return {"scope": "Selected geometry and algebra diagrams, grades 6–12",
            "corpus_root": root.as_posix(), "assets_status": asset_status,
            "source_manifests": {name: hashlib.sha256((SELECTION / name).read_bytes()).hexdigest()
                                 for name in (*IMAGE_LISTS, *PROBLEM_LISTS)},
            "statistics": statistics, "images": image_list, "problems": problems}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = build(args.corpus)
    target = REPO / "docs/dataset-selection.json"
    if args.write:
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(target)
    else:
        require(json.loads(target.read_text(encoding="utf-8")) == result,
                "Selection differs from source manifests; regenerate with --write")
    print(json.dumps(result["statistics"], ensure_ascii=True, indent=2))

if __name__ == "__main__":
    main()
