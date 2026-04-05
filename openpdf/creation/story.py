"""Story-based text flow — deferred to v0.3."""
from __future__ import annotations


class Story:
    """Mirrors fitz.Story for flow-based HTML→PDF layout. Not yet implemented."""

    def __init__(self, html: str = "", user_css: str = "") -> None:
        raise NotImplementedError(
            "Story is not yet implemented in OpenPDF v0.1. "
            "Use DocumentBuilder.draw_textbox() or page.insert_htmlbox() for basic text layout."
        )
