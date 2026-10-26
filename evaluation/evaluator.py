"""Two TikZ strings in, four deterministic metric scores out."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

from evaluation.tikz_coverage import compare_content
from evaluation.tikz_geometry import compare_geometry
from evaluation.tikz_observations import compile_observe, read_scene
from evaluation.tikz_readability import inspect_readability


def _percent(checks: list[bool]) -> float:
    return 100.0 * sum(checks) / len(checks) if checks else 0.0


class EvaluationError(ValueError):
    """Unavailable measurements retain independently established scores."""

    def __init__(self, message: str, scores: dict[str, float | int | None]):
        super().__init__(message)
        self.scores = dict(scores)


class EvaluationInfrastructureError(RuntimeError):
    """Compiler failures are operational errors, with any completed scores."""

    def __init__(self, message: str, scores: dict[str, float | int | None]):
        super().__init__(message)
        self.scores = dict(scores)


def _score_observations(target: dict[str, Any], output: dict[str, Any]) -> dict[str, float | int]:
    """Score independent evidence first; reference failures cannot erase it."""
    scores = {'compile': None, 'mathematical_correctness': None, 'content_coverage': None, 'visual_readability': None}
    errors, infrastructure = [], []
    for role, observation in (('target', target), ('output', output)):
        if not observation.get('compile_success') and observation.get('compile', {}).get('outcome') in (None, 'unknown'):
            infrastructure.append(f"{role} compiler unavailable: {observation.get('compile', {}).get('diagnostic', 'no result')}")
        elif role == 'output':
            scores['compile'] = int(bool(observation.get('compile_success')))

    produced = None
    if scores['compile'] == 0:
        scores.update(mathematical_correctness=0.0, content_coverage=0.0, visual_readability=0.0)
    elif scores['compile'] == 1:
        try:
            produced = read_scene(output)
            readability = inspect_readability(produced)
            if readability['unsupported'] or any(label['status'] == 'unknown' for label in readability['labels']):
                raise ValueError('readability unavailable: unresolved PGF text-box/paint measurements')
            scores['visual_readability'] = (_percent([label['status'] == 'pass' for label in readability['labels']])
                                            if readability['labels'] else 100.0)
        except ValueError as error:
            errors.append(f'Output measurements unavailable: {error}')

    if not target.get('compile_success'):
        errors.append('target_tikz does not compile')
    elif produced is not None and not infrastructure:
        try:
            reference = read_scene(target)
            if reference['unsupported'] or reference['unresolved']:
                raise ValueError(f"Unusable reference geometry: {reference['unsupported'] or reference['unresolved']}")
            mathematics, matches = compare_geometry(reference, produced)
            scores['mathematical_correctness'] = _percent(mathematics)
            scores['content_coverage'] = _percent(compare_content(reference, produced, matches))
        except ValueError as error:
            errors.append(str(error))
    if infrastructure:
        raise EvaluationInfrastructureError('; '.join(infrastructure), scores)
    if errors:
        raise EvaluationError('; '.join(errors), scores)
    return scores


@contextmanager
def _observe_pair(target_tikz: str, output_tikz: str, *, preview: bool = False) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Keep compiled artifacts alive while scoring or building a preview."""
    if not isinstance(target_tikz, str) or not isinstance(output_tikz, str):
        raise TypeError('target_tikz and output_tikz must be strings')
    with TemporaryDirectory(prefix='tikz-evaluation-') as directory, httpx.Client(
        base_url=os.environ.get('COMPILER_URL', 'http://127.0.0.1:18080'), timeout=200, trust_env=False,
    ) as compiler:
        root = Path(directory)
        target = compile_observe(target_tikz, root / 'target', compiler, preview=preview)
        output = target if output_tikz == target_tikz else compile_observe(output_tikz, root / 'output', compiler, preview=preview)
        yield target, output


def evaluate(target_tikz: str, output_tikz: str) -> dict[str, float | int]:
    """Compare observed reference geometry; compile is 0/1, other scores are 0-100."""
    with _observe_pair(target_tikz, output_tikz) as (target, output):
        return _score_observations(target, output)
