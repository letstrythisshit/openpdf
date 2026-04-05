"""Text search with hit rectangles."""
from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

from openpdf.geometry import Rect, Quad

if TYPE_CHECKING:
    from openpdf.page import Page


def search_page_for(
    page: "Page",
    needle: str,
    clip: Rect | None = None,
    quads: bool = False,
    hit_max: int = 16,
) -> list[Rect] | list[Quad]:
    """Find all occurrences of needle on the page. Returns list of Rect or Quad."""
    if not needle:
        return []

    source = page.parent._get_bytes_for_miner()
    from openpdf.backends.miner import MinerBackend
    words = MinerBackend.extract_text_words(source, page.number)

    if not words:
        return []

    # Normalize for case-insensitive matching
    needle_norm = _normalize(needle)
    word_texts = [_normalize(w[4]) for w in words]

    # Build joined string with position tracking
    joined_parts: list[tuple[int, int]] = []  # (word_idx, char_start_in_joined)
    joined = ""
    for i, wtext in enumerate(word_texts):
        start = len(joined)
        joined += wtext + " "
        joined_parts.append((i, start))

    needle_words = needle_norm.split()
    if not needle_words:
        return []

    hits = []
    search_str = " ".join(needle_words)
    pos = 0
    while pos < len(joined) and len(hits) < hit_max:
        idx = joined.find(search_str, pos)
        if idx < 0:
            break

        # Find which words are covered
        end_idx = idx + len(search_str)
        covered = []
        for wi, (w_idx, char_start) in enumerate(joined_parts):
            w_end = char_start + len(word_texts[w_idx])
            if char_start < end_idx and w_end > idx:
                covered.append(w_idx)

        if covered:
            # Union of bounding boxes of covered words
            rects = [Rect(words[i][0], words[i][1], words[i][2], words[i][3]) for i in covered]
            union = rects[0]
            for r in rects[1:]:
                union = union.include_rect(r)

            if clip is None or union.intersects(clip):
                hits.append(union.quad if quads else union)

        pos = idx + 1

    return hits[:hit_max]


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).lower()
