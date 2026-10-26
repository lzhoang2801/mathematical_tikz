"""Two synchronous HTTPX calls. Callers own clients, retries and persistence."""

import httpx

from .schemas import MAX_ARTIFACT_BYTES, MAX_RESPONSE_BYTES, CompileRequest, CompileResponse, RenderRequest, RenderResponse


def compile(http: httpx.Client, request: CompileRequest) -> CompileResponse:
    """Build exactly this source over HTTP; never run a local compiler."""
    reply = _post(http, "/compile", request, CompileResponse, request.timeout_seconds + 60)
    if not reply.toolchain_id or reply.source_digest != request.digest(reply.toolchain_id):
        raise ValueError("compiler response does not match the source/resources/toolchain")
    pdf = next((a for a in reply.artifacts if a.name == "result.pdf"), None)
    needs_pdf = request.outputs.pdf or request.outputs.images is not None and not reply.raster.success
    if reply.compile.success and (reply.compile.exit_code != 0 or needs_pdf and (pdf is None or not pdf.complete)):
        raise ValueError("successful compile omitted its complete PDF")
    if reply.raster.success:
        if not reply.compile.success or request.outputs.images is None:
            raise ValueError("unexpected raster success")
        _check_images(reply, request.outputs.images)
    return reply


def render_pdf(http: httpx.Client, request: RenderRequest) -> RenderResponse:
    """Rasterize an existing PDF without invoking TeX."""
    reply = _post(http, "/render", request, RenderResponse, 45)
    if reply.pdf_sha256 != request.pdf_sha256:
        raise ValueError("renderer response does not match the input PDF")
    if reply.raster.success:
        _check_images(reply, request.images)
    return reply


def _check_images(reply, images):
    if reply.page_count is None:
        raise ValueError("successful raster omitted its page count")
    pages = range(1, reply.page_count + 1) if images.pages == "all" else images.pages
    suffix = "jpg" if images.format == "jpeg" else "png"
    actual = {a.name for a in reply.artifacts if a.name.startswith("page-") and a.complete}
    if actual != {f"page-{page}.{suffix}" for page in pages}:
        raise ValueError("raster images do not match the requested pages and format")


def _post(http, path, request, schema, timeout):
    with http.stream("POST", path, json=request.model_dump(), timeout=httpx.Timeout(timeout, connect=3, pool=3)) as response:
        response.raise_for_status()
        body = bytearray()
        for chunk in response.iter_bytes():
            if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                raise ValueError("compiler response exceeds its byte limit")
            body.extend(chunk)
    reply = schema.model_validate_json(body)
    if len({a.name for a in reply.artifacts}) != len(reply.artifacts) or sum(len(a.data) for a in reply.artifacts) > MAX_ARTIFACT_BYTES:
        raise ValueError("compiler artifacts exceed quota or repeat names")
    return reply
