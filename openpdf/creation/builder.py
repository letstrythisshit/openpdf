"""DocumentBuilder — create PDFs from scratch using reportlab."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

from openpdf.geometry import Point, Rect
from openpdf.backends.rlab import ReportLabBackend


class DocumentBuilder:
    """Build a new PDF from scratch.

    Usage:
        builder = DocumentBuilder("output.pdf", page_size=(612, 792))
        builder.add_page()
        builder.draw_text(Point(72, 700), "Hello, World!", fontsize=24)
        builder.draw_rect(Rect(72, 500, 300, 600), fill=(0.9, 0.9, 1.0))
        doc = builder.finish()   # returns a Document for further manipulation
    """

    def __init__(
        self,
        path_or_buffer: Union[str, Path, io.BytesIO, None] = None,
        page_size: tuple[float, float] = (612.0, 792.0),
    ) -> None:
        self._output_path = Path(path_or_buffer) if isinstance(path_or_buffer, (str, Path)) else None
        self._page_size = page_size
        self._page_h = page_size[1]
        self._buf = io.BytesIO()
        self._canvas = ReportLabBackend.create_canvas(self._buf, page_size)
        self._page_count = 0
        self._current_page = -1

    def add_page(self, page_size: tuple | None = None) -> int:
        if self._page_count > 0:
            ReportLabBackend.new_page(self._canvas, page_size or self._page_size)
        if page_size:
            self._page_h = page_size[1]
            self._canvas.setPageSize(page_size)
        self._page_count += 1
        self._current_page = self._page_count - 1
        return self._current_page

    def set_current_page(self, page_index: int) -> None:
        self._current_page = page_index

    # ---- Drawing methods ---------------------------------------------------

    def draw_text(
        self, point: Point, text: str,
        fontsize: float = 11, fontname: str = "Helvetica",
        color: tuple = (0, 0, 0), rotate: float = 0,
    ) -> None:
        ReportLabBackend.draw_text(
            self._canvas, point, text, fontname, fontsize, color, self._page_h, rotate
        )

    def draw_textbox(
        self, rect: Rect, text: str,
        fontsize: float = 11, fontname: str = "Helvetica",
        color: tuple = (0, 0, 0), align: str = "left",
    ) -> None:
        ReportLabBackend.draw_text_in_rect(
            self._canvas, rect, text, fontname, fontsize, color, align, self._page_h
        )

    def draw_line(
        self, p1: Point, p2: Point,
        color: tuple = (0, 0, 0), width: float = 1,
    ) -> None:
        ReportLabBackend.draw_line(self._canvas, p1, p2, color, width, self._page_h)

    def draw_rect(
        self, rect: Rect,
        color: tuple | None = (0, 0, 0), fill: tuple | None = None,
        width: float = 1, radius: float = 0,
    ) -> None:
        ReportLabBackend.draw_rect(
            self._canvas, rect, color, fill, width, radius, self._page_h
        )

    def draw_circle(
        self, center: Point, radius: float,
        color: tuple | None = (0, 0, 0), fill: tuple | None = None, width: float = 1,
    ) -> None:
        ReportLabBackend.draw_circle(
            self._canvas, center, radius, color, fill, width, self._page_h
        )

    def draw_oval(
        self, rect: Rect,
        color: tuple | None = (0, 0, 0), fill: tuple | None = None, width: float = 1,
    ) -> None:
        ReportLabBackend.draw_oval(self._canvas, rect, color, fill, width, self._page_h)

    def draw_polygon(
        self, points: list[Point],
        color: tuple | None = (0, 0, 0), fill: tuple | None = None, width: float = 1,
    ) -> None:
        ReportLabBackend.draw_polygon(self._canvas, points, color, fill, width, self._page_h)

    def draw_polyline(
        self, points: list[Point], color: tuple = (0, 0, 0), width: float = 1,
    ) -> None:
        ReportLabBackend.draw_polyline(self._canvas, points, color, width, self._page_h)

    def draw_bezier(
        self, p1: Point, p2: Point, p3: Point, p4: Point,
        color: tuple = (0, 0, 0), width: float = 1,
    ) -> None:
        ReportLabBackend.draw_bezier(self._canvas, p1, p2, p3, p4, color, width, self._page_h)

    def draw_image(
        self, rect: Rect, image, keep_aspect: bool = True,
    ) -> None:
        ReportLabBackend.draw_image(self._canvas, rect, image, keep_aspect, self._page_h)

    def draw_table(
        self, origin: Point, data: list[list[str]],
        col_widths=None, row_heights=None, style=None,
    ) -> Rect:
        return ReportLabBackend.draw_table(
            self._canvas, origin, data, col_widths, row_heights, style, self._page_h
        )

    # ---- Metadata ----------------------------------------------------------

    def set_title(self, title: str) -> None:
        self._canvas.setTitle(title)

    def set_author(self, author: str) -> None:
        self._canvas.setAuthor(author)

    def set_subject(self, subject: str) -> None:
        self._canvas.setSubject(subject)

    # ---- Finish ------------------------------------------------------------

    def finish(self) -> "Document":  # type: ignore[return]
        """Finalize the canvas and return a Document for further manipulation."""
        from openpdf.document import Document
        ReportLabBackend.finish(self._canvas)
        data = self._buf.getvalue()
        if self._output_path is not None:
            self._output_path.write_bytes(data)
        return Document(stream=data)
