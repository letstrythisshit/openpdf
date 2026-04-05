"""Optional OCR integration via pytesseract."""
from __future__ import annotations

from openpdf.exceptions import DependencyError


def ocr_pixmap(pil_image, language: str = "eng", tessdata: str | None = None) -> str:
    """Run OCR on a PIL Image and return the extracted text.

    Requires pytesseract and a Tesseract binary to be installed.
    Install with: pip install openpdf[ocr]
    """
    try:
        import pytesseract
    except ImportError:
        raise DependencyError(
            "OCR requires pytesseract. Install it with: pip install openpdf[ocr]\n"
            "You also need the Tesseract binary: https://github.com/tesseract-ocr/tesseract"
        )
    config = f"--tessdata-dir {tessdata}" if tessdata else ""
    return pytesseract.image_to_string(pil_image, lang=language, config=config)
