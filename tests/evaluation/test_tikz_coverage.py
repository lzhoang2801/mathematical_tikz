"""Coverage measures named objects and styles independently of proportions."""
import pytest
from shapely.geometry import LineString

from evaluation.tikz_coverage import compare_content, connections


def scene(points, edges):
    return {'points': points, 'strokes': [
        {'path': i, 'geometry': LineString(edge[:2]), 'components': [LineString(edge[:2])],
         'dashed': edge[2] if len(edge) == 3 else False, 'width': 1}
        for i, edge in enumerate(edges)], 'unsupported': []}


def triangle(points):
    return scene(points, [(points[a], points[b]) for a, b in (('A', 'B'), ('B', 'C'), ('C', 'A'))])


def test_different_shapes_have_the_same_point_connection_coverage():
    target = triangle({'A': (0, 0), 'B': (100, 0), 'C': (0, 60)})
    output = triangle({'A': (20, 20), 'B': (170, 20), 'C': (70, 90)})
    assert compare_content(target, output, []) == [True] * 6


def test_interior_point_does_not_duplicate_a_long_connection():
    target = scene({'A': (0, 0), 'B': (100, 0), 'C': (50, 0)}, [((0, 0), (100, 0))])
    output = scene({'A': (0, 0), 'B': (100, 0), 'C': (50, 90)}, [((0, 0), (100, 0))])
    assert len(connections(target)) == 1
    assert compare_content(target, output, []) == [True] * 4


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'dash'])
def test_missing_extra_and_wrong_style_connections_fail(mutation):
    points = {'A': (0, 0), 'B': (100, 0), 'C': (50, 80), 'D': (150, 80)}
    edges = [(points['A'], points['B']), (points['B'], points['C'])]
    changed = list(edges)
    if mutation == 'missing':
        changed.pop()
    elif mutation == 'extra':
        changed.append((points['C'], points['D']))
    else:
        changed[0] = (*changed[0], True)
    checks = compare_content(scene(points, edges), scene(points, changed), [])
    assert checks.count(False) == 1
    assert len(checks) == (7 if mutation == 'extra' else 6)


def test_split_or_repeated_lines_do_not_change_target_or_output_units():
    points = {'A': (0, 0), 'B': (100, 0), 'M': (50, 0)}
    whole = scene(points, [((0, 0), (100, 0))])
    split = scene(points, [((0, 0), (50, 0)), ((50, 0), (100, 0)), ((0, 0), (50, 0))])
    for target, output in ((whole, split), (split, whole)):
        assert compare_content(target, output, []) == [True] * 4


def test_short_required_edge_cannot_disappear_in_a_length_average():
    points = {'A': (0, 0), 'B': (100, 0), 'C': (0, 10), 'D': (0.1, 10)}
    target = scene(points, [((0, 0), (100, 0)), ((0, 10), (0.1, 10))])
    output = scene(points, [((0, 0), (100, 0))])
    assert compare_content(target, output, []).count(False) == 1


def test_text_rules_do_not_create_geometry_requirements():
    points = {'A': (0, 0), 'B': (100, 0)}
    target = scene(points, [((0, 0), (100, 0)), ((40, 30), (45, 30))])
    output = scene(points, [((0, 0), (100, 0))])
    assert compare_content(target, output, []) == [True] * 3


def test_missing_unresolved_and_extra_point_identities_keep_the_denominator():
    target = triangle({'A': (0, 0), 'B': (100, 0), 'C': (50, 80)})
    output = triangle(dict(target['points']))
    output['points']['C'] = None
    checks = compare_content(target, output, [])
    assert len(checks) == 6 and sum(checks) == 3
    output['points'].pop('C')
    assert compare_content(target, output, []) == checks
    output['points']['X'] = (400, 400)
    checks = compare_content(target, output, [])
    assert len(checks) == 7 and sum(checks) == 3
