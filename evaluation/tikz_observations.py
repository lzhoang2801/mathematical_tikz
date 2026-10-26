"""Compile once and observe executed PGF geometry, independently of PDF/raster output."""
from __future__ import annotations

import math
import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from agent.latex._tex import _without_tex_comments
from agent.latex.tikz import SUPPORTED_TIKZ_LIBRARIES, standalone_tikz_document, validate_tikz
from latex_compiler.client import compile as compile_latex
from latex_compiler.schemas import CompileRequest, Images, Outputs
from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.tikz_geometry import REL_TOL, measure_circular_path, path_parts
from evaluation.tikz_pgf import _clipped, normalize_text, painted_geometry, parse_trace, text_regions

SCHEMA_VERSION = "tikz-observations:pgf-v2"
_POINT_LABEL = re.compile(r"[A-Z](?:[0-9]+|'+)?\Z")
TRACE_PATH = Path(__file__).with_name('pgf_trace.tex')
TRACE_SOURCE = TRACE_PATH.read_text(encoding='utf-8')
TRACER_SHA256 = hashlib.sha256(TRACE_SOURCE.encode()).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_records(response: Any, directory: Path) -> dict[str, dict[str, Any]]:
    """Persist returned bytes and retain each artifact's compiler identity."""
    directory.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    for artifact in response.artifacts:
        data = artifact.data
        path = directory / artifact.name
        path.write_bytes(data)
        records[artifact.name] = {
            "path": str(path.resolve()),
            "sha256": _sha256(data),
            "complete": artifact.complete,
            "size_bytes": len(data),
        }
    return records


def _stage_record(stage: Any) -> dict[str, Any]:
    return {
        "outcome": stage.outcome,
        "success": stage.success,
        "exit_code": stage.exit_code,
        "failure_code": stage.failure_code,
        "diagnostic": stage.diagnostic,
    }


def _validate_evaluation_tikz(tikz: str) -> str:
    """Allow dataset comments and shared libraries while compiling the exact source."""
    if "^^" in tikz:
        raise ValueError("TikZ output must not contain TeX character-code notation.")
    inspected = _without_tex_comments(tikz).strip()
    while match := re.match(r"\\usetikzlibrary\s*\{([^{}]*)\}", inspected):
        libraries = {name.strip() for name in match[1].split(",")}
        if not libraries <= set(SUPPORTED_TIKZ_LIBRARIES):
            raise ValueError("TikZ libraries must come from the shared wrapper.")
        inspected = inspected[match.end():].lstrip()
    validate_tikz(inspected)
    return tikz.strip()


def _native_circle(conic: dict, part: list) -> dict | None:
    """Use executed axes and interval; canvas deformation must still preserve a circle."""
    u, v = np.asarray(conic['axes'])
    ru, rv = np.linalg.norm(u), np.linalg.norm(v)
    if min(ru, rv) <= 0 or abs(ru/rv-1) > REL_TOL or abs(float(u @ v)) > REL_TOL*ru*rv:
        return None
    direction = conic['sweep'] * (u[0]*v[1]-u[1]*v[0])
    if not direction or len(part)<2:
        return None
    center = conic['center']
    a, b = (math.atan2(p[1]-center[1],p[0]-center[0]) for p in (part[0],part[-1]))
    sweep = (b-a) % math.tau if direction>0 else -((a-b) % math.tau)
    if not sweep:
        return None
    return {'center':list(center),'radius':float((ru+rv)/2),'closed':False,
            'start':list(part[0]),'end':list(part[-1]),'sweep':sweep}


def _merge_circular_paths(paths: list[dict]) -> list[dict]:
    """Union co-circular painted intervals, independent of command splitting."""
    groups = []
    for path in sorted(paths, key=lambda row: abs(row['sweep']), reverse=True):
        for group in groups:
            base = group[0]
            if (path['dashed'] == base['dashed'] and
                    math.dist(path['center'], base['center']) <= REL_TOL * base['radius'] and
                    abs(path['radius'] / base['radius'] - 1) <= REL_TOL):
                group.append(path)
                break
        else:
            groups.append([path])
    result = []
    for group in groups:
        base = group[0]
        cx, cy = base['center']
        intervals = []
        for path in group:
            if path['closed']:
                intervals = [(0.0, math.tau)]
                break
            first, last = (path['start'], path['end']) if path['sweep'] > 0 else (path['end'], path['start'])
            start = math.atan2(first[1] - cy, first[0] - cx) % math.tau
            span = (math.atan2(last[1] - cy, last[0] - cx) - start) % math.tau
            end = start + span
            intervals.append((start, min(end, math.tau)))
            if end > math.tau:
                intervals.append((0.0, end - math.tau))
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + REL_TOL:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        if len(merged) > 1 and merged[0][0] + math.tau - merged[-1][1] <= REL_TOL:
            merged = [[merged[-1][0], merged[0][1] + math.tau], *merged[1:-1]]
        for start, end in merged:
            closed = end - start >= math.tau - REL_TOL
            ends = [[cx + base['radius'] * math.cos(angle), cy + base['radius'] * math.sin(angle)]
                    for angle in (start, end)]
            result.append({**base, 'closed': closed, 'start': ends[0], 'end': ends[1],
                           'sweep': math.tau if closed else end - start})
    return result


def instrument(tikz: str) -> str:
    source = standalone_tikz_document(tikz)
    source = source.replace(r'\begin{document}', r'\input{pgf_trace.tex}' + '\n' +
                            r'\begin{document}\PgfEvalBegin', 1)
    return source.replace(r'\end{document}', r'\PgfEvalEnd\end{document}', 1)


def compile_observe(tikz: str, artifact_dir: Path, compiler_http: httpx.Client, *, preview: bool = False) -> dict[str, Any]:
    """Return compiler evidence; PNGs are optional preview artifacts, never scoring inputs."""
    metadata = {'schema_version': SCHEMA_VERSION, 'tracer_sha256': TRACER_SHA256,
                'input_tikz_sha256': _sha256(tikz.encode('utf-8'))}
    result = {'compile_success': False, 'raster_success': False, 'image_path': None, 'log_path': None,
              'artifacts': {}, 'metadata': metadata}
    try:
        canonical = _validate_evaluation_tikz(tikz)
    except ValueError as error:
        result['compile'] = {'outcome': 'validation_failed', 'success': False, 'diagnostic': str(error)}
        return result
    root = Path(artifact_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source, trace = instrument(canonical), TRACE_SOURCE
    (root / 'main.tex').write_text(source, encoding='utf-8')
    (root / 'pgf_trace.tex').write_text(trace, encoding='utf-8')
    metadata['wrapper_sha256'] = _sha256(source.encode())
    request = CompileRequest(source=source, support_files={'pgf_trace.tex': trace},
                             outputs=Outputs(pdf=False, images=Images() if preview else None))
    try:
        response = compile_latex(compiler_http, request)
        artifacts = _artifact_records(response, root)
        # A hook failure must not masquerade as a model compile failure.
        if not response.compile.success:
            original = compile_latex(compiler_http, CompileRequest(source=standalone_tikz_document(canonical), outputs=request.outputs))
            original_artifacts = _artifact_records(original, root / 'compile-check')
            result['artifacts']['compile_check'] = original_artifacts
            result['compile'] = _stage_record(original.compile)
            result['compile_success'] = original.compile.success
            metadata['trace_error'] = 'Instrumented compilation failed'
            if preview and original.raster.success and original_artifacts.get('page-1.png', {}).get('complete'):
                result.update(image_path=original_artifacts['page-1.png']['path'], raster_success=True)
        else:
            result.update(compile_success=True, compile=_stage_record(response.compile))
    except (httpx.HTTPError, ValueError) as error:
        result.update(compile={'outcome': 'unknown', 'success': False, 'diagnostic': str(error)})
        return result
    metadata.update(toolchain_id=response.toolchain_id, source_digest=response.source_digest, page_count=response.page_count)
    result['artifacts']['pgf'] = artifacts
    result['raster'] = _stage_record(response.raster)
    if response.compile.success:
        result['raster_success'] = response.raster.success
        if preview and response.raster.success and artifacts.get('page-1.png', {}).get('complete'):
            result['image_path'] = artifacts['page-1.png']['path']
        if artifacts.get('result.log', {}).get('complete'):
            result['log_path'] = artifacts['result.log']['path']
    return result


def read_scene(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve native paths and visible label attachments in PGF TeX pt, y upwards."""
    if not observation.get('compile_success'):
        raise ValueError('No successfully compiled TikZ')
    if observation.get('metadata', {}).get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Obsolete observation schema; recompile with the PGF evaluator')
    if observation['metadata'].get('tracer_sha256') != TRACER_SHA256:
        raise ValueError('PGF tracer changed; recompile in a new run directory')
    artifact = observation.get('artifacts', {}).get('pgf', {}).get('result.log', {})
    if not artifact.get('complete') or not observation.get('log_path'):
        raise ValueError('Complete PGF log unavailable')
    log = Path(observation['log_path']).read_bytes()
    if _sha256(log) != artifact.get('sha256'):
        raise ValueError('PGF log artifact changed')
    try:
        native = parse_trace(log.decode('utf-8'))
    except (KeyError, IndexError, UnicodeError) as error:
        raise ValueError(f'Malformed PGF evidence: {error}') from error
    text, points, bindings, unresolved = [], {}, {}, []
    paint, paint_issues = [], list(native['unsupported'])
    for node in native['nodes']:
        name = normalize_text(node['text'])
        if not name:
            continue
        boxes = native['text_boxes'].get(node['id'], [])
        if boxes and all(box['opacity'] <= 0 for box in boxes):
            continue
        label = {'id': node['id'], 'text': name, 'tex': node['text'], 'node': node['name'],
                 'parent': node['parent'], 'attachment': node['attachment'], 'boxes': boxes}
        try:
            raw, visible = text_regions(boxes)
            if boxes and not raw.is_empty and visible.is_empty:
                continue
            label.update(region=visible, box_region=raw, bbox=list(raw.bounds) if not raw.is_empty else [],
                         size=node.get('font_size', 10.), order=min((b['order'] for b in boxes), default=-1))
        except ValueError as error:
            label['measurement_error'] = str(error)
        text.append(label)
        if _POINT_LABEL.fullmatch(name):
            if name in points:
                points[name] = None
                unresolved.append(name)
            else:
                points[name] = tuple(node['attachment']['point'])
                bindings[name] = {'id': node['id'], **node['attachment']}
    drawings = []
    for index, path in enumerate(native['paths']):
        try:
            for piece in painted_geometry(path):
                if not piece['geometry'].is_empty:
                    paint.append({**piece, 'node_id':path['node_id'], 'path':index, 'order':path['order']})
        except ValueError as error:
            paint_issues.append(str(error))
        items = [item for subpath in path['subpaths'] for item in subpath[1:]]
        drawings.append({**path, 'path': index, 'items': items,
                         'stroked': path['operation'] in {'stroke', 'closestroke', 'fillstroke'} and path['stroke_opacity'] > 0})
    strokes, curves, circular, unsupported = [], [], [], list(native['unsupported'])
    visible_paths = {piece['path'] for piece in paint}
    arrow_ids = {drawing['arrow'] for drawing in drawings if drawing['path'] in visible_paths}
    arrows = [arrow for i,arrow in enumerate(native['arrows']) if i in arrow_ids]
    for drawing in drawings:
        if not drawing['stroked'] or drawing['arrow'] is not None:
            continue
        style = {'dashed': bool(drawing['dash']), 'path': drawing['path'], 'width': drawing['width'],
                 'opacity': drawing['stroke_opacity']}
        if any(item[0] == 'c' for item in drawing['items']):
            native_curves = {tuple(item['curve']):item for item in drawing['conics']}
            coordinates = [p for item in drawing['items'] if item[0] == 'c' for p in item[1:]]
            extent = max(max(p[axis] for p in coordinates) - min(p[axis] for p in coordinates) for axis in (0, 1))
            try:
                for subpath in drawing['subpaths']:
                    # Native constructors bind exact cubic spans, including saved/replayed paths.
                    groups, generic = [], []
                    for item in subpath[1:]:
                        if item[0] != 'c' or tuple(item) in native_curves:
                            if generic:
                                groups.append((generic,None))
                                generic=[]
                            if item[0] == 'c':
                                groups.append(([item],native_curves[tuple(item)]))
                        else:
                            generic.append(item)
                    if generic:
                        groups.append((generic,None))
                    for items, conic in groups:
                        for part in path_parts({'items':items},curve_tolerance=max(extent*1e-4,1e-8)):
                            geometry = _clipped(LineString(part),drawing['clips'])
                            if geometry.is_empty:
                                continue
                            curves.append({**style,'geometry':geometry})
                            pieces = [geometry] if geometry.geom_type == 'LineString' else list(geometry.geoms)
                            for piece in pieces:
                                if piece.geom_type != 'LineString':
                                    continue
                                curve_points = list(piece.coords)
                                circle = _native_circle(conic,curve_points) if conic else measure_circular_path(curve_points)
                                if circle is None:
                                    unsupported.append('A painted curved stroke is not a supported circular path')
                                else:
                                    circular.append({**circle,**style})
            except (ValueError, ArithmeticError) as error:
                unsupported.append(str(error))
        components = []
        try:
            for item in drawing['items']:
                if item[0] != 'l' or item[1] == item[2]:
                    continue
                geometry = _clipped(LineString(item[1:]), drawing['clips'])
                pieces = [geometry] if geometry.geom_type == 'LineString' else list(getattr(geometry, 'geoms', []))
                components.extend(piece for piece in pieces if piece.geom_type == 'LineString' and piece.length > 0)
        except ValueError as error:
            unsupported.append(str(error))
        if components:
            strokes.append({'components': components, 'geometry': unary_union(components),
                            'color': drawing['color'], **style})
    circular = _merge_circular_paths(circular)
    return {'frame': 'pgf', 'unit': 'tex_pt', 'trace_sha256': artifact['sha256'],
            'points': points, 'bindings': bindings, 'unresolved': sorted(set(unresolved)),
            'text': text, 'strokes': strokes, 'curves': curves, 'paint': paint, 'paint_issues': sorted(set(paint_issues)),
            'circles': [p for p in circular if p['closed']], 'arcs': [p for p in circular if not p['closed']],
            'arrows': arrows, 'paths': native['paths'], 'unsupported': sorted(set(unsupported)), 'bounds': native['bounds']}
