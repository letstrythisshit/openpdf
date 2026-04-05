"""TOC / bookmark tree classes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OutlineItem:
    """Single TOC entry."""
    level: int = 1            # 1-based depth
    title: str = ""
    page: int = 0             # 0-based target page
    dest: dict | None = None  # destination details (kind, to, zoom, etc.)
    color: tuple | None = None
    bold: bool = False
    italic: bool = False
    collapse: bool = False


class Outline:
    """Iterable TOC tree node. Mirrors fitz.Document.outline (first outline entry).

    Each node has .down (first child) and .next (next sibling).
    """

    def __init__(
        self,
        title: str = "",
        page: int = 0,
        dest: dict | None = None,
        uri: str | None = None,
        bold: bool = False,
        italic: bool = False,
        color: tuple | None = None,
        collapse: bool = False,
    ) -> None:
        self.title = title
        self.page = page
        self.dest = dest or {}
        self.uri = uri
        self.bold = bold
        self.italic = italic
        self.color = color
        self.collapse = collapse
        self.down: Optional["Outline"] = None   # first child
        self.next: Optional["Outline"] = None   # next sibling

    @property
    def is_external(self) -> bool:
        return self.uri is not None

    @classmethod
    def from_toc(cls, toc: list) -> Optional["Outline"]:
        """Build a linked-list Outline tree from a flat TOC list.

        toc: [[level, title, page, dest?], ...]
        Returns the first root node, or None if toc is empty.
        """
        if not toc:
            return None

        nodes = [
            cls(
                title=entry[1] if len(entry) > 1 else "",
                page=entry[2] if len(entry) > 2 else 0,
                dest=entry[3] if len(entry) > 3 else None,
            )
            for entry in toc
        ]
        levels = [entry[0] if len(entry) > 0 else 1 for entry in toc]

        # Build tree: stack of (level, node)
        stack: list[tuple[int, "Outline"]] = []
        roots: list["Outline"] = []

        for i, (node, level) in enumerate(zip(nodes, levels)):
            # Pop stack to find parent
            while stack and stack[-1][0] >= level:
                stack.pop()

            if not stack:
                # Root node
                if roots:
                    roots[-1].next = node
                roots.append(node)
            else:
                parent = stack[-1][1]
                if parent.down is None:
                    parent.down = node
                else:
                    # Find last sibling
                    sibling = parent.down
                    while sibling.next is not None:
                        sibling = sibling.next
                    sibling.next = node

            stack.append((level, node))

        return roots[0] if roots else None

    def __repr__(self) -> str:
        return f"Outline({self.title!r}, page={self.page})"
