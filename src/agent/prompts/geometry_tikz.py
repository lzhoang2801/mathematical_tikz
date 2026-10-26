"""Prompts for source-region to TikZ reconstruction."""

from __future__ import annotations

from typing import Any

from agent.prompts.tikz import TIKZ_INSTRUCTION

GEOMETRY_TIKZ_PROMPT_VERSION = "geometry_tikz:v0.9"


def geometry_generation_messages(source_image: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the image-only source reconstruction request."""
    parts: list[dict[str, Any]] = [
        {"type": "text", "text": "Reconstruct the diagram in this source image, preserving its visible objects, relations, labels and measurements."},
        source_image,
    ]
    return [
        {
            "role": "system",
            "content": TIKZ_INSTRUCTION,
        },
        {"role": "user", "content": parts},
    ]
