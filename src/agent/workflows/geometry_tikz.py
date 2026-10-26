"""Reconstruct TikZ only from source regions detected by document parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from langgraph.graph.state import CompiledStateGraph

from agent.prompts.geometry_tikz import geometry_generation_messages
from agent.schemas.tikz import TikzResult
from agent.utils.media import image_content_block
from agent.workflows.tikz import (
    Context,
    draw_tikz,
)


def geometry_region_to_tikz(
    *,
    image_path: str | Path,
    artifact_dir: str | Path,
    agent: CompiledStateGraph[Any, Context, Any, Any],
    compiler_http: httpx.Client | None = None,
) -> TikzResult:
    """Reconstruct one required source geometry crop as compile-valid TikZ."""
    source_image = Path(image_path).resolve()
    if not source_image.is_file():
        raise FileNotFoundError(f"Geometry source image does not exist: {source_image}")

    destination = Path(artifact_dir).resolve()
    source_content = image_content_block(source_image)
    initial_messages = geometry_generation_messages(source_content)
    result = draw_tikz(
        messages=initial_messages,
        artifact_dir=destination,
        agent=agent,
        compiler_http=compiler_http,
    )

    return result
