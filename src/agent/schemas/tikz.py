"""Drawing completion and application result contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_TIKZ_MAX_MODEL_CALLS = 16


class TikzCompletion(BaseModel):
    """Report whether the last observed drawing satisfies its instruction."""

    model_config = ConfigDict(extra="forbid")

    incomplete_reason: str | None = Field(min_length=1)


class TikzResult(BaseModel):
    """Expose the native drawing outcome to application callers."""

    success: bool
    status: Literal["accepted", "usable_with_issues", "failed"]
    usable: bool
    tikz: str
    rendered_png_path: str | None = None
    unresolved_issues: list[str] = Field(default_factory=list)
