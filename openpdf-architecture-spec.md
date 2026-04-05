# OpenPDF — Architecture Specification

> A comprehensive, commercially-free Python library that replicates the full
> surface area of PyMuPDF (`fitz`), enabling existing codebases to migrate with
> minimal refactoring.

---

## 1. Goals & Constraints

### 1.1 Goals

- Provide a **drop-in-compatible** API surface that mirrors PyMuPDF's `fitz`
  module as closely as possible.
- Cover **all major function groups**: document I/O, page manipulation, text
  extraction, image extraction, rendering, annotations, forms, TOC/bookmarks,
  metadata, redactions, links, widgets, drawing/creation, search, and geometry.
- Expose a single, unified `import openpdf` entry-point so that a migration
  from `import fitz` requires only a find-and-replace plus minor edge-case
  fixes.
- Be fully usable in commercial products with **zero copyleft obligations**.

### 1.2 Constraints

| Constraint | Detail |
|---|---|
| Python version | 3.10 – 3.11 |
| Licensing | Every runtime dependency must be Apache-2.0, MIT, BSD, MPL-2.0, or equivalent. No GPL/LGPL/AGPL. |
| No C compilation | All native code comes pre-built via wheels from the chosen dependencies. No user-side compiler needed. |
| Thread safety | Document objects are **not** thread-safe (same as PyMuPDF). Callers must synchronize. |

---

## 2. Dependency Map

Each dependency is chosen for a specific capability slice. No single backend
covers everything, so OpenPDF acts as a **unified façade** that delegates to the
right engine per operation.

| Dependency | License | Role in OpenPDF |
|---|---|---|
| `pypdfium2 >=4.25,<5` | Apache-2.0 / BSD-3 | Page rendering (bitmap), fast text extraction, page-level operations |
| `pikepdf >=8,<10` | MPL-2.0 | Low-level PDF structure, merge/split, metadata, encryption, streams, page transforms |
| `pdfminer.six >=20221105` | MIT | Layout-aware text extraction with bounding boxes, font info, character-level data |
| `Pillow >=10,<11` | HPND (MIT-like) | Image format conversion for rendered bitmaps and extracted images |
| `reportlab >=4,<5` | BSD-3 | PDF creation from scratch: drawing, text layout, table generation |
| `fonttools >=4.40` | MIT | Font inspection, glyph metrics, embedding metadata |

### Optional dependencies

| Dependency | License | Role |
|---|---|---|
| `pytesseract >=0.3.10` | Apache-2.0 | OCR on rendered page images (requires Tesseract binary) |

### Dependency–capability matrix

```
Capability              pypdfium2  pikepdf  pdfminer  reportlab  Pillow  fonttools
─────────────────────── ────────── ──────── ───────── ───────── ─────── ─────────
Open / parse PDF        ✓ primary  ✓ secondary
Save / write PDF                   ✓ primary           ✓ creation
Render page → image     ✓ primary                                ✓ format
Text extraction (fast)  ✓ primary
Text extraction (layout)                    ✓ primary
Image extraction                   ✓ stream                      ✓ decode
Merge / split                      ✓ primary
Metadata read/write                ✓ primary
Encryption / decrypt                ✓ primary
Annotations read                   ✓ read
Annotations write                  ✓ write
Form fields                        ✓ primary
TOC / bookmarks                    ✓ primary
Page transforms                    ✓ primary
Create new PDF                                         ✓ primary
Draw shapes / text                                     ✓ primary
Font metrics                                                             ✓ primary
OCR (optional)          (renders)                                ✓ feed   → pytesseract
```

---

## 3. Project Structure

```
openpdf/
├── pyproject.toml
├── README.md
├── LICENSE                          # MIT
├── openpdf/
│   ├── __init__.py                  # Public API re-exports
│   ├── _version.py                  # Single-source version string
│   │
│   ├── geometry.py                  # Point, Rect, IRect, Matrix, Quad
│   ├── color.py                     # Color helpers, PDF color space utils
│   ├── constants.py                 # Enums and constants mirroring fitz.*
│   ├── exceptions.py                # Custom exception hierarchy
│   │
│   ├── document.py                  # Document class  (top-level object)
│   ├── page.py                      # Page class
│   ├── outline.py                   # TOC / bookmark tree
│   ├── metadata.py                  # DocumentMetadata dataclass + helpers
│   │
│   ├── text/
│   │   ├── __init__.py
│   │   ├── extraction.py            # TextPage, get_text("text"|"dict"|"blocks"|…)
│   │   ├── search.py                # Text search with hit rectangles
│   │   └── layout.py                # Layout analysis (pdfminer integration)
│   │
│   ├── image/
│   │   ├── __init__.py
│   │   ├── extraction.py            # Extract embedded images from page/document
│   │   └── rendering.py             # Render page to PIL.Image / bytes / file
│   │
│   ├── annotations/
│   │   ├── __init__.py
│   │   ├── reader.py                # Read annotations from pages
│   │   ├── writer.py                # Add/update/delete annotations
│   │   └── models.py                # Annotation dataclasses (Highlight, FreeText, …)
│   │
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── reader.py                # Read form field values, types, flags
│   │   ├── writer.py                # Fill / modify form fields
│   │   └── models.py                # Widget / field dataclasses
│   │
│   ├── drawing/
│   │   ├── __init__.py
│   │   ├── shape.py                 # Shape builder (mirrors fitz.Shape)
│   │   └── canvas.py                # Low-level draw commands on a page
│   │
│   ├── creation/
│   │   ├── __init__.py
│   │   ├── builder.py               # DocumentBuilder for creating PDFs from scratch
│   │   ├── story.py                 # Story-based text flow (mirrors fitz.Story)
│   │   └── table.py                 # Table builder helper
│   │
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── pdfium.py                # pypdfium2 wrapper (rendering, fast text)
│   │   ├── pike.py                  # pikepdf wrapper (structure, merge, meta)
│   │   ├── miner.py                 # pdfminer.six wrapper (layout text)
│   │   └── rlab.py                  # reportlab wrapper (creation, drawing)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── io.py                    # File/stream/buffer helpers
│       ├── compat.py                # PyMuPDF compatibility shims and aliases
│       └── ocr.py                   # Optional OCR integration
│
└── tests/
    ├── conftest.py
    ├── test_document.py
    ├── test_page.py
    ├── test_text.py
    ├── test_image.py
    ├── test_annotations.py
    ├── test_forms.py
    ├── test_drawing.py
    ├── test_creation.py
    ├── test_geometry.py
    └── fixtures/
        └── sample.pdf
```

---

## 4. Geometry Module (`geometry.py`)

These primitives mirror `fitz.Point`, `fitz.Rect`, `fitz.IRect`, `fitz.Matrix`,
and `fitz.Quad`. They are pure-Python with no dependencies and are used
throughout every other module.

### 4.1 Point

```
class Point:
    x: float
    y: float

    # Construction
    Point()                        → origin (0, 0)
    Point(x, y)                    → from coordinates
    Point((x, y))                  → from tuple/list
    Point(other_point)             → copy

    # Arithmetic
    __add__(other) → Point         # vector addition
    __sub__(other) → Point         # vector subtraction
    __mul__(scalar) → Point        # scalar multiply
    __truediv__(scalar) → Point    # scalar divide
    __neg__() → Point              # negate
    __abs__() → float              # euclidean norm

    # Helpers
    norm → float                   # property, same as abs()
    distance_to(other) → float
    transform(matrix) → Point      # apply affine Matrix
    unit → Point                   # unit vector in same direction

    # Sequence protocol: len=2, indexable, iterable
```

### 4.2 Rect

```
class Rect:
    x0: float    # left
    y0: float    # top
    x1: float    # right
    y1: float    # bottom

    # Construction
    Rect()                         → empty rect (0,0,0,0)
    Rect(x0, y0, x1, y1)          → from coordinates
    Rect(top_left, bottom_right)   → from two Points
    Rect(rect)                     → copy
    Rect(sequence)                 → from 4-element iterable

    # Properties
    width → float
    height → float
    top_left → Point
    top_right → Point
    bottom_left → Point
    bottom_right → Point
    quad → Quad                    # the 4-corner Quad of this Rect
    is_empty → bool                # width or height <= 0
    is_infinite → bool             # matches the "infinite" sentinel rect

    # Geometric operations
    contains(point_or_rect) → bool
    intersects(other_rect) → bool
    intersect(other_rect) → Rect   # intersection; returns empty if disjoint
    include_point(point) → Rect    # smallest rect including self + point
    include_rect(other) → Rect     # union bounding box
    normalize() → Rect             # ensure x0<=x1, y0<=y1
    transform(matrix) → Rect       # apply Matrix, return bounding rect
    round() → IRect                # round outward to integer coords
    morph(fixpoint, matrix) → Quad # morph around a fixpoint

    # Sequence protocol: len=4, indexable, iterable
```

### 4.3 IRect

```
class IRect:
    """Integer rectangle — pixel coordinates for rendered bitmaps."""
    x0: int
    y0: int
    x1: int
    y1: int

    # Same interface as Rect but all values are int.
    # Additional property:
    rect → Rect                    # convert to float Rect
```

### 4.4 Matrix

```
class Matrix:
    a: float   b: float           # | a  b  0 |
    c: float   d: float           # | c  d  0 |
    e: float   f: float           # | e  f  1 |

    # Construction
    Matrix()                       → identity (1,0,0,1,0,0)
    Matrix(zoom_x, zoom_y)        → scale matrix
    Matrix(a, b, c, d, e, f)      → arbitrary affine
    Matrix(degree)                 → rotation around origin

    # Pre-built factories
    Matrix.identity() → Matrix
    Matrix.rotation(degrees) → Matrix
    Matrix.scale(sx, sy) → Matrix
    Matrix.translation(tx, ty) → Matrix
    Matrix.shear(sx, sy) → Matrix

    # Operations
    __mul__(other_matrix) → Matrix   # concatenation
    __invert__() → Matrix            # inverse matrix
    prerotate(degrees) → Matrix      # self = rotation · self
    prescale(sx, sy) → Matrix
    pretranslate(tx, ty) → Matrix
    concat(other) → Matrix           # self = self · other
    invert() → Matrix                # in-place inverse
    is_rectilinear → bool            # no rotation/shear component
```

### 4.5 Quad

```
class Quad:
    ul: Point   # upper-left
    ur: Point   # upper-right
    ll: Point   # lower-left
    lr: Point   # lower-right

    rect → Rect                     # bounding rectangle
    is_rectangular → bool           # is it axis-aligned?
    is_convex → bool
    transform(matrix) → Quad
    morph(fixpoint, matrix) → Quad
```

---

## 5. Constants & Enums (`constants.py`)

Mirror the `fitz.TEXT_*`, `fitz.PDF_ANNOT_*`, `fitz.LINK_*`, and other constants.

```python
# --- Text extraction flags (combinable with |) ---
TEXT_PRESERVE_LIGATURES   = 1
TEXT_PRESERVE_WHITESPACE  = 2
TEXT_PRESERVE_IMAGES      = 4
TEXT_INHIBIT_SPACES       = 8
TEXT_DEHYPHENATE          = 16
TEXT_PRESERVE_SPANS       = 32

# --- Annotation types ---
class AnnotationType(IntEnum):
    TEXT        = 0
    LINK        = 1
    FREE_TEXT   = 2
    LINE        = 3
    SQUARE      = 4
    CIRCLE      = 5
    POLYGON     = 6
    POLYLINE    = 7
    HIGHLIGHT   = 8
    UNDERLINE   = 9
    SQUIGGLY    = 10
    STRIKEOUT   = 11
    STAMP       = 12
    CARET       = 13
    INK         = 14
    POPUP       = 15
    FILE_ATTACHMENT = 16
    SOUND       = 17
    MOVIE       = 18
    WIDGET      = 19
    SCREEN      = 20
    PRINTER_MARK = 21
    TRAP_NET    = 22
    WATERMARK   = 23
    THREED      = 24
    REDACT      = 25

# --- Link types ---
class LinkType(IntEnum):
    NONE  = 0
    GOTO  = 1
    URI   = 2
    LAUNCH = 3
    NAMED  = 4
    GOTOR  = 5

# --- Widget / form field types ---
class WidgetType(IntEnum):
    UNKNOWN   = 0
    BUTTON    = 1
    CHECKBOX  = 2
    COMBOBOX  = 3
    LISTBOX   = 4
    RADIOBUTTON = 5
    SIGNATURE = 6
    TEXT      = 7

# --- Color spaces ---
class ColorSpace(IntEnum):
    CS_RGB   = 1
    CS_GRAY  = 2
    CS_CMYK  = 3

# --- Page rotation ---
VALID_ROTATIONS = {0, 90, 180, 270}

# --- Stamp names (for stamp annotations) ---
STAMP_NAMES = [
    "Approved", "Experimental", "NotApproved", "AsIs",
    "Expired", "NotForPublicRelease", "Confidential", "Final",
    "Sold", "Departmental", "ForComment", "TopSecret",
    "Draft", "ForPublicRelease",
]

# --- PDF permissions (for encryption) ---
class Permission(IntFlag):
    PRINT           = 4
    MODIFY          = 8
    COPY            = 16
    ANNOTATE        = 32
    FILL_FORMS      = 256
    ACCESSIBILITY   = 512
    ASSEMBLE        = 1024
    PRINT_HQ        = 2048
    ALL             = PRINT | MODIFY | COPY | ANNOTATE | FILL_FORMS | ACCESSIBILITY | ASSEMBLE | PRINT_HQ
```

---

## 6. Exceptions (`exceptions.py`)

```python
class OpenPdfError(Exception):
    """Base exception for all OpenPDF errors."""

class FileDataError(OpenPdfError):
    """Raised when the PDF data is corrupt or unreadable."""

class PasswordError(OpenPdfError):
    """Raised when a password is required or incorrect."""

class PageNumberError(OpenPdfError, IndexError):
    """Raised for out-of-range page numbers."""

class AnnotationError(OpenPdfError):
    """Raised for invalid annotation operations."""

class FormFieldError(OpenPdfError):
    """Raised for invalid form-field operations."""

class EncryptionError(OpenPdfError):
    """Raised for encryption/decryption failures."""

class DependencyError(OpenPdfError, ImportError):
    """Raised when an optional dependency is missing (e.g. pytesseract)."""
```

---

## 7. Backend Wrappers (`backends/`)

Each backend module wraps exactly one third-party library and exposes a
**private** internal API. No backend is imported directly by user code — only
the façade classes (`Document`, `Page`, etc.) call into backends.

### 7.1 `backends/pdfium.py` — pypdfium2

```
class PdfiumBackend:
    """Wraps pypdfium2 for rendering and fast text extraction."""

    open(path_or_bytes, password=None) → pdfium.PdfDocument
    close(handle)

    page_count(handle) → int
    page_size(handle, page_index) → (width_pt, height_pt)

    render_page(
        handle,
        page_index,
        scale: float = 1.0,       # 1.0 = 72 dpi
        rotation: int = 0,
        clip: Rect | None = None,
        alpha: bool = False,       # transparent background
        color: tuple | None = None # background RGBA
    ) → PIL.Image.Image

    render_page_to_bytes(
        handle, page_index, scale, rotation, clip, alpha, color,
        format: str = "png"       # "png", "jpeg", "ppm", etc.
    ) → bytes

    extract_text_simple(handle, page_index) → str
        # Fast extraction without layout. Uses pdfium's built-in text API.

    extract_text_chars(handle, page_index) → list[dict]
        # Per-character data: {"char": "A", "bbox": Rect, "font_size": 12.0}

    get_page_images_raw(handle, page_index) → list[dict]
        # Returns list of image object dicts with raw stream bytes.
        # {"index": int, "bbox": Rect, "width": int, "height": int,
        #  "colorspace": str, "bpc": int, "data": bytes}
```

### 7.2 `backends/pike.py` — pikepdf

```
class PikeBackend:
    """Wraps pikepdf for structural PDF operations."""

    open(path_or_bytes, password=None) → pikepdf.Pdf
    save(handle, path_or_buffer, **options)
    close(handle)

    # ---- Metadata ----------------------------------------------------------
    get_metadata(handle) → dict
        # Keys: title, author, subject, keywords, creator, producer,
        #       creation_date, mod_date, trapped
    set_metadata(handle, key, value)

    get_xml_metadata(handle) → str | None       # raw XMP
    set_xml_metadata(handle, xml_str)

    # ---- Page-level --------------------------------------------------------
    page_count(handle) → int
    get_page(handle, index) → pikepdf.Page
    insert_page(handle, page_obj, index)
    delete_page(handle, index)
    move_page(handle, from_index, to_index)
    copy_page(source_handle, src_idx, dest_handle, dest_idx)

    get_page_rotation(handle, index) → int      # 0/90/180/270
    set_page_rotation(handle, index, degrees)
    get_page_cropbox(handle, index) → Rect
    set_page_cropbox(handle, index, rect)
    get_page_mediabox(handle, index) → Rect
    set_page_mediabox(handle, index, rect)

    # ---- Merge / split -----------------------------------------------------
    merge(handles: list, output_path)
        # Concatenates multiple PDFs in order.
    split(handle, output_dir, page_ranges: list[range] | None = None)
        # Splits into separate files.  None → one file per page.

    # ---- TOC / outlines ----------------------------------------------------
    get_toc(handle) → list[TocEntry]
        # TocEntry = {"level": int, "title": str, "page": int, "dest": ...}
    set_toc(handle, entries: list[TocEntry])

    # ---- Links -------------------------------------------------------------
    get_links(handle, page_index) → list[LinkInfo]
        # LinkInfo = {"kind": LinkType, "uri": str|None, "page": int|None,
        #             "rect": Rect, "dest_name": str|None}

    # ---- Annotations (read / write) ----------------------------------------
    get_annotations(handle, page_index) → list[dict]
        # Returns raw annotation dicts with /Subtype, /Rect, /Contents, etc.
    add_annotation(handle, page_index, annot_dict)
    update_annotation(handle, page_index, annot_index, annot_dict)
    delete_annotation(handle, page_index, annot_index)

    # ---- Form fields -------------------------------------------------------
    get_form_fields(handle) → list[dict]
        # {"name": str, "type": WidgetType, "value": Any, "page": int,
        #  "rect": Rect, "options": list|None, "flags": int}
    set_form_field_value(handle, field_name, value)

    # ---- Encryption --------------------------------------------------------
    encrypt(handle, user_password, owner_password, permissions: Permission)
    decrypt(handle, password)
    is_encrypted(handle) → bool

    # ---- Embedded files / attachments --------------------------------------
    get_embedded_files(handle) → list[EmbeddedFile]
        # EmbeddedFile = {"name": str, "data": bytes, "mime": str|None,
        #                 "creation_date": str|None, "mod_date": str|None}
    add_embedded_file(handle, name, data, mime=None)
    delete_embedded_file(handle, name)

    # ---- Low-level stream access -------------------------------------------
    get_page_contents_stream(handle, page_index) → bytes
    extract_images_from_page(handle, page_index) → list[dict]
        # Walks the page's /Resources /XObject looking for /Subtype /Image
        # Returns {"name": str, "width": int, "height": int, "data": bytes,
        #          "colorspace": str, "filter": str, "bpc": int}
```

### 7.3 `backends/miner.py` — pdfminer.six

```
class MinerBackend:
    """Wraps pdfminer.six for layout-aware text extraction."""

    extract_text_simple(path_or_bytes, page_numbers=None) → str
        # Full-document plain-text extraction.

    extract_text_blocks(path_or_bytes, page_index) → list[TextBlock]
        # TextBlock = {"bbox": Rect, "text": str, "block_type": "text"|"image",
        #              "lines": list[TextLine]}
        # TextLine  = {"bbox": Rect, "text": str, "spans": list[TextSpan]}
        # TextSpan  = {"bbox": Rect, "text": str, "font": str, "size": float,
        #              "color": int|None, "flags": int}

    extract_text_dict(path_or_bytes, page_index) → dict
        # Returns the full hierarchical dict matching fitz's get_text("dict"):
        # {"width": float, "height": float,
        #  "blocks": [{"type": 0, "bbox": (...), "lines": [...]}]}

    extract_text_words(path_or_bytes, page_index) → list[tuple]
        # Each word: (x0, y0, x1, y1, "word", block_no, line_no, word_no)

    extract_text_rawdict(path_or_bytes, page_index) → dict
        # Like dict but with per-character data (chars instead of spans).

    extract_text_html(path_or_bytes, page_index) → str
    extract_text_xhtml(path_or_bytes, page_index) → str
    extract_text_xml(path_or_bytes, page_index) → str

    get_fonts(path_or_bytes, page_index) → list[FontInfo]
        # FontInfo = {"name": str, "flags": int, "size": float,
        #             "encoding": str, "is_embedded": bool}

    get_char_rects(path_or_bytes, page_index, char: str) → list[Rect]
        # Find all bounding boxes of a given character on a page.
```

### 7.4 `backends/rlab.py` — reportlab

```
class ReportLabBackend:
    """Wraps reportlab for PDF creation and drawing."""

    create_pdf(path, page_size=(612, 792)) → CanvasHandle
        # Returns a wrapper around reportlab.pdfgen.canvas.Canvas.

    # ---- Drawing primitives ------------------------------------------------
    draw_line(canvas, p1: Point, p2: Point, color, width)
    draw_rect(canvas, rect: Rect, color, fill, border_width, radius=0)
    draw_circle(canvas, center: Point, radius, color, fill, border_width)
    draw_oval(canvas, rect: Rect, color, fill, border_width)
    draw_polygon(canvas, points: list[Point], color, fill, border_width)
    draw_polyline(canvas, points: list[Point], color, width)
    draw_curve(canvas, p1, p2, p3, p4, color, width)  # cubic Bézier

    # ---- Text drawing ------------------------------------------------------
    draw_text(canvas, point: Point, text: str, fontname, fontsize, color)
    draw_text_in_rect(canvas, rect: Rect, text: str, fontname, fontsize,
                      color, align="left", valign="top")
    insert_textbox(canvas, rect: Rect, text: str, fontname, fontsize,
                   color, align, rotate=0) → float  # returns overflow height

    # ---- Image insertion ---------------------------------------------------
    draw_image(canvas, point_or_rect, image_path_or_pil, keep_aspect=True)

    # ---- Page management ---------------------------------------------------
    new_page(canvas, page_size=None)
    set_page_size(canvas, width, height)
    finish(canvas)                  # save and close

    # ---- Table helper ------------------------------------------------------
    draw_table(canvas, origin: Point, data: list[list[str]],
               col_widths, row_heights, style_commands) → Rect
        # Wraps reportlab.platypus.Table.  Returns bounding Rect of table.
```

---

## 8. Façade: Document Class (`document.py`)

The `Document` class is the primary user-facing object. It mirrors `fitz.Document`
(also known as `fitz.open`). Internally it holds handles to **both** the pdfium
and pikepdf backends so that it can delegate operations to the right engine.

```
class Document:
    """
    Central PDF document handle.

    Usage:
        doc = openpdf.open("file.pdf")
        doc = openpdf.Document("file.pdf")
        doc = openpdf.Document(stream=bytes_data, filetype="pdf")
    """

    # ==== Construction / lifecycle ==========================================

    __init__(
        filename: str | Path | None = None,
        stream: bytes | BytesIO | None = None,
        filetype: str = "pdf",
        password: str | None = None,
    )
        PSEUDOCODE:
            self._pike = PikeBackend.open(source, password)
            self._pdfium = PdfiumBackend.open(source, password)
            self._path = filename
            self._is_closed = False
            self._changes = []        # track unsaved modifications

    close()
        PSEUDOCODE:
            PikeBackend.close(self._pike)
            PdfiumBackend.close(self._pdfium)
            self._is_closed = True

    __enter__() / __exit__()          # context-manager support
    __del__()                         # calls close() if not already closed

    # ==== Properties ========================================================

    name → str                        # filename or "" for stream-based
    page_count → int                  # delegates to PikeBackend
    metadata → dict                   # delegates to PikeBackend.get_metadata
    is_encrypted → bool
    is_pdf → bool
    is_closed → bool
    needs_pass → bool                 # True if encrypted and not yet authed
    permissions → Permission          # PDF permission flags
    language → str                    # document language tag

    # ==== Authentication ====================================================

    authenticate(password: str) → bool
        PSEUDOCODE:
            try:
                re-open both backends with password
                return True
            except PasswordError:
                return False

    # ==== Page access =======================================================

    __len__() → int                   # page_count
    __getitem__(index) → Page         # returns Page object (see §9)
    __iter__() → Iterator[Page]       # iterate all pages
    __contains__(page) → bool

    load_page(page_id: int = 0) → Page
        # Mirrors fitz's doc.load_page(). Negative indexing supported.
        PSEUDOCODE:
            validate page_id in range (support negative indexing)
            return Page(self, page_id)

    pages(start=0, stop=None, step=1) → Iterator[Page]
        # Mirrors fitz's doc.pages() with optional slice args.

    # ==== Page manipulation =================================================

    new_page(pno: int = -1, width: float = 612, height: float = 792) → Page
        PSEUDOCODE:
            create a blank page via PikeBackend
            insert at position pno (-1 = append)
            reload pdfium handle
            return Page(self, resolved_index)

    insert_page(pno: int, text: str = "", ...) → Page
        # Insert page with optional pre-filled text.

    delete_page(pno: int)
    delete_pages(from_page: int = -1, to_page: int = -1, indices: list[int] | None = None)
        PSEUDOCODE:
            if indices given, delete those pages (descending order)
            else delete range [from_page, to_page]
            reload pdfium handle

    copy_page(pno: int, to: int = -1)
        # Duplicate page pno, insert copy at position to.

    move_page(pno: int, to: int = 0)
        # Move page pno to new position.

    select(page_numbers: Sequence[int])
        # Keep only the listed pages (in given order). Mirrors fitz.select().
        PSEUDOCODE:
            create new pikepdf.Pdf()
            for idx in page_numbers:
                copy page from self._pike into new pdf
            replace self._pike with new pdf
            reload pdfium handle

    # ==== Metadata ==========================================================

    set_metadata(metadata: dict)
        # Keys: title, author, subject, keywords, creator, producer,
        #       creationDate, modDate, trapped
        PSEUDOCODE:
            for key, value in metadata.items():
                PikeBackend.set_metadata(self._pike, key, value)

    get_xml_metadata() → str
    set_xml_metadata(xml: str)

    # ==== TOC / Outlines ====================================================

    get_toc(simple: bool = True) → list
        # Returns list of [level, title, page, dest] entries.
        # simple=True returns [level, title, page].
        PSEUDOCODE:
            raw = PikeBackend.get_toc(self._pike)
            if simple:
                return [[e.level, e.title, e.page] for e in raw]
            else:
                return [[e.level, e.title, e.page, e.dest_dict] for e in raw]

    set_toc(toc: list)
        # Accepts same format as get_toc output.

    # ==== Merge / Insert ====================================================

    insert_pdf(
        source: Document,
        from_page: int = 0,
        to_page: int = -1,
        start_at: int = -1,
        rotate: int = -1,
        links: bool = True,
        annots: bool = True,
    )
        PSEUDOCODE:
            resolve to_page (-1 → source.page_count - 1)
            resolve start_at (-1 → self.page_count)
            for i in range(from_page, to_page + 1):
                copy page from source._pike to self._pike at start_at + offset
                if rotate >= 0: set rotation
                if not links: strip link annotations
                if not annots: strip non-link annotations
            reload pdfium handle

    insert_file(path, ...)            # convenience: opens path, calls insert_pdf

    # ==== Save / Export =====================================================

    save(
        filename: str | Path | BytesIO,
        garbage: int = 0,             # 0-4, controls garbage collection level
        clean: bool = False,
        deflate: bool = True,
        deflate_images: bool = True,
        deflate_fonts: bool = True,
        incremental: bool = False,
        encryption: int = 0,          # 0=none, 1=RC4-40, 2=RC4-128, 3=AES-128, 4=AES-256
        owner_pw: str | None = None,
        user_pw: str | None = None,
        permissions: Permission = Permission.ALL,
        linear: bool = False,
    )
        PSEUDOCODE:
            opts = build pikepdf save options from parameters
            PikeBackend.save(self._pike, filename, **opts)

    write(garbage=0, clean=False, ...) → bytes
        # Like save() but returns bytes instead of writing to file.
        PSEUDOCODE:
            buf = BytesIO()
            self.save(buf, ...)
            return buf.getvalue()

    tobytes(garbage=0, ...) → bytes   # alias for write()

    convert_to_pdf() → bytes
        # For non-PDF inputs (future: images, XPS, etc.), convert to PDF bytes.
        # For actual PDFs, returns write().

    # ==== Embedded files ====================================================

    embfile_count() → int
    embfile_names() → list[str]
    embfile_info(name: str) → dict
    embfile_get(name: str) → bytes
    embfile_add(name: str, data: bytes, filename: str | None = None,
                desc: str | None = None)
    embfile_del(name: str)
    embfile_upd(name: str, data: bytes | None = None, filename: str | None = None)

    # ==== Search (document-wide) ============================================

    search_page_for(pno: int, text: str, quads: bool = False) → list
        # Convenience — delegates to Page.search_for.

    # ==== Miscellaneous =====================================================

    page_cropbox(pno) → Rect
    page_mediabox(pno) → Rect
    page_xref(pno) → int             # internal cross-reference number
    xref_length() → int              # total xref entries
    pdf_catalog() → int              # xref of catalog object
    pdf_trailer() → dict
    is_form_pdf → bool               # has AcroForm?
    is_reflowable → bool
    chapter_count → int
    last_location → tuple
    page_label(pno) → str            # "iv", "12", "A-3", etc.
    set_page_labels(rules: list)
    make_bookmark(loc) → int
    find_bookmark(bookmark_id) → tuple

    # ==== Reload internals after mutation ====================================

    _reload_pdfium()
        PSEUDOCODE:
            buf = self.write()
            PdfiumBackend.close(self._pdfium)
            self._pdfium = PdfiumBackend.open(buf)
```

---

## 9. Façade: Page Class (`page.py`)

Each `Page` holds a back-reference to its parent `Document` and its page index.
It delegates to the appropriate backend for each operation.

```
class Page:
    """Single page of a Document. Mirrors fitz.Page."""

    __init__(parent: Document, page_id: int)
        PSEUDOCODE:
            self.parent = parent
            self.number = page_id
            self._annots_cache = None
            self._widgets_cache = None

    # ==== Properties ========================================================

    rect → Rect              # page MediaBox as Rect (in points, 72 dpi)
    cropbox → Rect
    mediabox → Rect
    trimbox → Rect
    artbox → Rect
    bleedbox → Rect
    rotation → int           # 0, 90, 180, 270
    width → float
    height → float
    xref → int               # internal cross-ref id
    number → int             # 0-based page index

    # ==== Rotation ==========================================================

    set_rotation(rotation: int)
        PSEUDOCODE:
            validate rotation in {0, 90, 180, 270}
            PikeBackend.set_page_rotation(parent._pike, self.number, rotation)
            parent._reload_pdfium()

    # ==== CropBox / MediaBox ================================================

    set_cropbox(rect: Rect)
    set_mediabox(rect: Rect)
    set_trimbox(rect: Rect)
    set_artbox(rect: Rect)
    set_bleedbox(rect: Rect)

    # ==== Text extraction ===================================================

    get_text(
        option: str = "text",
        clip: Rect | None = None,
        flags: int = 0,
        sort: bool = False,
    ) → str | dict | list
        """
        option values (mirroring fitz):
            "text"     → plain string
            "blocks"   → list of (x0,y0,x1,y1, text, block_no, block_type)
            "words"    → list of (x0,y0,x1,y1, word, block_no, line_no, word_no)
            "dict"     → hierarchical dict {blocks: [{lines: [{spans: [...]}]}]}
            "rawdict"  → like dict but with per-char data
            "html"     → HTML string
            "xhtml"    → XHTML string
            "xml"      → XML string
        """
        PSEUDOCODE:
            if option == "text":
                # Prefer pypdfium2 for speed; fall back to pdfminer for accuracy
                text = PdfiumBackend.extract_text_simple(parent._pdfium, self.number)
                if clip:
                    text = filter_text_by_rect(text, clip)   # uses char positions
                if sort:
                    text = sort_by_reading_order(text)
                return text
            elif option in ("dict", "rawdict", "blocks", "words", "html", "xhtml", "xml"):
                return MinerBackend.extract_text_{option}(parent._path_or_bytes, self.number)

    get_textpage() → TextPage
        # Returns a TextPage object for reusable extraction (see §10).

    # ==== Text search =======================================================

    search_for(
        text: str,
        clip: Rect | None = None,
        quads: bool = False,
        flags: int = 0,
        hit_max: int = 16,
    ) → list[Rect] | list[Quad]
        PSEUDOCODE:
            extract all words with positions via MinerBackend
            find contiguous word sequences matching `text` (case-insensitive)
            collect bounding rects/quads of matches
            if clip: filter to matches intersecting clip
            return matches[:hit_max]

    # ==== Image extraction ==================================================

    get_images(full: bool = False) → list[tuple]
        """
        Returns list of images on the page.
        Basic:  (xref, smask, width, height, bpc, colorspace, alt_cs, name, filter, invoker)
        full=True adds the image bbox Rect.
        """
        PSEUDOCODE:
            images = PikeBackend.extract_images_from_page(parent._pike, self.number)
            return formatted tuples

    get_image_info(xrefs: bool = False) → list[dict]
        # More detailed image metadata.

    get_image_bbox(item: tuple | str) → Rect
        # Bounding box of a specific image on the page.

    extract_image(xref: int) → dict
        # {"ext": "png", "width": w, "height": h, "image": bytes,
        #  "colorspace": int, "cs-name": str, "xres": int, "yres": int}
        PSEUDOCODE:
            raw = PikeBackend.get_image_stream(parent._pike, xref)
            decode raw data based on filter/colorspace
            convert to PIL, export to PNG bytes
            return info dict

    # ==== Rendering =========================================================

    get_pixmap(
        matrix: Matrix = Matrix(),
        dpi: int | None = None,
        colorspace: ColorSpace = ColorSpace.CS_RGB,
        clip: Rect | None = None,
        alpha: bool = False,
        annots: bool = True,
    ) → Pixmap
        PSEUDOCODE:
            scale = matrix_to_scale(matrix) or dpi / 72
            pil_image = PdfiumBackend.render_page(
                parent._pdfium, self.number,
                scale=scale, clip=clip, alpha=alpha
            )
            return Pixmap(pil_image, colorspace)

    get_svg_image(matrix: Matrix = Matrix(), text_as_path: bool = True) → str
        # Render page to SVG string.
        # NOTE: pypdfium2 does not support SVG natively.
        # Strategy: render to high-res bitmap, embed as base64 in SVG.
        # Or: extract vectors via pdfminer layout and reconstruct SVG.

    # ==== Annotations =======================================================

    annots() → Iterator[Annotation]
        # Yields Annotation objects for each annotation on the page.
        PSEUDOCODE:
            raw_list = PikeBackend.get_annotations(parent._pike, self.number)
            for raw in raw_list:
                yield Annotation.from_raw(raw, self)

    first_annot → Annotation | None
    annot_count → int

    add_highlight_annot(quads: list[Quad] | None = None, text: str = "") → Annotation
    add_underline_annot(quads) → Annotation
    add_strikeout_annot(quads) → Annotation
    add_squiggly_annot(quads) → Annotation

    add_freetext_annot(
        rect: Rect, text: str, fontsize: float = 12,
        fontname: str = "helv", color: tuple = (0, 0, 0),
        fill_color: tuple | None = None, rotate: int = 0,
        align: int = 0,   # 0=left, 1=center, 2=right
    ) → Annotation

    add_text_annot(point: Point, text: str, icon: str = "Note") → Annotation
    add_line_annot(p1: Point, p2: Point) → Annotation
    add_rect_annot(rect: Rect) → Annotation
    add_circle_annot(rect: Rect) → Annotation
    add_polygon_annot(points: list[Point]) → Annotation
    add_polyline_annot(points: list[Point]) → Annotation
    add_ink_annot(paths: list[list[Point]]) → Annotation
    add_stamp_annot(rect: Rect, stamp: int | str = 0) → Annotation
    add_file_annot(point: Point, data: bytes, filename: str, desc: str = "") → Annotation
    add_caret_annot(point: Point) → Annotation

    add_redact_annot(
        quad: Quad | Rect, text: str | None = None,
        fill: tuple = (1, 1, 1), text_color: tuple = (0, 0, 0),
        cross_out: bool = True,
    ) → Annotation

    apply_redactions(images: int = 2, graphics: int = 1) → bool
        # Permanently removes content under redaction annotations.

    delete_annot(annot: Annotation)
    update_annot(annot: Annotation)  # write modified annot back to page

    # ==== Links =============================================================

    links() → Iterator[LinkInfo]
    insert_link(link_dict: dict)
        # link_dict keys: "kind", "from" (Rect), "uri", "page", "to" (Point), ...
    delete_link(link: LinkInfo)
    first_link → LinkInfo | None

    # ==== Widgets / Form Fields =============================================

    widgets() → Iterator[Widget]
    first_widget → Widget | None

    add_widget(widget: Widget)
        # Create a new form field on this page.

    # ==== Drawing (Shape) ===================================================

    new_shape() → Shape
        # Returns a Shape object that accumulates drawing commands and commits
        # them to the page. See §12 for Shape details.

    # Direct drawing convenience methods (create shape internally):

    draw_line(p1: Point, p2: Point, color=(0,0,0), width=1, ...) → Point
    draw_rect(rect: Rect, color=(0,0,0), fill=None, width=1, ...) → Point
    draw_circle(center: Point, radius: float, ...) → Point
    draw_oval(rect: Rect, ...) → Point
    draw_quad(quad: Quad, ...) → Point
    draw_polyline(points: list[Point], ...) → Point
    draw_polygon(points: list[Point], ...) → Point
    draw_bezier(p1, p2, p3, p4, ...) → Point
    draw_curve(p1, p2, p3, ...) → Point
    draw_squiggle(p1: Point, p2: Point, ...) → Point
    draw_zigzag(p1: Point, p2: Point, ...) → Point
    draw_sector(center, point, angle, ...) → Point

    # ==== Text insertion ====================================================

    insert_text(
        point: Point, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), rotate: int = 0,
        encoding: int = 0,
    ) → int   # returns number of lines written

    insert_textbox(
        rect: Rect, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), align: int = 0,
        rotate: int = 0, expandtabs: int = 8,
    ) → float  # returns unused height (negative if overflow)

    insert_htmlbox(rect: Rect, html: str, ...) → float

    # ==== Image insertion ===================================================

    insert_image(
        rect: Rect,
        filename: str | None = None,
        stream: bytes | None = None,
        pixmap: Pixmap | None = None,
        mask: Pixmap | None = None,
        overlay: bool = True,
        rotate: int = 0,
        keep_proportion: bool = True,
        xref: int = 0,
        oc: int = 0,
    ) → int   # returns xref of inserted image

    # ==== Page transforms ===================================================

    wrap_contents()
        # Wraps the page's /Contents in a q...Q graphics state pair.

    clean_contents(sanitize: bool = True)
        # Cleans and optionally sanitises the content stream.

    # ==== Misc ==============================================================

    get_fonts(full: bool = False) → list[tuple]
    get_drawings(extended: bool = False) → list[dict]
        # Returns vector graphics paths: lines, curves, rects, fills.
    get_texttrace() → dict
    get_label() → str
    get_links() → list[dict]

    derotation_matrix → Matrix     # matrix to undo page rotation
    transformation_matrix → Matrix # CTM from PDF default space to page space
```

---

## 10. TextPage Class (`text/extraction.py`)

A reusable text-extraction handle for a single page (mirrors `fitz.TextPage`).

```
class TextPage:
    """Pre-computed text extraction result for efficient re-querying."""

    __init__(page: Page, flags: int = 0)
        PSEUDOCODE:
            self._page = page
            self._blocks = MinerBackend.extract_text_blocks(...)
            self._chars = PdfiumBackend.extract_text_chars(...)

    extractText() → str                        # alias for get_text("text")
    extractBLOCKS() → list[tuple]              # alias for get_text("blocks")
    extractWORDS() → list[tuple]               # alias for get_text("words")
    extractDICT(sort: bool = False) → dict     # alias for get_text("dict")
    extractRAWDICT(sort: bool = False) → dict
    extractHTML() → str
    extractXHTML() → str
    extractXML() → str

    search(needle: str, quads: bool = False, hit_max: int = 16) → list
```

---

## 11. Pixmap Class (`image/rendering.py`)

A raster image container (mirrors `fitz.Pixmap`).

```
class Pixmap:
    """Raster image with pixel access. Wraps PIL.Image internally."""

    __init__(
        source: PIL.Image.Image | bytes | None = None,
        colorspace: ColorSpace = ColorSpace.CS_RGB,
        width: int = 0,
        height: int = 0,
        alpha: bool = False,
    )
        PSEUDOCODE:
            if source is PIL.Image:
                self._img = source
            elif source is bytes:
                self._img = PIL.Image.open(BytesIO(source))
            else:
                mode = "RGBA" if alpha else "RGB"
                self._img = PIL.Image.new(mode, (width, height))

    # ---- Properties --------------------------------------------------------
    width → int
    height → int
    x → int                    # x origin (usually 0)
    y → int                    # y origin
    n → int                    # components per pixel (3 for RGB, 4 for RGBA)
    alpha → bool
    stride → int               # bytes per row
    irect → IRect
    samples → bytes            # raw pixel data
    samples_mv → memoryview
    size → int                 # total byte count of samples
    colorspace → ColorSpace
    is_monochrome → bool
    is_unicolor → bool
    xres → int                 # horizontal resolution
    yres → int                 # vertical resolution

    # ---- Pixel access ------------------------------------------------------
    pixel(x: int, y: int) → tuple        # (r, g, b) or (r, g, b, a)
    set_pixel(x: int, y: int, color: tuple)

    # ---- Conversions -------------------------------------------------------
    tobytes(output: str = "png") → bytes
        # output: "png", "jpeg", "ppm", "pbm", "psd", "tga"
        PSEUDOCODE:
            buf = BytesIO()
            self._img.save(buf, format=output.upper())
            return buf.getvalue()

    save(filename: str, output: str | None = None)
        PSEUDOCODE:
            fmt = output or Path(filename).suffix.lstrip(".")
            self._img.save(filename, format=fmt.upper())

    pil_image() → PIL.Image.Image
        # Expose underlying PIL image.

    # ---- Manipulation ------------------------------------------------------
    set_alpha(alphavalues: bytes | None = None, premultiply: bool = True, opaque=None)
    clear_with(value: int = 255)           # fill with uniform value
    tint_with(black: int, white: int)
    gamma_with(gamma: float)
    invert_irect(irect: IRect | None = None)
    copy(source: Pixmap, irect: IRect)     # blit another pixmap onto self
    set_rect(irect: IRect, color: tuple)   # fill rectangle with color
    shrink(factor: int)                    # reduce by integer factor
    set_origin(x: int, y: int)
    set_resolution(xres: int, yres: int)

    # ---- Color space conversion --------------------------------------------
    to_rgb() → Pixmap
    to_gray() → Pixmap
    to_cmyk() → Pixmap

    # ---- OCR (optional) ----------------------------------------------------
    ocr(language: str = "eng", tessdata: str | None = None) → str
        PSEUDOCODE:
            ensure pytesseract is available (else raise DependencyError)
            return pytesseract.image_to_string(self._img, lang=language)
```

---

## 12. Shape Class (`drawing/shape.py`)

Accumulates drawing commands and commits them to a Page's content stream.
Mirrors `fitz.Shape`.

```
class Shape:
    """
    Vector-drawing accumulator. Created via page.new_shape().
    Draw operations are buffered; call commit() to write them into the page's
    content stream.
    """

    __init__(page: Page)
        PSEUDOCODE:
            self._page = page
            self._draw_commands = []      # list of PDF content-stream fragments
            self._text_commands = []
            self._totalRect = Rect()      # bounding box of all drawings

    # ---- Drawing primitives ------------------------------------------------

    draw_line(p1: Point, p2: Point) → Point
    draw_rect(rect: Rect) → Point
    draw_circle(center: Point, radius: float) → Point
    draw_oval(rect: Rect) → Point
    draw_quad(quad: Quad) → Point
    draw_polyline(points: list[Point]) → Point
    draw_polygon(points: list[Point]) → Point
    draw_bezier(p1, p2, p3, p4) → Point
    draw_curve(p1, p2, p3) → Point
    draw_squiggle(p1: Point, p2: Point, breadth: float = 2) → Point
    draw_zigzag(p1: Point, p2: Point, breadth: float = 2) → Point
    draw_sector(center: Point, point: Point, angle: float, fullSector: bool = True) → Point

    # All draw methods:
    #   - Append raw PDF drawing operators to self._draw_commands
    #   - Update self._totalRect
    #   - Return the "current point" (last drawn-to coordinate)

    # ---- Finishing (stroke/fill) -------------------------------------------

    finish(
        color: tuple | None = (0, 0, 0),
        fill: tuple | None = None,
        width: float = 1,
        dashes: str | None = None,
        lineCap: int = 0,          # 0=butt, 1=round, 2=square
        lineJoin: int = 0,         # 0=miter, 1=round, 2=bevel
        morph: tuple | None = None,    # (fixpoint, matrix) pair
        closePath: bool = True,
        even_odd: bool = False,
        opacity: float = 1.0,
        blend_mode: str = "Normal",
    )
        PSEUDOCODE:
            build PDF operators for stroke/fill settings
            if morph: apply transform around fixpoint
            wrap draw_commands in q...Q state block
            merge into self._text_commands (final list)
            reset self._draw_commands for next batch

    # ---- Text insertion via Shape ------------------------------------------

    insert_text(point: Point, text: str, fontsize=11, fontname="helv",
                color=(0,0,0), rotate=0, ...) → int

    insert_textbox(rect: Rect, text: str, fontsize=11, fontname="helv",
                   color=(0,0,0), align=0, rotate=0, ...) → float

    # ---- Commit to page ----------------------------------------------------

    commit(overlay: bool = True)
        PSEUDOCODE:
            content_stream = build_content_stream(self._text_commands)
            if overlay:
                append content_stream to page's existing /Contents
            else:
                prepend content_stream
            parent._reload_pdfium()

    # ---- Properties --------------------------------------------------------
    doc → Document
    page → Page
    totalRect → Rect              # bounding box of all committed drawings
    lastPoint → Point             # last current point
```

---

## 13. Annotation Class (`annotations/models.py`)

```
class Annotation:
    """Represents a single PDF annotation. Mirrors fitz.Annot."""

    # ---- Construction (internal) -------------------------------------------
    from_raw(raw_dict: dict, page: Page) → Annotation   # class method

    # ---- Properties --------------------------------------------------------
    type → tuple                   # (type_int, type_name) e.g. (8, "Highlight")
    info → dict                    # {"title": str, "content": str, "name": str,
                                   #  "subject": str, "creationDate": str, "modDate": str}
    rect → Rect                    # annotation rectangle
    flags → int                    # annotation flags bitmask
    colors → dict                  # {"stroke": tuple|None, "fill": tuple|None}
    border → dict                  # {"width": float, "style": str, "dashes": list}
    opacity → float                # 0.0 – 1.0
    popup_rect → Rect
    popup_xref → int
    has_popup → bool
    is_open → bool
    line_ends → tuple              # (start_style, end_style)
    vertices → list[Point]         # for Polygon/PolyLine/Ink
    xref → int

    # ---- Modification ------------------------------------------------------
    set_rect(rect: Rect)
    set_colors(stroke: tuple | None = None, fill: tuple | None = None)
    set_border(width: float = -1, style: str | None = None, dashes: list | None = None)
    set_opacity(opacity: float)
    set_flags(flags: int)
    set_info(info: dict)
    set_name(name: str)
    set_popup(rect: Rect)
    set_open(is_open: bool)
    set_line_ends(start: int, end: int)

    update(
        fontsize: float = 0,
        fontname: str | None = None,
        text_color: tuple | None = None,
        border_color: tuple | None = None,
        fill_color: tuple | None = None,
        cross_out: bool = True,          # for redactions
        rotate: int = -1,
    )
        PSEUDOCODE:
            apply all changed properties
            PikeBackend.update_annotation(page.parent._pike, page.number, self._index, self._dict)
            page.parent._reload_pdfium()

    # ---- Content -----------------------------------------------------------
    get_text(option: str = "text") → str     # text inside annotation rect
    get_textpage() → TextPage
    get_pixmap(...) → Pixmap                 # render just the annotation area
```

---

## 14. Widget Class (`forms/models.py`)

```
class Widget:
    """PDF form field / widget annotation. Mirrors fitz.Widget."""

    # Properties
    field_name → str
    field_label → str
    field_value → str | bool | list
    field_type → WidgetType
    field_type_string → str         # "Text", "CheckBox", etc.
    field_flags → int
    field_display → int             # visibility
    rect → Rect
    text_maxlen → int
    text_format → int
    choice_values → list[str]       # for ComboBox/ListBox
    is_signed → bool
    button_caption → str
    script → str                    # JavaScript action
    script_stroke → str
    script_format → str
    script_change → str
    script_calc → str
    xref → int

    # Setters
    set_field_value(value)
    set_text_maxlen(maxlen: int)
    set_rect(rect: Rect)
    set_field_flags(flags: int)

    update()
        PSEUDOCODE:
            PikeBackend.set_form_field_value(doc._pike, self.field_name, self.field_value)
```

---

## 15. Document Creation (`creation/builder.py`)

For creating PDFs from scratch (mirrors `fitz.open()` on a new document plus
page.insert_text, etc.). Wraps ReportLab.

```
class DocumentBuilder:
    """
    Build a new PDF from scratch.

    Usage:
        builder = DocumentBuilder("output.pdf", page_size=(612, 792))
        builder.add_page()
        builder.draw_text(Point(72, 700), "Hello, World!", fontsize=24)
        builder.draw_rect(Rect(72, 500, 300, 600), fill=(0.9, 0.9, 1.0))
        builder.draw_image(Rect(72, 200, 300, 480), "photo.jpg")
        builder.add_page()
        builder.draw_text(Point(72, 700), "Page 2")
        doc = builder.finish()   # returns a Document for further manipulation
    """

    __init__(path_or_buffer, page_size=(612, 792))

    add_page(page_size=None) → int               # returns page index
    set_current_page(page_index: int)

    # Drawing
    draw_text(point, text, fontsize=11, fontname="Helvetica", color=(0,0,0), rotate=0)
    draw_textbox(rect, text, fontsize=11, fontname="Helvetica", color=(0,0,0), align="left")
    draw_line(p1, p2, color=(0,0,0), width=1)
    draw_rect(rect, color=(0,0,0), fill=None, width=1, radius=0)
    draw_circle(center, radius, color=(0,0,0), fill=None, width=1)
    draw_oval(rect, color=(0,0,0), fill=None, width=1)
    draw_polygon(points, color=(0,0,0), fill=None, width=1)
    draw_polyline(points, color=(0,0,0), width=1)
    draw_bezier(p1, p2, p3, p4, color=(0,0,0), width=1)
    draw_image(rect, image_path_or_pil_or_bytes, keep_aspect=True)

    # Table
    draw_table(origin, data, col_widths=None, row_heights=None, style=None) → Rect

    # Metadata
    set_title(title: str)
    set_author(author: str)
    set_subject(subject: str)

    # Finish
    finish() → Document
        PSEUDOCODE:
            ReportLabBackend.finish(self._canvas)
            return Document(self._path)
```

---

## 16. Outline / TOC (`outline.py`)

```
class OutlineItem:
    """Single TOC entry."""
    level: int            # 1-based depth
    title: str
    page: int             # 0-based target page
    dest: dict | None     # destination details (kind, to, zoom, etc.)
    color: tuple | None
    bold: bool
    italic: bool
    collapse: bool

class Outline:
    """Iterable TOC tree. Mirrors fitz.Document.outline (first outline entry)."""

    title → str
    uri → str | None
    page → int
    dest → dict
    is_external → bool
    bold → bool
    italic → bool
    color → tuple
    collapse → bool
    down → Outline | None      # first child
    next → Outline | None      # next sibling
```

---

## 17. Utility: Compatibility Shims (`utils/compat.py`)

This module provides aliases so that code written for `fitz` can work with
minimal changes.

```python
# Aliases at module level (re-exported from openpdf.__init__)

open = Document                     # fitz.open() → openpdf.open()
Rect = geometry.Rect
Point = geometry.Point
Matrix = geometry.Matrix
Quad = geometry.Quad
IRect = geometry.IRect

# Page method aliases
Page.getText = Page.get_text        # deprecated fitz camelCase
Page.getTextPage = Page.get_textpage
Page.searchFor = Page.search_for
Page.getPixmap = Page.get_pixmap
Page.getImageList = Page.get_images
Page.getSVGimage = Page.get_svg_image
Page.insertText = Page.insert_text
Page.insertTextbox = Page.insert_textbox
Page.insertImage = Page.insert_image
Page.drawRect = Page.draw_rect
Page.drawLine = Page.draw_line
Page.drawCircle = Page.draw_circle
Page.newShape = Page.new_shape
Page.getDrawings = Page.get_drawings
Page.wrapContents = Page.wrap_contents
Page.cleanContents = Page.clean_contents
Page.setCropBox = Page.set_cropbox
Page.setMediaBox = Page.set_mediabox
Page.setRotation = Page.set_rotation
Page.addHighlightAnnot = Page.add_highlight_annot
Page.addUnderlineAnnot = Page.add_underline_annot
Page.addStrikeoutAnnot = Page.add_strikeout_annot
Page.addFreetextAnnot = Page.add_freetext_annot
Page.addTextAnnot = Page.add_text_annot
Page.addLineAnnot = Page.add_line_annot
Page.addRectAnnot = Page.add_rect_annot
Page.addCircleAnnot = Page.add_circle_annot
Page.addRedactAnnot = Page.add_redact_annot
Page.applyRedactions = Page.apply_redactions
Page.deleteAnnot = Page.delete_annot
Page.insertLink = Page.insert_link
Page.deleteLink = Page.delete_link

# Document method aliases
Document.loadPage = Document.load_page
Document.newPage = Document.new_page
Document.insertPage = Document.insert_page
Document.deletePage = Document.delete_page
Document.deletePages = Document.delete_pages
Document.copyPage = Document.copy_page
Document.movePage = Document.move_page
Document.insertPDF = Document.insert_pdf
Document.setMetadata = Document.set_metadata
Document.getToC = Document.get_toc
Document.setToC = Document.set_toc
Document.embeddedFileCount = Document.embfile_count
Document.embeddedFileNames = Document.embfile_names
Document.embeddedFileGet = Document.embfile_get
Document.embeddedFileAdd = Document.embfile_add
Document.embeddedFileDel = Document.embfile_del
Document.convertToPDF = Document.convert_to_pdf

# Pixmap aliases
Pixmap.getPNGData = lambda self: self.tobytes("png")
Pixmap.writePNG = lambda self, f: self.save(f, "png")
```

---

## 18. Module Entry Point (`__init__.py`)

```python
"""
OpenPDF — A commercially-free alternative to PyMuPDF.

Usage:
    import openpdf

    doc = openpdf.open("input.pdf")
    page = doc[0]
    text = page.get_text()
    pix = page.get_pixmap(dpi=150)
    pix.save("page0.png")
    doc.close()
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
)
from openpdf.exceptions import (
    OpenPdfError, FileDataError, PasswordError, PageNumberError,
    AnnotationError, FormFieldError, EncryptionError, DependencyError,
)
from openpdf.color import get_color

# Top-level convenience
open = Document  # openpdf.open("file.pdf") mirrors fitz.open("file.pdf")

# Version info
version = __version__
VersionBind = __version__    # fitz compat

# Paper sizes (in points)
paper_size = lambda s: _PAPER_SIZES.get(s.upper(), (612, 792))
paper_rect = lambda s: Rect(0, 0, *paper_size(s))

_PAPER_SIZES = {
    "A0": (2384, 3370), "A1": (1684, 2384), "A2": (1191, 1684),
    "A3": (842, 1191),  "A4": (595, 842),   "A5": (420, 595),
    "A6": (297, 420),   "A7": (210, 297),   "A8": (148, 210),
    "A9": (105, 148),   "A10": (74, 105),
    "B0": (2835, 4008), "B1": (2004, 2835), "B2": (1417, 2004),
    "B3": (1001, 1417), "B4": (709, 1001),  "B5": (499, 709),
    "LETTER": (612, 792), "LEGAL": (612, 1008), "TABLOID": (792, 1224),
    "LEDGER": (1224, 792),
}
```

---

## 19. Error Handling & Backend Selection Strategy

### 19.1 Backend selection logic

Operations are routed to backends according to this priority table:

| Operation | Primary | Fallback | Notes |
|---|---|---|---|
| Open / parse | pypdfium2 + pikepdf | — | Both opened on init; pdfium for render, pike for structure |
| Plain text extraction | pypdfium2 | pdfminer | pypdfium2 is 3-5× faster for bulk extraction |
| Layout text extraction | pdfminer | — | Only pdfminer has spatial layout analysis |
| Render to image | pypdfium2 | — | Only option; no GPL dependency |
| Merge / split | pikepdf | — | |
| Metadata | pikepdf | — | |
| Annotations | pikepdf | — | Read/write via raw PDF dict manipulation |
| Form fields | pikepdf | — | |
| Encryption | pikepdf | — | |
| Create from scratch | reportlab | — | |
| Drawing on existing page | reportlab (generate overlay) + pikepdf (merge overlay) | — | See §19.2 |

### 19.2 Drawing on existing pages — the overlay strategy

PyMuPDF modifies the page's content stream directly. Since we lack that
low-level access, the strategy is:

```
1. Create a single-page PDF with reportlab containing only the drawing commands.
2. Use pikepdf to merge (overlay) that single page onto the target page.
3. Reload the pdfium handle to reflect the changes.
```

This approach is slightly slower than direct stream manipulation but produces
correct output for all drawing operations, including transparency and blend modes.

### 19.3 Error cascading

When a primary backend raises an unexpected error:

```
try:
    result = primary_backend.operation(...)
except Exception as e:
    if fallback_backend:
        log.warning(f"Primary backend failed, falling back: {e}")
        result = fallback_backend.operation(...)
    else:
        raise OpenPdfError(f"Operation failed: {e}") from e
```

### 19.4 Lazy backend initialization

Not all backends need to load for every operation:

```
- pypdfium2 + pikepdf: Always loaded on Document.__init__
- pdfminer:  Loaded lazily on first layout-text call
- reportlab: Loaded lazily on first drawing/creation call
- fonttools:  Loaded lazily on first font-inspection call
```

---

## 20. Thread Safety & Resource Management

- `Document` objects are **not thread-safe**. If multiple threads need to
  process the same PDF, each should open its own `Document` instance.
- All `Document` objects implement the context manager protocol and should be
  used with `with` statements when possible.
- The `_reload_pdfium()` internal method serializes the current pikepdf state
  to bytes and re-opens it in pypdfium2. This is necessary after any structural
  mutation (add/delete pages, annotations, etc.) but is expensive. Mutations
  should be batched before a reload.
- A dirty-flag system tracks whether a pdfium reload is needed:

```
self._pdfium_dirty = False

def _mark_dirty(self):
    self._pdfium_dirty = True

def _ensure_pdfium_fresh(self):
    if self._pdfium_dirty:
        self._reload_pdfium()
        self._pdfium_dirty = False
```

Rendering and text-extraction methods call `_ensure_pdfium_fresh()` before
proceeding. Mutation methods call `_mark_dirty()`.

---

## 21. Migration Guide: fitz → openpdf

### 21.1 Import change

```python
# Before
import fitz

# After
import openpdf as fitz   # drop-in, most code works unchanged
# — or —
import openpdf            # use openpdf.open(...) etc.
```

### 21.2 Known behavioral differences

| fitz behavior | openpdf behavior | Workaround |
|---|---|---|
| `fitz.open()` handles images, XPS, EPUB | `openpdf.open()` handles PDF only (v0.1) | Convert to PDF first |
| `page.get_text("rawdict")` returns MuPDF-internal font flags | Font flags mapped from pdfminer equivalents; may differ in edge cases | Compare specific flag meanings |
| `page.get_svg_image()` produces vector SVG | Returns bitmap-in-SVG (v0.1) | Use get_pixmap for pure raster |
| `page.get_drawings()` returns MuPDF path data | Reconstructed from content stream; complex clipping may differ | Validate on target documents |
| Annotations have MuPDF-specific xref semantics | xref values are pikepdf object IDs; not interchangeable | Use annotation by index or name |
| `fitz.TOOLS` utility object | Not implemented in v0.1 | Use individual utility functions |
| `fitz.Story` for reflowable HTML→PDF | `DocumentBuilder` + `insert_htmlbox` covers basic cases | Complex layouts may need manual adjustment |

### 21.3 API coverage checklist

The table below tracks implementation status. An agent implementing this spec
should work through this list and check off each function.

```
[x] = implemented   [ ] = not yet   [~] = partial / different signature

Document:
  [x] open / close / context manager
  [x] page_count, metadata, is_encrypted
  [x] load_page, __getitem__, __iter__, pages()
  [x] new_page, insert_page, delete_page, delete_pages
  [x] copy_page, move_page, select
  [x] set_metadata, get/set_xml_metadata
  [x] get_toc, set_toc
  [x] insert_pdf, insert_file
  [x] save, write, tobytes
  [x] embfile_* (count, names, get, add, del, upd)
  [x] authenticate, permissions
  [ ] convert_to_pdf (non-PDF inputs)
  [ ] chapter_count, last_location
  [x] page_label, set_page_labels
  [ ] journal_* methods
  [ ] xref_get_key, xref_set_key (low-level)

Page:
  [x] rect, cropbox, mediabox, rotation, width, height
  [x] set_rotation, set_cropbox, set_mediabox
  [x] get_text (all options)
  [x] get_textpage
  [x] search_for
  [x] get_images, get_image_info, get_image_bbox, extract_image
  [x] get_pixmap
  [~] get_svg_image (bitmap fallback)
  [x] annots, add_*_annot (all types), delete_annot
  [x] apply_redactions
  [x] links, insert_link, delete_link
  [x] widgets, add_widget
  [x] new_shape, draw_* convenience methods
  [x] insert_text, insert_textbox
  [~] insert_htmlbox (basic support)
  [x] insert_image
  [x] get_fonts, get_drawings
  [x] wrap_contents, clean_contents
  [ ] show_pdf_page (display another page as image)

Pixmap:
  [x] width, height, samples, irect
  [x] tobytes, save
  [x] pixel, set_pixel
  [x] color space conversion
  [x] shrink, clear_with, invert_irect
  [~] gamma_with, tint_with (via PIL filters)

Geometry:
  [x] Point, Rect, IRect, Matrix, Quad — all operations

Annotations:
  [x] Read all properties
  [x] Modify and update
  [x] Create all standard types

Forms:
  [x] Read field values and types
  [x] Set field values
  [ ] Create new form fields from scratch (complex)

Drawing:
  [x] Shape class with all draw primitives
  [x] finish() with stroke/fill/opacity/blend
  [x] commit() overlay strategy
```

---

## 22. Testing Strategy

### 22.1 Test categories

Each module gets a dedicated test file. Tests are organized as:

```
Unit tests:
  - geometry.py: All arithmetic, transforms, edge cases (empty rects, degenerate matrices)
  - constants.py: Enum membership and values

Integration tests (require a sample PDF fixture):
  - test_document.py: open, close, metadata, save, encrypt/decrypt, merge, split
  - test_page.py: page properties, rotation, cropbox
  - test_text.py: all get_text options compared against known-good output
  - test_image.py: extract_image, get_pixmap rendering at various DPI
  - test_annotations.py: add, read, modify, delete each annotation type
  - test_forms.py: read and fill form fields
  - test_drawing.py: draw shapes, verify visual output via pixmap comparison
  - test_creation.py: DocumentBuilder creates valid PDF, text and images correct

Compatibility tests:
  - test_compat.py: verify all fitz aliases (camelCase methods) work
  - test_migration.py: run a suite of common fitz usage patterns through openpdf
```

### 22.2 Fixture PDFs

The `tests/fixtures/` directory should contain:

```
sample.pdf              — multi-page, text, images, links
annotated.pdf           — all annotation types
form.pdf                — AcroForm with text fields, checkboxes, dropdowns
encrypted.pdf           — AES-256 encrypted (password: "test")
toc.pdf                 — document with multi-level bookmarks
embedded.pdf            — PDF with embedded file attachments
rotated.pdf             — pages with 90° and 180° rotation
scanned.pdf             — image-only pages (for OCR testing)
complex_layout.pdf      — multi-column, tables, headers/footers
large.pdf               — 100+ pages for performance benchmarks
```

---

## 23. Performance Considerations

| Operation | Target | Strategy |
|---|---|---|
| Open document | <100ms for typical files | Both backends opened in parallel; pdfium is fast, pikepdf does lazy parsing |
| Plain text extraction | <50ms per page | pypdfium2's C-level text API |
| Layout text extraction | <200ms per page | pdfminer; cache results in TextPage |
| Render page (150 DPI) | <300ms per page | pypdfium2's C renderer |
| Save document | <500ms for typical files | pikepdf's QPDF backend is optimized |
| Reload pdfium after mutation | ~100-200ms | Serialize to bytes buffer, not disk; this is the main overhead vs. MuPDF's in-process approach |

### Hot path optimization

For batch-processing scenarios (e.g., extract text from 1000 pages), the library
should support a "fast mode" that skips pdfium reload between mutations:

```python
with doc.batch_mode():
    for i in range(doc.page_count):
        text = doc[i].get_text()
    # pdfium is reloaded only once at exit, not per page
```

---

## 24. Version Roadmap

| Version | Scope |
|---|---|
| 0.1.0 | Core: open, text extraction (all modes), rendering, metadata, merge/split, save, geometry, basic annotations |
| 0.2.0 | Full annotations (all types + redactions), form fields read/write, TOC, encryption |
| 0.3.0 | Drawing (Shape class + overlay strategy), image insertion, DocumentBuilder |
| 0.4.0 | Compatibility shims, migration guide validation, performance tuning |
| 0.5.0 | OCR integration, embedded files, advanced features |
| 1.0.0 | Full API parity audit, comprehensive test suite, documentation site |
