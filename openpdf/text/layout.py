"""Layout analysis — thin pdfminer wrapper used internally."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openpdf.page import Page


def get_page_layout(page: "Page"):
    """Return pdfminer LTPage for the given page."""
    from openpdf.backends.miner import MinerBackend
    source = page.parent._get_bytes_for_miner()
    return MinerBackend.extract_page_layout(source, page.number)
