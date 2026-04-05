"""Tests for fitz camelCase compatibility aliases."""
from __future__ import annotations

import pytest
import openpdf
import openpdf as fitz  # fitz alias


class TestDocumentCompatAliases:
    def test_load_page(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        page = doc.loadPage(0)
        assert page is not None
        assert page.number == 0
        doc.close()

    def test_new_page(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        original = doc.page_count
        doc.newPage(-1, width=612, height=792)
        assert doc.page_count == original + 1
        doc.close()

    def test_get_toc(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        toc = doc.getToC()
        assert isinstance(toc, list)
        doc.close()

    def test_set_toc(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc.setToC([[1, "Chapter 1", 1]])
        doc.close()

    def test_set_metadata(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc.setMetadata({"title": "Compat Test"})
        assert doc.metadata["title"] == "Compat Test"
        doc.close()

    def test_insert_pdf(self, sample_pdf_path):
        doc1 = fitz.open(str(sample_pdf_path))
        doc2 = fitz.open(str(sample_pdf_path))
        original = doc1.page_count
        doc1.insertPDF(doc2)
        assert doc1.page_count == original + doc2.page_count
        doc1.close()
        doc2.close()

    def test_delete_page(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        original = doc.page_count
        doc.deletePage(0)
        assert doc.page_count == original - 1
        doc.close()

    def test_copy_page(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        original = doc.page_count
        doc.copyPage(0)
        assert doc.page_count == original + 1
        doc.close()

    def test_move_page(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc.movePage(2, 0)
        assert doc.page_count == 3
        doc.close()

    def test_embedded_file_count(self, embedded_pdf_path):
        doc = fitz.open(str(embedded_pdf_path))
        count = doc.embeddedFileCount()
        assert count >= 1
        doc.close()

    def test_embedded_file_names(self, embedded_pdf_path):
        doc = fitz.open(str(embedded_pdf_path))
        names = doc.embeddedFileNames()
        assert "hello.txt" in names
        doc.close()

    def test_convert_to_pdf(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        data = doc.convertToPDF()
        assert isinstance(data, bytes)
        doc.close()

    def test_write(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        data = doc.write()
        assert isinstance(data, bytes)
        doc.close()


class TestPageCompatAliases:
    def test_get_text(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        text = doc[0].getText()
        assert isinstance(text, str)
        assert len(text) > 0
        doc.close()

    def test_get_textpage(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        tp = doc[0].getTextPage()
        assert tp is not None
        doc.close()

    def test_search_for(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        results = doc[0].searchFor("OpenPDF")
        assert isinstance(results, list)
        doc.close()

    def test_get_pixmap(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        pix = doc[0].getPixmap(dpi=72)
        assert pix.width > 0
        assert pix.height > 0
        doc.close()

    def test_get_image_list(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        imgs = doc[0].getImageList()
        assert isinstance(imgs, list)
        doc.close()

    def test_get_links(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        links = doc[0].getLinks()
        assert isinstance(links, list)
        doc.close()

    def test_get_drawings(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        drawings = doc[0].getDrawings()
        assert isinstance(drawings, list)
        doc.close()

    def test_get_fonts(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        fonts = doc[0].getFonts()
        assert isinstance(fonts, list)
        doc.close()

    def test_set_rotation(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc[0].setRotation(0)
        assert doc[0].rotation == 0
        doc.close()

    def test_add_highlight_annot(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        annot = doc[0].addHighlightAnnot(Rect(72, 680, 200, 696))
        assert annot is not None
        doc.close()

    def test_add_underline_annot(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        annot = doc[0].addUnderlineAnnot(Rect(72, 660, 200, 676))
        assert annot is not None
        doc.close()

    def test_add_strikeout_annot(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        annot = doc[0].addStrikeoutAnnot(Rect(72, 640, 200, 656))
        assert annot is not None
        doc.close()

    def test_add_rect_annot(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        annot = doc[0].addRectAnnot(Rect(50, 50, 200, 150))
        assert annot is not None
        doc.close()

    def test_add_circle_annot(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        annot = doc[0].addCircleAnnot(Rect(50, 50, 200, 150))
        assert annot is not None
        doc.close()

    def test_apply_redactions(self, annotated_pdf_path):
        doc = fitz.open(str(annotated_pdf_path))
        from openpdf.geometry import Rect
        doc[0].addRedactAnnot(Rect(72, 600, 400, 616))
        doc[0].applyRedactions()
        doc.close()

    def test_wrap_contents(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc[0].wrapContents()
        doc.close()

    def test_clean_contents(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        doc[0].cleanContents()
        doc.close()

    def test_new_shape(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        shape = doc[0].newShape()
        assert shape is not None
        doc.close()

    def test_insert_text(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        from openpdf.geometry import Point
        result = doc[0].insertText(Point(72, 300), "Compat text")
        doc.close()

    def test_draw_rect_method(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        from openpdf.geometry import Rect
        doc[0].drawRect(Rect(50, 50, 200, 150))
        doc.close()


class TestPixmapCompatAliases:
    def test_get_png_data(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        pix = doc[0].getPixmap(dpi=72)
        data = pix.getPNGData()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        doc.close()

    def test_write_png(self, sample_pdf_path, tmp_path):
        doc = fitz.open(str(sample_pdf_path))
        pix = doc[0].getPixmap(dpi=72)
        out = str(tmp_path / "compat_out.png")
        pix.writePNG(out)
        import os
        assert os.path.exists(out)
        doc.close()

    def test_get_image_data(self, sample_pdf_path):
        doc = fitz.open(str(sample_pdf_path))
        pix = doc[0].getPixmap(dpi=72)
        data = pix.getImageData("png")
        assert isinstance(data, bytes)
        doc.close()


class TestDropInReplacement:
    """Comprehensive drop-in replacement test simulating real fitz usage."""

    def test_fitz_workflow(self, sample_pdf_path):
        """Simulate typical fitz usage pattern."""
        doc = fitz.open(str(sample_pdf_path))
        assert doc.page_count > 0

        page = doc.loadPage(0)
        text = page.getText()
        assert len(text) > 0

        pix = page.getPixmap(dpi=72)
        assert pix.width > 0
        png_data = pix.getPNGData()
        assert png_data[:8] == b"\x89PNG\r\n\x1a\n"

        toc = doc.getToC()
        assert isinstance(toc, list)

        doc.close()
