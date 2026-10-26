"""One request in one disposable Linux sandbox. latexmk owns the TeX passes."""

import base64
import math
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .schemas import MAX_ARTIFACT_BYTES, MAX_REQUEST_BYTES, Artifact, CompileRequest, CompileResponse, Images, RenderRequest, RenderResponse, StageResult


@contextmanager
def build(request: CompileRequest) -> Iterator[tuple[CompileResponse, Path]]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "main.tex").write_bytes(request.source.encode("utf-8"))
        for name, source in request.support_files.items():
            (root / name).write_bytes(source.encode("utf-8"))
        for name, encoded in request.image_files.items():
            (root / name).write_bytes(base64.b64decode(encoded, validate=True))
        with (root / "console.log").open("wb") as console:
            try:
                result = subprocess.run(
                    ["latexmk", "-norc", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-no-shell-escape", "-no-parse-first-line", "main.tex"],
                    cwd=root, stdin=subprocess.DEVNULL, stdout=console, stderr=subprocess.STDOUT,
                    timeout=request.timeout_seconds, check=False,
                    env={**os.environ, "openin_any": "p", "openout_any": "p", "shell_escape": "f", "SOURCE_DATE_EPOCH": "0", "FORCE_SOURCE_DATE": "1"},
                )
                stage = StageResult(
                    outcome="ok" if result.returncode == 0 else "error",
                    exit_code=result.returncode,
                    failure_code="process_exit" if result.returncode != 0 else None,
                )
            except subprocess.TimeoutExpired:
                stage = StageResult(outcome="timeout", diagnostic="latexmk exceeded its deadline")
        artifacts = []
        log_path = root / "main.log"
        if not log_path.is_file():
            log_path = root / "console.log"
        with log_path.open("rb") as log:
            data = log.read(1024 * 1024)
        if not stage.success and not stage.diagnostic:
            text = data.decode("utf-8", errors="replace")
            error = re.search(r"(?m)^(?:[^\n]+:\d+: |! ).*(?:\n[ \t]*\S.*)*", text)
            if error:
                context = re.search(r"(?m)^l\.\d+[^\n]*", text[error.end():])
                stage.diagnostic = (error[0] + ("\n" + context[0] if context else ""))[:4096]
            else:
                stage.diagnostic = f"latexmk exited with status {stage.exit_code}. See result.log for details."
        artifacts.append(Artifact(name="result.log", complete=log_path.stat().st_size <= len(data), data_base64=base64.b64encode(data).decode()))
        pdf = root / "main.pdf"
        pdf_is_file = pdf.is_file() and not pdf.is_symlink()
        pdf_size = pdf.stat().st_size if pdf_is_file else 0
        if pdf_is_file and 0 < pdf_size <= MAX_ARTIFACT_BYTES - len(data):
            artifacts.append(Artifact(name="result.pdf", complete=stage.success, data_base64=base64.b64encode(pdf.read_bytes()).decode()))
        elif stage.success:
            if pdf.is_symlink():
                failure_code, diagnostic = "invalid_pdf_output", "PDF output is not a regular file"
            elif not pdf_is_file or pdf_size == 0:
                failure_code, diagnostic = "pdf_missing", "TeX succeeded without a usable PDF"
            else:
                failure_code, diagnostic = "artifact_quota", "PDF exceeds the artifact byte quota"
            stage = StageResult(
                outcome="error", exit_code=stage.exit_code,
                diagnostic=diagnostic, failure_code=failure_code,
            )
        yield CompileResponse(compile=stage, artifacts=artifacts), pdf


def rasterize(pdf: bytes | Path, images: Images, pdf_sha256: str = "") -> RenderResponse:
    import pymupdf

    artifacts = []
    page_count = None
    failure_code = None
    try:
        with (pymupdf.open(pdf) if isinstance(pdf, Path) else pymupdf.open(stream=pdf, filetype="pdf")) as document:
            page_count = document.page_count or None
            pages = list(range(1, document.page_count + 1)) if images.pages == "all" else images.pages
            if len(pages) > 32:
                failure_code = "raster_quota"
                raise ValueError("requested page count exceeds raster quota")
            if not pages or max(pages) > document.page_count:
                failure_code = "invalid_page_selection"
                raise ValueError("requested pages are outside the PDF")
            total = 0
            pixels = 0
            for number in pages:
                page = document[number - 1]
                width = math.ceil(page.rect.width * images.dpi / 72)
                height = math.ceil(page.rect.height * images.dpi / 72)
                pixels += width * height
                if width <= 0 or height <= 0 or width * height > 16_777_216 or pixels * 4 > 256 * 1024 * 1024:
                    failure_code = "raster_quota"
                    raise ValueError("raster dimensions exceed pixel quota")
                data = page.get_pixmap(dpi=images.dpi, alpha=False, colorspace=pymupdf.csRGB).tobytes(images.format)
                total += len(data)
                if total > MAX_ARTIFACT_BYTES:
                    failure_code = "artifact_quota"
                    raise ValueError("images exceed output byte quota")
                suffix = "jpg" if images.format == "jpeg" else "png"
                artifacts.append(Artifact(name=f"page-{number}.{suffix}", data_base64=base64.b64encode(data).decode()))
        stage = StageResult(outcome="ok")
    except (RuntimeError, ValueError) as error:
        stage = StageResult(
            outcome="error",
            diagnostic=str(error)[:4096],
            failure_code=failure_code or "renderer_error",
        )
    return RenderResponse(pdf_sha256=pdf_sha256, page_count=page_count, raster=stage, artifacts=artifacts)


if __name__ == "__main__":
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw.endswith(b"\n") or len(raw) > MAX_REQUEST_BYTES:
        raise SystemExit(64)
    if sys.argv[1:] == ["render"]:
        request = RenderRequest.model_validate_json(raw)
        response = rasterize(base64.b64decode(request.pdf_base64), request.images, request.pdf_sha256)
        print(response.model_dump_json(), flush=True)
    else:
        request = CompileRequest.model_validate_json(raw)
        with build(request) as (response, pdf):
            print(response.model_dump_json(), flush=True)
            if response.compile.success and request.outputs.images is not None:
                if sys.stdin.buffer.readline(2) != b"\n":
                    raise SystemExit(64)
                print(rasterize(pdf, request.outputs.images).model_dump_json(), flush=True)
