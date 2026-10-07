"""Two TikZ strings in, four deterministic metric scores out."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

from evaluation.tikz_coverage import carrier_scene, compare_content, connections
from evaluation.tikz_geometry import compare_geometry
from evaluation.tikz_observations import compile_observe, read_scene
from evaluation.tikz_readability import inspect_readability


def _percent(checks: list[bool]) -> float:
    return 100.0 * sum(checks) / len(checks) if checks else 0.0


def _score_observations(target: dict[str, Any], output: dict[str, Any]) -> dict[str, float | int]:
    """Internal boundary for scoring the same verified compiler observations in tests."""
    for role, observation in (('target', target), ('output', output)):
        if not observation.get('compile_success') and observation.get('compile', {}).get('outcome') in (None, 'unknown'):
            raise RuntimeError(f"{role} compiler unavailable: {observation.get('compile', {}).get('diagnostic', 'no result')}")
        discovery = observation.get('metadata', {}).get('discovery', {})
        if discovery.get('status') == 'request_error':
            raise RuntimeError(f"{role} geometry probe unavailable: {discovery.get('error', 'no result')}")
    if not target.get('compile_success'):
        raise ValueError('target_tikz does not compile')
    reference = read_scene(target)
    if reference['unsupported'] or reference['unresolved']:
        raise ValueError(f"Unusable reference geometry: {reference['unsupported'] or reference['unresolved']}")
    if not output.get('compile_success'):
        return {'compile': 0, 'mathematical_correctness': 0.0, 'content_coverage': 0.0, 'visual_readability': 0.0}
    produced = read_scene(output)
    mathematics, circle_matches = compare_geometry(reference, produced)
    content = compare_content(reference, produced, circle_matches)
    readability = inspect_readability(carrier_scene(produced, connections(reference)))
    return {'compile': 1, 'mathematical_correctness': _percent(mathematics), 'content_coverage': _percent(content),
            'visual_readability': _percent([label['status'] == 'pass' for label in readability['labels']])
            if readability['labels'] else 100.0}


@contextmanager
def _observe_pair(target_tikz: str, output_tikz: str) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Keep compiled artifacts alive while scoring or building a preview."""
    if not isinstance(target_tikz, str) or not isinstance(output_tikz, str):
        raise TypeError('target_tikz and output_tikz must be strings')
    with TemporaryDirectory(prefix='tikz-evaluation-') as directory, httpx.Client(
        base_url=os.environ.get('COMPILER_URL', 'http://127.0.0.1:18080'), timeout=200, trust_env=False,
    ) as compiler:
        root = Path(directory)
        target = compile_observe(target_tikz, root / 'target', compiler)
        output = target if output_tikz == target_tikz else compile_observe(output_tikz, root / 'output', compiler)
        yield target, output


def evaluate(target_tikz: str, output_tikz: str) -> dict[str, float | int]:
    """Compare observed reference geometry; compile is 0/1, other scores are 0-100."""
    with _observe_pair(target_tikz, output_tikz) as (target, output):
        return _score_observations(target, output)
