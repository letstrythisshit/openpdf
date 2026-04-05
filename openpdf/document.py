"""Document class — the primary user-facing object."""
from __future__ import annotations

import io
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Sequence, Union

import pikepdf

from openpdf.exceptions import (
    FileDataError, PasswordError, PageNumberError, EncryptionError,
)
from openpdf.constants import Permission
from openpdf.backends.pdfium import PdfiumBackend
from openpdf.backends.pike import PikeBackend
from openpdf.utils.io import normalize_source, source_to_bytes

if TYPE_CHECKING:
    from openpdf.page import Page


class Document:
    """Central PDF document handle. Mirrors fitz.Document / fitz.open().

    Usage:
        doc = openpdf.open("file.pdf")
        doc = openpdf.Document("file.pdf")
        doc = openpdf.Document(stream=bytes_data)

    Not thread-safe — each thread must open its own Document instance.
    """

    def __init__(
        self,
        filename: Union[str, Path, None] = None,
        stream: Union[bytes, io.BytesIO, None] = None,
        filetype: str = "pdf",
        password: str | None = None,
    ) -> None:
        self._path, self._source_bytes = normalize_source(filename, stream)
        self._is_closed = False
        self._password = password

        # State management
        self._pdfium_dirty = False
        self._bytes_cache: bytes | None = None   # for pdfminer — updated on reload
        self._revision: int = 0                  # monotone counter for TextPage invalidation
        self._auto_reload: bool = True           # set False in batch_mode

        # Determine source for opening
        if self._path is not None:
            pdfium_source: Union[str, bytes] = str(self._path)
            pike_source: Union[str, Path] = self._path
        elif self._source_bytes is not None:
            pdfium_source = self._source_bytes
            pike_source = self._source_bytes
        else:
            # New empty document — pikepdf gets empty, pdfium gets minimal 1-page PDF
            pike_source = _empty_pdf_bytes()
            pdfium_source = _minimal_single_page_pdf_bytes()
            self._source_bytes = pike_source

        self._pike: pikepdf.Pdf = PikeBackend.open(pike_source, password)
        self._pdfium = PdfiumBackend.open(pdfium_source, password)

    # ---- Context manager & lifecycle ---------------------------------------

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __del__(self) -> None:
        if not self._is_closed:
            try:
                self.close()
            except Exception:
                pass

    def close(self) -> None:
        if self._is_closed:
            return
        try:
            PikeBackend.close(self._pike)
        except Exception:
            pass
        try:
            PdfiumBackend.close(self._pdfium)
        except Exception:
            pass
        self._is_closed = True

    def _check_open(self) -> None:
        if self._is_closed:
            raise ValueError("Document is already closed.")

    # ---- Dirty-flag system -------------------------------------------------

    def _mark_dirty(self) -> None:
        """Call after any pikepdf mutation."""
        self._pdfium_dirty = True
        self._bytes_cache = None
        self._revision += 1
        if self._auto_reload:
            self._ensure_pdfium_fresh()

    def _ensure_pdfium_fresh(self) -> None:
        if self._pdfium_dirty:
            self._reload_pdfium()
            self._pdfium_dirty = False

    def _reload_pdfium(self) -> None:
        """Serialize pikepdf state to bytes and reopen pdfium from it."""
        data = self.write()
        PdfiumBackend.close(self._pdfium)
        self._pdfium = PdfiumBackend.open(data)
        self._bytes_cache = data

    def _get_bytes_for_miner(self) -> bytes:
        """Return current document bytes suitable for pdfminer."""
        if self._bytes_cache is not None:
            return self._bytes_cache
        data = self.write()
        self._bytes_cache = data
        return data

    @contextmanager
    def batch_mode(self):
        """Context manager that defers pdfium reloads until exit.

        Use when making many mutations to avoid repeated serialize+reopen cycles.
        """
        old = self._auto_reload
        self._auto_reload = False
        try:
            yield self
        finally:
            self._auto_reload = old
            if self._pdfium_dirty:
                self._reload_pdfium()
                self._pdfium_dirty = False

    # ---- Properties --------------------------------------------------------

    @property
    def name(self) -> str:
        return str(self._path) if self._path else ""

    @property
    def page_count(self) -> int:
        self._check_open()
        return PikeBackend.page_count(self._pike)

    @property
    def metadata(self) -> dict:
        self._check_open()
        return PikeBackend.get_metadata(self._pike)

    @property
    def is_encrypted(self) -> bool:
        return PikeBackend.is_encrypted(self._pike)

    @property
    def is_pdf(self) -> bool:
        return True

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    @property
    def needs_pass(self) -> bool:
        return self.is_encrypted

    @property
    def permissions(self) -> Permission:
        try:
            perms = self._pike.allow
            flags = Permission(0)
            if perms.print_lowres:
                flags |= Permission.PRINT
            if perms.print_highres:
                flags |= Permission.PRINT_HQ
            if perms.modify_other:
                flags |= Permission.MODIFY
            if perms.extract:
                flags |= Permission.COPY
            if perms.annotate:
                flags |= Permission.ANNOTATE
            if perms.fill_forms:
                flags |= Permission.FILL_FORMS
            if perms.accessibility:
                flags |= Permission.ACCESSIBILITY
            if perms.assemble:
                flags |= Permission.ASSEMBLE
            return flags
        except Exception:
            return Permission.ALL

    @property
    def is_form_pdf(self) -> bool:
        try:
            return "/AcroForm" in self._pike.Root
        except Exception:
            return False

    # ---- Authentication ----------------------------------------------------

    def authenticate(self, password: str) -> bool:
        try:
            PikeBackend.close(self._pike)
            PdfiumBackend.close(self._pdfium)
            source: Union[str, bytes] = str(self._path) if self._path else (self._source_bytes or b"")
            self._pike = PikeBackend.open(source, password)
            self._pdfium = PdfiumBackend.open(source, password)
            self._password = password
            return True
        except (PasswordError, Exception):
            return False

    # ---- Page access -------------------------------------------------------

    def __len__(self) -> int:
        return self.page_count

    def __getitem__(self, index: Union[int, slice]) -> Union["Page", list["Page"]]:
        from openpdf.page import Page
        self._check_open()
        if isinstance(index, slice):
            count = self.page_count
            return [Page(self, i) for i in range(*index.indices(count))]
        # Normalize negative index
        count = self.page_count
        if index < 0:
            index = count + index
        if not (0 <= index < count):
            raise PageNumberError(f"Page index {index} out of range for {count} pages.")
        return Page(self, index)

    def __iter__(self) -> Iterator["Page"]:
        from openpdf.page import Page
        for i in range(self.page_count):
            yield Page(self, i)

    def __contains__(self, item) -> bool:
        from openpdf.page import Page
        if isinstance(item, Page):
            return item.parent is self and 0 <= item.number < self.page_count
        return False

    def load_page(self, page_id: int = 0) -> "Page":
        from openpdf.page import Page
        self._check_open()
        count = self.page_count
        if page_id < 0:
            page_id = count + page_id
        if not (0 <= page_id < count):
            raise PageNumberError(f"Page {page_id} out of range (0-{count-1}).")
        return Page(self, page_id)

    def pages(
        self, start: int = 0, stop: int | None = None, step: int = 1
    ) -> Iterator["Page"]:
        from openpdf.page import Page
        count = self.page_count
        if stop is None:
            stop = count
        for i in range(start, stop, step):
            if 0 <= i < count:
                yield Page(self, i)

    # ---- Page manipulation -------------------------------------------------

    def new_page(
        self, pno: int = -1, width: float = 612.0, height: float = 792.0
    ) -> "Page":
        from openpdf.page import Page
        self._check_open()
        count = self.page_count
        index = count if pno == -1 else pno
        if index < 0:
            index = count + index + 1
        PikeBackend.insert_blank_page(self._pike, index, width, height)
        self._mark_dirty()
        return Page(self, index)

    def insert_page(
        self, pno: int, text: str = "", width: float = 612.0, height: float = 792.0
    ) -> "Page":
        page = self.new_page(pno, width, height)
        if text:
            page.insert_text(Point_lazy(72, 72), text)
        return page

    def delete_page(self, pno: int) -> None:
        self._check_open()
        count = self.page_count
        if pno < 0:
            pno = count + pno
        if not (0 <= pno < count):
            raise PageNumberError(f"Page {pno} out of range.")
        PikeBackend.delete_page(self._pike, pno)
        self._mark_dirty()

    def delete_pages(
        self,
        from_page: int = -1,
        to_page: int = -1,
        indices: list[int] | None = None,
    ) -> None:
        self._check_open()
        count = self.page_count
        if indices is not None:
            # Normalize and delete in descending order to avoid index shifting
            normalized = sorted(
                set(i if i >= 0 else count + i for i in indices),
                reverse=True,
            )
            with self.batch_mode():
                for i in normalized:
                    if 0 <= i < count:
                        PikeBackend.delete_page(self._pike, i)
                        count -= 1
        else:
            if from_page < 0:
                from_page = count + from_page
            if to_page < 0:
                to_page = count + to_page
            # Delete in descending order
            with self.batch_mode():
                for i in range(to_page, from_page - 1, -1):
                    if 0 <= i < len(self._pike.pages):
                        PikeBackend.delete_page(self._pike, i)
        self._mark_dirty()

    def copy_page(self, pno: int, to: int = -1) -> None:
        self._check_open()
        count = self.page_count
        if pno < 0:
            pno = count + pno
        dest = count if to == -1 else to
        PikeBackend.copy_page(self._pike, pno, dest)
        self._mark_dirty()

    def move_page(self, pno: int, to: int = 0) -> None:
        self._check_open()
        count = self.page_count
        if pno < 0:
            pno = count + pno
        PikeBackend.move_page(self._pike, pno, to)
        self._mark_dirty()

    def select(self, page_numbers: Sequence[int]) -> None:
        """Keep only the listed pages in the given order."""
        self._check_open()
        count = self.page_count
        new_pdf = pikepdf.Pdf.new()
        for idx in page_numbers:
            if idx < 0:
                idx = count + idx
            PikeBackend.copy_page_from(self._pike, idx, new_pdf, len(new_pdf.pages))
        PikeBackend.close(self._pike)
        self._pike = new_pdf
        self._mark_dirty()

    # ---- Metadata ----------------------------------------------------------

    def set_metadata(self, metadata: dict) -> None:
        self._check_open()
        for key, value in metadata.items():
            PikeBackend.set_metadata(self._pike, key, str(value))
        self._bytes_cache = None  # metadata change doesn't need pdfium reload

    def get_xml_metadata(self) -> str:
        return PikeBackend.get_xml_metadata(self._pike) or ""

    def set_xml_metadata(self, xml: str) -> None:
        PikeBackend.set_xml_metadata(self._pike, xml)
        self._bytes_cache = None

    # ---- TOC ---------------------------------------------------------------

    def get_toc(self, simple: bool = True) -> list:
        self._check_open()
        raw = PikeBackend.get_toc(self._pike)
        if simple:
            return [[e["level"], e["title"], e["page"]] for e in raw]
        return [[e["level"], e["title"], e["page"], e.get("dest", {})] for e in raw]

    def set_toc(self, toc: list) -> None:
        self._check_open()
        PikeBackend.set_toc(self._pike, toc)
        self._bytes_cache = None

    # ---- Merge / Insert ----------------------------------------------------

    def insert_pdf(
        self,
        source: "Document",
        from_page: int = 0,
        to_page: int = -1,
        start_at: int = -1,
        rotate: int = -1,
        links: bool = True,
        annots: bool = True,
    ) -> None:
        self._check_open()
        src_count = source.page_count
        if to_page < 0:
            to_page = src_count - 1
        dest_start = self.page_count if start_at == -1 else start_at

        with self.batch_mode():
            for offset, src_idx in enumerate(range(from_page, to_page + 1)):
                dest_idx = dest_start + offset
                PikeBackend.copy_page_from(source._pike, src_idx, self._pike, dest_idx)
                if rotate >= 0:
                    PikeBackend.set_page_rotation(self._pike, dest_idx, rotate)
                if not annots or not links:
                    _filter_page_annots(self._pike, dest_idx, links, annots)

        self._mark_dirty()

    def insert_file(self, path: Union[str, Path], **kwargs) -> None:
        with Document(filename=path) as src:
            self.insert_pdf(src, **kwargs)

    # ---- Save / Export -----------------------------------------------------

    def save(
        self,
        filename: Union[str, Path, io.BytesIO],
        garbage: int = 0,
        clean: bool = False,
        deflate: bool = True,
        deflate_images: bool = True,
        deflate_fonts: bool = True,
        incremental: bool = False,
        encryption: int = 0,
        owner_pw: str | None = None,
        user_pw: str | None = None,
        permissions: Permission = Permission.ALL,
        linear: bool = False,
    ) -> None:
        self._check_open()
        enc = None
        if encryption > 0 and (owner_pw or user_pw):
            enc = pikepdf.Encryption(
                user=user_pw or "",
                owner=owner_pw or "",
                R=6 if encryption == 4 else (5 if encryption == 3 else (3 if encryption == 2 else 2)),
            )
        PikeBackend.save(
            self._pike, filename,
            garbage=garbage, deflate=deflate, linear=linear, encryption=enc,
        )

    def write(self, **kwargs) -> bytes:
        self._check_open()
        return PikeBackend.write_to_bytes(self._pike, **kwargs)

    def tobytes(self, **kwargs) -> bytes:
        return self.write(**kwargs)

    def convert_to_pdf(self) -> bytes:
        return self.write()

    # ---- Embedded files ----------------------------------------------------

    def embfile_count(self) -> int:
        return len(PikeBackend.get_embedded_files(self._pike))

    def embfile_names(self) -> list[str]:
        return [f["name"] for f in PikeBackend.get_embedded_files(self._pike)]

    def embfile_info(self, name: str) -> dict:
        for f in PikeBackend.get_embedded_files(self._pike):
            if f["name"] == name:
                return f
        raise KeyError(f"Embedded file not found: {name!r}")

    def embfile_get(self, name: str) -> bytes:
        return self.embfile_info(name)["data"]

    def embfile_add(
        self, name: str, data: bytes, filename: str | None = None, desc: str | None = None
    ) -> None:
        PikeBackend.add_embedded_file(self._pike, name, data, filename, desc)
        self._bytes_cache = None

    def embfile_del(self, name: str) -> None:
        PikeBackend.delete_embedded_file(self._pike, name)
        self._bytes_cache = None

    def embfile_upd(
        self, name: str, data: bytes | None = None, filename: str | None = None
    ) -> None:
        # Delete and re-add
        old = self.embfile_info(name)
        self.embfile_del(name)
        new_data = data if data is not None else old["data"]
        self.embfile_add(name, new_data, filename or old.get("name"), old.get("desc"))

    # ---- Page box accessors ------------------------------------------------

    def page_cropbox(self, pno: int) -> "Rect":
        from openpdf.geometry import Rect
        cb = PikeBackend.get_page_cropbox(self._pike, pno)
        return cb if cb is not None else self.page_mediabox(pno)

    def page_mediabox(self, pno: int) -> "Rect":
        return PikeBackend.get_page_mediabox(self._pike, pno)

    # ---- Search (document-wide) --------------------------------------------

    def search_page_for(self, pno: int, text: str, quads: bool = False) -> list:
        return self[pno].search_for(text, quads=quads)

    # ---- Repr --------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Document('{self.name}', pages={self.page_count})"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _empty_pdf_bytes() -> bytes:
    """Return bytes of a minimal valid empty PDF (0 pages)."""
    pdf = pikepdf.Pdf.new()
    buf = io.BytesIO()
    pdf.save(buf)
    buf.seek(0)
    return buf.read()


def _minimal_single_page_pdf_bytes() -> bytes:
    """Return a minimal single-page PDF for pdfium initialization."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 612, 792]),
        Resources=pikepdf.Dictionary(),
    ))
    pdf.pages.append(page)
    buf = io.BytesIO()
    pdf.save(buf)
    buf.seek(0)
    return buf.read()


def _filter_page_annots(
    pike_pdf: pikepdf.Pdf, page_index: int, keep_links: bool, keep_annots: bool
) -> None:
    """Remove link or non-link annotations from a page based on flags."""
    if keep_links and keep_annots:
        return
    try:
        page = pike_pdf.pages[page_index]
        annots = page.obj.get("/Annots", None)
        if annots is None:
            return
        to_delete = []
        for i, annot_ref in enumerate(annots):
            try:
                annot = annot_ref
                if hasattr(annot, "get_object"):
                    annot = annot.get_object()
                is_link = str(annot.get("/Subtype", "")) == "/Link"
                if is_link and not keep_links:
                    to_delete.append(i)
                elif not is_link and not keep_annots:
                    to_delete.append(i)
            except Exception:
                continue
        for i in reversed(to_delete):
            del annots[i]
    except Exception:
        pass


def Point_lazy(x: float, y: float):
    """Lazy import helper for Point to avoid circular imports at module level."""
    from openpdf.geometry import Point
    return Point(x, y)
