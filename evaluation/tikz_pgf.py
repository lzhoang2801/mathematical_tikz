"""Executed PGF paths, graphics state and native TeX text boxes."""
from __future__ import annotations

import math
import re

from shapely.affinity import affine_transform
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, substring, unary_union

from evaluation.tikz_geometry import path_parts


def _compose(a, b):
    x, y, z, w, tx, ty = a
    u, v, s, t, dx, dy = b
    return (x*u+z*v, y*u+w*v, x*s+z*t, y*s+w*t, x*dx+z*dy+tx, y*dx+w*dy+ty)


def _number(value):
    number = float(value.removesuffix("pt"))
    if not math.isfinite(number):
        raise ValueError("Nonfinite native dimension")
    return number


def _point(matrix, point):
    a, b, c, d, x, y = matrix
    u, v = point
    return (a*u+c*v+x, b*u+d*v+y)


def _parts(path):
    # Reuse the evaluator's error-bounded curve flattening instead of fixed samples.
    return [part for subpath in path["subpaths"]
            for part in path_parts({"items":subpath[1:]},curve_tolerance=0.01)]


def _filled(path):
    rings = []
    for part in _parts(path):
        if len(part)<3:
            continue
        polygon = Polygon(part)
        if not polygon.is_valid:
            raise ValueError("self_intersecting_fill_unresolved")
        if polygon.area:
            rings.append(polygon)
    faces = polygonize(unary_union([polygon.boundary for polygon in rings]))
    return unary_union([face for face in faces
        if ((sum(p.covers(face.representative_point()) for p in rings)%2 != 0)
            if path["fill_rule"]=="even_odd" else
            sum((1 if p.exterior.is_ccw else -1)*p.covers(face.representative_point()) for p in rings)!=0)])


def _clipped(shape, clips):
    for clip in clips:
        shape = shape.intersection(_filled(clip))
    return shape


def painted_geometry(path):
    """Measure native paint support; text-box overlap remains a candidate."""
    pieces, strokes = [], []
    if path["operation"] in {"fill","fillstroke"} and path["fill_opacity"]>0:
        pieces.append({"kind":"fill", "geometry":_filled(path), "opacity":path["fill_opacity"]})
    if path["operation"] in {"stroke","closestroke","fillstroke"} and path["stroke_opacity"]>0:
        if path["width"]<=0:
            raise ValueError("device_dependent_hairline")
        if path["dash"] is None:
            raise ValueError("native_dash_value_unobserved")
        a,b,c,d,x,y = path["matrix"]
        determinant = a*d-b*c
        if not determinant:
            raise ValueError("singular_stroke_transform")
        inverse = [d/determinant,-c/determinant,-b/determinant,a/determinant,
                   (c*y-d*x)/determinant,(b*x-a*y)/determinant]
        forward = [a,c,b,d,x,y]
        pattern = path["dash"]*(2 if len(path["dash"])%2 else 1)
        if pattern and (min(pattern)<0 or sum(pattern)<=0):
            raise ValueError("invalid_native_dash_pattern")
        for part in _parts(path):
            if len(part)<2:
                continue
            line = affine_transform(LineString(part),inverse)
            fragments = [line]
            if pattern:
                fragments,index,position = [],0,-(path["dash_phase"]%sum(pattern))
                while position<line.length:
                    end = position+pattern[index%len(pattern)]
                    if index%2==0 and end>=0:
                        fragments.append(substring(line,max(0.,position),min(end,line.length)))
                    position,index = end,index+1
                    if index>10000:
                        raise ValueError("dash_expansion_quota")
            for fragment in fragments:
                support = fragment.buffer(path["width"]/2,cap_style={"round":1,"butt":2,"rect":3}[path["cap"]],
                    join_style={"round":1,"miter":2,"bevel":3}[path["join"]],mitre_limit=path["miter_limit"])
                strokes.append(affine_transform(support,forward))
    if strokes:
        pieces.append({"kind":"stroke", "geometry":unary_union(strokes), "opacity":path["stroke_opacity"]})
    return [{**piece,"geometry":_clipped(piece["geometry"],path["clips"])} for piece in pieces]


def parse_trace(log: str) -> dict:
    """Read framed log records; reject partial or malformed execution evidence."""
    unwrapped = log.replace('\r', '').replace('\n', '')
    records = re.findall(r'PGFEVAL\|(.*?)\|ENDPGFEVAL', unwrapped)
    if not records or not records[0].startswith('BEGIN|') or records[-1] != 'DONE':
        raise ValueError('Incomplete PGF trace')
    if len(records) >= 100000 or 'TRUNCATED' in records:
        raise ValueError('PGF observation limit exceeded')
    if sum(row.startswith('BEGIN|') for row in records) != 1 or records.count('DONE') != 1:
        raise ValueError('Ambiguous PGF execution trace')
    # Metadata is evaluated at construction; graphics state follows actual box insertion.
    shipped = re.findall(r'PGFORDER\|(.*?)\|ENDPGFORDER', unwrapped)
    native_order = any(row.startswith('ORDER|') for row in records)
    events = records[1:-1]
    if native_order:
        if not shipped or shipped[-1]!='DONE' or shipped.count('DONE')!=1:
            raise ValueError('Incomplete native shipout')
        identities = list(map(int,shipped[:-1]))
        if len(set(identities))!=len(identities):
            raise ValueError('Reused native text box has ambiguous paint occurrences')
        definitions, buffered, pending = [], {}, None
        for event in events:
            if event.startswith('ORDER|'):
                if pending is not None:
                    raise ValueError('Missing ordered PGF event')
                pending = int(event.split('|')[1])
            elif pending is not None:
                if pending in buffered:
                    raise ValueError('Duplicate ordered PGF event')
                buffered[pending], pending = event, None
            else:
                definitions.append(event)
        if pending is not None or any(identity not in buffered for identity in identities):
            raise ValueError('Incomplete native shipout evidence')
        events = definitions + [buffered[identity] for identity in identities]
    matrix = (1., 0., 0., 1., 0., 0.)
    state = {'width': .4, 'cap': 'butt', 'join': 'miter', 'miter_limit': 10.,
             'dash': [], 'dash_phase': 0., 'stroke_opacity': 1., 'fill_opacity': 1.,
             'fill_rule': 'nonzero', 'clips': [], 'color': [0., 0., 0.]}
    stack, owners, paths, subpaths, current = [], [], [], [], []
    nodes, text_boxes, unsupported = {}, {}, []
    conic_registry, conics, arrows, arrow_stack = {}, [], [], []
    bounds, current_id, pending_clip = None, None, False

    def finish_part():
        nonlocal current
        if current:
            subpaths.append(current)
        current = []

    arities = {'NODE_CONTEXT': 1, 'NODE_BEGIN': 2, 'NODE_END': 0, 'NODE': 4, 'ATTACH': 4,
               'CONIC': 15, 'ARROW_BEGIN': 4, 'ARROW_END': 0, 'TEXTBOX': 9, 'TEXTFONT': 2, 'TEXTSIZE': 5, 'BOUNDS': 4, 'UNSUPPORTED': 1, 'beginscope': 0, 'endscope': 0,
               'transformcm': 6, 'setlinewidth': 1, 'setdash': 2, 'setmiterlimit': 1,
               'roundcap': 0, 'buttcap': 0, 'rectcap': 0, 'roundjoin': 0, 'miterjoin': 0,
               'beveljoin': 0, 'stroke@opacity': 1, 'fill@opacity': 1, 'FILL_RULE': 1,
               'moveto': 2, 'lineto': 2, 'curveto': 6, 'rect': 4, 'closepath': 0,
               'closestroke': 0, 'stroke': 0, 'fill': 0, 'fillstroke': 0, 'clipnext': 0,
               'discardpath': 0, 'color@rgb@stroke': 3, 'color@rgb@fill': 3,
               'color@gray@stroke': 1, 'color@gray@fill': 1}
    for order, record in enumerate(events):
        op, *raw = record.split('|')
        if op == 'TEXT':
            _, index, text = record.split('|', 2)
            nodes[int(index)]['text'] = text
            continue
        if op not in arities or len(raw) != arities[op]:
            raise ValueError(f'Malformed PGF operation: {op}')
        if op == 'CONIC':
            values = list(map(_number, raw))
            key = tuple(round(v*65536) for v in values[9:])
            conic_registry.setdefault(key, []).append(values[:9])
        elif op == 'ARROW_BEGIN':
            values = list(map(_number, raw))
            tip, end = _point(matrix,values[:2]), _point(matrix,values[2:])
            length = math.dist(tip,end)
            if not length:
                raise ValueError('Degenerate native arrow transform')
            arrow_stack.append(len(arrows))
            arrows.append({'tip':tip,'direction':[(end[i]-tip[i])/length for i in (0,1)],
                           'dashed':bool(state['dash']),'width':state['width']})
        elif op == 'ARROW_END':
            if not arrow_stack:
                raise ValueError('Unbalanced native arrow')
            arrow_stack.pop()
        elif op == 'NODE_CONTEXT':
            current_id = int(raw[0])
            if current_id in nodes or len(nodes) >= 512:
                raise ValueError('Duplicate node occurrence or PGF node limit exceeded')
            nodes[current_id] = {'id': current_id, 'matrix': matrix}
        elif op == 'NODE_BEGIN':
            identity = int(raw[1]) if raw[1] else None
            owners.append((raw[0],identity))
            if native_order and identity in nodes:
                node = nodes[identity]
                node['attachment']['point'] = _point(matrix,node['attachment']['point'])
                node['inserted'] = True
        elif op == 'NODE_END':
            if not owners:
                raise ValueError('Unbalanced PGF node')
            owners.pop()
        elif op == 'NODE':
            nodes[int(raw[0])].update(name=raw[1], parent=raw[2] or None, shape=raw[3])
        elif op == 'ATTACH':
            node = nodes[int(raw[0])]
            node['attachment'] = {'kind': raw[1], 'point': _point(node['matrix'], list(map(_number, raw[2:])))}
        elif op == 'TEXTBOX':
            values = list(map(_number, raw[1:]))
            corners = [_point(matrix, values[i:i+2]) for i in range(0, 8, 2)]
            text_boxes.setdefault(int(raw[0]), []).append(
                {'corners': corners, 'clips': state['clips'], 'opacity': state['fill_opacity'], 'order':order})
        elif op == 'TEXTFONT':
            nodes[int(raw[0])]['font_pt'] = _number(raw[1])
        elif op == 'TEXTSIZE':
            values = list(map(_number, raw[1:]))
            node = nodes[int(raw[0])]
            node['font_size'] = node['font_pt'] * math.dist(_point(matrix, values[:2]), _point(matrix, values[2:]))
        elif op == 'BOUNDS':
            if bounds is not None:
                raise ValueError('More than one PGF picture')
            bounds = list(map(_number, raw))
        elif op == 'UNSUPPORTED':
            unsupported.append(raw[0])
        elif op == 'beginscope':
            stack.append((matrix, state.copy()))
        elif op == 'endscope':
            if not stack:
                raise ValueError('Unbalanced PGF graphics scope')
            matrix, state = stack.pop()
        elif op == 'transformcm':
            matrix = _compose(matrix, tuple(map(_number, raw)))
        elif op == 'setlinewidth':
            state['width'] = _number(raw[0])
        elif op == 'setdash':
            values = raw[0].replace('{', ' ').replace('}', ' ').replace(',', ' ').split()
            state['dash'] = list(map(_number, values))
            state['dash_phase'] = _number(raw[1])
        elif op == 'setmiterlimit':
            state['miter_limit'] = _number(raw[0])
        elif op in {'roundcap', 'buttcap', 'rectcap'}:
            state['cap'] = op.removesuffix('cap')
        elif op in {'roundjoin', 'miterjoin', 'beveljoin'}:
            state['join'] = op.removesuffix('join')
        elif op in {'stroke@opacity', 'fill@opacity'}:
            state[op.replace('@', '_')] = _number(raw[0])
        elif op == 'FILL_RULE':
            if raw[0] not in {'even_odd', 'nonzero'}:
                raise ValueError('Unsupported PGF fill rule')
            state['fill_rule'] = raw[0]
        elif op.startswith('color@'):
            if op.endswith('@stroke'):
                state['color'] = list(map(_number, raw))
        elif op == 'moveto':
            finish_part()
            current = [('m', _point(matrix, list(map(_number, raw))))]
        elif op in {'lineto', 'curveto'}:
            if not current:
                raise ValueError('PGF path has no current point')
            values = list(map(_number, raw))
            points = [_point(matrix, values[i:i+2]) for i in range(0, len(values), 2)]
            current.append(('l' if op == 'lineto' else 'c', current[-1][-1], *points))
            if op == 'curveto':
                key = tuple(round(v*65536) for v in values)
                for native in conic_registry.get(key, []):
                    if math.dist(_point(matrix,native[:2]), current[-1][1]) > 0.0001:
                        continue
                    center = _point(matrix,native[2:4])
                    origin = _point(matrix,(0,0))
                    axes = [[p[i]-origin[i] for i in (0,1)]
                            for p in (_point(matrix,native[4:6]),_point(matrix,native[6:8]))]
                    conics.append({'curve':current[-1],'center':center,'axes':axes,
                                   'sweep':math.radians(native[8])})
                    break
        elif op == 'rect':
            finish_part()
            x, y, w, h = map(_number, raw)
            corners = [_point(matrix, p) for p in [(x,y), (x+w,y), (x+w,y+h), (x,y+h), (x,y)]]
            subpaths.append([('m', corners[0]), *(('l', a, b) for a, b in zip(corners, corners[1:]))])
        elif op in {'closepath', 'closestroke'}:
            if current and current[-1][-1] != current[0][1]:
                current.append(('l', current[-1][-1], current[0][1]))
        elif op == 'clipnext':
            pending_clip = True
        if op in {'stroke', 'closestroke', 'fillstroke', 'fill', 'discardpath'}:
            finish_part()
            if op != 'discardpath' and subpaths:
                paths.append({'subpaths': subpaths, 'operation': op, **state, 'matrix': matrix,
                              'node_name': owners[-1][0] if owners else None,
                              'node_id': owners[-1][1] if owners else None, 'order':order,
                              'conics':conics, 'arrow':arrow_stack[-1] if arrow_stack else None})
                if len(paths) > 4000:
                    raise ValueError('PGF path limit exceeded')
            if pending_clip:
                state['clips'] = state['clips'] + [{'subpaths': subpaths, 'fill_rule': state['fill_rule']}]
            subpaths, current, conics, pending_clip = [], [], [], False
    if stack or owners or arrow_stack or current or subpaths or pending_clip or bounds is None:
        raise ValueError('Incomplete PGF picture or unbalanced graphics state')
    if any('text' not in node or 'attachment' not in node for node in nodes.values()):
        raise ValueError('Incomplete PGF node evidence')
    if native_order:
        nodes = {i:node for i,node in nodes.items() if node.get('inserted')}
    return {'paths': paths, 'nodes': list(nodes.values()), 'text_boxes': text_boxes,
            'unsupported': sorted(set(unsupported)), 'bounds': bounds, 'arrows':arrows, 'pgf_version': records[0].split('|')[1]}


def normalize_text(text: str) -> str:
    """Normalize simple mathematical identities; arbitrary TeX stays display text."""
    text = re.sub(r'\^\s*\{?\s*\\circ\s*\}?', '\u00b0', text)
    text = re.sub(r'\\(?:mathrm|mathbf|mathit|text|textrm|textbf)\b', '', text)
    text = text.replace(r'\prime', "'").replace('\u2032', "'").replace('\u2019', "'")
    text = re.sub(r'\\(?:vert|mid)\b', '|', text)
    return ''.join(text.translate(str.maketrans('', '', '${}_^')).split())


def text_regions(boxes: list[dict]) -> tuple:
    raw, visible = [], []
    for box in boxes:
        if box['opacity'] <= 0:
            continue
        region = Polygon([box['corners'][j] for j in (0, 1, 3, 2)])
        if not region.is_valid:
            raise ValueError('Degenerate native text box')
        raw.append(region)
        visible.append(_clipped(region, box['clips']))
    return unary_union(raw), unary_union(visible)
