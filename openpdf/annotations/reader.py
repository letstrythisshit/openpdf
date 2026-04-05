"""Read annotations from pages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from openpdf.annotations.models import Annotation
from openpdf.backends.pike import PikeBackend

if TYPE_CHECKING:
    from openpdf.page import Page


def get_annots(page: "Page", types: list | None = None) -> Iterator[Annotation]:
    """Yield Annotation objects for each annotation on the page."""
    raw_list = PikeBackend.get_annotations(page.parent._pike, page.number)
    for raw in raw_list:
        annot = Annotation.from_raw(raw, page)
        if types is None or annot.type[0] in types:
            yield annot
