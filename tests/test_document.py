"""Tests for openpdf.document.Document."""
from __future__ import annotations

import io
import pytest

import openpdf
from openpdf import Document
from openpdf.exceptions import PasswordError, PageNumberError


class TestDocumentOpen:
    def test_open_from_path(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert doc.page_count == 3
        doc.close()

    def test_open_via_class(self, sample_pdf_path):
        doc = Document(str(sample_pdf_path))
        assert doc.page_count == 3
        doc.close()

    def test_open_from_bytes(self, sample_pdf_path):
        data = sample_pdf_path.read_bytes()
        doc = openpdf.open(stream=data)
        assert doc.page_count > 0
        doc.close()

    def test_open_from_bytesio(self, sample_pdf_path):
        data = sample_pdf_path.read_bytes()
        buf = io.BytesIO(data)
        doc = openpdf.open(stream=buf)
        assert doc.page_count > 0
        doc.close()

    def test_context_manager(self, sample_pdf_path):
        with openpdf.open(str(sample_pdf_path)) as doc:
            assert doc.page_count == 3

    def test_open_encrypted_with_password(self, encrypted_pdf_path):
        doc = openpdf.open(str(encrypted_pdf_path), password="test")
        assert doc.page_count >= 1
        doc.close()

    def test_open_encrypted_wrong_password(self, encrypted_pdf_path):
        with pytest.raises(PasswordError):
            openpdf.open(str(encrypted_pdf_path), password="wrong_password")

    def test_repr(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        r = repr(doc)
        assert "Document" in r or "openpdf" in r.lower()
        doc.close()


class TestDocumentMetadata:
    def test_metadata_keys_present(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        meta = doc.metadata
        required_keys = ["format", "encryption", "title", "author", "subject",
                         "keywords", "creator", "producer", "creationDate",
                         "modDate", "trapped"]
        for key in required_keys:
            assert key in meta, f"Missing metadata key: {key}"
        doc.close()

    def test_metadata_title(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert doc.metadata["title"] == "Sample PDF"
        doc.close()

    def test_metadata_author(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert doc.metadata["author"] == "OpenPDF Tests"
        doc.close()

    def test_metadata_format(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        fmt = doc.metadata["format"]
        assert fmt.startswith("PDF")
        doc.close()

    def test_set_metadata(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        doc.set_metadata({"title": "New Title", "author": "Test Author"})
        assert doc.metadata["title"] == "New Title"
        assert doc.metadata["author"] == "Test Author"
        doc.close()


class TestDocumentPageAccess:
    def test_getitem_positive(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[0]
        assert page.number == 0
        doc.close()

    def test_getitem_negative(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc[-1]
        assert page.number == doc.page_count - 1
        doc.close()

    def test_getitem_slice(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pages = doc[0:2]
        assert len(pages) == 2
        doc.close()

    def test_getitem_out_of_range(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        with pytest.raises((PageNumberError, IndexError)):
            _ = doc[999]
        doc.close()

    def test_load_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        page = doc.load_page(0)
        assert page is not None
        doc.close()

    def test_iteration(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        pages = list(doc)
        assert len(pages) == 3
        doc.close()

    def test_len(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert len(doc) == 3
        doc.close()


class TestDocumentPageManipulation:
    def test_new_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        original_count = doc.page_count
        doc.new_page(-1, width=612, height=792)
        assert doc.page_count == original_count + 1
        doc.close()

    def test_insert_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        original_count = doc.page_count
        doc.insert_page(0, width=612, height=792)
        assert doc.page_count == original_count + 1
        doc.close()

    def test_delete_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        original_count = doc.page_count
        doc.delete_page(0)
        assert doc.page_count == original_count - 1
        doc.close()

    def test_delete_pages(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        doc.delete_pages(0, 1)
        assert doc.page_count == 1
        doc.close()

    def test_copy_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        original_count = doc.page_count
        doc.copy_page(0)
        assert doc.page_count == original_count + 1
        doc.close()

    def test_move_page(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        # Move last page to front
        doc.move_page(doc.page_count - 1, 0)
        assert doc.page_count == 3  # count unchanged
        doc.close()


class TestDocumentSave:
    def test_write_returns_bytes(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        data = doc.write()
        assert isinstance(data, bytes)
        assert data[:4] == b"%PDF"
        doc.close()

    def test_save_to_path(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        doc.save(str(tmp_pdf_path))
        assert tmp_pdf_path.exists()
        assert tmp_pdf_path.stat().st_size > 0
        doc.close()

    def test_save_and_reload(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        doc.save(str(tmp_pdf_path))
        doc.close()
        doc2 = openpdf.open(str(tmp_pdf_path))
        assert doc2.page_count == 3
        doc2.close()

    def test_convert_to_pdf(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        data = doc.convert_to_pdf()
        assert isinstance(data, bytes)
        assert data[:4] == b"%PDF"
        doc.close()


class TestDocumentMerge:
    def test_insert_pdf(self, sample_pdf_path):
        doc1 = openpdf.open(str(sample_pdf_path))
        doc2 = openpdf.open(str(sample_pdf_path))
        original_count = doc1.page_count
        doc1.insert_pdf(doc2)
        assert doc1.page_count == original_count + doc2.page_count
        doc1.close()
        doc2.close()

    def test_select(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        doc.select([0, 2])
        assert doc.page_count == 2
        doc.close()


class TestDocumentTOC:
    def test_get_toc_empty(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        toc = doc.get_toc()
        assert isinstance(toc, list)
        doc.close()

    def test_get_toc_with_bookmarks(self, toc_pdf_path):
        doc = openpdf.open(str(toc_pdf_path))
        toc = doc.get_toc()
        assert len(toc) > 0
        # Each entry is [level, title, page_number, ...]
        for entry in toc:
            assert len(entry) >= 3
            assert isinstance(entry[0], int)   # level
            assert isinstance(entry[1], str)   # title
            assert isinstance(entry[2], int)   # page
        doc.close()

    def test_set_toc(self, sample_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        toc = [
            [1, "Chapter 1", 1],
            [2, "Section 1.1", 1],
            [1, "Chapter 2", 2],
        ]
        doc.set_toc(toc)
        doc.save(str(tmp_pdf_path))
        doc.close()

        doc2 = openpdf.open(str(tmp_pdf_path))
        saved_toc = doc2.get_toc()
        assert len(saved_toc) == 3
        doc2.close()


class TestDocumentEncryption:
    def test_is_encrypted_false(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        assert not doc.is_encrypted
        doc.close()

    def test_is_encrypted_true(self, encrypted_pdf_path):
        doc = openpdf.open(str(encrypted_pdf_path), password="test")
        assert doc.is_encrypted
        doc.close()

    def test_permissions(self, sample_pdf_path):
        doc = openpdf.open(str(sample_pdf_path))
        perms = doc.permissions
        assert isinstance(perms, int)
        doc.close()


class TestDocumentEmbeddedFiles:
    def test_embfile_count(self, embedded_pdf_path):
        doc = openpdf.open(str(embedded_pdf_path))
        assert doc.embfile_count() >= 1
        doc.close()

    def test_embfile_names(self, embedded_pdf_path):
        doc = openpdf.open(str(embedded_pdf_path))
        names = doc.embfile_names()
        assert "hello.txt" in names
        doc.close()

    def test_embfile_get(self, embedded_pdf_path):
        doc = openpdf.open(str(embedded_pdf_path))
        result = doc.embfile_get("hello.txt")
        assert isinstance(result, bytes)
        assert b"Hello" in result
        doc.close()
