"""Refresh image and problem anchors after a corpus Markdown export."""
import argparse
import bisect
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from prepare_dataset_selection import (
    REPO, SELECTION, IMAGE_LISTS, PROBLEM_LISTS, build, require, source,
)

IMAGE_LINK = re.compile(r"!\[\]\(images/([^\)]+)\)")
CAPTION_LINE = re.compile(r"^(?:Hình\b|H\.\s*\d|[a-d]\))", re.IGNORECASE)


def image_names(node):
    if isinstance(node, dict):
        if isinstance(node.get('image_path'), str):
            yield Path(node['image_path']).name
        for value in node.values():
            yield from image_names(value)
    elif isinstance(node, list):
        for value in node:
            yield from image_names(value)


def anchor_image(root, row, markdown_cache, layout_cache):
    md = source(root, row['source_md'])
    if md not in markdown_cache:
        markdown_cache[md] = md.read_text(encoding='utf-8-sig').splitlines()
    name = Path(row['source_image']).name
    matches = [n for n, line in enumerate(markdown_cache[md], 1) if name in line]
    if matches:
        previous = row.get('source_line')
        row['source_line'] = min(
            matches,
            key=lambda n: (abs(n - previous), n) if type(previous) is int else (n, n),
        )
        row['source_anchor'] = 'markdown'
        row.pop('source_layout', None)
        return True

    layout_name = 'layout.final.json' if row['grade'] <= 9 else 'layout.json'
    layout_rel = row.get('source_layout') or (Path(row['source_md']).parent / layout_name).as_posix()
    layout = source(root, layout_rel)
    if layout not in layout_cache:
        data = json.loads(layout.read_text(encoding='utf-8'))
        layout_cache[layout] = {
            page['page_idx'] + 1: set(image_names(page))
            for page in data['pdf_info']
        }
    pages = [page for page, names in layout_cache[layout].items() if name in names]
    if not pages:
        return False
    old_page = row.get('pdf_page')
    row['source_anchor'] = 'layout'
    row['source_layout'] = Path(layout_rel).as_posix()
    row['source_line'] = None
    row['pdf_page'] = old_page if old_page in pages else pages[0]
    return True


def anchor_problem(root, row, markdown_cache):
    md = source(root, row["source_md"])
    if md not in markdown_cache:
        markdown_cache[md] = md.read_text(encoding="utf-8-sig").splitlines()
    lines = markdown_cache[md]
    document = "\n".join(lines)
    text = row["source_text"].strip()

    if document.count(text) == 1:
        offset = document.find(text)
        start = document.count("\n", 0, offset)
        end = document.count("\n", 0, offset + len(text))
        if "\n".join(lines[start:end + 1]).strip() == text:
            return start, end

    positions = {}
    for index, line in enumerate(lines):
        if line.strip():
            positions.setdefault(line.strip(), []).append(index)
    old_lines = [line.strip() for line in text.splitlines() if line.strip()]
    removed_images = {
        i for i, line in enumerate(old_lines)
        if line.startswith("![](") and line not in positions
    }

    def watermark(line):
        value = "".join(
            char for char in unicodedata.normalize("NFD", line.upper())
            if unicodedata.category(char) != "Mn"
        )
        return "KET NOI TRI THUC" in value or "VOI CUOC SONG" in value

    def caption(line):
        return bool(CAPTION_LINE.match(line)) or (
            len(line) <= 70 and not line.endswith((".", ":", ";", "?", "!", ","))
        )

    def locate(kept):
        if not kept:
            return None
        candidates = []
        for first in positions.get(kept[0], []):
            previous = first
            for line in kept[1:]:
                matches = positions[line]
                index = bisect.bisect_right(matches, previous)
                if index == len(matches):
                    break
                previous = matches[index]
            else:
                gap = previous - first - len(kept) + 1
                candidates.append((gap, first, previous))
        if not candidates:
            return None
        candidates.sort()
        best = [item for item in candidates if item[0] == candidates[0][0]]
        if len(best) != 1 or best[0][0] > max(50, 2 * len(kept)):
            return None
        return best[0][1], best[0][2]

    kept, unknown = [], []
    for i, line in enumerate(old_lines):
        if line.startswith("![](") and i in removed_images:
            continue
        if watermark(line):
            continue
        near_removed_image = any(abs(i - image_index) <= 2 for image_index in removed_images)
        if line not in positions and near_removed_image and caption(line):
            continue
        if line not in positions:
            unknown.append(line)
        else:
            kept.append(line)

    result = locate(kept) if not unknown else None
    if result is None and not unknown:
        kept = [
            line for i, line in enumerate(old_lines)
            if not (
                (line.startswith("![](") and i in removed_images)
                or watermark(line)
                or (any(abs(i - image_index) <= 2 for image_index in removed_images)
                    and caption(line))
            )
        ]
        result = locate(kept)
    require(result is not None and not unknown,
            f"Cannot safely re-anchor problem {row['id']}; unmatched source lines: {unknown[:3]}")
    return result


def refresh(root, write=False):
    root = root.resolve()
    target = REPO / 'docs/dataset-selection.json'
    data = json.loads(target.read_bytes())
    outputs, retained, removed = {}, {}, []
    markdown_cache, layout_cache = {}, {}
    for name in IMAGE_LISTS:
        path = SELECTION / name
        lines = []
        for line in path.read_text(encoding='utf-8-sig').splitlines(keepends=True):
            if not line.strip():
                lines.append(line)
                continue
            row = json.loads(line)
            image = (root / row['source_image']).resolve()
            require(image.is_relative_to(root) and 6 <= row['grade'] <= 12, 'Invalid source scope')
            reason = None
            if not image.is_file():
                reason = 'missing_file'
            elif not anchor_image(root, row, markdown_cache, layout_cache):
                require(row['decision'] != 'selected',
                        f"Selected image has no Markdown/layout reference: {image}")
                reason = 'unreferenced'
            if reason:
                removed.append({'manifest': name, 'source_image': row['source_image'],
                                'decision': row['decision'], 'reason': reason})
                continue
            lines.append(json.dumps(row, ensure_ascii=False) + '\n')
            retained[row['source_image']] = row
        outputs[path] = ''.join(lines).encode('utf-8')

    problem_stats = Counter()
    for name in PROBLEM_LISTS:
        path = SELECTION / name
        refreshed = []
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            require(6 <= row['grade'] <= 9, 'Problem selections are restricted to grades 6–9')
            md = source(root, row['source_md'])
            old_anchor = (row['start_line'], row['end_line'], row['source_text'])
            start, end = anchor_problem(root, row, markdown_cache)
            row['start_line'], row['end_line'] = start + 1, end + 1
            row['source_text'] = '\n'.join(markdown_cache[md][start:end + 1]).strip()
            links = set(IMAGE_LINK.findall(row['source_text']))
            broken = [name for name in links if not (md.parent / 'images' / name).is_file()]
            require(not broken, f"Current Markdown references missing problem image: {row['id']}: {broken}")
            kept_paths = []
            for relative in row.get('image_paths', []):
                image = (root / relative).resolve()
                require(image.is_relative_to(root), f"Invalid problem image path: {relative}")
                if image.is_file() and Path(relative).name in links:
                    kept_paths.append(relative)
                else:
                    problem_stats['image_paths_removed'] += 1
                    problem_stats['missing_image_paths'] += not image.is_file()
            row['image_paths'] = kept_paths
            problem_stats['rows_checked'] += 1
            problem_stats['rows_reanchored'] += old_anchor != (
                row['start_line'], row['end_line'], row['source_text'])
            refreshed.append(json.dumps(row, ensure_ascii=False))
        outputs[path] = ('\n'.join(refreshed) + '\n').encode('utf-8')
    images = []
    for item in data['images']:
        item['sources'] = [
            retained[s['source_image']] for s in item['sources']
            if s['source_image'] in retained
            and retained[s['source_image']]['decision'] == 'selected'
        ]
        if not item['sources']: continue
        item['grades'] = sorted({s['grade'] for s in item['sources']})
        item['diagram_types'] = sorted({t for s in item['sources'] for t in s['diagram_types']})
        images.append(item)
    data['images'] = images
    stats = data['statistics']
    stats['selected_images'] = len(images)
    stats['selected_source_crops'] = sum(r['decision'] == 'selected' for r in retained.values())
    stats['images_by_type'] = dict(sorted(Counter(t for im in images for t in im['diagram_types']).items()))
    stats['decisions']['images'] = dict(Counter(r['decision'] for r in retained.values()))
    for grade, counts in stats['by_grade'].items():counts['images'] = sum(int(grade) in im['grades'] for im in images)
    for path, content in outputs.items():data['source_manifests'][path.name] = hashlib.sha256(content).hexdigest()
    copied = sum(
        (REPO / item['asset_path']).is_file()
        and hashlib.sha256((REPO / item['asset_path']).read_bytes()).hexdigest() == item['sha256']
        for item in images
    )
    data['assets_status'] = 'copied' if copied == len(images) and copied else (
        'partially_copied' if copied else 'listed_not_copied')
    outputs[target] = (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    print(json.dumps({'removed_lines':len(removed),
                      'removed_by_reason':dict(Counter(r['reason'] for r in removed)),
                      'removed_by_decision':dict(Counter(r['decision'] for r in removed)),
                      'selected_images':len(images),
                      'problem_sources':dict(problem_stats),
                      'markdown_books_checked':len(markdown_cache),
                      'layout_books_checked':len(layout_cache)},indent=2))
    if write:
        backup = REPO/'.tmp-coverage-review'/('dataset-refresh-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        backup.mkdir(parents=True)
        for path in outputs:(backup/path.name).write_bytes(path.read_bytes())
        try:
            for path, content in outputs.items():
                if path != target:
                    path.write_bytes(content)
            result = build(root)
            temp = target.with_suffix('.json.tmp')
            temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp.replace(target)
        except Exception:
            for path in outputs:
                path.write_bytes((backup / path.name).read_bytes())
            raise
        (REPO/'docs/dataset-selection-refresh.json').write_text(json.dumps({
            'removed_images': removed,
            'problem_sources': dict(problem_stats),
            'backup': backup.relative_to(REPO).as_posix(),
        }, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',required=True,type=Path)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    refresh(args.corpus,args.write)
