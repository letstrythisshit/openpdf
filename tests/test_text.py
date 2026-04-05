"""Tests for text extraction modes."""
from __future__ import annotations

import pytest
import openpdf


class TestGetTextSimple:
    def test_returns_string(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        text = doc[0].get_text()
        assert isinstance(text, str)
        doc.close()

    def test_contains_known_text(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        text = doc[0].get_text()
        assert "OpenPDF" in text or "Sample" in text
        doc.close()

    def test_page2_text(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        text = doc[1].get_text()
        assert "Lorem ipsum" in text or "Page 2" in text
        doc.close()

    def test_page3_monospace(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        text = doc[2].get_text()
        assert "quick brown fox" in text or "Page 3" in text
        doc.close()

    def test_explicit_mode_text(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        text = doc[0].get_text("text")
        assert isinstance(text, str)
        assert len(text) > 0
        doc.close()


class TestGetTextBlocks:
    def test_returns_list(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        blocks = doc[0].get_text("blocks")
        assert isinstance(blocks, list)
        doc.close()

    def test_block_structure(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        blocks = doc[0].get_text("blocks")
        for block in blocks:
            # (x0, y0, x1, y1, text, block_no, block_type)
            assert len(block) >= 5
            assert isinstance(block[4], str)  # text
        doc.close()

    def test_blocks_nonempty(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        blocks = doc[0].get_text("blocks")
        assert len(blocks) > 0
        doc.close()


class TestGetTextWords:
    def test_returns_list(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        words = doc[0].get_text("words")
        assert isinstance(words, list)
        doc.close()

    def test_word_structure(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        words = doc[0].get_text("words")
        for word in words:
            # (x0, y0, x1, y1, word, block_no, line_no, word_no)
            assert len(word) >= 5
            assert isinstance(word[4], str)
        doc.close()

    def test_words_nonempty(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        words = doc[0].get_text("words")
        assert len(words) > 0
        doc.close()


class TestGetTextDict:
    def test_returns_dict(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        result = doc[0].get_text("dict")
        assert isinstance(result, dict)
        doc.close()

    def test_has_blocks(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        result = doc[0].get_text("dict")
        assert "blocks" in result
        assert isinstance(result["blocks"], list)
        doc.close()

    def test_has_width_height(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        result = doc[0].get_text("dict")
        assert "width" in result
        assert "height" in result
        doc.close()

    def test_block_schema(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        result = doc[0].get_text("dict")
        for block in result["blocks"]:
            assert "type" in block
            assert "bbox" in block
            if block["type"] == 0:  # text block
                assert "lines" in block
                for line in block["lines"]:
                    assert "spans" in line
                    assert "bbox" in line
                    for span in line["spans"]:
                        assert "text" in span
                        assert "font" in span
                        assert "size" in span
                        assert "bbox" in span
        doc.close()


class TestGetTextHTML:
    def test_returns_string(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        html = doc[0].get_text("html")
        assert isinstance(html, str)
        doc.close()

    def test_is_html(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        html = doc[0].get_text("html")
        assert "<" in html and ">" in html
        doc.close()


class TestGetTextXML:
    def test_returns_string(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        xml = doc[0].get_text("xml")
        assert isinstance(xml, str)
        doc.close()


class TestSearchFor:
    def test_find_existing_text(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        results = doc[0].search_for("OpenPDF")
        assert isinstance(results, list)
        # Should find at least one match
        if results:
            from openpdf.geometry import Rect
            assert all(isinstance(r, Rect) for r in results)
        doc.close()

    def test_find_nonexistent_text(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        results = doc[0].search_for("ZZZZZNOTHERE")
        assert results == []
        doc.close()

    def test_case_insensitive(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        # "openpdf" (lowercase) should still find something with hit_max=16
        results_lower = doc[0].search_for("openpdf")
        results_upper = doc[0].search_for("OpenPDF")
        # Both should return same count (case-insensitive by default)
        assert len(results_lower) == len(results_upper)
        doc.close()


class TestGetTextPage:
    def test_get_textpage(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        tp = doc[0].get_textpage()
        assert tp is not None
        doc.close()
