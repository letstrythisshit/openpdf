"""Enums and constants mirroring fitz.* namespace."""
from __future__ import annotations

from enum import IntEnum, IntFlag

# ---------------------------------------------------------------------------
# Text extraction flags (combinable with |)
# ---------------------------------------------------------------------------

TEXT_PRESERVE_LIGATURES = 1
TEXT_PRESERVE_WHITESPACE = 2
TEXT_PRESERVE_IMAGES = 4
TEXT_INHIBIT_SPACES = 8
TEXT_DEHYPHENATE = 16
TEXT_PRESERVE_SPANS = 32

# ---------------------------------------------------------------------------
# Annotation types  (integer values match PyMuPDF / fitz convention)
# ---------------------------------------------------------------------------

class AnnotationType(IntEnum):
    TEXT = 0
    LINK = 1
    FREE_TEXT = 2
    LINE = 3
    SQUARE = 4
    CIRCLE = 5
    POLYGON = 6
    POLYLINE = 7
    HIGHLIGHT = 8
    UNDERLINE = 9
    SQUIGGLY = 10
    STRIKEOUT = 11
    STAMP = 12
    CARET = 13
    INK = 14
    POPUP = 15
    FILE_ATTACHMENT = 16
    SOUND = 17
    MOVIE = 18
    WIDGET = 19
    SCREEN = 20
    PRINTER_MARK = 21
    TRAP_NET = 22
    WATERMARK = 23
    THREED = 24
    REDACT = 25


# Mapping from PDF /Subtype Name strings to AnnotationType integers
_ANNOT_SUBTYPE_TO_INT: dict[str, int] = {
    "/Text": 0,
    "/Link": 1,
    "/FreeText": 2,
    "/Line": 3,
    "/Square": 4,
    "/Circle": 5,
    "/Polygon": 6,
    "/PolyLine": 7,
    "/Highlight": 8,
    "/Underline": 9,
    "/Squiggly": 10,
    "/StrikeOut": 11,
    "/Stamp": 12,
    "/Caret": 13,
    "/Ink": 14,
    "/Popup": 15,
    "/FileAttachment": 16,
    "/Sound": 17,
    "/Movie": 18,
    "/Widget": 19,
    "/Screen": 20,
    "/PrinterMark": 21,
    "/TrapNet": 22,
    "/Watermark": 23,
    "/3D": 24,
    "/Redact": 25,
}

_ANNOT_INT_TO_NAME: dict[int, str] = {v: k.lstrip("/") for k, v in _ANNOT_SUBTYPE_TO_INT.items()}

# ---------------------------------------------------------------------------
# Link types
# ---------------------------------------------------------------------------

class LinkType(IntEnum):
    NONE = 0
    GOTO = 1
    URI = 2
    LAUNCH = 3
    NAMED = 4
    GOTOR = 5


# ---------------------------------------------------------------------------
# Widget / form field types
# ---------------------------------------------------------------------------

class WidgetType(IntEnum):
    UNKNOWN = 0
    BUTTON = 1
    CHECKBOX = 2
    COMBOBOX = 3
    LISTBOX = 4
    RADIOBUTTON = 5
    SIGNATURE = 6
    TEXT = 7


_WIDGET_FT_TO_TYPE: dict[str, WidgetType] = {
    "/Btn": WidgetType.BUTTON,
    "/Ch": WidgetType.COMBOBOX,
    "/Tx": WidgetType.TEXT,
    "/Sig": WidgetType.SIGNATURE,
}

# ---------------------------------------------------------------------------
# Color spaces
# ---------------------------------------------------------------------------

class ColorSpace(IntEnum):
    CS_RGB = 1
    CS_GRAY = 2
    CS_CMYK = 3


# ---------------------------------------------------------------------------
# Page rotation
# ---------------------------------------------------------------------------

VALID_ROTATIONS = {0, 90, 180, 270}

# ---------------------------------------------------------------------------
# Stamp annotation names
# ---------------------------------------------------------------------------

STAMP_NAMES = [
    "Approved", "Experimental", "NotApproved", "AsIs",
    "Expired", "NotForPublicRelease", "Confidential", "Final",
    "Sold", "Departmental", "ForComment", "TopSecret",
    "Draft", "ForPublicRelease",
]

# ---------------------------------------------------------------------------
# PDF permissions (for encryption)
# ---------------------------------------------------------------------------

class Permission(IntFlag):
    NONE = 0
    PRINT = 4
    MODIFY = 8
    COPY = 16
    ANNOTATE = 32
    FILL_FORMS = 256
    ACCESSIBILITY = 512
    ASSEMBLE = 1024
    PRINT_HQ = 2048
    ALL = PRINT | MODIFY | COPY | ANNOTATE | FILL_FORMS | ACCESSIBILITY | ASSEMBLE | PRINT_HQ
