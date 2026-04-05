"""Table builder helper — thin wrapper over reportlab Table."""
from __future__ import annotations

from openpdf.geometry import Point, Rect


def draw_table(
    canvas,
    origin: Point,
    data: list[list[str]],
    col_widths=None,
    row_heights=None,
    style_commands=None,
    page_h: float = 792.0,
) -> Rect:
    """Draw a table at the given origin using reportlab."""
    from openpdf.backends.rlab import ReportLabBackend
    return ReportLabBackend.draw_table(
        canvas, origin, data, col_widths, row_heights, style_commands, page_h
    )
