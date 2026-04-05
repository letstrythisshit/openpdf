"""Tests for annotation read/write/modify/delete."""
from __future__ import annotations

import pytest
import openpdf
from openpdf.geometry import Rect, Point
from openpdf.annotations.models import Annotation
from openpdf.constants import AnnotationType


class TestHighlightAnnotation:
    def test_add_highlight(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 680, 200, 696)
        annot = page.add_highlight_annot(rect)
        assert annot is not None
        assert isinstance(annot, Annotation)
        doc.close()

    def test_highlight_type(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 680, 200, 696)
        annot = page.add_highlight_annot(rect)
        assert annot.type[1] == "Highlight"
        doc.close()

    def test_highlight_rect(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 10, 200, 30)
        annot = page.add_highlight_annot(rect)
        ar = annot.rect
        assert abs(ar.x0 - 72) < 2
        doc.close()


class TestUnderlineAnnotation:
    def test_add_underline(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 660, 200, 676)
        annot = page.add_underline_annot(rect)
        assert annot is not None
        assert annot.type[1] == "Underline"
        doc.close()


class TestStrikeoutAnnotation:
    def test_add_strikeout(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 640, 200, 656)
        annot = page.add_strikeout_annot(rect)
        assert annot is not None
        assert annot.type[1] == "StrikeOut"
        doc.close()


class TestSquigglyAnnotation:
    def test_add_squiggly(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 620, 200, 636)
        annot = page.add_squiggly_annot(rect)
        assert annot is not None
        doc.close()


class TestTextAnnotation:
    def test_add_text_annot(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        point = Point(100, 300)
        annot = page.add_text_annot(point, "Hello, annotation!")
        assert annot is not None
        assert annot.type[1] == "Text"
        doc.close()

    def test_text_annot_info(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        annot = page.add_text_annot(Point(100, 300), "Test note")
        info = annot.info
        assert isinstance(info, dict)
        doc.close()


class TestFreetextAnnotation:
    def test_add_freetext(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(200, 400, 400, 450)
        annot = page.add_freetext_annot(rect, "Free text annotation")
        assert annot is not None
        doc.close()


class TestLineAnnotation:
    def test_add_line(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        p1 = Point(72, 500)
        p2 = Point(300, 500)
        annot = page.add_line_annot(p1, p2)
        assert annot is not None
        assert annot.type[1] == "Line"
        doc.close()


class TestRectAnnotation:
    def test_add_rect(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(100, 200, 300, 350)
        annot = page.add_rect_annot(rect)
        assert annot is not None
        assert annot.type[1] == "Square"
        doc.close()


class TestCircleAnnotation:
    def test_add_circle(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(100, 200, 300, 350)
        annot = page.add_circle_annot(rect)
        assert annot is not None
        assert annot.type[1] == "Circle"
        doc.close()


class TestPolygonAnnotation:
    def test_add_polygon(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        points = [Point(100, 200), Point(200, 300), Point(100, 300)]
        annot = page.add_polygon_annot(points)
        assert annot is not None
        assert annot.type[1] == "Polygon"
        doc.close()


class TestPolylineAnnotation:
    def test_add_polyline(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        points = [Point(100, 200), Point(200, 200), Point(200, 300)]
        annot = page.add_polyline_annot(points)
        assert annot is not None
        assert annot.type[1] == "PolyLine"
        doc.close()


class TestAnnotationModify:
    def test_update_colors(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        annot = page.add_rect_annot(Rect(50, 50, 200, 150))
        annot.set_colors(stroke=(1, 0, 0), fill=(0, 1, 0))
        annot.update()
        colors = annot.colors
        assert isinstance(colors, dict)
        doc.close()

    def test_update_border(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        annot = page.add_rect_annot(Rect(50, 50, 200, 150))
        annot.set_border(width=2.0)
        annot.update()
        border = annot.border
        assert isinstance(border, dict)
        doc.close()

    def test_update_opacity(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        annot = page.add_rect_annot(Rect(50, 50, 200, 150))
        annot.set_opacity(0.5)
        annot.update()
        assert annot.opacity == pytest.approx(0.5, abs=0.01)
        doc.close()


class TestAnnotationDelete:
    def test_delete_annot(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        annot = page.add_text_annot(Point(100, 400), "To be deleted")
        before_count = len(page.annots())
        page.delete_annot(annot)
        after_count = len(page.annots())
        assert after_count == before_count - 1
        doc.close()


class TestAnnotationRead:
    def test_annots_returns_list(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        annots = doc[0].annots()
        assert isinstance(annots, list)
        doc.close()

    def test_annots_after_add(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        before = len(page.annots())
        page.add_rect_annot(Rect(10, 10, 100, 100))
        after = len(page.annots())
        assert after == before + 1
        doc.close()


class TestRedactAnnotation:
    def test_add_redact(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 600, 400, 616)
        annot = page.add_redact_annot(rect)
        assert annot is not None
        doc.close()

    def test_apply_redactions(self, annotated_pdf_path):
        doc = openpdf.open(str(annotated_pdf_path))
        page = doc[0]
        rect = Rect(72, 600, 400, 616)
        page.add_redact_annot(rect)
        # apply_redactions should not raise
        page.apply_redactions()
        doc.close()
