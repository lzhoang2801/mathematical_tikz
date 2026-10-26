"""Score notebook prediction JSONL with the existing two-string TikZ evaluator."""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable
import json
from pathlib import Path

from evaluation.evaluator import EvaluationError, EvaluationInfrastructureError, evaluate

METRICS = ('compile', 'mathematical_correctness', 'content_coverage', 'visual_readability')


def _aggregate(rows: list[dict]) -> dict:
    scored = [row['scores'] for row in rows if row['status'] == 'scored']
    values = {metric: [row['scores'][metric] for row in rows
                       if row.get('scores') and row['scores'].get(metric) is not None] for metric in METRICS}
    return {
        'rows': len(rows),
        'scored': len(scored),
        'errors': dict(Counter(row['status'] for row in rows if row['status'] != 'scored')),
        'scored_by_metric': {metric: len(items) for metric, items in values.items()},
        'mean_scores': {
            metric: sum(values[metric]) / len(values[metric]) if values[metric] else None
            for metric in METRICS
        },
    }


def evaluate_file(predictions: Path, results: Path, *, evaluator: Callable[[str, str], dict] | None = None) -> dict:
    """Keep every row, flush results incrementally, and stop on unavailable infrastructure."""
    evaluate_pair = evaluate if evaluator is None else evaluator
    predictions, results = Path(predictions), Path(results)
    summary_path = results.with_suffix('.summary.json')
    if len({path.resolve() for path in (predictions, results, summary_path)}) != 3:
        raise ValueError('Predictions, results and summary must be different files')
    if results.exists() or summary_path.exists():
        raise FileExistsError('Choose a new results path; existing evaluation files are preserved')
    lines = [
        (number, line) for number, line in enumerate(
            predictions.read_text(encoding='utf-8-sig').splitlines(), 1
        ) if line.strip()
    ]
    if not lines:
        raise ValueError('The predictions file contains no rows')
    results.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with results.open('x', encoding='utf-8', newline='\n') as stream:
        try:
            for number, line in lines:
                record = {'line': number, 'task': 'unknown'}
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError('Each prediction must be a JSON object')
                    if row.get('task') not in ('reconstruct', 'generate', 'edit'):
                        raise ValueError('task must be reconstruct, generate or edit')
                    record.update({name: row.get(name) for name in ('task', 'split', 'row_index', 'id')})
                    if not all(isinstance(row.get(name), str) for name in ('target_tikz', 'output_tikz')):
                        raise ValueError('target_tikz and output_tikz must be strings')
                except ValueError as error:
                    record.update(status='invalid_record', error=str(error), scores=None)
                else:
                    try:
                        scores = evaluate_pair(row['target_tikz'], row['output_tikz'])
                    except EvaluationInfrastructureError as error:
                        record.update(status='infrastructure_error', error=str(error), scores=error.scores)
                    except EvaluationError as error:
                        record.update(status='evaluation_error', error=str(error), scores=error.scores)
                    except ValueError as error:
                        record.update(status='evaluation_error', error=str(error), scores=None)
                    except RuntimeError as error:
                        record.update(status='infrastructure_error', error=str(error), scores=None)
                    else:
                        record.update(status='scored', scores=scores)
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                records.append(record)
                if record['status'] == 'infrastructure_error':
                    break
        finally:
            summary = {
                'status': 'incomplete' if len(records) != len(lines) else (
                    'completed_with_errors' if any(row['status'] != 'scored' for row in records)
                    else 'completed'
                ),
                'predictions': len(lines),
                'processed': len(records),
                'pending': len(lines) - len(records),
                'overall': _aggregate(records),
                'by_task': {
                    task: _aggregate([row for row in records if row['task'] == task])
                    for task in sorted({row['task'] for row in records})
                },
            }
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + '\n',
                encoding='utf-8',
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True, help='Colab prediction JSONL')
    parser.add_argument('--results', type=Path, required=True, help='New per-row score JSONL')
    args = parser.parse_args()
    summary = evaluate_file(args.predictions, args.results)
    print(json.dumps(summary, allow_nan=False, indent=2))
    if summary['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
