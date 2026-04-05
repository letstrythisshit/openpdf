"""Shared pytest fixtures for the OpenPDF test suite."""
from __future__ import annotations

import os
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    p = fixture_path("sample.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}. Run tests/fixtures/generate_fixtures.py first.")
    return p


@pytest.fixture(scope="session")
def annotated_pdf_path() -> Path:
    p = fixture_path("annotated.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture(scope="session")
def form_pdf_path() -> Path:
    p = fixture_path("form.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture(scope="session")
def encrypted_pdf_path() -> Path:
    p = fixture_path("encrypted.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture(scope="session")
def toc_pdf_path() -> Path:
    p = fixture_path("toc.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture(scope="session")
def embedded_pdf_path() -> Path:
    p = fixture_path("embedded.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture(scope="session")
def rotated_pdf_path() -> Path:
    p = fixture_path("rotated.pdf")
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}")
    return p


@pytest.fixture
def tmp_pdf_path(tmp_path: Path) -> Path:
    return tmp_path / "output.pdf"


@pytest.fixture
def sample_doc(sample_pdf_path):
    """Open sample.pdf as a Document; close after test."""
    import openpdf
    doc = openpdf.open(str(sample_pdf_path))
    yield doc
    doc.close()
