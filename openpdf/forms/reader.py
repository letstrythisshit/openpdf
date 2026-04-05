"""Read form fields from a Document."""
from __future__ import annotations

from typing import TYPE_CHECKING

from openpdf.forms.models import Widget
from openpdf.backends.pike import PikeBackend

if TYPE_CHECKING:
    from openpdf.document import Document
    from openpdf.page import Page


def get_widgets_for_page(page: "Page") -> list[Widget]:
    """Return all Widget objects for the given page."""
    fields = PikeBackend.get_form_fields(page.parent._pike)
    return [
        Widget.from_field_dict(f, page)
        for f in fields
        if f.get("page") == page.number
    ]


def get_all_fields(doc: "Document") -> list[Widget]:
    """Return all form fields across the document."""
    from openpdf.page import Page
    fields = PikeBackend.get_form_fields(doc._pike)
    result = []
    for f in fields:
        page_num = f.get("page", 0)
        page = Page(doc, page_num)
        result.append(Widget.from_field_dict(f, page))
    return result
