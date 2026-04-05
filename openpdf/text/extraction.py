"""TextPage — reusable text extraction handle for a single page."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openpdf.page import Page


class TextPage:
    """Pre-computed text extraction result for efficient re-querying.

    Caches results per extraction mode. Invalidates when the document changes
    (detected via document _revision counter).
    """

    def __init__(self, page: "Page", flags: int = 0) -> None:
        self._page = page
        self._flags = flags
        self._creation_revision = page.parent._revision
        self._cache: dict = {}

    def _is_stale(self) -> bool:
        return self._page.parent._revision != self._creation_revision

    def _refresh_if_needed(self) -> None:
        if self._is_stale():
            self._cache.clear()
            self._creation_revision = self._page.parent._revision

    def _get(self, mode: str):
        self._refresh_if_needed()
        if mode not in self._cache:
            self._cache[mode] = self._page.get_text(mode)
        return self._cache[mode]

    # ---- fitz-compatible extraction methods --------------------------------

    def extractText(self) -> str:
        return self._get("text")

    def extractBLOCKS(self) -> list:
        return self._get("blocks")

    def extractWORDS(self) -> list:
        return self._get("words")

    def extractDICT(self, sort: bool = False) -> dict:
        return self._get("dict")

    def extractRAWDICT(self, sort: bool = False) -> dict:
        return self._get("rawdict")

    def extractHTML(self) -> str:
        return self._get("html")

    def extractXHTML(self) -> str:
        return self._get("xhtml")

    def extractXML(self) -> str:
        return self._get("xml")

    def search(self, needle: str, quads: bool = False, hit_max: int = 16) -> list:
        return self._page.search_for(needle, quads=quads, hit_max=hit_max)
