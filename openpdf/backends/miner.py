"""pdfminer.six backend — layout-aware text extraction.

pdfminer is stateless: every call takes bytes or a file path.
The Document facade is responsible for passing fresh bytes after mutations.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

from openpdf.geometry import Rect, Point
from openpdf.exceptions import FileDataError
from openpdf.utils.io import pdf_to_fitz_rect


# Tuned LAParams for best balance of accuracy and performance
_LAPARAMS_DEFAULTS = dict(
    line_margin=0.5,
    word_margin=0.1,
    char_margin=2.0,
    boxes_flow=0.5,
)


class MinerBackend:
    """Wraps pdfminer.six for layout-aware text extraction. All methods static."""

    @staticmethod
    def extract_text_simple(source: bytes, page_numbers: list[int] | None = None) -> str:
        """Full plain-text extraction using pdfminer's high-level API."""
        from pdfminer.high_level import extract_text
        try:
            return extract_text(
                io.BytesIO(source),
                page_numbers=page_numbers,
                laparams=_make_laparams(),
            )
        except Exception as exc:
            raise FileDataError(f"pdfminer text extraction failed: {exc}") from exc

    @staticmethod
    def extract_page_layout(source: bytes, page_index: int):
        """Return pdfminer LTPage for the given page index."""
        from pdfminer.high_level import extract_pages
        try:
            layouts = list(extract_pages(
                io.BytesIO(source),
                page_numbers=[page_index],
                laparams=_make_laparams(),
            ))
            if not layouts:
                return None
            return layouts[0]
        except Exception as exc:
            raise FileDataError(f"pdfminer layout extraction failed: {exc}") from exc

    @staticmethod
    def extract_text_dict(source: bytes, page_index: int) -> dict:
        """Return fitz-compatible get_text("dict") structure."""
        layout = MinerBackend.extract_page_layout(source, page_index)
        if layout is None:
            return {"width": 0, "height": 0, "blocks": []}
        page_h = float(layout.height)
        return _layout_to_dict(layout, page_h)

    @staticmethod
    def extract_text_rawdict(source: bytes, page_index: int) -> dict:
        """Return fitz-compatible get_text("rawdict") structure (per-char data)."""
        layout = MinerBackend.extract_page_layout(source, page_index)
        if layout is None:
            return {"width": 0, "height": 0, "blocks": []}
        page_h = float(layout.height)
        return _layout_to_dict(layout, page_h, rawdict=True)

    @staticmethod
    def extract_text_blocks(source: bytes, page_index: int) -> list[tuple]:
        """Return list of block tuples: (x0, y0, x1, y1, text, block_no, block_type)."""
        d = MinerBackend.extract_text_dict(source, page_index)
        result = []
        for block in d.get("blocks", []):
            bbox = block["bbox"]
            btype = block.get("type", 0)
            if btype == 0:
                text = "\n".join(
                    "".join(sp["text"] for sp in line["spans"])
                    for line in block.get("lines", [])
                )
            else:
                text = ""
            result.append((bbox[0], bbox[1], bbox[2], bbox[3], text,
                           block.get("number", 0), btype))
        return result

    @staticmethod
    def extract_text_words(source: bytes, page_index: int) -> list[tuple]:
        """Return list of word tuples: (x0, y0, x1, y1, word, block_no, line_no, word_no)."""
        d = MinerBackend.extract_text_dict(source, page_index)
        words = []
        for block in d.get("blocks", []):
            if block.get("type", 0) != 0:
                continue
            block_no = block.get("number", 0)
            for line_no, line in enumerate(block.get("lines", [])):
                line_text = "".join(sp["text"] for sp in line.get("spans", []))
                # Split into words, track positions via character data
                raw_words = line_text.split()
                if not raw_words:
                    continue
                # Approximate word bbox by splitting span bbox proportionally
                line_bbox = line["bbox"]
                line_w = max(line_bbox[2] - line_bbox[0], 1.0)
                char_w = line_w / max(len(line_text), 1)
                char_pos = 0
                for word_no, word in enumerate(raw_words):
                    start = line_text.find(word, char_pos)
                    if start < 0:
                        start = char_pos
                    end = start + len(word)
                    x0 = line_bbox[0] + start * char_w
                    x1 = line_bbox[0] + end * char_w
                    y0 = line_bbox[1]
                    y1 = line_bbox[3]
                    words.append((x0, y0, x1, y1, word, block_no, line_no, word_no))
                    char_pos = end
        return words

    @staticmethod
    def extract_text_html(source: bytes, page_index: int) -> str:
        """Return HTML representation of page text."""
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextBox, LTAnno, LTChar
        layout = MinerBackend.extract_page_layout(source, page_index)
        if layout is None:
            return "<html><body></body></html>"
        page_h = float(layout.height)
        parts = ["<html><body>"]
        for block in layout:
            if hasattr(block, "__iter__"):
                for line in block:
                    if hasattr(line, "__iter__"):
                        line_text = ""
                        for char in line:
                            if hasattr(char, "get_text"):
                                line_text += char.get_text()
                        if line_text.strip():
                            parts.append(f"<p>{line_text.strip()}</p>")
        parts.append("</body></html>")
        return "\n".join(parts)

    @staticmethod
    def extract_text_xhtml(source: bytes, page_index: int) -> str:
        html = MinerBackend.extract_text_html(source, page_index)
        return html.replace("<html>", '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml">', 1)

    @staticmethod
    def extract_text_xml(source: bytes, page_index: int) -> str:
        d = MinerBackend.extract_text_dict(source, page_index)
        parts = ['<?xml version="1.0"?>', "<page>"]
        for block in d.get("blocks", []):
            parts.append(f'  <block bbox="{block["bbox"]}">')
            for line in block.get("lines", []):
                text = "".join(sp["text"] for sp in line.get("spans", []))
                parts.append(f'    <line bbox="{line["bbox"]}">{text}</line>')
            parts.append("  </block>")
        parts.append("</page>")
        return "\n".join(parts)

    @staticmethod
    def get_fonts(source: bytes, page_index: int) -> list[dict]:
        """Return list of FontInfo dicts for the page."""
        layout = MinerBackend.extract_page_layout(source, page_index)
        if layout is None:
            return []
        fonts = {}
        _collect_fonts(layout, fonts)
        return list(fonts.values())


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _make_laparams():
    from pdfminer.layout import LAParams
    return LAParams(**_LAPARAMS_DEFAULTS)


def _layout_to_dict(layout, page_h: float, rawdict: bool = False) -> dict:
    """Convert pdfminer LTPage to fitz-compatible dict structure."""
    from pdfminer.layout import LTTextBox, LTTextLine, LTChar, LTAnno, LTFigure, LTImage

    blocks = []
    block_no = 0

    for element in layout:
        if isinstance(element, LTTextBox):
            block_bbox = _flip_bbox(element.bbox, page_h)
            lines = []
            for line in element:
                if not isinstance(line, LTTextLine):
                    continue
                line_bbox = _flip_bbox(line.bbox, page_h)
                spans = []
                current_span: dict | None = None

                for char in line:
                    if isinstance(char, LTChar):
                        font = char.fontname or ""
                        size = round(char.size, 2)
                        color = _color_int(char.graphicstate.ncolor if hasattr(char, "graphicstate") else None)
                        flags = _font_flags(font)
                        char_bbox = _flip_bbox(char.bbox, page_h)

                        if rawdict:
                            # Per-character spans in rawdict mode
                            char_dict = {
                                "c": char.get_text(),
                                "origin": (char_bbox[0], char_bbox[3]),
                                "bbox": char_bbox,
                                "flags": flags,
                                "color": color,
                                "size": size,
                            }
                            # Each char is its own "span" in rawdict
                            if current_span is None or current_span.get("font") != font:
                                if current_span:
                                    spans.append(current_span)
                                current_span = {
                                    "bbox": char_bbox,
                                    "origin": (char_bbox[0], char_bbox[3]),
                                    "font": font,
                                    "size": size,
                                    "flags": flags,
                                    "color": color,
                                    "ascender": 1.0,
                                    "descender": -0.2,
                                    "chars": [char_dict],
                                    "text": char.get_text(),
                                }
                            else:
                                current_span["chars"].append(char_dict)
                                current_span["text"] += char.get_text()
                                # Expand span bbox
                                sb = current_span["bbox"]
                                current_span["bbox"] = (
                                    min(sb[0], char_bbox[0]), min(sb[1], char_bbox[1]),
                                    max(sb[2], char_bbox[2]), max(sb[3], char_bbox[3]),
                                )
                        else:
                            # Regular dict: group chars into spans by font
                            if current_span is None or current_span.get("font") != font:
                                if current_span:
                                    spans.append(current_span)
                                current_span = {
                                    "bbox": char_bbox,
                                    "origin": (char_bbox[0], char_bbox[3]),
                                    "font": font,
                                    "size": size,
                                    "flags": flags,
                                    "color": color,
                                    "ascender": 1.0,
                                    "descender": -0.2,
                                    "text": char.get_text(),
                                }
                            else:
                                current_span["text"] += char.get_text()
                                sb = current_span["bbox"]
                                current_span["bbox"] = (
                                    min(sb[0], char_bbox[0]), min(sb[1], char_bbox[1]),
                                    max(sb[2], char_bbox[2]), max(sb[3], char_bbox[3]),
                                )
                    elif isinstance(char, LTAnno):
                        if current_span is not None:
                            current_span["text"] += char.get_text()

                if current_span:
                    spans.append(current_span)

                if spans:
                    lines.append({
                        "bbox": line_bbox,
                        "wmode": 0,
                        "dir": (1, 0),
                        "spans": spans,
                    })

            blocks.append({
                "type": 0,
                "bbox": block_bbox,
                "lines": lines,
                "number": block_no,
            })
            block_no += 1

        elif isinstance(element, (LTFigure, LTImage)):
            block_bbox = _flip_bbox(element.bbox, page_h)
            blocks.append({
                "type": 1,
                "bbox": block_bbox,
                "lines": [],
                "number": block_no,
            })
            block_no += 1

    return {
        "width": float(layout.width),
        "height": float(layout.height),
        "blocks": blocks,
    }


def _flip_bbox(bbox, page_h: float) -> tuple:
    """Convert pdfminer bbox (bottom-left origin) to fitz bbox (top-left origin)."""
    x0, y0_pdf, x1, y1_pdf = bbox
    return (x0, page_h - y1_pdf, x1, page_h - y0_pdf)


def _color_int(color) -> int:
    """Convert a color value to an integer for fitz compatibility."""
    if color is None:
        return 0
    if isinstance(color, (int, float)):
        v = int(float(color) * 255)
        return (v << 16) | (v << 8) | v
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        r = int(float(color[0]) * 255)
        g = int(float(color[1]) * 255)
        b = int(float(color[2]) * 255)
        return (r << 16) | (g << 8) | b
    return 0


def _font_flags(fontname: str) -> int:
    """Map font name hints to fitz font flags bitmask.

    fitz flags: bit0=superscript, bit1=italic, bit2=serif, bit3=monospace, bit4=bold
    """
    flags = 0
    name_lower = fontname.lower()
    if "italic" in name_lower or "oblique" in name_lower:
        flags |= (1 << 1)
    if "serif" in name_lower or "times" in name_lower or "georgia" in name_lower:
        flags |= (1 << 2)
    if "mono" in name_lower or "courier" in name_lower or "fixed" in name_lower:
        flags |= (1 << 3)
    if "bold" in name_lower:
        flags |= (1 << 4)
    return flags


def _pdfminer_flags_to_fitz(pdf_flags: int) -> int:
    """Map PDF /FontDescriptor /Flags bits to fitz flag bits.

    PDF spec bits (1-indexed): 1=FixedPitch, 2=Serif, 3=Symbolic, 6=Italic, 17=Bold
    fitz bits (0-indexed):     0=superscript, 1=italic, 2=serif, 3=mono, 4=bold
    """
    fitz_flags = 0
    if pdf_flags & (1 << 0):   # bit 1 = FixedPitch (0-indexed: bit 0)
        fitz_flags |= (1 << 3)  # mono
    if pdf_flags & (1 << 1):   # bit 2 = Serif
        fitz_flags |= (1 << 2)  # serif
    if pdf_flags & (1 << 5):   # bit 6 = Italic (0-indexed: bit 5)
        fitz_flags |= (1 << 1)  # italic
    if pdf_flags & (1 << 16):  # bit 17 = Bold (0-indexed: bit 16)
        fitz_flags |= (1 << 4)  # bold
    return fitz_flags


def _collect_fonts(layout, fonts: dict) -> None:
    """Collect font info from layout elements."""
    from pdfminer.layout import LTChar, LTTextBox, LTTextLine
    for element in layout:
        if isinstance(element, LTTextBox):
            for line in element:
                if isinstance(line, LTTextLine):
                    for char in line:
                        if isinstance(char, LTChar):
                            font = char.fontname or "Unknown"
                            if font not in fonts:
                                fonts[font] = {
                                    "name": font,
                                    "flags": 0,
                                    "size": round(char.size, 2),
                                    "encoding": "unknown",
                                    "is_embedded": True,
                                }
