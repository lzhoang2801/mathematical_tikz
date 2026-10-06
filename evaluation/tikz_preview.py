"""Write a self-contained, human-reviewable preview of TikZ evaluation rows."""

from __future__ import annotations

import html
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

_IMAGE_KEYS = (
    "image_path",
    "source_image_path",
    "crop_image_path",
    "crop_path",
    "image",
    "crop",
    "path",
)
_IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
_GAP_KEYS = {"error", "errors", "gap", "gaps", "unknown", "unknowns", "unresolved", "unsupported"}


def write_preview(rows: list[dict[str, Any]], run_dir: Path) -> Path:
    """Write `preview.html` for manual inspection; judgments remain unapproved."""
    destination = Path(run_dir)
    destination.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(_render_row(row, destination) for row in rows)
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikZ evaluation review</title>
<style>
:root {{ color-scheme: light; font: 16px/1.5 system-ui, sans-serif; }}
body {{ margin: 0 auto; max-width: 1100px; padding: 1rem; color: #182230; }}
header {{ position: sticky; top: 0; z-index: 2; padding: .8rem; background: #fff; border-bottom: 1px solid #bbc5d1; }}
.pending {{ padding: .7rem; background: #fff3cd; border: 1px solid #e2c35b; }}
.filters {{ display: flex; gap: .8rem; align-items: center; flex-wrap: wrap; }}
article {{ margin: 1rem 0; padding: 1rem; border: 1px solid #bbc5d1; border-radius: .5rem; }}
article[hidden] {{ display: none; }}
h2 {{ margin-top: 0; }}
h3 {{ margin-bottom: .3rem; }}
details {{ margin: .6rem 0; border-top: 1px solid #d8dee7; padding-top: .5rem; }}
summary {{ cursor: pointer; font-weight: 650; }}
pre {{ overflow: auto; max-height: 34rem; padding: .8rem; background: #f3f5f8; white-space: pre-wrap; overflow-wrap: anywhere; }}
pre.code {{ white-space: pre; }}
figure {{ display: inline-block; max-width: min(100%, 680px); margin: .5rem 1rem .5rem 0; vertical-align: top; }}
.images {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1rem; align-items: start; }}
.images figure {{ margin: 0; }}
img {{ display: block; max-width: 100%; height: auto; border: 1px solid #bbc5d1; }}
figcaption {{ overflow-wrap: anywhere; }}
small {{ color: #485465; }}
</style>
</head>
<body>
<header>
  <h1>TikZ evaluation review</h1>
  <p class="pending"><strong>Human review pending.</strong> This preview displays evidence and evaluator predictions only; it does not compute an aggregate score or approve any candidate.</p>
  <div class="filters">
    <label for="task-filter">Task</label>
    <select id="task-filter">
      <option value="all">All tasks</option>
      <option value="Generate">Generate</option>
      <option value="Reconstruct">Reconstruct</option>
      <option value="Edit">Edit</option>
    </select>
    <span id="visible-count" aria-live="polite"></span>
  </div>
</header>
<main>
{cards}
</main>
<script>
const filter = document.getElementById('task-filter');
const cards = [...document.querySelectorAll('article[data-task]')];
const count = document.getElementById('visible-count');
function applyFilter() {{
  let visible = 0;
  for (const card of cards) {{
    const shown = filter.value === 'all' || card.dataset.task === filter.value;
    card.hidden = !shown;
    if (shown) visible += 1;
  }}
  count.textContent = `${{visible}} candidate${{visible === 1 ? '' : 's'}} shown`;
}}
filter.addEventListener('change', applyFilter);
applyFilter();
</script>
</body>
</html>
"""
    preview_path = destination / "preview.html"
    preview_path.write_text(document, encoding="utf-8")
    return preview_path


def _render_row(row: Mapping[str, Any], run_dir: Path) -> str:
    candidate = _mapping(row.get("candidate"))
    candidate_id = candidate.get("id", "unknown candidate")
    task = candidate.get("task", "Unknown")
    task_name = str(task)
    title = f"{candidate_id} â€” {task_name}"
    source = row.get("source")
    target = _mapping(row.get("target"))
    current = _mapping(row.get("current"))
    output = _mapping(row.get("output"))
    worker = _mapping(row.get("worker"))
    source_image_path = _source_image_path(source)
    if source_image_path is None:
        source_image_path = candidate.get("image_path")

    source_image = _image_figure("Source crop", source_image_path, run_dir)
    displayed_source_image = (
        _asset_src(str(source_image_path), run_dir) if source_image_path else None
    )
    target_image = _image_figure("Target render", target.get("image_path"), run_dir)
    current_image = _image_figure("Current diagram (Edit input)", current.get("image_path"), run_dir) if task_name == "Edit" else ""
    output_image_path = output.get("image_path") or worker.get("image_path") or worker.get("rendered_png_path")
    output_image = _image_figure("Output render", output_image_path, run_dir)

    code_sections = [
        _code_details("Target TikZ", candidate.get("target_tikz")),
        _code_details("Current TikZ (Edit input)", candidate.get("current_tikz")),
        _code_details(
            "Output TikZ",
            _find_text(output, "tikz")
            or _find_text(worker, "tikz")
            or _find_text(worker, "output_tikz"),
        ),
    ]
    provenance = {
        "source_pack": source,
        "candidate_image_path": candidate.get("image_path"),
        "displayed_source_image": displayed_source_image,
    }
    body = [
        _json_details("Row error", row.get("error")) if row.get("error") else "",
        f"<p>{html.escape(str(candidate.get('instruction', '')))}</p>",
        f"<p><strong>Variant:</strong> {html.escape(str(candidate['variant']))}</p>" if candidate.get("variant") else "",
        '<div class="images">' + (source_image if source_image_path else "") + current_image + target_image + output_image + '</div>',
        _json_details("Givens and scope", {"givens": candidate.get("givens"), "scope_decisions": candidate.get("scope_decisions")}),
        _json_details("Source provenance", provenance),
        _json_details("Evaluation rubric", candidate.get("evaluation_rubric")),
        *code_sections,
        _render_evaluation("Target evaluation evidence", target),
        _render_evaluation("Output evaluation evidence", output),
        _json_details("Worker result and errors", worker),
    ]
    source_group = candidate.get("source_group")
    grade = candidate.get("grade")
    meta = " Â· ".join(
        html.escape(str(value))
        for value in (task_name, source_group, f"Grade {grade}" if grade is not None else None)
        if value not in (None, "")
    )
    return (
        f'<article data-task="{html.escape(task_name, quote=True)}">'
        f"<h2>{html.escape(str(title))}</h2>"
        f"<p><small>{meta}</small> Â· <strong>Human review pending</strong></p>"
        + "\n".join(section for section in body if section)
        + "</article>"
    )


def _render_evaluation(title: str, evaluation: Mapping[str, Any]) -> str:
    if "pair_comparison" in evaluation:
        comparison = evaluation["pair_comparison"]
        rows = "".join(f"<tr><td>{html.escape(name)}</td><td><strong>{html.escape(check['status'])}</strong></td></tr>" for name, check in comparison.get("checks", {}).items())
        return (f"<section><h3>Reference comparison: {html.escape(comparison['status'])}</h3>"
                "<p>Reference fidelity only. The reference's correctness against the instruction is not evaluated here.</p>"
                f"<table><thead><tr><th>Check</th><th>Observation</th></tr></thead><tbody>{rows}</tbody></table>"
                + _json_details("Measurements, correspondence, tolerances and limitations", comparison) + "</section>")
    if not evaluation:
        return _json_details(title, "No evaluator result recorded.")
    visible = {
        key: evaluation.get(key)
        for key in ("compiler", "checks", "perception", "jev", "criterion_results", "limitations", "render_equivalence")
        if key in evaluation
    }
    gaps = _collect_gaps(evaluation)
    jev = _mapping(evaluation.get("jev"))
    jev_criteria = _mapping(jev.get("criteria"))
    insufficient = [
        criterion_id
        for criterion_id, result in jev_criteria.items()
        if _mapping(result).get("choice") == "insufficient_evidence"
    ]
    if insufficient:
        gaps["jev.insufficient_evidence"] = insufficient
    return (
        f"<section><h3>{html.escape(title)}</h3>"
        + _json_details("Compiler observations, executable checks, perception and full Jev distributions", visible)
        + _json_details("Gaps and errors", gaps or "None recorded; this does not imply a pass.")
        + "</section>"
    )


def _json_details(title: str, value: Any) -> str:
    if value is None:
        value = "Not recorded."
    rendered = json.dumps(value, ensure_ascii=False, indent=2, default=_json_default)
    return (
        "<details><summary>"
        f"{html.escape(title)}"
        "</summary><pre>"
        f"{html.escape(rendered)}"
        "</pre></details>"
    )


def _code_details(title: str, code: Any) -> str:
    if not isinstance(code, str) or not code:
        return _json_details(title, "No code artifact recorded.")
    return (
        "<details><summary>"
        f"{html.escape(title)}"
        "</summary><pre class=\"code\">"
        f"{html.escape(code)}"
        "</pre></details>"
    )


def _image_figure(title: str, path: Any, run_dir: Path) -> str:
    if not path:
        return f"<p><small>{html.escape(title)}: no image recorded.</small></p>"
    raw_path = str(path)
    src = _asset_src(raw_path, run_dir)
    if src is None:
        return (
            "<p><small>"
            f"{html.escape(title)} unavailable at {html.escape(raw_path)}"
            "</small></p>"
        )
    return (
        "<figure><figcaption>"
        f"{html.escape(title)}"
        "</figcaption><img loading=\"lazy\" src=\""
        f"{html.escape(src, quote=True)}"
        "\" alt=\""
        f"{html.escape(title, quote=True)}"
        "\"></figure>"
    )


def _asset_src(raw_path: str, run_dir: Path) -> str | None:
    if raw_path.startswith("data:image/"):
        return raw_path
    path = Path(raw_path).expanduser()
    candidates = [path] if path.is_absolute() else [run_dir / path, Path.cwd() / path]
    existing = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
    if existing is None:
        return None
    try:
        relative = os.path.relpath(existing, run_dir.resolve()).replace(os.sep, "/")
        return quote(relative, safe="/.:_-~")
    except ValueError:
        return existing.as_uri()


def _source_image_path(source: Any) -> Any:
    if isinstance(source, Mapping):
        for key in _IMAGE_KEYS:
            if key in source:
                found = _image_value(source[key], named=key != "path")
                if found is not None:
                    return found
        for value in source.values():
            found = _source_image_path(value)
            if found is not None:
                return found
    elif isinstance(source, (list, tuple)):
        for value in source:
            found = _source_image_path(value)
            if found is not None:
                return found
    return None


def _image_value(value: Any, *, named: bool) -> Any:
    if isinstance(value, str):
        if value.startswith("data:image/") or named or Path(value).suffix.lower() in _IMAGE_SUFFIXES:
            return value
    elif isinstance(value, (Mapping, list, tuple)):
        return _source_image_path(value)
    return None


def _find_text(value: Any, key: str) -> str | None:
    if isinstance(value, Mapping):
        candidate = value.get(key)
        if isinstance(candidate, str):
            return candidate
        for nested in value.values():
            found = _find_text(nested, key)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for nested in value:
            found = _find_text(nested, key)
            if found is not None:
                return found
    return None


def _collect_gaps(value: Any, path: str = "") -> dict[str, Any]:
    gaps: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in _GAP_KEYS and nested not in (None, [], {}):
                gaps[nested_path] = nested
            else:
                gaps.update(_collect_gaps(nested, nested_path))
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            gaps.update(_collect_gaps(nested, f"{path}[{index}]"))
    return gaps


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)
