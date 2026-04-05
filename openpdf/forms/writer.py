"""Fill / modify form fields."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openpdf.backends.pike import PikeBackend

if TYPE_CHECKING:
    from openpdf.document import Document


def set_field_value(doc: "Document", field_name: str, value: Any) -> None:
    """Set the value of a form field by name."""
    PikeBackend.set_form_field_value(doc._pike, field_name, value)
    doc._mark_dirty()
