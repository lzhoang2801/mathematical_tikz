"""Copy checked source crops and verify their paths and hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from prepare_dataset_selection import REPO, SELECTION, require, source

MANIFEST = REPO / "docs/dataset-selection.json"
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_selection():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected in data["source_manifests"].items():
        require(digest(source(SELECTION.resolve(), name)) == expected,
                f"Changed source manifest: {name}; regenerate dataset-selection.json first")
    items = data["images"]
    require(len({im["sha256"] for im in items}) == len(items), "Duplicate selected image")
    require(len(items) == data["statistics"]["selected_images"], "Stale image count")
    for im in items:
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


def self_check():
    """Runnable regression check for copying, reruns, and rejected unsafe inputs."""
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
    print("PASS: selected-only copy, paths, hashes, reruns, and conflicts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("copy", "check"))
    parser.add_argument("--corpus", type=Path, help="Override source corpus location for copying")
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



if __name__ == "__main__":
    main()
