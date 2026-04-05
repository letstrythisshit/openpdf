"""Tests for drawing/shape functionality."""
from __future__ import annotations

import pytest
import openpdf
from openpdf.geometry import Point, Rect
from openpdf.drawing.shape import Shape
from openpdf.image.rendering import Pixmap


class TestShape:
    def test_new_shape(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        assert isinstance(shape, Shape)
        doc.close()

    def test_draw_line(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        shape.draw_line(Point(72, 400), Point(300, 400))
        shape.finish(color=(1, 0, 0), width=2)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()
        # Verify saved PDF is still valid
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()

    def test_draw_rect(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        shape.draw_rect(Rect(72, 400, 300, 500))
        shape.finish(color=(0, 0, 1), fill=(0.9, 0.9, 1), width=1)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()

    def test_draw_circle(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        shape.draw_circle(Point(200, 400), 50)
        shape.finish(color=(0, 1, 0), width=2)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()

    def test_draw_oval(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        shape.draw_oval(Rect(100, 300, 300, 400))
        shape.finish(color=(1, 0.5, 0), width=1)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()

    def test_draw_polyline(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        points = [Point(72, 300), Point(200, 350), Point(300, 300)]
        shape.draw_polyline(points)
        shape.finish(color=(0.5, 0, 0.5), width=1)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()

    def test_draw_polygon(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        points = [Point(72, 300), Point(200, 350), Point(300, 300), Point(200, 250)]
        shape.draw_polygon(points)
        shape.finish(color=(0, 0.5, 0.5), fill=(0.9, 1, 1), width=1)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()

    def test_draw_bezier(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.new_shape()
        shape.draw_bezier(
            Point(72, 200),
            Point(150, 250),
            Point(250, 150),
            Point(300, 200),
        )
        shape.finish(color=(0.5, 0.5, 0), width=1)
        shape.commit()
        doc.save(str(tmp_pdf_path))
        doc.close()


class TestPageDrawConvenience:
    def test_draw_rect_method(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        # page.draw_rect returns the Shape (committed)
        shape = page.draw_rect(Rect(50, 50, 200, 150), color=(1, 0, 0))
        assert shape is not None
        doc.save(str(tmp_pdf_path))
        doc.close()

    def test_draw_line_method(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.draw_line(Point(50, 400), Point(400, 400), color=(0, 0, 1))
        assert shape is not None
        doc.save(str(tmp_pdf_path))
        doc.close()

    def test_draw_circle_method(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        shape = page.draw_circle(Point(300, 300), 40, color=(0, 1, 0))
        assert shape is not None
        doc.save(str(tmp_pdf_path))
        doc.close()


class TestInsertText:
    def test_insert_text(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        # insert_text returns number of extra lines (or a value)
        result = page.insert_text(Point(72, 300), "Inserted text", fontsize=12)
        assert result is not None
        doc.save(str(tmp_pdf_path))
        doc.close()
        # Verify PDF is still valid (text rendered via Form XObject overlay)
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()

    def test_insert_textbox(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        rect = Rect(72, 200, 400, 280)
        result = page.insert_textbox(rect, "Textbox content here.", fontsize=11)
        doc.save(str(tmp_pdf_path))
        doc.close()


class TestInsertImage:
    def test_insert_image_from_pixmap(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        # Create a tiny pixmap to insert
        from PIL import Image
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        page = doc[0]
        page.insert_image(Rect(72, 600, 172, 700), stream=buf.read())
        doc.save(str(tmp_pdf_path))
        doc.close()
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()
