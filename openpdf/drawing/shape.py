"""Shape class — vector drawing accumulator. Mirrors fitz.Shape."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openpdf.geometry import Point, Rect, Quad, Matrix
from openpdf.color import normalize_color, color_to_pdf_ops

if TYPE_CHECKING:
    from openpdf.page import Page
    from openpdf.document import Document

# Bezier approximation constant for quarter circles
_CIRCLE_BEZIER_K = 0.5523


# ---------------------------------------------------------------------------
# Command objects (stored before rendering to allow morph transformation)
# ---------------------------------------------------------------------------

@dataclass
class _MoveCmd:
    x: float; y: float  # PDF coordinates (bottom-left origin)

@dataclass
class _LineCmd:
    x: float; y: float

@dataclass
class _CurveCmd:
    x1: float; y1: float
    x2: float; y2: float
    x3: float; y3: float

@dataclass
class _CloseCmd:
    pass

@dataclass
class _RectCmd:
    x: float; y: float; w: float; h: float  # PDF coords (x, y_bottom, w, h)


class Shape:
    """Accumulates drawing commands and commits them to a page via overlay strategy."""

    def __init__(self, page: "Page") -> None:
        self._page = page
        self._draw_commands: list = []   # path command objects (in PDF coords)
        self._finish_commands: list = [] # callable(canvas, page_h) after finish()
        self._total_rect = Rect()
        self._last_point = Point()
        self._text_commands: list = []   # text draw callables

    @property
    def doc(self) -> "Document":
        return self._page.parent

    @property
    def page(self) -> "Page":
        return self._page

    @property
    def totalRect(self) -> Rect:
        return self._total_rect

    @property
    def lastPoint(self) -> Point:
        return self._last_point

    # ---- Coordinate helpers ------------------------------------------------

    def _to_pdf_y(self, y_fitz: float) -> float:
        """Convert fitz y-coord to PDF y-coord."""
        return self._page.height - y_fitz

    def _update_total_rect(self, pt: Point) -> None:
        if self._total_rect.is_empty:
            self._total_rect = Rect(pt.x, pt.y, pt.x, pt.y)
        else:
            self._total_rect = self._total_rect.include_point(pt)

    # ---- Drawing primitives ------------------------------------------------

    def draw_line(self, p1: Point, p2: Point) -> Point:
        self._draw_commands.append(_MoveCmd(p1.x, self._to_pdf_y(p1.y)))
        self._draw_commands.append(_LineCmd(p2.x, self._to_pdf_y(p2.y)))
        self._update_total_rect(p1)
        self._update_total_rect(p2)
        self._last_point = p2
        return p2

    def draw_rect(self, rect: Rect) -> Point:
        x = rect.x0
        y_bottom = self._to_pdf_y(rect.y1)
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        self._draw_commands.append(_RectCmd(x, y_bottom, w, h))
        self._update_total_rect(rect.top_left)
        self._update_total_rect(rect.bottom_right)
        self._last_point = rect.bottom_right
        return rect.bottom_right

    def draw_circle(self, center: Point, radius: float) -> Point:
        """Approximate circle using 4 cubic Bezier curves."""
        k = radius * _CIRCLE_BEZIER_K
        cx = center.x; cy = center.y
        # Right point going counter-clockwise in fitz coords
        # PDF coords: bottom-left origin
        ccy = self._to_pdf_y(cy)

        self._draw_commands.append(_MoveCmd(cx + radius, ccy))
        # Bottom quarter (fitz: bottom is higher y value)
        self._draw_commands.append(_CurveCmd(
            cx + radius, ccy - k,
            cx + k, ccy - radius,
            cx, ccy - radius,
        ))
        self._draw_commands.append(_CurveCmd(
            cx - k, ccy - radius,
            cx - radius, ccy - k,
            cx - radius, ccy,
        ))
        self._draw_commands.append(_CurveCmd(
            cx - radius, ccy + k,
            cx - k, ccy + radius,
            cx, ccy + radius,
        ))
        self._draw_commands.append(_CurveCmd(
            cx + k, ccy + radius,
            cx + radius, ccy + k,
            cx + radius, ccy,
        ))
        self._draw_commands.append(_CloseCmd())

        rect = Rect(cx - radius, cy - radius, cx + radius, cy + radius)
        self._update_total_rect(rect.top_left)
        self._update_total_rect(rect.bottom_right)
        self._last_point = center
        return center

    def draw_oval(self, rect: Rect) -> Point:
        """Approximate ellipse using 4 Bezier curves."""
        cx = (rect.x0 + rect.x1) / 2
        cy = (rect.y0 + rect.y1) / 2
        rx = (rect.x1 - rect.x0) / 2
        ry = (rect.y1 - rect.y0) / 2
        kx = rx * _CIRCLE_BEZIER_K
        ky = ry * _CIRCLE_BEZIER_K
        ccy = self._to_pdf_y(cy)

        self._draw_commands.append(_MoveCmd(cx + rx, ccy))
        self._draw_commands.append(_CurveCmd(cx + rx, ccy - ky, cx + kx, ccy - ry, cx, ccy - ry))
        self._draw_commands.append(_CurveCmd(cx - kx, ccy - ry, cx - rx, ccy - ky, cx - rx, ccy))
        self._draw_commands.append(_CurveCmd(cx - rx, ccy + ky, cx - kx, ccy + ry, cx, ccy + ry))
        self._draw_commands.append(_CurveCmd(cx + kx, ccy + ry, cx + rx, ccy + ky, cx + rx, ccy))
        self._draw_commands.append(_CloseCmd())

        self._update_total_rect(rect.top_left)
        self._update_total_rect(rect.bottom_right)
        self._last_point = Point(cx, cy)
        return self._last_point

    def draw_quad(self, quad: Quad) -> Point:
        # Draw as polygon
        return self.draw_polygon([quad.ul, quad.ur, quad.lr, quad.ll])

    def draw_polyline(self, points: list[Point]) -> Point:
        if not points:
            return Point()
        self._draw_commands.append(_MoveCmd(points[0].x, self._to_pdf_y(points[0].y)))
        for pt in points[1:]:
            self._draw_commands.append(_LineCmd(pt.x, self._to_pdf_y(pt.y)))
            self._update_total_rect(pt)
        self._last_point = points[-1]
        return self._last_point

    def draw_polygon(self, points: list[Point]) -> Point:
        result = self.draw_polyline(points)
        self._draw_commands.append(_CloseCmd())
        return result

    def draw_bezier(self, p1: Point, p2: Point, p3: Point, p4: Point) -> Point:
        self._draw_commands.append(_MoveCmd(p1.x, self._to_pdf_y(p1.y)))
        self._draw_commands.append(_CurveCmd(
            p2.x, self._to_pdf_y(p2.y),
            p3.x, self._to_pdf_y(p3.y),
            p4.x, self._to_pdf_y(p4.y),
        ))
        for pt in [p1, p2, p3, p4]:
            self._update_total_rect(pt)
        self._last_point = p4
        return p4

    def draw_curve(self, p1: Point, p2: Point, p3: Point) -> Point:
        """Quadratic Bezier approximated as cubic."""
        # Convert quadratic p1,p2,p3 to cubic: cp1 = p1 + 2/3*(p2-p1), cp2 = p3 + 2/3*(p2-p3)
        cp1 = p1 + (p2 - p1) * (2.0 / 3.0)
        cp2 = p3 + (p2 - p3) * (2.0 / 3.0)
        return self.draw_bezier(p1, cp1, cp2, p3)

    def draw_squiggle(self, p1: Point, p2: Point, breadth: float = 2) -> Point:
        """Draw a wavy (squiggle) line from p1 to p2."""
        dx = p2.x - p1.x; dy = p2.y - p1.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return p2
        n_waves = max(1, int(length / (breadth * 2)))
        # Perpendicular direction
        px = -dy / length * breadth
        py = dx / length * breadth
        pts = [p1]
        for i in range(n_waves):
            t1 = (2 * i + 1) / (2 * n_waves)
            t2 = (2 * i + 2) / (2 * n_waves)
            mid1 = Point(p1.x + dx * t1 + px, p1.y + dy * t1 + py)
            mid2 = Point(p1.x + dx * t2, p1.y + dy * t2)
            pts.append(mid1)
            pts.append(mid2)
        pts.append(p2)
        return self.draw_polyline(pts)

    def draw_zigzag(self, p1: Point, p2: Point, breadth: float = 2) -> Point:
        """Draw a zigzag line from p1 to p2."""
        dx = p2.x - p1.x; dy = p2.y - p1.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return p2
        n_zigs = max(1, int(length / (breadth * 2)))
        px = -dy / length * breadth; py = dx / length * breadth
        pts = [p1]
        for i in range(n_zigs):
            t = (2 * i + 1) / (2 * n_zigs)
            side = 1 if i % 2 == 0 else -1
            mid = Point(p1.x + dx * t + px * side, p1.y + dy * t + py * side)
            pts.append(mid)
        pts.append(p2)
        return self.draw_polyline(pts)

    def draw_sector(
        self, center: Point, point: Point, angle: float, fullSector: bool = True
    ) -> Point:
        """Draw an arc sector."""
        radius = center.distance_to(point)
        start_angle = math.degrees(math.atan2(-(point.y - center.y), point.x - center.x))
        end_angle = start_angle + angle
        # Approximate arc with line segments
        steps = max(8, int(abs(angle) / 5))
        pts = []
        if fullSector:
            pts.append(center)
        for i in range(steps + 1):
            a = math.radians(start_angle + (end_angle - start_angle) * i / steps)
            pts.append(Point(center.x + radius * math.cos(a),
                             center.y - radius * math.sin(a)))  # fitz y-down
        if fullSector:
            pts.append(center)
        if pts:
            self.draw_polygon(pts)
        return point

    # ---- Finish (apply stroke/fill settings) --------------------------------

    def finish(
        self,
        color: tuple | None = (0, 0, 0),
        fill: tuple | None = None,
        width: float = 1,
        dashes: str | None = None,
        lineCap: int = 0,
        lineJoin: int = 0,
        morph: tuple | None = None,
        closePath: bool = True,
        even_odd: bool = False,
        opacity: float = 1.0,
        blend_mode: str = "Normal",
    ) -> None:
        """Compile accumulated draw commands into a reportlab-callable."""
        commands = list(self._draw_commands)
        self._draw_commands.clear()

        norm_color = normalize_color(color)
        norm_fill = normalize_color(fill)

        def draw_cmd(canvas, page_h, _cmds=commands, _color=norm_color, _fill=norm_fill,
                     _width=width, _lc=lineCap, _lj=lineJoin, _op=opacity):
            from openpdf.backends.rlab import _set_stroke_color, _set_fill_color
            canvas.saveState()

            if _op < 1.0:
                canvas.setFillAlpha(_op)
                canvas.setStrokeAlpha(_op)

            if _color:
                _set_stroke_color(canvas, _color)
            if _fill:
                _set_fill_color(canvas, _fill)
            canvas.setLineWidth(_width)
            canvas.setLineCap(_lc)
            canvas.setLineJoin(_lj)

            path = canvas.beginPath()
            for cmd in _cmds:
                if isinstance(cmd, _MoveCmd):
                    path.moveTo(cmd.x, cmd.y)
                elif isinstance(cmd, _LineCmd):
                    path.lineTo(cmd.x, cmd.y)
                elif isinstance(cmd, _CurveCmd):
                    path.curveTo(cmd.x1, cmd.y1, cmd.x2, cmd.y2, cmd.x3, cmd.y3)
                elif isinstance(cmd, _CloseCmd):
                    path.close()
                elif isinstance(cmd, _RectCmd):
                    path.rect(cmd.x, cmd.y, cmd.w, cmd.h)

            do_stroke = 1 if _color else 0
            do_fill = 1 if _fill else 0
            canvas.drawPath(path, stroke=do_stroke, fill=do_fill)
            canvas.restoreState()

        self._finish_commands.append(draw_cmd)

    # ---- Text insertion ----------------------------------------------------

    def insert_text(
        self, point: Point, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), rotate: float = 0,
        **kwargs,
    ) -> int:
        from openpdf.backends.rlab import ReportLabBackend
        norm_color = normalize_color(color)

        def text_cmd(canvas, ph, _pt=point, _t=text, _fn=fontname, _fs=fontsize,
                     _c=norm_color, _r=rotate):
            ReportLabBackend.draw_text(canvas, _pt, _t, _fn, _fs, _c or (0, 0, 0), ph, _r)

        self._finish_commands.append(text_cmd)
        lines = text.count("\n") + 1
        return lines

    def insert_textbox(
        self, rect: Rect, text: str,
        fontsize: float = 11, fontname: str = "helv",
        color: tuple = (0, 0, 0), align: int = 0,
        rotate: float = 0, **kwargs,
    ) -> float:
        from openpdf.backends.rlab import ReportLabBackend
        align_str = {0: "left", 1: "center", 2: "right"}.get(align, "left")
        norm_color = normalize_color(color)

        def text_cmd(canvas, ph, _r=rect, _t=text, _fn=fontname, _fs=fontsize,
                     _c=norm_color, _a=align_str):
            ReportLabBackend.draw_text_in_rect(canvas, _r, _t, _fn, _fs, _c or (0, 0, 0), _a, ph)

        self._finish_commands.append(text_cmd)
        return 0.0

    # ---- Commit to page ----------------------------------------------------

    def commit(self, overlay: bool = True) -> None:
        """Render all accumulated commands into the page via overlay strategy."""
        if not self._finish_commands:
            return
        from openpdf.drawing.canvas import commit_overlay
        commit_overlay(self._page, self._finish_commands)
        self._finish_commands.clear()
        self._total_rect = Rect()
        self._last_point = Point()
