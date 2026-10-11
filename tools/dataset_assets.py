"""Copy approved selected images, or regenerate the two dataset figures.

python tools/dataset_assets.py copy
python tools/dataset_assets.py figures
python tools/dataset_assets.py figures --seed 1
python tools/dataset_assets.py check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

from prepare_dataset_selection import REPO, SELECTION, TYPES, require, source

MANIFEST = REPO / "docs/dataset-selection.json"
TYPE_ORDER = tuple(f"G{i:02}" for i in range(1, 18)) + tuple(f"A{i:02}" for i in range(1, 7))
EXAMPLE_OVERRIDES = {
    "G02": "image-d387e538f447e44e",
    "G06": "image-839f069b429fc86a",
    "G07": "image-1492300acd9c5830",
    "G08": "image-8b3b3f08df86fd7c",
    "G13": "image-5573da6f7b3ea9f2",
    "G17": "image-a63da0c960a3aa26",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def type_counts(images):
    counts = Counter(t for im in images for t in set(im["diagram_types"]))
    return {kind: counts[kind] for kind in TYPE_ORDER}


def select_examples(images, seed=2):
    """Choose reproducible examples, preferring single-label images."""
    candidates = {kind: [] for kind in TYPE_ORDER}
    for im in images:
        for kind in set(im["diagram_types"]):
            candidates[kind].append(im)
    def order(im):
        key = f"{seed}:{im['sha256']}".encode()
        return hashlib.sha256(key).hexdigest(), im["id"]
    return {
        kind: min(
            (im for im in rows if len(set(im["diagram_types"])) == 1),
            key=order,
            default=None,
        ) or min(rows, key=order, default=None)
        for kind, rows in candidates.items()
    }


def load_selection():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected in data["source_manifests"].items():
        require(digest(source(SELECTION.resolve(), name)) == expected,
                f"Changed source manifest: {name}; regenerate dataset-selection.json first")
    items = data["images"]
    require(len({im["sha256"] for im in items}) == len(items), "Duplicate selected image")
    counts = Counter(t for im in items for t in set(im["diagram_types"]))
    expected_counts = {kind: count for kind, count in data["statistics"]["images_by_type"].items() if count}
    require(dict(counts) == expected_counts, "Stale type counts")
    require(len(items) == data["statistics"]["selected_images"], "Stale image count")
    for im in items:
        require(im["diagram_types"] and set(im["diagram_types"]) <= TYPES, "Unknown type")
        require(im["sources"] and all(r["decision"] == "selected" and
                type(r["grade"]) is int and 6 <= r["grade"] <= 12 and
                Path(r["source_image"]).parts[0] == str(r["grade"]) for r in im["sources"]),
                f"Not an approved selected image: {im['id']}")
    return data


def copy_images(items, corpus, assets):
    """Preflight the whole batch; skip identical files and never overwrite conflicts."""
    corpus, assets = corpus.resolve(), assets.resolve()
    plan, seen = [], set()
    for im in items:
        require(im["sources"] and all(r["decision"] == "selected" and
                type(r["grade"]) is int and 6 <= r["grade"] <= 12 and
                Path(r["source_image"]).parts[0] == str(r["grade"]) for r in im["sources"]),
                "Copy accepts selected grades 6-12 only")
        src = source(corpus, im["sources"][0]["source_image"])
        expected = im["sha256"]
        require(re.fullmatch(r"[0-9a-f]{64}", expected), "Invalid SHA-256")
        rel = Path(im["asset_path"])
        require(rel.parts == ("assets", expected + src.suffix.lower()), "Invalid asset path")
        dst = (assets / rel.name).resolve()
        require(dst.is_relative_to(assets) and dst not in seen, "Escaping/duplicate destination")
        seen.add(dst)
        require(digest(src) == expected, f"Source hash mismatch: {src}")
        if dst.exists():
            require(dst.is_file() and digest(dst) == expected, f"Asset conflict: {dst}")
        plan.append((src, dst, expected))
    assets.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src, dst, expected in plan:
        if dst.exists():
            continue
        with src.open("rb") as input_file, dst.open("xb") as output_file:
            shutil.copyfileobj(input_file, output_file)
        require(digest(dst) == expected, f"Copy verification failed: {dst}")
        copied += 1
    return copied, len(plan) - copied


def plot_figures(data, dpi, seed=2):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    labels = dict(re.findall(r"^\| ([GA]\d{2}) \| ([^|]+) \|$",
                  (REPO / "docs/diagram-k12-vn.md").read_text(encoding="utf-8"), re.M))
    require(set(labels) == TYPES == set(TYPE_ORDER), "Expected 17 geometry + 6 algebra types")
    items = {im["id"]: im for im in data["images"]}
    examples = select_examples(data["images"], seed)
    for kind, image_id in EXAMPLE_OVERRIDES.items():
        example = items.get(image_id)
        require(example is not None and kind in example["diagram_types"],
                f"Invalid curated example for {kind}: {image_id}")
        examples[kind] = example
    counts = type_counts(data["images"])
    total = len(items)
    colors = {t: "#176A85" if t.startswith("G") else "#CB692E" for t in TYPE_ORDER}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, axes = plt.subplots(4, 6, figsize=(9.6, 6.0))
    fig.subplots_adjust(left=.02, right=.99, bottom=.055, top=.925, hspace=.34, wspace=.20)
    provenance = []
    for i, kind in enumerate(TYPE_ORDER):
        im = examples[kind]
        ax = axes.flat[i if i < 17 else i + 1]
        if im is None:
            ax.text(.5, .5, "Chưa có ảnh", transform=ax.transAxes,
                    ha="center", va="center", fontsize=8, color="#677680")
        else:
            require(kind in im["diagram_types"], f"Example no longer has label {kind}: {im['id']}")
            path = source(REPO.resolve(), im["asset_path"])
            require(digest(path) == im["sha256"], f"Changed example asset: {path}")
            with Image.open(path) as picture:
                ax.imshow(picture.convert("RGB"))
        ax.set_title(kind + " · " + textwrap.fill(labels[kind], 19), fontsize=6.5,
                     color=colors[kind], weight="bold", pad=3)
        ax.axis("off")
        if im is not None:
            ax.text(.5, -.08, "Lớp " + ", ".join(map(str, im["grades"])), transform=ax.transAxes,
                    ha="center", fontsize=6.2, color="#677680")
        provenance.append({"diagram_type": kind, "label": labels[kind],
                           "image_id": im["id"] if im else None,
                           "asset_path": im["asset_path"] if im else None,
                           "count": counts[kind], "sources": im["sources"] if im else []})
    axes.flat[17].axis("off")
    axes.flat[17].text(.5, .62, "HÌNH HỌC", ha="center", va="center",
                       fontsize=8, color=colors["G01"], weight="bold",
                       transform=axes.flat[17].transAxes)
    axes.flat[17].text(.5, .48, "G01–G17", ha="center", va="center",
                       fontsize=7, color="#44515B", transform=axes.flat[17].transAxes)
    axes.flat[17].text(.5, .29, "ĐẠI SỐ", ha="center", va="center",
                       fontsize=8, color=colors["A01"], weight="bold",
                       transform=axes.flat[17].transAxes)
    axes.flat[17].text(.5, .15, "A01–A06", ha="center", va="center",
                       fontsize=7, color="#44515B", transform=axes.flat[17].transAxes)
    fig.savefig(REPO / "docs/dataset-coverage-overview.png", dpi=dpi, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.05, 6.5))
    fig.subplots_adjust(left=.48, right=.98, bottom=.14, top=.985)
    kinds = list(TYPE_ORDER)
    values = [counts[t] for t in kinds]
    bars = ax.barh(range(len(kinds)), values, color=[colors[t] for t in kinds], height=.68)
    ax.set_yticks(range(len(kinds)), [t + " · " + textwrap.fill(labels[t], 50) for t in kinds])
    ax.invert_yaxis()
    ax.set_xlim(0, max(1, max(values, default=0) * 1.15))
    ax.bar_label(bars, padding=4, fontsize=8, weight="bold")
    ax.axhline(16.5, color="#B5C1C8", linewidth=1, linestyle="--")
    ax.grid(axis="x", color="#E3E9ED", linewidth=.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=6, labelsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.set_xlabel("Số ảnh", labelpad=7, fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(.5, .025, "Một ảnh có thể mang nhiều nhãn loại hình.",
             ha="center", fontsize=7, color="#677680")
    fig.savefig(REPO / "docs/dataset-type-counts.png", dpi=dpi, facecolor="white")
    plt.close(fig)
    (REPO / "docs/dataset-coverage-sources.json").write_text(json.dumps({
        "selection": "dataset-selection.json", "overview": "dataset-coverage-overview.png",
        "counts_figure": "dataset-type-counts.png", "image_count": total,
        "geometry_types": 17, "algebra_types": 6,
        "sample_selection": f"seed={seed}; single-label first; SHA-256 order; curated overrides: {', '.join(EXAMPLE_OVERRIDES)}",
        "sources": provenance,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def self_check():
    """Runnable regression check for copying, reruns, and rejected unsafe inputs."""
    assert len(TYPE_ORDER) == 23 and set(TYPE_ORDER) == TYPES
    fixture = [
        {"id": "multi", "sha256": "0" * 64, "diagram_types": ["G01", "G02", "A01"]},
        {"id": "single-z", "sha256": "f" * 64, "diagram_types": ["G01"]},
        {"id": "single-a", "sha256": "1" * 64, "diagram_types": ["G01"]},
    ]
    examples = select_examples(fixture)
    assert tuple(examples) == TYPE_ORDER
    assert examples["G01"]["diagram_types"] == ["G01"]  # single-label image preferred
    assert examples["G02"]["id"] == examples["A01"]["id"] == "multi"  # multilabel fallback
    assert examples["G03"] is None and type_counts(fixture)["G03"] == 0
    assert [(kind, im["id"] if im else None) for kind, im in examples.items()] == [
        (kind, im["id"] if im else None)
        for kind, im in select_examples(list(reversed(fixture))).items()
    ]
    assert [(kind, im["id"] if im else None) for kind, im in examples.items()] == [
        (kind, im["id"] if im else None)
        for kind, im in select_examples(fixture, seed=2).items()
    ]
    empty = select_examples([])
    assert tuple(empty) == TYPE_ORDER and all(im is None for im in empty.values())
    assert set(type_counts([]).values()) == {0}
    base = REPO / ".tmp-coverage-review"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="assets-check-", dir=base) as temp:
        root = Path(temp).resolve()
        require(root.is_relative_to(base.resolve()), "Unexpected test directory")
        corpus = root / "corpus"
        (corpus / "6").mkdir(parents=True)
        src = corpus / "6/example.jpg"
        src.write_bytes(b"selected-image-fixture")
        sha = digest(src)
        im = {"sha256": sha, "asset_path": f"assets/{sha}.jpg", "sources": [
            {"source_image": "6/example.jpg", "decision": "selected", "grade": 6}]}
        assets = root / "assets"
        assert copy_images([im], corpus, assets) == (1, 0)
        assert copy_images([im], corpus, assets) == (0, 1)
        assert (assets / f"{sha}.jpg").read_bytes() == src.read_bytes()
        for change in ("unselected", "outside_assets", "wrong_source_hash", "primary_grade"):
            bad = json.loads(json.dumps(im))
            if change == "unselected":
                bad["sources"][0]["decision"] = "needs_review"
            elif change == "outside_assets":
                bad["asset_path"] = "assets/../../unexpected.jpg"
            elif change == "wrong_source_hash":
                bad["sha256"] = "0" * 64
                bad["asset_path"] = "assets/" + "0" * 64 + ".jpg"
            else:
                bad["sources"][0]["source_image"] = "1/example.jpg"
            target = root / change
            try:
                copy_images([bad], corpus, target)
            except ValueError:
                pass
            else:
                raise AssertionError(f"Accepted {change}")
            assert not target.exists(), "Preflight wrote files before rejecting the batch"
        dst = assets / f"{sha}.jpg"
        dst.write_bytes(b"conflicting-file")
        try:
            copy_images([im], corpus, assets)
        except ValueError:
            pass
        else:
            raise AssertionError("Overwrote a conflicting asset")
        assert dst.read_bytes() == b"conflicting-file"
    print("PASS: deterministic samples, missing types, selected-only copy, hashes, and conflicts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("copy", "figures", "check"))
    parser.add_argument("--corpus", type=Path, help="Override source corpus location for copying")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--seed", type=int, default=2, help="Change overview sample examples")
    args = parser.parse_args()
    if args.action == "check":
        self_check()
        return
    data = load_selection()
    if args.action == "copy":
        copied, present = copy_images(data["images"], args.corpus or Path(data["corpus_root"]), REPO / "assets")
        data["assets_status"] = "copied"
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Copied {copied}; already present and verified {present}; total {copied + present}")
    else:
        require(args.dpi > 0, "DPI must be positive")
        plot_figures(data, args.dpi, args.seed)
        print("Wrote docs/dataset-coverage-overview.png and docs/dataset-type-counts.png")


if __name__ == "__main__":
    main()
