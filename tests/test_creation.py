"""Tests for DocumentBuilder PDF creation."""
from __future__ import annotations

import io
import pytest

import openpdf
from openpdf.creation.builder import DocumentBuilder
from openpdf.geometry import Point, Rect


class TestDocumentBuilder:
    def test_create_empty_doc(self, tmp_pdf_path):
        builder = DocumentBuilder()
        builder.add_page(page_size=(612, 792))
        doc = builder.finish()
        assert isinstance(doc, openpdf.Document)
        assert doc.page_count == 1
        doc.close()

    def test_create_with_path(self, tmp_pdf_path):
        builder = DocumentBuilder(str(tmp_pdf_path))
        builder.add_page(page_size=(612, 792))
        builder.finish()
        assert tmp_pdf_path.exists()
        assert tmp_pdf_path.stat().st_size > 0

    def test_create_multiple_pages(self, tmp_pdf_path):
        builder = DocumentBuilder()
        builder.add_page(page_size=(612, 792))
        builder.add_page(page_size=(612, 792))
        builder.add_page(page_size=(595, 842))  # A4
        doc = builder.finish()
        assert doc.page_count == 3
        doc.close()

    def test_add_text(self, tmp_pdf_path):
        builder = DocumentBuilder()
        builder.add_page(page_size=(612, 792))
        builder.draw_text(Point(72, 720), "Hello, World!", fontname="Helvetica", fontsize=12)
        doc = builder.finish()
        text = doc[0].get_text()
        assert "Hello" in text
        doc.close()

    def test_add_multiple_text(self, tmp_pdf_path):
        builder = DocumentBuilder()
        builder.add_page(page_size=(612, 792))
        builder.draw_text(Point(72, 720), "Title", fontname="Helvetica", fontsize=14)
        builder.draw_text(Point(72, 690), "Body text", fontname="Times-Roman", fontsize=12)
        doc = builder.finish()
        text = doc[0].get_text()
        assert "Title" in text
        assert "Body text" in text
        doc.close()

    def test_draw_rectangle(self, tmp_pdf_path):
        builder = DocumentBuilder()
        builder.add_page(page_size=(612, 792))
        builder.draw_rect(Rect(72, 600, 300, 700), color=(0, 0, 1), fill=(0.9, 0.9, 1))
        doc = builder.finish()
        # Just verify the document is valid
        assert doc.page_count == 1
        doc.close()

    def test_finish_returns_document(self):
        builder = DocumentBuilder()
        builder.add_page()
        result = builder.finish()
        assert isinstance(result, openpdf.Document)
        result.close()

    def test_valid_pdf_output(self, tmp_pdf_path):
        builder = DocumentBuilder(str(tmp_pdf_path))
        builder.add_page()
        builder.draw_text(Point(72, 700), "Test content")
        builder.finish()

        # Should be a valid PDF
        doc = openpdf.open(str(tmp_pdf_path))
        assert doc.page_count == 1
        text = doc[0].get_text()
        assert "Test" in text
        doc.close()

    def test_set_title(self):
        builder = DocumentBuilder()
        builder.add_page()
        builder.set_title("My Test PDF")
        builder.set_author("Test Author")
        doc = builder.finish()
        meta = doc.metadata
        assert meta.get("title") == "My Test PDF"
        assert meta.get("author") == "Test Author"
        doc.close()


class TestDocumentBuilderFromNew:
    def test_openpdf_new_creates_empty(self):
        """openpdf.open() with no args creates a new empty document."""
        doc = openpdf.open()
        assert isinstance(doc, openpdf.Document)
        assert doc.page_count == 0
        doc.close()

    def test_new_page_in_empty_doc(self):
        doc = openpdf.open()
        doc.new_page(-1, width=612, height=792)
        assert doc.page_count == 1
        doc.close()
