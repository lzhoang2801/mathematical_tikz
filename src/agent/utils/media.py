"""Convert PDF and image data for multimodal model inputs."""

from __future__ import annotations

import base64
from pathlib import Path

import pymupdf

DEFAULT_PDF_RENDER_DPI = 200


def render_pdf_pages(
    pdf: bytes | str | Path,
    *,
    dpi: int = DEFAULT_PDF_RENDER_DPI,
    max_output_bytes: int | None = None,
    max_page_pixels: int | None = None,
) -> dict[int, bytes]:
    """Render every PDF page to PNG bytes without creating output files."""
    # PyMuPDF does not annotate Document construction or Pixmap.tobytes.
    document = (
        pymupdf.open(stream=pdf, filetype="pdf")  # type: ignore[no-untyped-call]
        if isinstance(pdf, bytes)
        else pymupdf.open(Path(pdf).resolve())  # type: ignore[no-untyped-call]
    )
    with document:
        pages: dict[int, bytes] = {}
        total = 0
        for index in range(document.page_count):
            if max_page_pixels is not None and (
                (document[index].rect.width * dpi / 72)
                * (document[index].rect.height * dpi / 72)
                > max_page_pixels
            ):
                raise ValueError("PDF page exceeds the raster pixel budget.")
            rendered = document[index].get_pixmap(dpi=dpi, alpha=False).tobytes("png")
            total += len(rendered)
            if max_output_bytes is not None and total > max_output_bytes:
                raise ValueError("Rendered PDF exceeds the image byte budget.")
            pages[index] = rendered
    if not pages:
        raise ValueError("PDF rendered no pages.")
    return pages


def image_content_block(image: bytes | Path) -> dict[str, object]:
    """Encode rendered PNG bytes or a PNG/JPEG file for a multimodal request."""
    if isinstance(image, Path):
        content = image.read_bytes()
        suffix = image.suffix.lower()
        if suffix == ".png":
            mime = "image/png"
        elif suffix in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        else:
            raise ValueError("Image paths must use .png, .jpg, or .jpeg.")
    else:
        content = image
        mime = "image/png"
    encoded = base64.b64encode(content).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{encoded}"},
    }
