"""A self-contained target/output preview, independent of scoring policy."""
from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any


def write_preview(target: dict[str, Any], output: dict[str, Any], scores: dict[str, float | int], path: Path) -> Path:
    """Embed the existing PNGs before temporary compiler artifacts are cleaned up."""
    panels = []
    for title, observation in (('Target', target), ('Output', output)):
        image_path = observation.get('image_path')
        if image_path:
            image = base64.b64encode(Path(image_path).read_bytes()).decode('ascii')
            render = f'<img src="data:image/png;base64,{image}" alt="{title} diagram">'
        else:
            diagnostic = observation.get('compile', {}).get('diagnostic') or 'Render unavailable.'
            render = f'<p>{html.escape(diagnostic)}</p>'
        code = html.escape(observation.get('tikz', ''))
        panels.append(f'<section><h2>{title}</h2>{render}<details><summary>{title} TikZ</summary>'
                      f'<pre><code>{code}</code></pre></details></section>')
    rows = []
    for name, score in scores.items():
        value = str(score) if name == 'compile' else f'{score:.2f}%'
        rows.append(f'<tr><th scope="row">{html.escape(name.replace("_", " ").capitalize())}</th><td>{value}</td></tr>')
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikZ comparison</title>
<style>
:root {{ color-scheme: light; font: 16px/1.5 system-ui, sans-serif; }}
body {{ max-width: 1100px; margin: auto; padding: 1rem; }}
.diagrams {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); gap: 1rem; }}
section {{ min-width: 0; }}
img {{ display: block; max-width: 100%; height: auto; }}
pre {{ overflow: auto; max-height: 24rem; padding: .8rem; background: #f3f5f8; }}
th, td {{ text-align: left; padding: .25rem .75rem .25rem 0; }}
</style></head><body><main>
<h1>TikZ comparison</h1>
<table><caption>Output scores against the target</caption><tbody>{''.join(rows)}</tbody></table>
<div class="diagrams">{''.join(panels)}</div>
</main></body></html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding='utf-8')
    return path
