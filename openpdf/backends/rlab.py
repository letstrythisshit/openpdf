"""reportlab backend — PDF creation and drawing.

All drawing methods receive coordinates in fitz convention (top-left origin)
and convert internally to reportlab convention (bottom-left origin).
"""
from __future__ import annotations

import io
from typing import Union

from openpdf.geometry import Point, Rect


# fitz short font name aliases → reportlab font names
_FITZ_FONT_ALIASES: dict[str, str] = {
    "helv": "Helvetica",
    "hebo": "Helvetica-Bold",
    "heit": "Helvetica-Oblique",
    "hebi": "Helvetica-BoldOblique",
    "tiro": "Times-Roman",
    "tibo": "Times-Bold",
    "tiit": "Times-Italic",
    "tibi": "Times-BoldItalic",
    "cour": "Courier",
    "cobo": "Courier-Bold",
    "coit": "Courier-Oblique",
    "cobi": "Courier-BoldOblique",
    "symb": "Symbol",
    "zadb": "ZapfDingbats",
    # Common full-name aliases
    "helvetica": "Helvetica",
    "times": "Times-Roman",
    "courier": "Courier",
}


def resolve_font(fontname: str) -> str:
    """Map fitz/openpdf font name to a reportlab font name."""
    return _FITZ_FONT_ALIASES.get(fontname.lower(), fontname)


class ReportLabBackend:
    """Wraps reportlab for PDF creation and drawing. All methods static."""

    # ---- Canvas creation ---------------------------------------------------

    @staticmethod
    def create_canvas(
        buffer: io.BytesIO,
        page_size: tuple[float, float] = (612.0, 792.0),
    ):
        """Return a reportlab Canvas writing to buffer."""
        from reportlab.pdfgen.canvas import Canvas
        return Canvas(buffer, pagesize=page_size)

    @staticmethod
    def finish(canvas) -> None:
        """Finalize the canvas (save to buffer)."""
        canvas.showPage()
        canvas.save()

    # ---- Drawing primitives (all coords in fitz top-left convention) -------

    @staticmethod
    def draw_line(
        canvas, p1: Point, p2: Point, color: tuple, width: float, page_h: float
    ) -> None:
        canvas.saveState()
        _set_stroke_color(canvas, color)
        canvas.setLineWidth(width)
        canvas.line(p1.x, page_h - p1.y, p2.x, page_h - p2.y)
        canvas.restoreState()

    @staticmethod
    def draw_rect(
        canvas, rect: Rect, color: tuple | None, fill: tuple | None,
        border_width: float, radius: float = 0, page_h: float = 792.0
    ) -> None:
        canvas.saveState()
        _set_stroke_color(canvas, color)
        if fill is not None:
            _set_fill_color(canvas, fill)
        canvas.setLineWidth(border_width)
        # reportlab rect: (x, y_bottom, width, height)
        x = rect.x0
        y_bottom = page_h - rect.y1
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        if radius > 0:
            canvas.roundRect(x, y_bottom, w, h, radius,
                             stroke=1 if color else 0,
                             fill=1 if fill else 0)
        else:
            canvas.rect(x, y_bottom, w, h,
                        stroke=1 if color else 0,
                        fill=1 if fill else 0)
        canvas.restoreState()

    @staticmethod
    def draw_circle(
        canvas, center: Point, radius: float,
        color: tuple | None, fill: tuple | None,
        border_width: float, page_h: float = 792.0
    ) -> None:
        canvas.saveState()
        _set_stroke_color(canvas, color)
        if fill is not None:
            _set_fill_color(canvas, fill)
        canvas.setLineWidth(border_width)
        canvas.circle(center.x, page_h - center.y, radius,
                      stroke=1 if color else 0,
                      fill=1 if fill else 0)
        canvas.restoreState()

    @staticmethod
    def draw_oval(
        canvas, rect: Rect, color: tuple | None, fill: tuple | None,
        border_width: float, page_h: float = 792.0
    ) -> None:
        canvas.saveState()
        _set_stroke_color(canvas, color)
        if fill is not None:
            _set_fill_color(canvas, fill)
        canvas.setLineWidth(border_width)
        x = rect.x0; y_bottom = page_h - rect.y1
        w = rect.x1 - rect.x0; h = rect.y1 - rect.y0
        canvas.ellipse(x, y_bottom, x + w, y_bottom + h,
                       stroke=1 if color else 0,
                       fill=1 if fill else 0)
        canvas.restoreState()

    @staticmethod
    def draw_polygon(
        canvas, points: list[Point], color: tuple | None, fill: tuple | None,
        border_width: float, page_h: float = 792.0
    ) -> None:
        if not points:
            return
        canvas.saveState()
        _set_stroke_color(canvas, color)
        if fill is not None:
            _set_fill_color(canvas, fill)
        canvas.setLineWidth(border_width)
        from reportlab.graphics.shapes import Polygon
        path = canvas.beginPath()
        path.moveTo(points[0].x, page_h - points[0].y)
        for pt in points[1:]:
            path.lineTo(pt.x, page_h - pt.y)
        path.close()
        canvas.drawPath(path, stroke=1 if color else 0, fill=1 if fill else 0)
        canvas.restoreState()

    @staticmethod
    def draw_polyline(
        canvas, points: list[Point], color: tuple, width: float, page_h: float = 792.0
    ) -> None:
        if len(points) < 2:
            return
        canvas.saveState()
        _set_stroke_color(canvas, color)
        canvas.setLineWidth(width)
        path = canvas.beginPath()
        path.moveTo(points[0].x, page_h - points[0].y)
        for pt in points[1:]:
            path.lineTo(pt.x, page_h - pt.y)
        canvas.drawPath(path, stroke=1, fill=0)
        canvas.restoreState()

    @staticmethod
    def draw_bezier(
        canvas, p1: Point, p2: Point, p3: Point, p4: Point,
        color: tuple, width: float, page_h: float = 792.0
    ) -> None:
        canvas.saveState()
        _set_stroke_color(canvas, color)
        canvas.setLineWidth(width)
        path = canvas.beginPath()
        path.moveTo(p1.x, page_h - p1.y)
        path.curveTo(p2.x, page_h - p2.y, p3.x, page_h - p3.y, p4.x, page_h - p4.y)
        canvas.drawPath(path, stroke=1, fill=0)
        canvas.restoreState()

    # ---- Text drawing ------------------------------------------------------

    @staticmethod
    def draw_text(
        canvas, point: Point, text: str, fontname: str, fontsize: float,
        color: tuple, page_h: float = 792.0, rotate: float = 0
    ) -> None:
        canvas.saveState()
        _set_fill_color(canvas, color)
        canvas.setFont(resolve_font(fontname), fontsize)
        if rotate:
            canvas.translate(point.x, page_h - point.y)
            canvas.rotate(rotate)
            canvas.drawString(0, 0, text)
        else:
            canvas.drawString(point.x, page_h - point.y, text)
        canvas.restoreState()

    @staticmethod
    def draw_text_in_rect(
        canvas, rect: Rect, text: str, fontname: str, fontsize: float,
        color: tuple, align: str = "left", page_h: float = 792.0
    ) -> float:
        """Draw text wrapped inside rect. Returns overflow height (negative = overflow)."""
        from reportlab.platypus import Paragraph, Frame
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        align_map = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}
        style = ParagraphStyle(
            "custom",
            fontName=resolve_font(fontname),
            fontSize=fontsize,
            alignment=align_map.get(align, TA_LEFT),
        )
        canvas.saveState()
        para = Paragraph(text, style)
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        y_bottom = page_h - rect.y1
        frame = Frame(rect.x0, y_bottom, w, h, showBoundary=0)
        frame.addFromList([para], canvas)
        canvas.restoreState()
        return 0.0  # Simplified; full overflow tracking requires platypus Story

    # ---- Image insertion ---------------------------------------------------

    @staticmethod
    def draw_image(
        canvas, rect: Rect, image_source, keep_aspect: bool = True,
        page_h: float = 792.0
    ) -> None:
        canvas.saveState()
        x = rect.x0
        y_bottom = page_h - rect.y1
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        canvas.drawImage(image_source, x, y_bottom, width=w, height=h,
                         preserveAspectRatio=keep_aspect, mask="auto")
        canvas.restoreState()

    # ---- Page management ---------------------------------------------------

    @staticmethod
    def new_page(canvas, page_size: tuple | None = None) -> None:
        if page_size:
            canvas.setPageSize(page_size)
        canvas.showPage()

    # ---- Table helper ------------------------------------------------------

    @staticmethod
    def draw_table(
        canvas, origin: Point, data: list[list[str]],
        col_widths, row_heights, style_commands,
        page_h: float = 792.0,
    ) -> Rect:
        from reportlab.platypus import Table, TableStyle
        table = Table(data, colWidths=col_widths, rowHeights=row_heights)
        if style_commands:
            table.setStyle(TableStyle(style_commands))
        w, h = table.wrapOn(canvas, 10000, 10000)
        y_bottom = page_h - origin.y - h
        table.drawOn(canvas, origin.x, y_bottom)
        return Rect(origin.x, origin.y, origin.x + w, origin.y + h)

    # ---- Overlay PDF creation ----------------------------------------------

    @staticmethod
    def create_overlay_pdf(
        draw_commands: list,
        page_size: tuple[float, float],
    ) -> bytes:
        """Create a minimal single-page PDF containing the given draw commands.

        draw_commands is a list of callables: fn(canvas, page_h) → None
        Returns raw PDF bytes.
        """
        buf = io.BytesIO()
        canvas = ReportLabBackend.create_canvas(buf, page_size)
        page_h = page_size[1]
        for cmd in draw_commands:
            cmd(canvas, page_h)
        ReportLabBackend.finish(canvas)
        buf.seek(0)
        return buf.read()


# ---------------------------------------------------------------------------
# Private color helpers
# ---------------------------------------------------------------------------


def _set_stroke_color(canvas, color: tuple | None) -> None:
    if color is None:
        return
    n = len(color)
    if n == 1:
        canvas.setStrokeGray(color[0])
    elif n == 3:
        canvas.setStrokeColorRGB(*color)
    elif n == 4:
        canvas.setStrokeColorCMYK(*color)


def _set_fill_color(canvas, color: tuple | None) -> None:
    if color is None:
        return
    n = len(color)
    if n == 1:
        canvas.setFillGray(color[0])
    elif n == 3:
        canvas.setFillColorRGB(*color)
    elif n == 4:
        canvas.setFillColorCMYK(*color)
