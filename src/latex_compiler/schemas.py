"""Compiler-owned HTTP contract. No application identity or filesystem paths."""

import base64
import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 46 * 1024 * 1024
MAX_RESPONSE_BYTES = 46 * 1024 * 1024


class Images(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["png", "jpeg"] = "png"
    pages: list[int] | Literal["all"] = Field(default_factory=lambda: [1])
    dpi: int = Field(default=200, ge=72, le=300)

    @field_validator("pages")
    @classmethod
    def valid_pages(cls, value):
        if value != "all" and (not value or len(value) > 32 or len(set(value)) != len(value) or min(value) < 1):
            raise ValueError("request 1 to 32 distinct pages, numbered from 1")
        return value


class Outputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pdf: bool = True
    images: Images | None = None


class CompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1)
    support_files: dict[str, str] = Field(default_factory=dict)
    image_files: dict[str, str] = Field(default_factory=dict)
    outputs: Outputs = Field(default_factory=Outputs)
    timeout_seconds: int = Field(default=90, ge=1, le=90)

    @model_validator(mode="after")
    def validate_resources(self):
        if not self.source.strip() or len(self.source.encode("utf-8")) > 2 * 1024 * 1024:
            raise ValueError("source must contain 1 to 2097152 UTF-8 bytes")
        if len(self.support_files) > 32 or sum(len(v.encode("utf-8")) for v in self.support_files.values()) > 4 * 1024 * 1024:
            raise ValueError("support files exceed their count or byte limit")
        for name in self.support_files:
            if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,100}\.(tex|sty|cls|bib)", name) or ".." in name or name.casefold() == "main.tex":
                raise ValueError("support files must be plain text filenames, excluding main.tex")
        if len({n.casefold() for n in self.support_files}) != len(self.support_files):
            raise ValueError("support filenames must be distinct ignoring case")
        if len(self.image_files) > 32:
            raise ValueError("use at most 32 input images")
        total = 0
        for name, encoded in self.image_files.items():
            if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,100}\.png", name) or ".." in name:
                raise ValueError("input images must have plain PNG filenames")
            data = base64.b64decode(encoded, validate=True)
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("input images must contain PNG bytes")
            total += len(data)
        if total > 24 * 1024 * 1024:
            raise ValueError("input images exceed their byte limit")
        if len({name.casefold() for name in self.image_files}) != len(self.image_files):
            raise ValueError("input image names must be distinct ignoring case")
        return self

    def digest(self, toolchain_id: str) -> str:
        payload = {"main.tex": self.source, "support_files": self.support_files, "toolchain_id": toolchain_id, "image_files": {name: hashlib.sha256(base64.b64decode(data, validate=True)).hexdigest() for name, data in self.image_files.items()}}
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pdf_base64: str = Field(max_length=45 * 1024 * 1024)
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    images: Images = Field(default_factory=Images)

    @model_validator(mode="after")
    def validate_pdf(self):
        data = base64.b64decode(self.pdf_base64, validate=True)
        if not data or len(data) > MAX_ARTIFACT_BYTES or hashlib.sha256(data).hexdigest() != self.pdf_sha256:
            raise ValueError("PDF size or digest is invalid")
        return self


class StageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["ok", "error", "timeout", "unknown", "not_requested", "not_run"]
    exit_code: int | None = None
    diagnostic: str = Field(default="", max_length=4096)
    failure_code: Literal[
        "process_exit",
        "pdf_missing",
        "invalid_pdf_output",
        "artifact_quota",
        "invalid_page_selection",
        "raster_quota",
        "renderer_error",
    ] | None = None

    @property
    def success(self) -> bool:
        return self.outcome == "ok"


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=r"^(result\.(pdf|log)|page-[0-9]+\.(png|jpg))$")
    complete: bool = True
    data_base64: str = Field(max_length=45 * 1024 * 1024)

    @property
    def data(self) -> bytes:
        return base64.b64decode(self.data_base64, validate=True)


class CompileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_digest: str = ""
    toolchain_id: str = ""
    page_count: int | None = Field(default=None, ge=1)
    compile: StageResult
    raster: StageResult = Field(default_factory=lambda: StageResult(outcome="not_requested"))
    artifacts: list[Artifact] = Field(default_factory=list, max_length=34)


class RenderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pdf_sha256: str
    page_count: int | None = Field(default=None, ge=1)
    raster: StageResult
    artifacts: list[Artifact] = Field(default_factory=list, max_length=32)
