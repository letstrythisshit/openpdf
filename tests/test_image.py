"""Tests for rendering and image extraction."""
from __future__ import annotations

import io
import pytest

import openpdf
from openpdf.image.rendering import Pixmap


class TestGetPixmap:
    def test_returns_pixmap(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap()
        assert isinstance(pix, Pixmap)
        doc.close()

    def test_default_dpi(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap()
        assert pix.width > 0
        assert pix.height > 0
        doc.close()

    def test_dpi_72(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        # 72 DPI on a 612pt page => width ~612px (1pt = 1px at 72dpi)
        assert abs(pix.width - 612) <= 5
        assert abs(pix.height - 792) <= 5
        doc.close()

    def test_dpi_150(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix_72 = doc[0].get_pixmap(dpi=72)
        pix_150 = doc[0].get_pixmap(dpi=150)
        # Higher DPI means larger image
        assert pix_150.width > pix_72.width
        doc.close()

    def test_colorspace_rgb(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        assert pix.n in (3, 4)  # RGB or RGBA
        doc.close()

    def test_get_pixmap_with_clip(self, sample_pdf_path):
        from openpdf.geometry import Rect
        doc = openpdf.open(str(sample_pdf_path))
        clip = Rect(0, 0, 100, 100)
        pix = doc[0].get_pixmap(dpi=72, clip=clip)
        assert isinstance(pix, Pixmap)
        doc.close()


class TestPixmap:
    def test_samples(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        samples = pix.samples
        assert isinstance(samples, (bytes, bytearray, memoryview))
        assert len(samples) > 0
        doc.close()

    def test_tobytes_png(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        data = pix.tobytes("png")
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        doc.close()

    def test_tobytes_jpeg(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        data = pix.tobytes("jpeg")
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes
        doc.close()

    def test_save_png(self, sample_pdf_path, tmp_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        out = tmp_path / "out.png"
        pix.save(str(out))
        assert out.exists()
        assert out.stat().st_size > 0
        doc.close()

    def test_save_ppm(self, sample_pdf_path, tmp_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        out = tmp_path / "out.ppm"
        pix.save(str(out))
        assert out.exists()
        doc.close()

    def test_pil_image(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        img = pix.pil_image()
        assert img.width == pix.width
        assert img.height == pix.height
        doc.close()

    def test_to_rgb(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        rgb_pix = pix.to_rgb()
        assert isinstance(rgb_pix, Pixmap)
        assert rgb_pix.n == 3
        doc.close()

    def test_to_gray(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        gray_pix = pix.to_gray()
        assert isinstance(gray_pix, Pixmap)
        assert gray_pix.n == 1
        doc.close()

    def test_colorspace_property(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        from openpdf.constants import ColorSpace
        assert isinstance(pix.colorspace, ColorSpace)
        doc.close()

    def test_stride(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pix = doc[0].get_pixmap(dpi=72)
        assert pix.stride == pix.width * pix.n
        doc.close()


class TestExtractImage:
    def test_extract_image_by_xref(self, sample_pdf_path):
        """Test extract_image on a PDF that might have images."""
        doc = openpdf.open(str(sample_pdf_path))
        # sample.pdf may not have embedded images, just test API
        images = doc[0].get_images()
        for img_info in images:
            xref = img_info[0]
            result = doc.extract_image(xref)
            assert isinstance(result, dict)
            assert "image" in result
            assert "ext" in result
            assert "width" in result
            assert "height" in result
        doc.close()
