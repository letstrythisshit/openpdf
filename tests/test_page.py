"""Tests for openpdf.page.Page."""
from __future__ import annotations

import pytest
import openpdf
from openpdf.geometry import Rect


class TestPageProperties:
    def test_number(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert doc[0].number == 0
        assert doc[1].number == 1
        assert doc[2].number == 2
        doc.close()

    def test_rect(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        r = page.rect
        assert isinstance(r, Rect)
        assert r.x0 == 0.0
        assert r.y0 == 0.0
        assert r.width == pytest.approx(612.0)
        assert r.height == pytest.approx(792.0)
        doc.close()

    def test_width_height(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        assert page.width == pytest.approx(612.0)
        assert page.height == pytest.approx(792.0)
        doc.close()

    def test_mediabox(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        mb = doc[0].mediabox
        assert isinstance(mb, Rect)
        assert mb.width == pytest.approx(612.0)
        doc.close()

    def test_cropbox(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        cb = doc[0].cropbox
        assert isinstance(cb, Rect)
        doc.close()

    def test_rotation_default(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert doc[0].rotation == 0
        doc.close()

    def test_rotation_90(self):
        import openpdf
        from pathlib import Path
        path = Path("tests/fixtures/rotated.pdf")
        if not path.exists():
            pytest.skip("rotated.pdf not found")
        doc = openpdf.open(str(path))
        assert doc[1].rotation == 90
        assert doc[2].rotation == 180
        doc.close()

    def test_parent(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        assert page.parent is doc
        doc.close()


class TestPageRotation:
    def test_set_rotation(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        page.set_rotation(90)
        assert page.rotation == 90
        page.set_rotation(0)
        assert page.rotation == 0
        doc.close()

    def test_set_invalid_rotation(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        with pytest.raises((ValueError, Exception)):
            doc[0].set_rotation(45)
        doc.close()


class TestPageCropBox:
    def test_set_cropbox(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        new_crop = Rect(10, 10, 600, 780)
        page.set_cropbox(new_crop)
        cb = page.cropbox
        assert cb.x0 == pytest.approx(10.0)
        assert cb.y0 == pytest.approx(10.0)
        doc.close()


class TestPageGetImages:
    def test_get_images_empty(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        images = doc[0].get_images()
        assert isinstance(images, list)
        doc.close()


class TestPageLinks:
    def test_get_links(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        links = doc[0].get_links()
        assert isinstance(links, list)
        doc.close()


class TestPageWrapContents:
    def test_wrap_contents(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        # Should not raise
        doc[0].wrap_contents()
        doc.close()
