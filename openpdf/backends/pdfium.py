"""pypdfium2 backend — rendering and fast text extraction."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import pypdfium2 as pdfium
from PIL import Image

from openpdf.geometry import Rect, IRect
from openpdf.exceptions import FileDataError, PasswordError, PageNumberError
from openpdf.utils.io import pdf_to_fitz_rect, fitz_to_pdf_rect


class PdfiumBackend:
    """Wraps pypdfium2 for rendering and fast text extraction.

    All methods are static — callers pass the handle returned by open().
    """

    # ---- Lifecycle ---------------------------------------------------------

    @staticmethod
    def open(
        source: Union[str, Path, bytes, io.BytesIO],
        password: str | None = None,
    ) -> pdfium.PdfDocument:
        """Open a PDF and return a pypdfium2 PdfDocument handle."""
        try:
            kwargs = {}
            if password:
                kwargs["password"] = password
            if isinstance(source, (bytes, bytearray)):
                doc = pdfium.PdfDocument(source, **kwargs)
            elif isinstance(source, io.BytesIO):
                source.seek(0)
                doc = pdfium.PdfDocument(source.read(), **kwargs)
            else:
                doc = pdfium.PdfDocument(str(source), **kwargs)
            return doc
        except pdfium.PdfiumError as exc:
            msg = str(exc)
            if "password" in msg.lower() or "incorrect" in msg.lower():
                raise PasswordError(f"Incorrect password for PDF: {exc}") from exc
            raise FileDataError(f"Failed to open PDF with pypdfium2: {exc}") from exc
        except Exception as exc:
            raise FileDataError(f"Failed to open PDF: {exc}") from exc

    @staticmethod
    def close(handle: pdfium.PdfDocument) -> None:
        try:
            handle.close()
        except Exception:
            pass

    # ---- Document-level info -----------------------------------------------

    @staticmethod
    def page_count(handle: pdfium.PdfDocument) -> int:
        return len(handle)

    @staticmethod
    def page_size(handle: pdfium.PdfDocument, page_index: int) -> tuple[float, float]:
        """Return (width, height) in points for the given page (accounts for rotation)."""
        page = handle[page_index]
        w = page.get_width()
        h = page.get_height()
        return float(w), float(h)

    # ---- Rendering ---------------------------------------------------------

    @staticmethod
    def render_page(
        handle: pdfium.PdfDocument,
        page_index: int,
        scale: float = 1.0,
        rotation: int = 0,
        clip: Rect | None = None,
        alpha: bool = False,
        color: tuple | None = None,
    ) -> Image.Image:
        """Render a page to a PIL Image.

        clip: optional Rect in fitz coordinates (top-left origin).
        rotation: additional rotation in degrees (0, 90, 180, 270).
        """
        page = handle[page_index]
        page_w = page.get_width()
        page_h = page.get_height()

        kwargs: dict = {
            "scale": scale,
            "rotation": rotation,
        }

        if color is not None:
            kwargs["background_color"] = _rgba_to_int(*color)

        if clip is not None:
            # pdfium crop = (left, bottom, right, top) amounts to cut from each border
            # fitz clip is (x0, y0, x1, y1) top-left origin
            # Clamp to page bounds
            cx0 = max(0.0, min(clip.x0, page_w))
            cy0 = max(0.0, min(clip.y0, page_h))
            cx1 = max(0.0, min(clip.x1, page_w))
            cy1 = max(0.0, min(clip.y1, page_h))
            left = cx0
            top = cy0
            right = page_w - cx1
            bottom = page_h - cy1
            kwargs["crop"] = (left, bottom, right, top)

        bitmap = page.render(**kwargs)
        pil = bitmap.to_pil()
        if alpha and pil.mode != "RGBA":
            pil = pil.convert("RGBA")
        elif not alpha and pil.mode == "RGBA":
            pil = pil.convert("RGB")
        return pil

    @staticmethod
    def render_page_to_bytes(
        handle: pdfium.PdfDocument,
        page_index: int,
        scale: float = 1.0,
        rotation: int = 0,
        clip: Rect | None = None,
        alpha: bool = False,
        color: tuple | None = None,
        fmt: str = "PNG",
    ) -> bytes:
        pil = PdfiumBackend.render_page(
            handle, page_index, scale=scale, rotation=rotation,
            clip=clip, alpha=alpha, color=color,
        )
        buf = io.BytesIO()
        pil.save(buf, format=fmt.upper())
        return buf.getvalue()

    # ---- Fast text extraction ----------------------------------------------

    @staticmethod
    def extract_text_simple(handle: pdfium.PdfDocument, page_index: int) -> str:
        """Fast plain-text extraction using pdfium's built-in text API."""
        page = handle[page_index]
        textpage = page.get_textpage()
        return textpage.get_text_bounded()

    @staticmethod
    def extract_text_chars(
        handle: pdfium.PdfDocument, page_index: int
    ) -> list[dict]:
        """Per-character data with bounding boxes in fitz coordinates.

        Returns list of dicts:
          {"char": str, "bbox": Rect, "font_size": float}
        """
        page = handle[page_index]
        page_h = page.get_height()
        textpage = page.get_textpage()
        count = textpage.count_chars()
        result = []
        for i in range(count):
            char = textpage.get_text_bounded(i, i + 1)
            try:
                box = textpage.get_charbox(i, loose=False)
                # box is (left, bottom, right, top) in PDF coords
                left, bottom, right, top = box
                bbox = pdf_to_fitz_rect(left, bottom, right, top, page_h)
            except Exception:
                bbox = Rect()
            try:
                font_size = textpage.get_charbox(i)[3] - textpage.get_charbox(i)[1]
            except Exception:
                font_size = 0.0
            result.append({"char": char, "bbox": bbox, "font_size": abs(font_size)})
        return result

    # ---- Image enumeration (basic) -----------------------------------------

    @staticmethod
    def get_page_image_count(handle: pdfium.PdfDocument, page_index: int) -> int:
        """Return number of image objects on the page."""
        page = handle[page_index]
        count = 0
        for obj in page.get_objects():
            if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                count += 1
        return count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rgba_to_int(r: float, g: float, b: float, a: float = 1.0) -> int:
    """Convert RGBA floats [0,1] to a packed 32-bit ARGB integer for pdfium."""
    ri = int(r * 255) & 0xFF
    gi = int(g * 255) & 0xFF
    bi = int(b * 255) & 0xFF
    ai = int(a * 255) & 0xFF
    return (ai << 24) | (ri << 16) | (gi << 8) | bi
