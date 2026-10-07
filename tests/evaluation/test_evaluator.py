"""Reference geometry and the two-string API, without live model/compiler calls."""
import inspect
import math
from pathlib import Path

import pymupdf
import pytest

from evaluation.evaluator import _score_observations as score, evaluate


def diagram(path: Path, *, scale: float = 1, missing_edge: bool = False, wrong_text: bool = False, rotation: bool = False, reflection: bool = False, markers: bool = True, label_shift: float = 0, collide: bool = False, coordinates=None) -> dict:
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=250 * scale, height=180 * scale)
        coords = coordinates if coordinates is not None else [(30, 100), (130, 100), (60, 30)]
        if rotation:
            coords = [(180 - y, x) for x, y in coords]
        if reflection:
            coords = [(180 - x, y) for x, y in coords]
        points = [pymupdf.Point(x * scale, y * scale) for x, y in coords]
        for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
            if not missing_edge or i != 1:
                page.draw_line(a, b, color=(0, 0, 0), width=scale)
        for label, p in zip("ABC", points):
            if markers:
                page.draw_circle(p, 1.5 * scale, color=(0, 0, 0), fill=(0, 0, 0))
            position = points[0] if collide and label == "B" else p
            dx, dy = (0, -10 if label == "C" else 14)
            if rotation:
                dx, dy = (5, 0) if label == "C" else (-12, 0)
            page.insert_text((position.x + dx * scale + label_shift, position.y + dy * scale), label, fontsize=8 * scale)
        page.insert_text((30 * scale, 160 * scale), "8 cm" if wrong_text else "6 cm", fontsize=8 * scale)
        pdf.save(path)
    return {"compile_success": True, "pdf_path": str(path), "labeled_points": {
        label: {"status": "measured", "pdf_x": p.x, "pdf_y": p.y, "evidence_id": "constructed-pdf-fixture"}
        for label, p in zip("ABC", points)
    }}


@pytest.mark.parametrize('options,readable', [
    ({'scale': 1.7}, True), ({'reflection': True}, True), ({'rotation': True}, True),
    ({'rotation': True, 'reflection': True}, False),
    ({'label_shift': 4}, True), ({'markers': False}, True), ({'wrong_text': True}, True),
])
def test_similarity_and_text_changes_preserve_geometry(tmp_path, options, readable):
    coordinates = [(30, 100), (130, 100), (30, 30)]
    target = diagram(tmp_path / 'target.pdf', coordinates=coordinates)
    output = diagram(tmp_path / 'output.pdf', coordinates=coordinates, **options)
    result = score(target, output)
    assert set(result) == {'compile', 'mathematical_correctness', 'content_coverage', 'visual_readability'}
    assert result['compile'] == 1
    assert result['mathematical_correctness'] == result['content_coverage'] == 100
    assert (result['visual_readability'] == 100) == readable


def test_missing_connection_and_free_proportions_are_separate(tmp_path):
    target = diagram(tmp_path / 'target.pdf')
    missing = diagram(tmp_path / 'missing.pdf', missing_edge=True)
    varied = diagram(tmp_path / 'varied.pdf', coordinates=[(30,100),(160,100),(60,30)])
    first, second = score(target, missing), score(target, varied)
    assert first['mathematical_correctness'] == 100
    assert first['content_coverage'] == pytest.approx(500 / 6)
    assert second['mathematical_correctness'] == 100
    assert second['content_coverage'] == 100


def test_nonsimilar_construction_does_not_require_target_side_proportions(tmp_path):
    target = diagram(tmp_path / 'target.pdf', coordinates=[(30, 100), (130, 100), (30, 30)])
    output = diagram(tmp_path / 'output.pdf', coordinates=[(30, 100), (160, 100), (30, 60)])
    result = score(target, output)
    assert result['mathematical_correctness'] == 100
    assert result['content_coverage'] == 100


def test_readability_is_absolute_and_does_not_change_geometry(tmp_path):
    target = diagram(tmp_path / 'target.pdf', collide=True)
    result = score(target, target)
    assert result['mathematical_correctness'] == result['content_coverage'] == 100
    assert result['visual_readability'] < 100


def test_text_rules_are_not_connections_or_carrier_collisions(tmp_path):
    target = diagram(tmp_path / 'target.pdf')
    with pymupdf.open(target['pdf_path']) as pdf:
        pdf[0].draw_line((30, 157), (47, 157), color=(0, 0, 0))
        pdf.saveIncr()
    result = score(target, target)
    assert result['content_coverage'] == result['visual_readability'] == 100


def test_missing_point_evidence_loses_credit_without_shrinking_the_denominator(tmp_path):
    target = diagram(tmp_path / 'target.pdf')
    output = diagram(tmp_path / 'output.pdf')
    output['labeled_points']['C'] = {'status': 'unknown'}
    result = score(target, output)
    assert result['mathematical_correctness'] == 25
    assert result['content_coverage'] == 50
    with pytest.raises(ValueError, match='Unusable reference'):
        score(output, target)


def test_infrastructure_errors_and_invalid_references_are_not_model_scores(tmp_path):
    target = diagram(tmp_path / 'target.pdf')
    unavailable = {'compile_success': False, 'compile': {'outcome': 'unknown'}}
    invalid = {'compile_success': False, 'compile': {'outcome': 'validation_failed'}}
    with pytest.raises(RuntimeError, match='compiler unavailable'):
        score(target, unavailable)
    with pytest.raises(ValueError, match='target_tikz'):
        score(invalid, target)
    assert score(target, invalid) == {'compile': 0, 'mathematical_correctness': 0,
                                      'content_coverage': 0, 'visual_readability': 0}


@pytest.mark.parametrize('mutation', ['identity', 'radius', 'center', 'missing', 'style', 'duplicate', 'transform', 'ellipse'])
def test_drawn_circle_geometry_and_presence_are_separate(tmp_path, mutation):
    coordinates = [(100, 100), (140, 100), (100, 70)]
    target = diagram(tmp_path / 'target.pdf', coordinates=coordinates)
    transform = {'scale': 1.7, 'rotation': True, 'reflection': True} if mutation == 'transform' else {}
    output = diagram(tmp_path / 'output.pdf', coordinates=coordinates, **transform)
    for role, observation in (('target', target), ('output', output)):
        points = observation['labeled_points']
        center = (points['A']['pdf_x'], points['A']['pdf_y'])
        radius = math.dist(center, (points['C']['pdf_x'], points['C']['pdf_y']))
        change = mutation if role == 'output' else 'identity'
        if change == 'missing':
            continue
        if change == 'radius':
            radius *= 1.25
        if change == 'center':
            center = (center[0] + 10, center[1])
        with pymupdf.open(observation['pdf_path']) as pdf:
            if change == 'ellipse':
                pdf[0].draw_oval((center[0]-radius, center[1]-radius/2, center[0]+radius, center[1]+radius/2), dashes='[4 3]')
            else:
                for _ in range(2 if change == 'duplicate' else 1):
                    pdf[0].draw_circle(center, radius, dashes='[]' if change == 'style' else '[4 3]')
            pdf.saveIncr()
    result = score(target, output)
    assert result['mathematical_correctness'] == (80 if mutation in {'radius', 'center', 'missing', 'ellipse'} else 100)
    assert (result['content_coverage'] == 100) == (mutation not in {'missing', 'style', 'ellipse'})
    if mutation in {'missing', 'style'}:
        assert result['content_coverage'] == pytest.approx(600 / 7)
    assert score(target, target)['mathematical_correctness'] == 100
    if mutation == 'ellipse':
        with pytest.raises(ValueError, match='Unusable reference'):
            score(output, target)


@pytest.mark.parametrize('swap_style', [False, True])
def test_circle_order_is_irrelevant_and_style_is_coverage(tmp_path, swap_style):
    target = diagram(tmp_path / 'target.pdf', coordinates=[(100, 100), (140, 100), (100, 70)])
    output = diagram(tmp_path / 'output.pdf', coordinates=[(100, 100), (140, 100), (100, 70)])
    for observation, names in ((target, 'AB'), (output, 'BA')):
        for name in names:
            point = observation['labeled_points'][name]
            center = (point['pdf_x'], point['pdf_y'])
            radius = math.dist(center, (100, 70))
            dashed = (name == 'A') != (observation is output and swap_style)
            with pymupdf.open(observation['pdf_path']) as pdf:
                pdf[0].draw_circle(center, radius, dashes='[4 3]' if dashed else '[]')
                pdf.saveIncr()
    result = score(target, output)
    assert result['mathematical_correctness'] == 100
    assert result['content_coverage'] == (75 if swap_style else 100)


def test_public_api_accepts_exactly_two_tikz_strings(tmp_path, monkeypatch):
    import evaluation.evaluator as evaluator
    assert list(inspect.signature(evaluate).parameters) == ['target_tikz', 'output_tikz']
    target = diagram(tmp_path / 'target.pdf')
    output = diagram(tmp_path / 'output.pdf', reflection=True)
    calls = []
    def compile_stub(tikz, directory, compiler):
        calls.append(tikz)
        return {'target code': target, 'output code': output}[tikz]
    monkeypatch.setattr(evaluator, 'compile_observe', compile_stub)
    assert evaluate('target code', 'output code') == score(target, output)
    assert calls == ['target code', 'output code']
    calls.clear()
    assert evaluate('target code', 'target code')['mathematical_correctness'] == 100
    assert calls == ['target code']
    with pytest.raises(TypeError, match='strings'):
        evaluate({}, 'output code')
    for extra in ('diagram_types', 'geometry_space', 'evaluation_rubric', 'evaluation_policy', 'content_requirements'):
        with pytest.raises(TypeError):
            evaluate('target code', 'output code', **{extra: None})


def test_no_geometry_does_not_manufacture_mathematical_credit(tmp_path):
    path = tmp_path / 'empty.pdf'
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(path)
    observation = {'compile_success': True, 'pdf_path': str(path)}
    assert score(observation, observation) == {'compile': 1, 'mathematical_correctness': 0,
                                              'content_coverage': 0, 'visual_readability': 100}


@pytest.mark.parametrize('role', ['target', 'output'])
def test_probe_infrastructure_failure_is_not_a_geometry_score(tmp_path, role):
    observed = diagram(tmp_path / 'observed.pdf')
    unavailable = {**observed, 'labeled_points': {}, 'metadata': {
        'discovery': {'status': 'request_error', 'error': 'compiler connection lost'}}}
    with pytest.raises(RuntimeError, match='geometry probe unavailable'):
        score(unavailable, observed) if role == 'target' else score(observed, unavailable)
