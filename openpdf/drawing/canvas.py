"""Low-level canvas operations — the overlay merge pipeline."""
from __future__ import annotations

from typing import TYPE_CHECKING

from openpdf.backends.pike import PikeBackend
from openpdf.backends.rlab import ReportLabBackend

if TYPE_CHECKING:
    from openpdf.page import Page


def commit_overlay(page: "Page", draw_commands: list) -> None:
    """Execute draw commands and merge them as a Form XObject overlay onto the page.

    draw_commands: list of callables fn(canvas, page_height) -> None
    """
    page_w = page.width
    page_h = page.height

    overlay_bytes = ReportLabBackend.create_overlay_pdf(draw_commands, (page_w, page_h))
    PikeBackend.overlay_page(page.parent._pike, page.number, overlay_bytes)
    page.parent._mark_dirty()
