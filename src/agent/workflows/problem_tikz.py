"""Supply explicit drawing inputs to the TikZ harness."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
from langgraph.graph.state import CompiledStateGraph

from agent.prompts.problem_tikz import problem_tikz_messages
from agent.schemas.tikz import TikzResult
from agent.utils.media import image_content_block
from agent.workflows.tikz import (
    Context,
    draw_tikz,
)


def problem_tikz(
    *,
    instruction: str,
    source_statement: str | None = None,
    current_tikz: str | None = None,
    reference_images: Sequence[bytes | Path] = (),
    artifact_dir: str | Path,
    agent: CompiledStateGraph[Any, Context, Any, Any],
    compiler_http: httpx.Client | None = None,
) -> TikzResult:
    """Draw from explicit inputs without retaining context between invocations."""
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("instruction must be a nonblank string.")
    prior_tikz = current_tikz.strip() if current_tikz and current_tikz.strip() else None
    normalized_instruction = instruction.strip()
    images = [image_content_block(path) for path in reference_images]
    messages = problem_tikz_messages(
        instruction=normalized_instruction,
        source_statement=source_statement,
        current_tikz=prior_tikz,
        reference_images=images,
    )
    return draw_tikz(
        messages=messages,
        artifact_dir=artifact_dir,
        agent=agent,
        compiler_http=compiler_http,
    )
