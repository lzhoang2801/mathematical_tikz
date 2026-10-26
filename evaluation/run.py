"""Evaluate a target/output TikZ file pair and print four scores as JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.evaluator import EvaluationError, EvaluationInfrastructureError, _observe_pair, _score_observations, evaluate
from evaluation.tikz_preview import write_preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True, help='Reference TikZ file')
    parser.add_argument('--output', type=Path, required=True, help='Produced TikZ file')
    parser.add_argument('--preview', type=Path, help='Save a self-contained target/output HTML preview')
    args = parser.parse_args()
    if args.preview and args.preview.resolve() in {args.target.resolve(), args.output.resolve()}:
        parser.error('--preview must not overwrite either TikZ input')
    target_tikz, output_tikz = args.target.read_text(encoding='utf-8'), args.output.read_text(encoding='utf-8')
    error = None
    if args.preview:
        with _observe_pair(target_tikz, output_tikz, preview=True) as (target, output):
            try:
                scores = _score_observations(target, output)
            except (EvaluationError, EvaluationInfrastructureError) as failure:
                scores, error = failure.scores, str(failure)
            write_preview({**target, 'tikz': target_tikz}, {**output, 'tikz': output_tikz}, scores, args.preview, error=error)
    else:
        try:
            scores = evaluate(target_tikz, output_tikz)
        except (EvaluationError, EvaluationInfrastructureError) as failure:
            scores, error = failure.scores, str(failure)
    print(json.dumps(scores if error is None else {'scores': scores, 'error': error}, allow_nan=False))
    if error is not None:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
