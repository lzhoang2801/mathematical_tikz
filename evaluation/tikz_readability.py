"""Conservative label clearance from native TeX boxes and PGF paint support."""
from __future__ import annotations

from typing import Any
from shapely.geometry import box
from shapely.ops import unary_union


def inspect_readability(scene: dict[str, Any]) -> dict[str, Any]:
    """One unit per text node; native boxes do not resolve glyph holes or kerning."""
    page = box(*scene['bounds']).buffer(4.0)
    labels, regions = [], []
    fills = [p for p in scene['paint'] if p['kind']=='fill']
    opaque = [p for p in fills if p['opacity']==1]
    strokes = []
    for p in scene['paint']:
        if p['kind']=='stroke':
            cover = unary_union([q['geometry'] for q in opaque if q['order']>p['order']])
            strokes.append({**p,'geometry':p['geometry'].difference(cover)})
    for label in scene['text']:
        if label['text'] and set(label['text']) <= {'|', '\u2223', '\u2016'}:
            continue
        region, raw = label.get('region'), label.get('box_region')
        known = (region is not None and raw is not None and not raw.is_empty
                 and not label.get('measurement_error') and not scene.get('paint_issues'))
        row = {'text': label['text'], 'status': 'pass' if known else 'unknown', 'issues': []}
        if known:
            if raw.difference(region).area > 0.02 or raw.difference(page).area > 0.02:
                row['issues'].append({'kind': 'clipped'})
            # A prior fill is background. A later fill can cover text or earlier strokes.
            later = [p for p in fills if p['order']>label['order'] and p['node_id']!=label['id']]
            for painted in strokes + later:
                if painted['node_id'] == label['id']:
                    continue
                area = region.intersection(painted['geometry']).area
                if area > 0.02:
                    row['issues'].append({'kind':'overpainted' if painted['kind']=='fill' else 'paint_overlap',
                                          'path':painted['path'],'area_tex_pt2':area})
            cover = unary_union([p['geometry'] for p in later if p['opacity']==1])
            region = region.difference(cover)
            if row['issues']:
                row['status'] = 'fail'
        labels.append(row)
        regions.append(region if known else None)
    for i, first in enumerate(regions):
        for j in range(i + 1, len(regions)):
            if first is not None and regions[j] is not None and first.intersection(regions[j]).area > 0.02:
                for a, b in ((i, j), (j, i)):
                    labels[a]['issues'].append({'kind': 'text_overlap', 'other_label': b})
                    labels[a]['status'] = 'fail'
    return {'labels': labels, 'unsupported': scene.get('paint_issues', [])}
