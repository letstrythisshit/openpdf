"""Add/update/delete annotations on pages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

import pikepdf

from openpdf.geometry import Rect, Point, Quad
from openpdf.annotations.models import Annotation
from openpdf.backends.pike import PikeBackend, _rect_to_arr
from openpdf.constants import STAMP_NAMES

if TYPE_CHECKING:
    from openpdf.page import Page


def _make_annot_base(page: "Page", subtype: str, rect: Rect) -> pikepdf.Dictionary:
    """Build a base annotation dictionary."""
    page_h = page.height
    return pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"),
        Subtype=pikepdf.Name(f"/{subtype}"),
        Rect=_rect_to_arr(rect, page_h),
        P=page.parent._pike.pages[page.number].obj,
    )


def _commit_annot(page: "Page", annot_dict: pikepdf.Dictionary) -> Annotation:
    """Add annotation to page and return Annotation object."""
    idx = PikeBackend.add_annotation(page.parent._pike, page.number, annot_dict)
    page.parent._mark_dirty()
    raw_annots = PikeBackend.get_annotations(page.parent._pike, page.number)
    # Find the just-added annotation
    if raw_annots and idx < len(raw_annots):
        return Annotation.from_raw(raw_annots[idx], page)
    # Fallback: return last
    if raw_annots:
        return Annotation.from_raw(raw_annots[-1], page)
    return Annotation({"index": idx, "rect": Rect(), "type_int": -1, "subtype": "", "raw": annot_dict}, page)


def add_markup_annot(
    page: "Page", subtype: str,
    quads=None, text: str = ""
) -> Annotation:
    """Add a markup annotation (Highlight, Underline, StrikeOut, Squiggly).

    quads: a Rect, Quad, or list of Rect/Quad objects.
    """
    # Normalize quads to a list
    if quads is not None and not isinstance(quads, (list, tuple)):
        quads = [quads]
    if quads:
        # Use bounding rect of all quads
        if hasattr(quads[0], "rect"):
            rect = quads[0].rect
            for q in quads[1:]:
                rect = rect.include_rect(q.rect)
        else:
            rect = quads[0] if isinstance(quads[0], Rect) else Rect()
            for q in quads[1:]:
                if isinstance(q, Rect):
                    rect = rect.include_rect(q)
    else:
        rect = Rect(0, 0, 0, 0)

    page_h = page.height
    d = _make_annot_base(page, subtype, rect)
    d["/Contents"] = pikepdf.String(text)
    d["/C"] = pikepdf.Array([1.0, 1.0, 0.0])  # Yellow default for highlights

    # Build QuadPoints array (8 numbers per quad: ul, ur, ll, lr in PDF coords)
    if quads:
        qp = pikepdf.Array()
        for q in quads:
            if isinstance(q, Rect):
                q = q.quad
            # QuadPoints order in PDF: ul, ur, ll, lr — all in PDF (bottom-left) coords
            for pt in [q.ul, q.ur, q.ll, q.lr]:
                qp.append(float(pt.x))
                qp.append(float(page_h - pt.y))
        d["/QuadPoints"] = qp

    return _commit_annot(page, d)


def add_freetext_annot(
    page: "Page", rect: Rect, text: str, fontsize: float, fontname: str,
    color: tuple, fill_color: tuple | None, rotate: int, align: int,
) -> Annotation:
    d = _make_annot_base(page, "FreeText", rect)
    d["/Contents"] = pikepdf.String(text)
    d["/DA"] = pikepdf.String(f"/{fontname} {fontsize} Tf")
    d["/Q"] = align  # 0=left, 1=center, 2=right
    d["/C"] = pikepdf.Array([float(v) for v in color])
    if fill_color:
        d["/IC"] = pikepdf.Array([float(v) for v in fill_color])
    if rotate:
        d["/Rotate"] = rotate
    return _commit_annot(page, d)


def add_text_annot(page: "Page", point: Point, text: str, icon: str) -> Annotation:
    rect = Rect(point.x, point.y, point.x + 20, point.y + 20)
    d = _make_annot_base(page, "Text", rect)
    d["/Contents"] = pikepdf.String(text)
    d["/Name"] = pikepdf.Name(f"/{icon}")
    d["/Open"] = False
    return _commit_annot(page, d)


def add_line_annot(page: "Page", p1: Point, p2: Point) -> Annotation:
    rect = Rect(
        min(p1.x, p2.x), min(p1.y, p2.y),
        max(p1.x, p2.x), max(p1.y, p2.y),
    )
    page_h = page.height
    d = _make_annot_base(page, "Line", rect)
    d["/L"] = pikepdf.Array([
        float(p1.x), float(page_h - p1.y),
        float(p2.x), float(page_h - p2.y),
    ])
    return _commit_annot(page, d)


def add_rect_annot(page: "Page", rect: Rect) -> Annotation:
    d = _make_annot_base(page, "Square", rect)
    return _commit_annot(page, d)


def add_circle_annot(page: "Page", rect: Rect) -> Annotation:
    d = _make_annot_base(page, "Circle", rect)
    return _commit_annot(page, d)


def add_polygon_annot(page: "Page", points: list[Point]) -> Annotation:
    if not points:
        return _commit_annot(page, _make_annot_base(page, "Polygon", Rect()))
    xs = [p.x for p in points]; ys = [p.y for p in points]
    rect = Rect(min(xs), min(ys), max(xs), max(ys))
    page_h = page.height
    d = _make_annot_base(page, "Polygon", rect)
    verts = pikepdf.Array()
    for pt in points:
        verts.append(float(pt.x)); verts.append(float(page_h - pt.y))
    d["/Vertices"] = verts
    return _commit_annot(page, d)


def add_polyline_annot(page: "Page", points: list[Point]) -> Annotation:
    if not points:
        return _commit_annot(page, _make_annot_base(page, "PolyLine", Rect()))
    xs = [p.x for p in points]; ys = [p.y for p in points]
    rect = Rect(min(xs), min(ys), max(xs), max(ys))
    page_h = page.height
    d = _make_annot_base(page, "PolyLine", rect)
    verts = pikepdf.Array()
    for pt in points:
        verts.append(float(pt.x)); verts.append(float(page_h - pt.y))
    d["/Vertices"] = verts
    return _commit_annot(page, d)


def add_ink_annot(page: "Page", paths: list[list[Point]]) -> Annotation:
    all_pts = [pt for path in paths for pt in path]
    if not all_pts:
        return _commit_annot(page, _make_annot_base(page, "Ink", Rect()))
    xs = [p.x for p in all_pts]; ys = [p.y for p in all_pts]
    rect = Rect(min(xs), min(ys), max(xs), max(ys))
    page_h = page.height
    d = _make_annot_base(page, "Ink", rect)
    ink_list = pikepdf.Array()
    for path in paths:
        path_arr = pikepdf.Array()
        for pt in path:
            path_arr.append(float(pt.x)); path_arr.append(float(page_h - pt.y))
        ink_list.append(path_arr)
    d["/InkList"] = ink_list
    return _commit_annot(page, d)


def add_stamp_annot(page: "Page", rect: Rect, stamp: Union[int, str] = 0) -> Annotation:
    if isinstance(stamp, int):
        name = STAMP_NAMES[stamp % len(STAMP_NAMES)]
    else:
        name = stamp
    d = _make_annot_base(page, "Stamp", rect)
    d["/Name"] = pikepdf.Name(f"/{name}")
    return _commit_annot(page, d)


def add_file_annot(
    page: "Page", point: Point, data: bytes, filename: str, desc: str
) -> Annotation:
    rect = Rect(point.x, point.y, point.x + 20, point.y + 20)
    d = _make_annot_base(page, "FileAttachment", rect)
    # Embed file spec
    stream = page.parent._pike.make_stream(data)
    stream["/Type"] = pikepdf.Name("/EmbeddedFile")
    ef_dict = pikepdf.Dictionary(F=page.parent._pike.make_indirect(stream))
    spec = pikepdf.Dictionary(
        Type=pikepdf.Name("/Filespec"),
        F=filename,
        UF=filename,
        EF=ef_dict,
        Desc=desc,
    )
    d["/FS"] = page.parent._pike.make_indirect(spec)
    d["/Name"] = pikepdf.String(filename)
    return _commit_annot(page, d)


def add_caret_annot(page: "Page", point: Point) -> Annotation:
    rect = Rect(point.x - 5, point.y - 10, point.x + 5, point.y + 2)
    d = _make_annot_base(page, "Caret", rect)
    return _commit_annot(page, d)


def add_redact_annot(
    page: "Page",
    quad: Union[Quad, Rect],
    text: str | None,
    fill: tuple,
    text_color: tuple,
    cross_out: bool,
) -> Annotation:
    if isinstance(quad, Rect):
        rect = quad
    else:
        rect = quad.rect
    d = _make_annot_base(page, "Redact", rect)
    d["/IC"] = pikepdf.Array([float(v) for v in fill])
    if text:
        d["/OverlayText"] = pikepdf.String(text)
    return _commit_annot(page, d)


def apply_redactions(page: "Page") -> bool:
    """Apply redaction annotations — v0.2 implementation: visual cover only.

    This covers content visually with a filled rectangle overlay.
    It does NOT scrub underlying text from the content stream (v0.5 feature).
    """
    from openpdf.backends.rlab import ReportLabBackend

    page_h = page.height
    page_w = page.width
    redacts = list(page.annots(types=[25]))  # AnnotationType.REDACT = 25

    if not redacts:
        return False

    draw_cmds = []
    for annot in redacts:
        fill = annot.colors.get("fill") or (1, 1, 1)
        rect = annot.rect

        def make_cmd(r=rect, f=fill):
            def cmd(canvas, ph):
                ReportLabBackend.draw_rect(canvas, r, None, f, 0, page_h=ph)
            return cmd

        draw_cmds.append(make_cmd())

    overlay_bytes = ReportLabBackend.create_overlay_pdf(draw_cmds, (page_w, page_h))
    PikeBackend.overlay_page(page.parent._pike, page.number, overlay_bytes)

    # Remove redaction annotations
    indices = sorted([a._index for a in redacts], reverse=True)
    for idx in indices:
        PikeBackend.delete_annotation(page.parent._pike, page.number, idx)

    page.parent._mark_dirty()
    return True


def insert_link(page: "Page", link_dict: dict) -> None:
    """Insert a link annotation from a fitz-style link dict."""
    from openpdf.constants import LinkType
    rect = link_dict.get("from", Rect())
    d = _make_annot_base(page, "Link", rect)
    kind = link_dict.get("kind", LinkType.NONE)

    if kind == LinkType.URI:
        d["/A"] = pikepdf.Dictionary(
            S=pikepdf.Name("/URI"),
            URI=pikepdf.String(link_dict.get("uri", "")),
        )
    elif kind == LinkType.GOTO:
        dest_page = link_dict.get("page", 0)
        try:
            dest_obj = page.parent._pike.pages[dest_page].obj
            d["/A"] = pikepdf.Dictionary(
                S=pikepdf.Name("/GoTo"),
                D=pikepdf.Array([dest_obj, pikepdf.Name("/Fit")]),
            )
        except Exception:
            pass

    PikeBackend.add_annotation(page.parent._pike, page.number, d)
    page.parent._mark_dirty()
