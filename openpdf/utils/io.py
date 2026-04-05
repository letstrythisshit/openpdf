"""File/stream/buffer helpers and coordinate-system conversion utilities.

Coordinate conventions
----------------------
  fitz / OpenPDF: top-left origin, y increases downward.
  PDF spec:       bottom-left origin, y increases upward.

Every backend that reads coordinates from a PDF must call pdf_to_fitz_rect.
Every backend that writes coordinates to a PDF must call fitz_to_pdf_rect.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

from openpdf.geometry import Rect


# ---------------------------------------------------------------------------
# Coordinate conversion — the single source of truth
# ---------------------------------------------------------------------------


def pdf_to_fitz_rect(
    x0: float, y0_pdf: float, x1: float, y1_pdf: float, page_height: float
) -> Rect:
    """Convert a PDF bbox (bottom-left origin) to a fitz Rect (top-left origin).

    PDF stores [x0, y0_pdf, x1, y1_pdf] where y0_pdf < y1_pdf (bottom < top).
    fitz wants [x0, y0_fitz, x1, y1_fitz] where y0_fitz < y1_fitz (top < bottom).
    """
    return Rect(x0, page_height - y1_pdf, x1, page_height - y0_pdf)


def fitz_to_pdf_rect(rect: Rect, page_height: float) -> tuple[float, float, float, float]:
    """Convert a fitz Rect (top-left origin) to PDF bbox (bottom-left origin).

    Returns (x0, y0_pdf, x1, y1_pdf).
    """
    return (rect.x0, page_height - rect.y1, rect.x1, page_height - rect.y0)


def pdf_to_fitz_point_y(y_pdf: float, page_height: float) -> float:
    """Convert a single y-coordinate from PDF to fitz convention."""
    return page_height - y_pdf


def fitz_to_pdf_point_y(y_fitz: float, page_height: float) -> float:
    """Convert a single y-coordinate from fitz to PDF convention."""
    return page_height - y_fitz


# ---------------------------------------------------------------------------
# Source normalisation
# ---------------------------------------------------------------------------


def normalize_source(
    filename: Union[str, Path, None],
    stream: Union[bytes, io.BytesIO, None],
) -> tuple[Path | None, bytes | None]:
    """Resolve (filename, stream) into (path_or_None, bytes_or_None).

    Exactly one of the return values will be non-None unless both inputs
    are None (in which case both are None, for new-document creation).
    """
    if filename is not None:
        return Path(filename), None
    if stream is not None:
        if isinstance(stream, (bytes, bytearray)):
            return None, bytes(stream)
        if isinstance(stream, io.BytesIO):
            stream.seek(0)
            return None, stream.read()
        raise TypeError(f"stream must be bytes or BytesIO, got {type(stream)}")
    return None, None


def bytes_or_path(source: Union[str, Path, bytes, io.BytesIO]) -> Union[bytes, Path]:
    """Coerce a source into either bytes or a Path, for backends that want either."""
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if isinstance(source, io.BytesIO):
        source.seek(0)
        return source.read()
    return Path(source)


def source_to_bytes(path: Path | None, data: bytes | None) -> bytes:
    """Return raw bytes given (path, data). Reads file if data is None."""
    if data is not None:
        return data
    if path is not None:
        return path.read_bytes()
    raise ValueError("Both path and data are None; cannot obtain bytes.")


def source_to_bytesio(path: Path | None, data: bytes | None) -> io.BytesIO:
    """Return BytesIO given (path, data)."""
    raw = source_to_bytes(path, data)
    return io.BytesIO(raw)
