"""OpenPDF — A commercially-free alternative to PyMuPDF.

Usage:
    import openpdf

    doc = openpdf.open("input.pdf")
    page = doc[0]
    text = page.get_text()
    pix = page.get_pixmap(dpi=150)
    pix.save("page0.png")
    doc.close()

Drop-in replacement:
    import openpdf as fitz    # most existing fitz code works unchanged
"""

from openpdf._version import __version__

from openpdf.geometry import Point, Rect, IRect, Matrix, Quad
from openpdf.document import Document
from openpdf.page import Page
from openpdf.image.rendering import Pixmap
from openpdf.text.extraction import TextPage
from openpdf.annotations.models import Annotation
from openpdf.forms.models import Widget
from openpdf.drawing.shape import Shape
from openpdf.creation.builder import DocumentBuilder
from openpdf.outline import Outline, OutlineItem
from openpdf.constants import (
    AnnotationType, LinkType, WidgetType, ColorSpace, Permission,
    TEXT_PRESERVE_LIGATURES, TEXT_PRESERVE_WHITESPACE,
    TEXT_PRESERVE_IMAGES, TEXT_INHIBIT_SPACES, TEXT_DEHYPHENATE,
    TEXT_PRESERVE_SPANS,
)
from openpdf.exceptions import (
    OpenPdfError, FileDataError, PasswordError, PageNumberError,
    AnnotationError, FormFieldError, EncryptionError, DependencyError,
)
from openpdf.color import get_color

# ---- Compatibility aliases -------------------------------------------------

# Install camelCase aliases for fitz compatibility
import openpdf.utils.compat  # noqa: F401  (side-effect: installs aliases)

# ---- Top-level convenience -------------------------------------------------

# openpdf.open("file.pdf") mirrors fitz.open("file.pdf")
open = Document

# Version info
version = __version__
VersionBind = __version__    # fitz compat alias

# Paper sizes (in points, portrait orientation)
_PAPER_SIZES: dict[str, tuple[float, float]] = {
    "A0": (2384, 3370), "A1": (1684, 2384), "A2": (1191, 1684),
    "A3": (842, 1191),  "A4": (595, 842),   "A5": (420, 595),
    "A6": (297, 420),   "A7": (210, 297),   "A8": (148, 210),
    "A9": (105, 148),   "A10": (74, 105),
    "B0": (2835, 4008), "B1": (2004, 2835), "B2": (1417, 2004),
    "B3": (1001, 1417), "B4": (709, 1001),  "B5": (499, 709),
    "LETTER": (612, 792), "LEGAL": (612, 1008), "TABLOID": (792, 1224),
    "LEDGER": (1224, 792),
}


def paper_size(s: str) -> tuple[float, float]:
    """Return (width, height) in points for a paper size name."""
    return _PAPER_SIZES.get(s.upper(), (612, 792))


def paper_rect(s: str) -> Rect:
    """Return Rect(0, 0, w, h) for a paper size name."""
    w, h = paper_size(s)
    return Rect(0, 0, w, h)


__all__ = [
    "__version__", "version", "VersionBind",
    "Point", "Rect", "IRect", "Matrix", "Quad",
    "Document", "Page", "Pixmap", "TextPage",
    "Annotation", "Widget", "Shape", "DocumentBuilder",
    "Outline", "OutlineItem",
    "AnnotationType", "LinkType", "WidgetType", "ColorSpace", "Permission",
    "TEXT_PRESERVE_LIGATURES", "TEXT_PRESERVE_WHITESPACE",
    "TEXT_PRESERVE_IMAGES", "TEXT_INHIBIT_SPACES", "TEXT_DEHYPHENATE",
    "TEXT_PRESERVE_SPANS",
    "OpenPdfError", "FileDataError", "PasswordError", "PageNumberError",
    "AnnotationError", "FormFieldError", "EncryptionError", "DependencyError",
    "get_color", "open", "paper_size", "paper_rect",
]
