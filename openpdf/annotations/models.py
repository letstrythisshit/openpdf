"""Annotation dataclasses and Annotation class."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pikepdf

from openpdf.geometry import Rect, Point
from openpdf.constants import AnnotationType, _ANNOT_SUBTYPE_TO_INT, _ANNOT_INT_TO_NAME
from openpdf.backends.pike import PikeBackend, _rect_to_arr

if TYPE_CHECKING:
    from openpdf.page import Page


class Annotation:
    """Represents a single PDF annotation. Mirrors fitz.Annot."""

    def __init__(self, raw_dict: dict, page: "Page") -> None:
        self._raw = raw_dict.get("raw")  # pikepdf.Dictionary reference
        self._index = raw_dict.get("index", 0)
        self._page = page
        self._type_int = raw_dict.get("type_int", -1)
        self._subtype = raw_dict.get("subtype", "/Unknown")
        self._rect = raw_dict.get("rect", Rect())
        self._page_height = page.height

    @classmethod
    def from_raw(cls, raw_dict: dict, page: "Page") -> "Annotation":
        return cls(raw_dict, page)

    # ---- Properties --------------------------------------------------------

    @property
    def type(self) -> tuple:
        """(type_int, type_name) e.g. (8, "Highlight")."""
        return (self._type_int, _ANNOT_INT_TO_NAME.get(self._type_int, "Unknown"))

    @property
    def info(self) -> dict:
        result = {"title": "", "content": "", "name": "",
                  "subject": "", "creationDate": "", "modDate": ""}
        if self._raw is None:
            return result
        try:
            result["title"] = str(self._raw.get("/T", ""))
            result["content"] = str(self._raw.get("/Contents", ""))
            result["name"] = str(self._raw.get("/NM", ""))
            result["subject"] = str(self._raw.get("/Subj", ""))
            result["creationDate"] = str(self._raw.get("/CreationDate", ""))
            result["modDate"] = str(self._raw.get("/M", ""))
        except Exception:
            pass
        return result

    @property
    def rect(self) -> Rect:
        return self._rect

    @property
    def flags(self) -> int:
        if self._raw is None:
            return 0
        return int(self._raw.get("/F", 0))

    @property
    def colors(self) -> dict:
        result = {"stroke": None, "fill": None}
        if self._raw is None:
            return result
        try:
            c = self._raw.get("/C", None)
            if c is not None:
                result["stroke"] = tuple(float(v) for v in c)
            ic = self._raw.get("/IC", None)
            if ic is not None:
                result["fill"] = tuple(float(v) for v in ic)
        except Exception:
            pass
        return result

    @property
    def border(self) -> dict:
        result = {"width": 1.0, "style": "S", "dashes": []}
        if self._raw is None:
            return result
        try:
            bs = self._raw.get("/BS", None)
            if bs is not None:
                result["width"] = float(bs.get("/W", 1.0))
                result["style"] = str(bs.get("/S", "S")).lstrip("/")
                d = bs.get("/D", None)
                if d is not None:
                    result["dashes"] = [float(v) for v in d]
        except Exception:
            pass
        return result

    @property
    def opacity(self) -> float:
        if self._raw is None:
            return 1.0
        try:
            ca = self._raw.get("/CA", None)
            return float(ca) if ca is not None else 1.0
        except Exception:
            return 1.0

    @property
    def has_popup(self) -> bool:
        if self._raw is None:
            return False
        return "/Popup" in self._raw

    @property
    def popup_rect(self) -> Rect:
        if self._raw is None:
            return Rect()
        try:
            popup = self._raw.get("/Popup", None)
            if popup is not None:
                if hasattr(popup, "get_object"):
                    popup = popup.get_object()
                rect_arr = popup.get("/Rect", None)
                if rect_arr:
                    from openpdf.backends.pike import _arr_to_rect
                    return _arr_to_rect(rect_arr, self._page_height)
        except Exception:
            pass
        return Rect()

    @property
    def popup_xref(self) -> int:
        return 0

    @property
    def is_open(self) -> bool:
        if self._raw is None:
            return False
        try:
            return bool(self._raw.get("/Open", False))
        except Exception:
            return False

    @property
    def line_ends(self) -> tuple:
        if self._raw is None:
            return (0, 0)
        try:
            le = self._raw.get("/LE", None)
            if le and len(le) >= 2:
                return (str(le[0]), str(le[1]))
        except Exception:
            pass
        return (0, 0)

    @property
    def vertices(self) -> list[Point]:
        """Vertex points for Polygon/PolyLine/Ink annotations (in fitz coords)."""
        if self._raw is None:
            return []
        try:
            subtype = self._subtype
            if subtype in ("/Ink",):
                ink_list = self._raw.get("/InkList", None)
                if ink_list is None:
                    return []
                pts = []
                for path in ink_list:
                    for i in range(0, len(path) - 1, 2):
                        x = float(path[i])
                        y_pdf = float(path[i + 1])
                        pts.append(Point(x, self._page_height - y_pdf))
                return pts
            else:
                verts = self._raw.get("/Vertices", None)
                if verts is None:
                    return []
                pts = []
                for i in range(0, len(verts) - 1, 2):
                    x = float(verts[i])
                    y_pdf = float(verts[i + 1])
                    pts.append(Point(x, self._page_height - y_pdf))
                return pts
        except Exception:
            return []

    @property
    def xref(self) -> int:
        if self._raw is not None and hasattr(self._raw, "objgen"):
            return self._raw.objgen[0]
        return 0

    # ---- Modification methods ----------------------------------------------

    def set_rect(self, rect: Rect) -> None:
        self._rect = rect
        if self._raw is not None:
            self._raw["/Rect"] = _rect_to_arr(rect, self._page_height)

    def set_colors(self, stroke: tuple | None = None, fill: tuple | None = None) -> None:
        if self._raw is None:
            return
        if stroke is not None:
            self._raw["/C"] = pikepdf.Array([float(v) for v in stroke])
        if fill is not None:
            self._raw["/IC"] = pikepdf.Array([float(v) for v in fill])
        # Delete appearance stream so viewer regenerates it
        if "/AP" in self._raw:
            del self._raw["/AP"]

    def set_border(
        self, width: float = -1, style: str | None = None, dashes: list | None = None
    ) -> None:
        if self._raw is None:
            return
        if "/BS" not in self._raw:
            self._raw["/BS"] = pikepdf.Dictionary()
        bs = self._raw["/BS"]
        if width >= 0:
            bs["/W"] = width
        if style is not None:
            bs["/S"] = pikepdf.Name(f"/{style}")
        if dashes is not None:
            bs["/D"] = pikepdf.Array([float(d) for d in dashes])
        if "/AP" in self._raw:
            del self._raw["/AP"]

    def set_opacity(self, opacity: float) -> None:
        if self._raw is not None:
            self._raw["/CA"] = opacity
            if "/AP" in self._raw:
                del self._raw["/AP"]

    def set_flags(self, flags: int) -> None:
        if self._raw is not None:
            self._raw["/F"] = flags

    def set_info(self, info: dict) -> None:
        if self._raw is None:
            return
        if "title" in info:
            self._raw["/T"] = pikepdf.String(info["title"])
        if "content" in info:
            self._raw["/Contents"] = pikepdf.String(info["content"])
        if "subject" in info:
            self._raw["/Subj"] = pikepdf.String(info["subject"])

    def set_name(self, name: str) -> None:
        if self._raw is not None:
            self._raw["/NM"] = pikepdf.String(name)

    def set_popup(self, rect: Rect) -> None:
        pass  # Popup creation is complex; deferred

    def set_open(self, is_open: bool) -> None:
        if self._raw is not None:
            self._raw["/Open"] = is_open

    def set_line_ends(self, start: int, end: int) -> None:
        if self._raw is not None:
            self._raw["/LE"] = pikepdf.Array([
                pikepdf.Name(f"/{start}"), pikepdf.Name(f"/{end}")
            ])

    def update(
        self,
        fontsize: float = 0,
        fontname: str | None = None,
        text_color: tuple | None = None,
        border_color: tuple | None = None,
        fill_color: tuple | None = None,
        cross_out: bool = True,
        rotate: int = -1,
    ) -> None:
        """Write all pending changes back to pikepdf."""
        if self._raw is None:
            return
        if fontsize > 0 and fontname:
            # Update default appearance string for FreeText
            self._raw["/DA"] = pikepdf.String(f"/{fontname} {fontsize} Tf")
        if border_color is not None:
            self.set_colors(stroke=border_color)
        if fill_color is not None:
            self.set_colors(fill=fill_color)
        if text_color is not None and "/DA" in self._raw:
            pass  # Text color embedded in /DA stream for FreeText
        # Update the annotation in pikepdf
        PikeBackend.update_annotation(
            self._page.parent._pike, self._page.number,
            self._index, self._raw
        )
        self._page.parent._mark_dirty()

    # ---- Content -----------------------------------------------------------

    def get_text(self, option: str = "text") -> str:
        return self._page.get_text(option, clip=self._rect)

    def get_textpage(self):
        from openpdf.text.extraction import TextPage
        # Create a mini TextPage for the annotation area
        return TextPage(self._page)

    def get_pixmap(self, **kwargs) -> Any:
        return self._page.get_pixmap(clip=self._rect, **kwargs)

    def __repr__(self) -> str:
        return f"Annot({self.type[1]!r}, {self._rect!r})"
