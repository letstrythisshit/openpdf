"""Page class — single page of a Document."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Union

from openpdf.geometry import Rect, Point, IRect, Matrix, Quad
from openpdf.constants import ColorSpace, VALID_ROTATIONS
from openpdf.exceptions import AnnotationError, PageNumberError
from openpdf.backends.pdfium import PdfiumBackend
from openpdf.backends.pike import PikeBackend
from openpdf.backends.miner import MinerBackend
from openpdf.utils.io import fitz_to_pdf_rect

if TYPE_CHECKING:
    from openpdf.document import Document
    from openpdf.annotations.models import Annotation
    from openpdf.forms.models import Widget
    from openpdf.drawing.shape import Shape
    from openpdf.image.rendering import Pixmap
    from openpdf.text.extraction import TextPage


class Page:
    """Single page of a Document. Mirrors fitz.Page.

    IMPORTANT: Never cache the pdfium page handle as an instance attribute.
    Always access as self.parent._pdfium[self.number] at call time to remain
    valid after _reload_pdfium().
    """

    def __init__(self, parent: "Document", page_id: int) -> None:
        self.parent = parent
        self.number = page_id
        self._annots_cache = None
        self._widgets_cache = None

    # ---- Properties --------------------------------------------------------

    @property
    def rect(self) -> Rect:
        """Page rect as (0, 0, width, height) using pdfium dimensions (rotation-aware)."""
        w, h = PdfiumBackend.page_size(self.parent._pdfium, self.number)
        return Rect(0, 0, w, h)

    @property
    def width(self) -> float:
        return PdfiumBackend.page_size(self.parent._pdfium, self.number)[0]

    @property
    def height(self) -> float:
        return PdfiumBackend.page_size(self.parent._pdfium, self.number)[1]

    @property
    def mediabox(self) -> Rect:
        """Raw MediaBox from pikepdf (not rotation-adjusted)."""
        return PikeBackend.get_page_mediabox(self.parent._pike, self.number)

    @property
    def cropbox(self) -> Rect:
        cb = PikeBackend.get_page_cropbox(self.parent._pike, self.number)
        return cb if cb is not None else self.mediabox

    @property
    def trimbox(self) -> Rect:
        return self.mediabox

    @property
    def artbox(self) -> Rect:
        return self.mediabox

    @property
    def bleedbox(self) -> Rect:
        return self.mediabox

    @property
    def rotation(self) -> int:
        return PikeBackend.get_page_rotation(self.parent._pike, self.number)

    @property
    def xref(self) -> int:
        try:
            return self.parent._pike.pages[self.number].obj.objgen[0]
        except Exception:
            return 0

    @property
    def derotation_matrix(self) -> Matrix:
        rot = self.rotation
        if rot == 0:
            return Matrix.identity()
        return Matrix.rotation(-rot)

    @property
    def transformation_matrix(self) -> Matrix:
        return Matrix.identity()

    # ---- Box setters -------------------------------------------------------

    def set_rotation(self, rotation: int) -> None:
        if rotation not in VALID_ROTATIONS:
            raise ValueError(f"rotation must be one of {VALID_ROTATIONS}, got {rotation}")
        PikeBackend.set_page_rotation(self.parent._pike, self.number, rotation)
        self.parent._mark_dirty()

    def set_cropbox(self, rect: Rect) -> None:
        PikeBackend.set_page_cropbox(self.parent._pike, self.number, rect)
        self.parent._bytes_cache = None

    def set_mediabox(self, rect: Rect) -> None:
        PikeBackend.set_page_mediabox(self.parent._pike, self.number, rect)
        self.parent._mark_dirty()

    def set_trimbox(self, rect: Rect) -> None:
        self.set_mediabox(rect)

    def set_artbox(self, rect: Rect) -> None:
        self.set_mediabox(rect)

    def set_bleedbox(self, rect: Rect) -> None:
        self.set_mediabox(rect)

    # ---- Text extraction ---------------------------------------------------

    def get_text(
        self,
        option: str = "text",
        clip: Rect | None = None,
        flags: int = 0,
        sort: bool = False,
    ) -> Union[str, dict, list]:
        """Extract text in various formats, mirroring fitz.Page.get_text()."""
        self.parent._ensure_pdfium_fresh()

        if option == "text":
            return self._get_text_simple(clip, sort)
        else:
            return self._get_text_layout(option, clip, sort)

    def _get_text_simple(self, clip: Rect | None, sort: bool) -> str:
        text = PdfiumBackend.extract_text_simple(self.parent._pdfium, self.number)
        if clip or sort:
            # Use char-level data for clip filtering and sorting
            chars = PdfiumBackend.extract_text_chars(self.parent._pdfium, self.number)
            if clip:
                chars = [c for c in chars if clip.intersects(c["bbox"])]
            if sort:
                chars = sorted(chars, key=lambda c: (c["bbox"].y0, c["bbox"].x0))
            return "".join(c["char"] for c in chars)
        return text

    def _get_text_layout(self, option: str, clip: Rect | None, sort: bool) -> Union[str, dict, list]:
        source = self.parent._get_bytes_for_miner()
        if option == "dict":
            result = MinerBackend.extract_text_dict(source, self.number)
        elif option == "rawdict":
            result = MinerBackend.extract_text_rawdict(source, self.number)
        elif option == "blocks":
            result = MinerBackend.extract_text_blocks(source, self.number)
        elif option == "words":
            result = MinerBackend.extract_text_words(source, self.number)
        elif option == "html":
            result = MinerBackend.extract_text_html(source, self.number)
        elif option == "xhtml":
            result = MinerBackend.extract_text_xhtml(source, self.number)
        elif option == "xml":
            result = MinerBackend.extract_text_xml(source, self.number)
        else:
            result = MinerBackend.extract_text_dict(source, self.number)

        if clip is not None and isinstance(result, dict):
            result = _clip_dict_blocks(result, clip)
        elif clip is not None and isinstance(result, list):
            result = _clip_list_blocks(result, clip)

        if sort and isinstance(result, dict):
            result["blocks"] = sorted(
                result.get("blocks", []),
                key=lambda b: (b["bbox"][1], b["bbox"][0])
            )
        return result

    def get_textpage(self) -> "TextPage":
        from openpdf.text.extraction import TextPage
        return TextPage(self)

    # ---- Text search -------------------------------------------------------

    def search_for(
        self,
        text: str,
        clip: Rect | None = None,
        quads: bool = False,
        flags: int = 0,
        hit_max: int = 16,
    ) -> list:
        from openpdf.text.search import search_page_for
        return search_page_for(self, text, clip=clip, quads=quads, hit_max=hit_max)

    # ---- Image operations --------------------------------------------------

    def get_images(self, full: bool = False) -> list[tuple]:
        """List images on the page.

        Returns tuples: (xref, smask, width, height, bpc, colorspace, alt_cs, name, filter, invoker)
        If full=True, adds bbox Rect as 11th element.
        """
        images = PikeBackend.extract_images_from_page(self.parent._pike, self.number)
        result = []
        for img in images:
            t = (
                img["xref"], 0, img["width"], img["height"], img["bpc"],
                img["colorspace"], "", img["name"], img["filter"], ""
            )
            if full:
                t = t + (Rect(),)  # bbox would need content-stream parsing; use empty
            result.append(t)
        return result

    def get_image_info(self, xrefs: bool = False) -> list[dict]:
        images = PikeBackend.extract_images_from_page(self.parent._pike, self.number)
        return [
            {
                "xref": img["xref"],
                "width": img["width"],
                "height": img["height"],
                "colorspace": img["colorspace"],
                "bpc": img["bpc"],
                "filter": img["filter"],
                "name": img["name"],
            }
            for img in images
        ]

    def get_image_bbox(self, item: Union[tuple, str]) -> Rect:
        """Approximate: returns empty Rect (content-stream parsing not yet implemented)."""
        return Rect()

    def extract_image(self, xref: int) -> dict:
        from openpdf.image.extraction import extract_image_by_xref
        return extract_image_by_xref(self.parent._pike, xref)

    # ---- Rendering ---------------------------------------------------------

    def get_pixmap(
        self,
        matrix: Matrix | None = None,
        dpi: int | None = None,
        colorspace: ColorSpace = ColorSpace.CS_RGB,
        clip: Rect | None = None,
        alpha: bool = False,
        annots: bool = True,
    ) -> "Pixmap":
        from openpdf.image.rendering import Pixmap
        self.parent._ensure_pdfium_fresh()

        # Determine scale
        if dpi is not None:
            scale = dpi / 72.0
        elif matrix is not None:
            # Extract scale from matrix (use average of x and y scale factors)
            scale = (abs(matrix.a) + abs(matrix.d)) / 2.0
        else:
            scale = 1.0

        rotation = 0
        if matrix is not None and not matrix.is_rectilinear:
            pass  # Non-rectilinear rotation not directly supported; ignore

        pil = PdfiumBackend.render_page(
            self.parent._pdfium, self.number,
            scale=scale, rotation=rotation, clip=clip, alpha=alpha,
        )

        # Convert colorspace if needed
        if colorspace == ColorSpace.CS_GRAY:
            pil = pil.convert("L")
        elif colorspace == ColorSpace.CS_CMYK:
            pil = pil.convert("CMYK")

        return Pixmap(source=pil, colorspace=colorspace, alpha=alpha)

    def get_svg_image(self, matrix: Matrix | None = None, text_as_path: bool = True) -> str:
        """Render page to SVG (bitmap-embedded fallback)."""
        import base64
        import io as _io
        scale = 1.0
        if matrix is not None:
            scale = (abs(matrix.a) + abs(matrix.d)) / 2.0
        pil = PdfiumBackend.render_page(self.parent._pdfium, self.number, scale=scale)
        buf = _io.BytesIO()
        pil.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        w, h = pil.size
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}">'
            f'<image x="0" y="0" width="{w}" height="{h}" '
            f'xlink:href="data:image/png;base64,{b64}"/>'
            f'</svg>'
        )

    # ---- Annotations -------------------------------------------------------

    def annots(self, types: list | None = None) -> list["Annotation"]:
        from openpdf.annotations.models import Annotation as AnnotModel
        raw_list = PikeBackend.get_annotations(self.parent._pike, self.number)
        result = []
        for raw in raw_list:
            annot = AnnotModel.from_raw(raw, self)
            if types is None or annot.type[0] in types:
                result.append(annot)
        return result

    @property
    def first_annot(self) -> "Annotation | None":
        return next(self.annots(), None)

    @property
    def annot_count(self) -> int:
        try:
            annots = self.parent._pike.pages[self.number].obj.get("/Annots", None)
            return len(annots) if annots else 0
        except Exception:
            return 0

    def add_highlight_annot(self, quads: list | None = None, text: str = "") -> "Annotation":
        from openpdf.annotations.writer import add_markup_annot
        return add_markup_annot(self, "Highlight", quads=quads, text=text)

    def add_underline_annot(self, quads: list | None = None) -> "Annotation":
        from openpdf.annotations.writer import add_markup_annot
        return add_markup_annot(self, "Underline", quads=quads)

    def add_strikeout_annot(self, quads: list | None = None) -> "Annotation":
        from openpdf.annotations.writer import add_markup_annot
        return add_markup_annot(self, "StrikeOut", quads=quads)

    def add_squiggly_annot(self, quads: list | None = None) -> "Annotation":
        from openpdf.annotations.writer import add_markup_annot
        return add_markup_annot(self, "Squiggly", quads=quads)

    def add_freetext_annot(
        self, rect: Rect, text: str, fontsize: float = 12,
        fontname: str = "helv", color: tuple = (0, 0, 0),
        fill_color: tuple | None = None, rotate: int = 0, align: int = 0,
    ) -> "Annotation":
        from openpdf.annotations.writer import add_freetext_annot
        return add_freetext_annot(self, rect, text, fontsize, fontname, color, fill_color, rotate, align)

    def add_text_annot(self, point: Point, text: str, icon: str = "Note") -> "Annotation":
        from openpdf.annotations.writer import add_text_annot
        return add_text_annot(self, point, text, icon)

    def add_line_annot(self, p1: Point, p2: Point) -> "Annotation":
        from openpdf.annotations.writer import add_line_annot
        return add_line_annot(self, p1, p2)

    def add_rect_annot(self, rect: Rect) -> "Annotation":
        from openpdf.annotations.writer import add_rect_annot
        return add_rect_annot(self, rect)

    def add_circle_annot(self, rect: Rect) -> "Annotation":
        from openpdf.annotations.writer import add_circle_annot
        return add_circle_annot(self, rect)

    def add_polygon_annot(self, points: list[Point]) -> "Annotation":
        from openpdf.annotations.writer import add_polygon_annot
        return add_polygon_annot(self, points)

    def add_polyline_annot(self, points: list[Point]) -> "Annotation":
        from openpdf.annotations.writer import add_polyline_annot
        return add_polyline_annot(self, points)

    def add_ink_annot(self, paths: list[list[Point]]) -> "Annotation":
        from openpdf.annotations.writer import add_ink_annot
        return add_ink_annot(self, paths)

    def add_stamp_annot(self, rect: Rect, stamp: Union[int, str] = 0) -> "Annotation":
        from openpdf.annotations.writer import add_stamp_annot
        return add_stamp_annot(self, rect, stamp)

    def add_file_annot(
        self, point: Point, data: bytes, filename: str, desc: str = ""
    ) -> "Annotation":
        from openpdf.annotations.writer import add_file_annot
        return add_file_annot(self, point, data, filename, desc)

    def add_caret_annot(self, point: Point) -> "Annotation":
        from openpdf.annotations.writer import add_caret_annot
        return add_caret_annot(self, point)

    def add_redact_annot(
        self, quad: Union[Quad, Rect], text: str | None = None,
        fill: tuple = (1, 1, 1), text_color: tuple = (0, 0, 0),
        cross_out: bool = True,
    ) -> "Annotation":
        from openpdf.annotations.writer import add_redact_annot
        return add_redact_annot(self, quad, text, fill, text_color, cross_out)

    def apply_redactions(self, images: int = 2, graphics: int = 1) -> bool:
        from openpdf.annotations.writer import apply_redactions
        return apply_redactions(self)

    def delete_annot(self, annot: "Annotation") -> None:
        PikeBackend.delete_annotation(self.parent._pike, self.number, annot._index)
        self.parent._mark_dirty()

    def update_annot(self, annot: "Annotation") -> None:
        annot.update()

    # ---- Links -------------------------------------------------------------

    def links(self) -> Iterator[dict]:
        for link in PikeBackend.get_links(self.parent._pike, self.number):
            yield link

    @property
    def first_link(self) -> dict | None:
        return next(self.links(), None)

    def get_links(self) -> list[dict]:
        return PikeBackend.get_links(self.parent._pike, self.number)

    def insert_link(self, link_dict: dict) -> None:
        from openpdf.annotations.writer import insert_link
        insert_link(self, link_dict)

    def delete_link(self, link: dict) -> None:
        # Links are annotations with /Subtype /Link; find and delete by rect match
        annots = PikeBackend.get_annotations(self.parent._pike, self.number)
        for annot in annots:
            if annot["subtype"] == "/Link":
                if annot["rect"] == link.get("rect", Rect()):
                    PikeBackend.delete_annotation(self.parent._pike, self.number, annot["index"])
                    self.parent._mark_dirty()
                    return

    # ---- Widgets -----------------------------------------------------------

    def widgets(self) -> list["Widget"]:
        from openpdf.forms.models import Widget as WidgetModel
        fields = PikeBackend.get_form_fields(self.parent._pike)
        return [
            WidgetModel.from_field_dict(field, self)
            for field in fields
            if field.get("page") == self.number
        ]

    def get_widgets(self) -> list["Widget"]:
        """Alias for widgets(), returns a list of Widget objects on this page."""
        return self.widgets()

    @property
    def first_widget(self) -> "Widget | None":
        return next(self.widgets(), None)

    def add_widget(self, widget: "Widget") -> None:
        widget._page = self
        # Widget creation requires building an AcroForm entry — deferred
        pass

    # ---- Drawing -----------------------------------------------------------

    def new_shape(self) -> "Shape":
        from openpdf.drawing.shape import Shape
        return Shape(self)

    def draw_line(
        self, p1: Point, p2: Point,
        color: tuple = (0, 0, 0), width: float = 1, **kwargs
    ) -> Point:
        shape = self.new_shape()
        shape.draw_line(p1, p2)
        shape.finish(color=color, width=width, **kwargs)
        shape.commit()
        return p2

    def draw_rect(
        self, rect: Rect,
        color: tuple = (0, 0, 0), fill: tuple | None = None, width: float = 1, **kwargs
    ) -> Point:
        shape = self.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=color, fill=fill, width=width, **kwargs)
        shape.commit()
        return rect.bottom_right

    def draw_circle(
        self, center: Point, radius: float,
        color: tuple = (0, 0, 0), fill: tuple | None = None, width: float = 1, **kwargs
    ) -> Point:
        shape = self.new_shape()
        shape.draw_circle(center, radius)
        shape.finish(color=color, fill=fill, width=width, **kwargs)
        shape.commit()
        return center

    def draw_oval(self, rect: Rect, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_oval(rect)
        shape.finish(**kwargs)
        shape.commit()
        return rect.bottom_right

    def draw_quad(self, quad: Quad, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_quad(quad)
        shape.finish(**kwargs)
        shape.commit()
        return quad.lr

    def draw_polyline(self, points: list[Point], **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_polyline(points)
        shape.finish(**kwargs)
        shape.commit()
        return points[-1] if points else Point()

    def draw_polygon(self, points: list[Point], **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_polygon(points)
        shape.finish(**kwargs)
        shape.commit()
        return points[-1] if points else Point()

    def draw_bezier(self, p1: Point, p2: Point, p3: Point, p4: Point, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_bezier(p1, p2, p3, p4)
        shape.finish(**kwargs)
        shape.commit()
        return p4

    def draw_curve(self, p1: Point, p2: Point, p3: Point, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_curve(p1, p2, p3)
        shape.finish(**kwargs)
        shape.commit()
        return p3

    def draw_squiggle(self, p1: Point, p2: Point, breadth: float = 2, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_squiggle(p1, p2, breadth)
        shape.finish(**kwargs)
        shape.commit()
        return p2

    def draw_zigzag(self, p1: Point, p2: Point, breadth: float = 2, **kwargs) -> Point:
        shape = self.new_shape()
        shape.draw_zigzag(p1, p2, breadth)
        shape.finish(**kwargs)
        shape.commit()
        return p2

    def draw_sector(
        self, center: Point, point: Point, angle: float, **kwargs
    ) -> Point:
        shape = self.new_shape()
        shape.draw_sector(center, point, angle)
        shape.finish(**kwargs)
        shape.commit()
        return point

    # ---- Text insertion ----------------------------------------------------

    def insert_text(
        self, point: Point, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), rotate: int = 0,
        encoding: int = 0,
    ) -> int:
        from openpdf.drawing.shape import Shape
        shape = Shape(self)
        n = shape.insert_text(point, text, fontsize=fontsize, fontname=fontname,
                              color=color, rotate=rotate)
        shape.commit()
        return n

    def insert_textbox(
        self, rect: Rect, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), align: int = 0,
        rotate: int = 0, expandtabs: int = 8,
    ) -> float:
        from openpdf.drawing.shape import Shape
        shape = Shape(self)
        overflow = shape.insert_textbox(rect, text, fontsize=fontsize, fontname=fontname,
                                        color=color, align=align, rotate=rotate)
        shape.commit()
        return overflow

    def insert_htmlbox(self, rect: Rect, html: str, **kwargs) -> float:
        # Basic implementation: strip HTML tags and use insert_textbox
        import re
        text = re.sub(r"<[^>]+>", "", html)
        return self.insert_textbox(rect, text, **kwargs)

    # ---- Image insertion ---------------------------------------------------

    def insert_image(
        self, rect: Rect,
        filename: str | None = None,
        stream: bytes | None = None,
        pixmap: "Pixmap | None" = None,
        overlay: bool = True,
        rotate: int = 0,
        keep_proportion: bool = True,
        **kwargs,
    ) -> int:
        """Insert an image into the page using the drawing overlay strategy."""
        import io as _io
        from openpdf.backends.rlab import ReportLabBackend
        from PIL import Image as PILImage

        page_h = self.height
        page_w = self.width

        # Get PIL image source
        pil_source = None
        if pixmap is not None:
            pil_source = pixmap._img
        elif stream is not None:
            pil_source = PILImage.open(_io.BytesIO(stream))
        elif filename is not None:
            pil_source = PILImage.open(filename)

        if pil_source is None:
            return 0

        # Save PIL image to temp file for reportlab
        tmp = _io.BytesIO()
        pil_source.save(tmp, format="PNG")
        tmp.seek(0)

        from reportlab.lib.utils import ImageReader
        rl_img = ImageReader(tmp)

        def draw_cmd(canvas, ph):
            ReportLabBackend.draw_image(canvas, rect, rl_img, keep_proportion, ph)

        overlay_bytes = ReportLabBackend.create_overlay_pdf(
            [draw_cmd], (page_w, page_h)
        )
        PikeBackend.overlay_page(self.parent._pike, self.number, overlay_bytes)
        self.parent._mark_dirty()
        return 0

    # ---- Page transforms ---------------------------------------------------

    def wrap_contents(self) -> None:
        """Wrap page /Contents in a q...Q graphics state pair."""
        try:
            page = self.parent._pike.pages[self.number]
            existing = PikeBackend.get_page_contents_bytes(self.parent._pike, self.number)
            wrapped = b"q\n" + existing + b"\nQ\n"
            new_stream = self.parent._pike.make_stream(wrapped)
            page.obj["/Contents"] = self.parent._pike.make_indirect(new_stream)
            self.parent._mark_dirty()
        except Exception:
            pass

    def clean_contents(self, sanitize: bool = True) -> None:
        """Minimal implementation: no-op (full stream sanitization is complex)."""
        pass

    # ---- Fonts & Drawings --------------------------------------------------

    def get_fonts(self, full: bool = False) -> list[tuple]:
        source = self.parent._get_bytes_for_miner()
        fonts = MinerBackend.get_fonts(source, self.number)
        if full:
            return [(0, 0, 0, f["name"], f["name"], f["encoding"]) for f in fonts]
        return [(0, 0, 0, f["name"], f["name"]) for f in fonts]

    def get_drawings(self, extended: bool = False) -> list[dict]:
        """Return vector drawing paths. Full implementation deferred to v0.5."""
        # TODO: implement content-stream parsing for path operators
        return []

    def get_texttrace(self) -> dict:
        return {}

    def get_label(self) -> str:
        return str(self.number + 1)

    # ---- Repr --------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Page({self.number}, {self.rect!r})"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _clip_dict_blocks(d: dict, clip: Rect) -> dict:
    """Filter dict blocks to those intersecting clip rect."""
    result = dict(d)
    filtered = []
    for block in d.get("blocks", []):
        bbox = block["bbox"]
        block_rect = Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        if block_rect.intersects(clip):
            filtered.append(block)
    result["blocks"] = filtered
    return result


def _clip_list_blocks(lst: list, clip: Rect) -> list:
    """Filter block/word tuples to those intersecting clip rect."""
    result = []
    for item in lst:
        if len(item) >= 4:
            item_rect = Rect(item[0], item[1], item[2], item[3])
            if item_rect.intersects(clip):
                result.append(item)
    return result
