"""pikepdf backend — structural PDF operations.

Handles: open/save, metadata, page operations, TOC, annotations,
form fields, encryption, embedded files, image extraction, and
the drawing overlay merge.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Union

import pikepdf

from openpdf.geometry import Rect, Point
from openpdf.constants import (
    AnnotationType, LinkType, WidgetType, Permission,
    _ANNOT_SUBTYPE_TO_INT, _WIDGET_FT_TO_TYPE,
)
from openpdf.exceptions import (
    FileDataError, PasswordError, EncryptionError, AnnotationError,
)
from openpdf.utils.io import pdf_to_fitz_rect, fitz_to_pdf_rect


class PikeBackend:
    """Wraps pikepdf for structural PDF operations. All methods are static."""

    # ---- Lifecycle ---------------------------------------------------------

    @staticmethod
    def open(
        source: Union[str, Path, bytes, io.BytesIO],
        password: str | None = None,
    ) -> pikepdf.Pdf:
        try:
            kwargs: dict = {}
            if password:
                kwargs["password"] = password
            if isinstance(source, (bytes, bytearray)):
                pdf = pikepdf.open(io.BytesIO(source), **kwargs)
            elif isinstance(source, io.BytesIO):
                source.seek(0)
                pdf = pikepdf.open(source, **kwargs)
            else:
                pdf = pikepdf.open(str(source), **kwargs)
            return pdf
        except pikepdf.PasswordError as exc:
            raise PasswordError(f"Incorrect password: {exc}") from exc
        except pikepdf.PdfError as exc:
            raise FileDataError(f"Failed to open PDF with pikepdf: {exc}") from exc

    @staticmethod
    def save(
        handle: pikepdf.Pdf,
        dest: Union[str, Path, io.BytesIO],
        garbage: int = 0,
        clean: bool = False,
        deflate: bool = True,
        linear: bool = False,
        encryption: pikepdf.Encryption | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "compress_streams": deflate,
            "linearize": linear,
        }
        if garbage >= 1:
            kwargs["object_stream_mode"] = pikepdf.ObjectStreamMode.generate
        if encryption is not None:
            kwargs["encryption"] = encryption
        if isinstance(dest, (str, Path)):
            handle.save(str(dest), **kwargs)
        else:
            handle.save(dest, **kwargs)

    @staticmethod
    def close(handle: pikepdf.Pdf) -> None:
        try:
            handle.close()
        except Exception:
            pass

    @staticmethod
    def write_to_bytes(handle: pikepdf.Pdf, **kwargs) -> bytes:
        buf = io.BytesIO()
        PikeBackend.save(handle, buf, **kwargs)
        buf.seek(0)
        return buf.read()

    # ---- Metadata ----------------------------------------------------------

    @staticmethod
    def get_metadata(handle: pikepdf.Pdf) -> dict:
        """Return a metadata dict with all fitz-expected keys."""
        info = {}
        raw = {}

        # Read from /Info dictionary
        try:
            doc_info = handle.docinfo
            raw = {
                "title": str(doc_info.get("/Title", "")),
                "author": str(doc_info.get("/Author", "")),
                "subject": str(doc_info.get("/Subject", "")),
                "keywords": str(doc_info.get("/Keywords", "")),
                "creator": str(doc_info.get("/Creator", "")),
                "producer": str(doc_info.get("/Producer", "")),
                "creationDate": _parse_pdf_date(str(doc_info.get("/CreationDate", ""))),
                "modDate": _parse_pdf_date(str(doc_info.get("/ModDate", ""))),
                "trapped": str(doc_info.get("/Trapped", "")),
            }
        except Exception:
            raw = {}

        # PDF version / format
        try:
            version = handle.pdf_version
            info["format"] = f"PDF {version}"
        except Exception:
            info["format"] = "PDF"

        # Encryption info
        try:
            info["encryption"] = str(handle.encryption) if handle.is_encrypted else None
        except Exception:
            info["encryption"] = None

        info.update(raw)
        # Ensure all expected keys are present
        for key in ("title", "author", "subject", "keywords", "creator", "producer",
                    "creationDate", "modDate", "trapped"):
            info.setdefault(key, "")

        return info

    @staticmethod
    def set_metadata(handle: pikepdf.Pdf, key: str, value: str) -> None:
        # Map fitz key names to PDF /Info key names
        _KEY_MAP = {
            "title": "/Title", "author": "/Author", "subject": "/Subject",
            "keywords": "/Keywords", "creator": "/Creator", "producer": "/Producer",
            "creationDate": "/CreationDate", "modDate": "/ModDate", "trapped": "/Trapped",
        }
        pdf_key = _KEY_MAP.get(key, f"/{key.capitalize()}")
        try:
            handle.docinfo[pdf_key] = value
        except Exception:
            pass

    @staticmethod
    def get_xml_metadata(handle: pikepdf.Pdf) -> str | None:
        try:
            return handle.open_metadata().__str__()
        except Exception:
            return None

    @staticmethod
    def set_xml_metadata(handle: pikepdf.Pdf, xml_str: str) -> None:
        try:
            with handle.open_metadata(update_docinfo=False) as meta:
                meta.load_from_docinfo(xml_str)
        except Exception:
            pass

    # ---- Page-level --------------------------------------------------------

    @staticmethod
    def page_count(handle: pikepdf.Pdf) -> int:
        return len(handle.pages)

    @staticmethod
    def get_page(handle: pikepdf.Pdf, index: int) -> pikepdf.Page:
        return handle.pages[index]

    @staticmethod
    def insert_blank_page(
        handle: pikepdf.Pdf, index: int, width: float, height: float
    ) -> None:
        page_dict = pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=pikepdf.Array([0, 0, width, height]),
            Resources=pikepdf.Dictionary(),
            Contents=handle.make_stream(b""),
        )
        new_page = pikepdf.Page(page_dict)
        handle.pages.insert(index, new_page)

    @staticmethod
    def delete_page(handle: pikepdf.Pdf, index: int) -> None:
        del handle.pages[index]

    @staticmethod
    def copy_page(handle: pikepdf.Pdf, src_index: int, dest_index: int) -> None:
        """Copy a page within the same PDF by serializing and reloading."""
        buf = io.BytesIO()
        handle.save(buf)
        buf.seek(0)
        tmp = pikepdf.open(buf)
        src_page = tmp.pages[src_index]
        handle.pages.insert(dest_index, src_page)

    @staticmethod
    def move_page(handle: pikepdf.Pdf, from_index: int, to_index: int) -> None:
        page = handle.pages[from_index]
        del handle.pages[from_index]
        # Adjust destination index if it shifted
        actual_to = to_index if to_index <= from_index else to_index - 1
        handle.pages.insert(actual_to, page)

    @staticmethod
    def copy_page_from(
        source: pikepdf.Pdf, src_idx: int,
        dest: pikepdf.Pdf, dest_idx: int,
    ) -> None:
        src_page = source.pages[src_idx]
        dest.pages.insert(dest_idx, src_page)

    @staticmethod
    def get_page_rotation(handle: pikepdf.Pdf, index: int) -> int:
        try:
            page = handle.pages[index]
            rot = page.obj.get("/Rotate", 0)
            return int(rot) % 360
        except Exception:
            return 0

    @staticmethod
    def set_page_rotation(handle: pikepdf.Pdf, index: int, degrees: int) -> None:
        handle.pages[index].obj["/Rotate"] = degrees

    @staticmethod
    def get_page_mediabox(handle: pikepdf.Pdf, index: int) -> Rect:
        try:
            mb = handle.pages[index].mediabox
            return Rect(float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3]))
        except Exception:
            return Rect(0, 0, 612, 792)

    @staticmethod
    def set_page_mediabox(handle: pikepdf.Pdf, index: int, rect: Rect) -> None:
        handle.pages[index].obj["/MediaBox"] = pikepdf.Array(
            [rect.x0, rect.y0, rect.x1, rect.y1]
        )

    @staticmethod
    def get_page_cropbox(handle: pikepdf.Pdf, index: int) -> Rect | None:
        try:
            page = handle.pages[index]
            if "/CropBox" in page.obj:
                cb = page.obj["/CropBox"]
                return Rect(float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3]))
        except Exception:
            pass
        return None

    @staticmethod
    def set_page_cropbox(handle: pikepdf.Pdf, index: int, rect: Rect) -> None:
        handle.pages[index].obj["/CropBox"] = pikepdf.Array(
            [rect.x0, rect.y0, rect.x1, rect.y1]
        )

    # ---- TOC / Outlines ----------------------------------------------------

    @staticmethod
    def get_toc(handle: pikepdf.Pdf) -> list[dict]:
        """Return flat TOC list as [{"level": int, "title": str, "page": int, "dest": dict}]."""
        entries = []
        try:
            with handle.open_outline() as outline:
                _flatten_outline(outline.root, 1, entries, handle)
        except Exception:
            pass
        return entries

    @staticmethod
    def set_toc(handle: pikepdf.Pdf, toc: list) -> None:
        """Set document outline from flat list [[level, title, page, dest?], ...]."""
        try:
            with handle.open_outline() as outline:
                outline.root = _build_outline_tree(toc, handle)
        except Exception:
            pass

    # ---- Links -------------------------------------------------------------

    @staticmethod
    def get_links(handle: pikepdf.Pdf, page_index: int) -> list[dict]:
        """Return list of link dicts for the page."""
        page_h = _page_height(handle, page_index)
        page = handle.pages[page_index]
        links = []
        try:
            annots = page.obj.get("/Annots", pikepdf.Array())
            for annot_ref in annots:
                try:
                    annot = annot_ref
                    if isinstance(annot, pikepdf.Object):
                        annot = annot.get_object()
                    subtype = str(annot.get("/Subtype", ""))
                    if subtype != "/Link":
                        continue
                    rect_arr = annot.get("/Rect", None)
                    rect = _arr_to_rect(rect_arr, page_h) if rect_arr else Rect()
                    link: dict = {"rect": rect, "kind": LinkType.NONE,
                                  "uri": None, "page": None, "dest_name": None}
                    # Determine kind
                    action = annot.get("/A", None)
                    dest = annot.get("/Dest", None)
                    if action is not None:
                        action_type = str(action.get("/S", ""))
                        if action_type == "/URI":
                            link["kind"] = LinkType.URI
                            link["uri"] = str(action.get("/URI", ""))
                        elif action_type == "/GoTo":
                            link["kind"] = LinkType.GOTO
                            link["page"] = _resolve_dest_page(action.get("/D"), handle)
                        elif action_type == "/Launch":
                            link["kind"] = LinkType.LAUNCH
                        elif action_type == "/Named":
                            link["kind"] = LinkType.NAMED
                            link["dest_name"] = str(action.get("/N", ""))
                        elif action_type == "/GoToR":
                            link["kind"] = LinkType.GOTOR
                    elif dest is not None:
                        link["kind"] = LinkType.GOTO
                        link["page"] = _resolve_dest_page(dest, handle)
                    links.append(link)
                except Exception:
                    continue
        except Exception:
            pass
        return links

    # ---- Annotations -------------------------------------------------------

    @staticmethod
    def get_annotations(handle: pikepdf.Pdf, page_index: int) -> list[dict]:
        """Return list of annotation dicts with rects already in fitz coords."""
        page_h = _page_height(handle, page_index)
        page = handle.pages[page_index]
        annots = []
        try:
            annot_array = page.obj.get("/Annots", None)
            if annot_array is None:
                return []
            for i, annot_ref in enumerate(annot_array):
                try:
                    annot = annot_ref
                    if hasattr(annot, "get_object"):
                        annot = annot.get_object()
                    subtype_raw = str(annot.get("/Subtype", "/Unknown"))
                    type_int = _ANNOT_SUBTYPE_TO_INT.get(subtype_raw, -1)
                    rect_arr = annot.get("/Rect", None)
                    rect = _arr_to_rect(rect_arr, page_h) if rect_arr is not None else Rect()
                    annots.append({
                        "index": i,
                        "type_int": type_int,
                        "subtype": subtype_raw,
                        "rect": rect,
                        "raw": annot,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return annots

    @staticmethod
    def add_annotation(
        handle: pikepdf.Pdf, page_index: int, annot_dict: pikepdf.Dictionary
    ) -> int:
        """Append an annotation dict to the page. Returns the new annotation index."""
        page = handle.pages[page_index]
        if "/Annots" not in page.obj:
            page.obj["/Annots"] = pikepdf.Array()
        annots = page.obj["/Annots"]
        ind = handle.make_indirect(annot_dict)
        annots.append(ind)
        return len(annots) - 1

    @staticmethod
    def update_annotation(
        handle: pikepdf.Pdf, page_index: int, annot_index: int,
        updated_dict: pikepdf.Dictionary,
    ) -> None:
        page = handle.pages[page_index]
        annots = page.obj.get("/Annots", pikepdf.Array())
        if annot_index < len(annots):
            ref = annots[annot_index]
            if hasattr(ref, "get_object"):
                obj = ref.get_object()
                for key, val in updated_dict.items():
                    obj[key] = val
            else:
                annots[annot_index] = updated_dict

    @staticmethod
    def delete_annotation(handle: pikepdf.Pdf, page_index: int, annot_index: int) -> None:
        page = handle.pages[page_index]
        annots = page.obj.get("/Annots", None)
        if annots is not None and annot_index < len(annots):
            del annots[annot_index]

    # ---- Form fields -------------------------------------------------------

    @staticmethod
    def get_form_fields(handle: pikepdf.Pdf) -> list[dict]:
        """Return flat list of form field dicts."""
        fields = []
        try:
            catalog = handle.Root
            acroform = catalog.get("/AcroForm", None)
            if acroform is None:
                return []
            root_fields = acroform.get("/Fields", pikepdf.Array())
            _walk_fields(root_fields, fields, handle)
        except Exception:
            pass
        return fields

    @staticmethod
    def set_form_field_value(handle: pikepdf.Pdf, field_name: str, value: Any) -> None:
        """Set the value of a form field by name."""
        try:
            catalog = handle.Root
            acroform = catalog.get("/AcroForm", None)
            if acroform is None:
                return
            root_fields = acroform.get("/Fields", pikepdf.Array())
            _set_field_value_by_name(root_fields, field_name, value, handle)
        except Exception:
            pass

    # ---- Encryption --------------------------------------------------------

    @staticmethod
    def is_encrypted(handle: pikepdf.Pdf) -> bool:
        return handle.is_encrypted

    @staticmethod
    def encrypt(
        handle: pikepdf.Pdf,
        user_password: str,
        owner_password: str,
        permissions: Permission,
    ) -> None:
        enc = pikepdf.Encryption(
            user=user_password,
            owner=owner_password,
            allow=pikepdf.Permissions(
                print_lowres=(Permission.PRINT in permissions),
                print_highres=(Permission.PRINT_HQ in permissions),
                modify_other=(Permission.MODIFY in permissions),
                extract=(Permission.COPY in permissions),
                annotate=(Permission.ANNOTATE in permissions),
                fill_forms=(Permission.FILL_FORMS in permissions),
                accessibility=(Permission.ACCESSIBILITY in permissions),
                assemble=(Permission.ASSEMBLE in permissions),
            ),
        )
        buf = io.BytesIO()
        handle.save(buf, encryption=enc)
        buf.seek(0)
        # Replace handle contents (in-memory)
        handle.close()

    @staticmethod
    def decrypt(handle: pikepdf.Pdf, password: str) -> bool:
        """For pikepdf, decryption happens at open time. This just validates."""
        return not handle.is_encrypted

    # ---- Embedded files ----------------------------------------------------

    @staticmethod
    def get_embedded_files(handle: pikepdf.Pdf) -> list[dict]:
        files = []
        try:
            catalog = handle.Root
            names = catalog.get("/Names", None)
            if names is None:
                return []
            ef_tree = names.get("/EmbeddedFiles", None)
            if ef_tree is None:
                return []
            # Walk the Names tree
            name_pairs = _flatten_name_tree(ef_tree)
            for name, filespec in name_pairs:
                try:
                    ef = filespec.get("/EF", None)
                    data = b""
                    if ef is not None:
                        f_stream = ef.get("/F", None)
                        if f_stream is not None:
                            data = f_stream.read_bytes()
                    files.append({
                        "name": name,
                        "data": data,
                        "mime": str(filespec.get("/Subtype", "")),
                        "desc": str(filespec.get("/Desc", "")),
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return files

    @staticmethod
    def add_embedded_file(
        handle: pikepdf.Pdf, name: str, data: bytes,
        filename: str | None = None, desc: str | None = None,
    ) -> None:
        stream = handle.make_stream(data)
        stream["/Type"] = pikepdf.Name("/EmbeddedFile")
        ef_dict = pikepdf.Dictionary(F=handle.make_indirect(stream))
        spec = pikepdf.Dictionary(
            Type=pikepdf.Name("/Filespec"),
            F=name if filename is None else filename,
            EF=ef_dict,
        )
        if desc:
            spec["/Desc"] = desc
        spec_ref = handle.make_indirect(spec)
        # Ensure /Names /EmbeddedFiles exists
        if "/Names" not in handle.Root:
            handle.Root["/Names"] = pikepdf.Dictionary()
        names = handle.Root["/Names"]
        if "/EmbeddedFiles" not in names:
            names["/EmbeddedFiles"] = pikepdf.Dictionary(Names=pikepdf.Array())
        ef_names = names["/EmbeddedFiles"]["/Names"]
        ef_names.append(pikepdf.String(name))
        ef_names.append(spec_ref)

    @staticmethod
    def delete_embedded_file(handle: pikepdf.Pdf, name: str) -> None:
        try:
            ef_names = handle.Root["/Names"]["/EmbeddedFiles"]["/Names"]
            for i in range(0, len(ef_names) - 1, 2):
                if str(ef_names[i]) == name:
                    del ef_names[i]  # name entry
                    del ef_names[i]  # filespec entry
                    return
        except Exception:
            pass

    # ---- Image extraction --------------------------------------------------

    @staticmethod
    def extract_images_from_page(handle: pikepdf.Pdf, page_index: int) -> list[dict]:
        """Walk page XObjects, extract image streams."""
        images = []
        try:
            page = handle.pages[page_index]
            resources = page.obj.get("/Resources", None)
            if resources is None:
                return []
            xobjects = resources.get("/XObject", None)
            if xobjects is None:
                return []
            for name, xobj_ref in xobjects.items():
                try:
                    xobj = xobj_ref
                    if hasattr(xobj, "get_object"):
                        xobj = xobj.get_object()
                    if str(xobj.get("/Subtype", "")) != "/Image":
                        continue
                    w = int(xobj.get("/Width", 0))
                    h = int(xobj.get("/Height", 0))
                    bpc = int(xobj.get("/BitsPerComponent", 8))
                    cs_raw = xobj.get("/ColorSpace", None)
                    cs = _parse_colorspace(cs_raw)
                    filt_raw = xobj.get("/Filter", None)
                    filt = _parse_filter(filt_raw)
                    xref = xobj.objgen[0] if hasattr(xobj, "objgen") else 0
                    try:
                        raw_data = xobj.read_raw_bytes()
                    except Exception:
                        try:
                            raw_data = xobj.read_bytes()
                        except Exception:
                            raw_data = b""
                    images.append({
                        "name": str(name),
                        "width": w, "height": h,
                        "bpc": bpc,
                        "colorspace": cs,
                        "filter": filt,
                        "data": raw_data,
                        "xref": xref,
                        "obj": xobj,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return images

    # ---- Low-level page contents -------------------------------------------

    @staticmethod
    def get_page_contents_bytes(handle: pikepdf.Pdf, page_index: int) -> bytes:
        """Return the combined content stream bytes for a page."""
        try:
            page = handle.pages[page_index]
            contents = page.obj.get("/Contents", None)
            if contents is None:
                return b""
            if isinstance(contents, pikepdf.Array):
                return b"".join(s.get_object().read_bytes() for s in contents)
            else:
                obj = contents
                if hasattr(obj, "get_object"):
                    obj = obj.get_object()
                return obj.read_bytes()
        except Exception:
            return b""

    # ---- Drawing overlay ---------------------------------------------------

    @staticmethod
    def overlay_page(
        handle: pikepdf.Pdf,
        page_index: int,
        overlay_bytes: bytes,
        xobj_name: str | None = None,
    ) -> None:
        """Merge an overlay PDF (single page) onto the target page as a Form XObject.

        This is the core of the drawing overlay strategy:
        reportlab generates overlay_bytes → this function merges it.
        """
        overlay_pdf = pikepdf.open(io.BytesIO(overlay_bytes))
        overlay_page = overlay_pdf.pages[0]

        # Build Form XObject from the overlay page
        try:
            contents_raw = PikeBackend.get_page_contents_bytes(overlay_pdf, 0)
        except Exception:
            contents_raw = b""

        xobj_dict = pikepdf.Dictionary(
            Type=pikepdf.Name("/XObject"),
            Subtype=pikepdf.Name("/Form"),
            FormType=1,
            BBox=list(overlay_page.mediabox),
        )

        # Copy resources from overlay page into XObject
        try:
            overlay_res = overlay_page.obj.get("/Resources", None)
            if overlay_res is not None:
                xobj_dict["/Resources"] = handle.copy_foreign(overlay_res)
        except Exception:
            xobj_dict["/Resources"] = pikepdf.Dictionary()

        xobj_stream = handle.make_stream(contents_raw, xobj_dict)
        xobj_ref = handle.make_indirect(xobj_stream)

        # Assign a unique name for the XObject in the target page's resources
        target_page = handle.pages[page_index]
        if "/Resources" not in target_page.obj:
            target_page.obj["/Resources"] = pikepdf.Dictionary()
        resources = target_page.obj["/Resources"]
        if "/XObject" not in resources:
            resources["/XObject"] = pikepdf.Dictionary()
        xobjs = resources["/XObject"]

        if xobj_name is None:
            # Generate a unique name
            idx = 0
            while True:
                candidate = f"/OpenPdfOverlay{idx}"
                if candidate not in xobjs:
                    xobj_name = candidate
                    break
                idx += 1

        xobjs[xobj_name] = xobj_ref

        # Normalize /Contents to an array and append Do operator
        contents = target_page.obj.get("/Contents", None)
        do_stream = handle.make_stream(
            f"q {xobj_name[1:]} Do Q\n".encode()
        )
        do_ref = handle.make_indirect(do_stream)

        if contents is None:
            target_page.obj["/Contents"] = pikepdf.Array([do_ref])
        elif isinstance(contents, pikepdf.Array):
            contents.append(do_ref)
        else:
            # Single stream → wrap in array
            target_page.obj["/Contents"] = pikepdf.Array([contents, do_ref])

        overlay_pdf.close()

    # ---- Page labels -------------------------------------------------------

    @staticmethod
    def get_page_labels(handle: pikepdf.Pdf) -> list[dict]:
        try:
            labels = handle.Root.get("/PageLabels", None)
            if labels is None:
                return []
            # PageLabels is a number tree
            # For simplicity, return raw entries
            return []
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _page_height(handle: pikepdf.Pdf, page_index: int) -> float:
    """Get page height from the MediaBox (not rotation-adjusted)."""
    try:
        mb = handle.pages[page_index].mediabox
        return float(mb[3]) - float(mb[1])
    except Exception:
        return 792.0


def _arr_to_rect(arr, page_h: float) -> Rect:
    """Convert a pikepdf /Rect array (PDF coords) to a fitz Rect."""
    try:
        x0, y0_pdf, x1, y1_pdf = float(arr[0]), float(arr[1]), float(arr[2]), float(arr[3])
        return pdf_to_fitz_rect(x0, y0_pdf, x1, y1_pdf, page_h)
    except Exception:
        return Rect()


def _rect_to_arr(rect: Rect, page_h: float) -> pikepdf.Array:
    """Convert fitz Rect to pikepdf /Rect array (PDF coords)."""
    x0, y0_pdf, x1, y1_pdf = fitz_to_pdf_rect(rect, page_h)
    return pikepdf.Array([x0, y0_pdf, x1, y1_pdf])


def _parse_pdf_date(s: str) -> str:
    """Parse PDF date string; return ISO format string or original."""
    if not s:
        return ""
    s = str(s).strip()
    if s.startswith("D:"):
        s = s[2:]
    # Replace single-quote timezone separators: +05'30' → +05:30
    s = re.sub(r"([+-]\d{2})'(\d{2})'?$", r"\1:\2", s)
    # Remove trailing Z/apostrophe
    s = s.rstrip("Z'")
    for fmt in ("%Y%m%d%H%M%S%z", "%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
        try:
            dt = datetime.strptime(s[:len(fmt.replace("%", "XX").replace("X", ""))], fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return s  # return as-is if unparseable


def _parse_colorspace(cs_raw) -> str:
    if cs_raw is None:
        return "DeviceRGB"
    s = str(cs_raw)
    if "DeviceGray" in s or "Gray" in s:
        return "DeviceGray"
    if "DeviceCMYK" in s or "CMYK" in s:
        return "DeviceCMYK"
    if "Indexed" in s:
        return "Indexed"
    return "DeviceRGB"


def _parse_filter(filt_raw) -> str:
    if filt_raw is None:
        return ""
    s = str(filt_raw)
    if "DCT" in s:
        return "DCTDecode"
    if "JBIG2" in s:
        return "JBIG2Decode"
    if "JPX" in s:
        return "JPXDecode"
    if "Flate" in s:
        return "FlateDecode"
    if "CCITT" in s:
        return "CCITTFaxDecode"
    return s


def _flatten_outline(items, level: int, out: list, handle: pikepdf.Pdf) -> None:
    """Recursively flatten a pikepdf outline tree to a flat list."""
    if items is None:
        return
    for item in items:
        try:
            title = str(item.title) if hasattr(item, "title") else ""
            page_num = _resolve_dest_page(item.destination, handle) if hasattr(item, "destination") else 0
            out.append({
                "level": level,
                "title": title,
                "page": page_num if page_num is not None else 0,
                "dest": {},
            })
            if hasattr(item, "children") and item.children:
                _flatten_outline(item.children, level + 1, out, handle)
        except Exception:
            continue


def _build_outline_tree(toc: list, handle: pikepdf.Pdf) -> list:
    """Convert flat [[level, title, page, ...], ...] list to pikepdf outline items."""
    from pikepdf import OutlineItem as PikepdfOutlineItem
    root = []
    stack: list[tuple[int, list]] = [(0, root)]

    for entry in toc:
        level = entry[0] if len(entry) > 0 else 1
        title = entry[1] if len(entry) > 1 else ""
        page = entry[2] if len(entry) > 2 else 0

        try:
            dest = pikepdf.PageLocation(handle.pages[page], pikepdf.PageLocation.Fit)
            item = PikepdfOutlineItem(title, dest)
        except Exception:
            try:
                item = PikepdfOutlineItem(title, page)
            except Exception:
                continue

        # Find parent at the correct depth
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()

        parent_list = stack[-1][1]
        parent_list.append(item)
        stack.append((level, item.children))

    return root


def _resolve_dest_page(dest, handle: pikepdf.Pdf) -> int | None:
    """Resolve a PDF destination to a 0-based page index."""
    if dest is None:
        return None
    try:
        # dest can be an array [page_obj, /XYZ, x, y, zoom] or a name string
        if isinstance(dest, pikepdf.Array) and len(dest) > 0:
            page_ref = dest[0]
            for i, page in enumerate(handle.pages):
                if page.obj.objgen == page_ref.objgen:
                    return i
            # Fallback: try as direct page index
            return int(dest[0])
        elif isinstance(dest, (int, float)):
            return int(dest)
        elif isinstance(dest, pikepdf.String):
            # Named destination
            return None
    except Exception:
        pass
    return None


def _walk_fields(fields_array, out: list, handle: pikepdf.Pdf, page_map: dict | None = None) -> None:
    """Recursively walk AcroForm field tree and collect terminal widget fields."""
    if page_map is None:
        page_map = {page.obj.objgen: i for i, page in enumerate(handle.pages)}

    for field_ref in fields_array:
        try:
            field = field_ref
            if hasattr(field, "get_object"):
                field = field.get_object()

            # Check if this is a non-terminal node (has /Kids)
            kids = field.get("/Kids", None)
            ft = field.get("/FT", None)

            if ft is None and kids is not None:
                # Intermediate node — recurse
                _walk_fields(kids, out, handle, page_map)
                continue

            # Terminal field
            ft_str = str(ft) if ft is not None else ""
            widget_type = _WIDGET_FT_TO_TYPE.get(ft_str, WidgetType.UNKNOWN)

            # Distinguish checkbox vs button vs radio
            if widget_type == WidgetType.BUTTON:
                ff = int(field.get("/Ff", 0))
                if ff & (1 << 15):  # Radio bit
                    widget_type = WidgetType.RADIOBUTTON
                elif ff & (1 << 16):  # Pushbutton bit
                    widget_type = WidgetType.BUTTON
                else:
                    widget_type = WidgetType.CHECKBOX

            # Multi-select listbox
            if widget_type == WidgetType.COMBOBOX:
                ff = int(field.get("/Ff", 0))
                if not (ff & (1 << 17)):  # Not Combo bit → it's a ListBox
                    widget_type = WidgetType.LISTBOX

            # Get page and rect
            page_num = 0
            rect = Rect()
            page_ref = field.get("/P", None)
            if page_ref is not None and hasattr(page_ref, "objgen"):
                page_num = page_map.get(page_ref.objgen, 0)

            rect_arr = field.get("/Rect", None)
            if rect_arr is not None:
                page_h = _page_height(handle, page_num)
                rect = _arr_to_rect(rect_arr, page_h)

            # Get value
            raw_value = field.get("/V", None)
            value = _parse_field_value(widget_type, raw_value)

            # Get options for combo/list boxes
            options = []
            opt_arr = field.get("/Opt", None)
            if opt_arr is not None:
                for opt in opt_arr:
                    if isinstance(opt, pikepdf.Array):
                        options.append(str(opt[1]) if len(opt) > 1 else str(opt[0]))
                    else:
                        options.append(str(opt))

            name_parts = []
            _collect_field_name(field, name_parts)
            full_name = ".".join(reversed(name_parts)) if name_parts else str(field.get("/T", ""))

            out.append({
                "name": full_name,
                "type": widget_type,
                "value": value,
                "page": page_num,
                "rect": rect,
                "options": options if options else None,
                "flags": int(field.get("/Ff", 0)),
                "obj": field,
            })

            # Recurse into kids for merged widget groups
            if kids is not None and ft is not None:
                _walk_fields(kids, out, handle, page_map)

        except Exception:
            continue


def _collect_field_name(field, parts: list) -> None:
    """Walk up the parent chain collecting /T values to build full field name."""
    t = field.get("/T", None)
    if t is not None:
        parts.append(str(t))
    parent = field.get("/Parent", None)
    if parent is not None:
        try:
            if hasattr(parent, "get_object"):
                parent = parent.get_object()
            _collect_field_name(parent, parts)
        except Exception:
            pass


def _set_field_value_by_name(
    fields_array, field_name: str, value: Any, handle: pikepdf.Pdf
) -> bool:
    """Recursively search for field by name and set its value."""
    for field_ref in fields_array:
        try:
            field = field_ref
            if hasattr(field, "get_object"):
                field = field.get_object()
            t = str(field.get("/T", ""))
            if t == field_name or t.split(".")[-1] == field_name:
                ft_str = str(field.get("/FT", "/Tx"))
                widget_type = _WIDGET_FT_TO_TYPE.get(ft_str, WidgetType.TEXT)
                ff = int(field.get("/Ff", 0))
                if widget_type == WidgetType.BUTTON:
                    if ff & (1 << 15):
                        widget_type = WidgetType.RADIOBUTTON
                    elif not (ff & (1 << 16)):
                        widget_type = WidgetType.CHECKBOX

                if widget_type == WidgetType.CHECKBOX:
                    pdf_val = pikepdf.Name("/Yes") if value else pikepdf.Name("/Off")
                    field["/V"] = pdf_val
                    field["/AS"] = pdf_val
                else:
                    field["/V"] = pikepdf.String(str(value))
                # Remove appearance stream to force regeneration
                if "/AP" in field:
                    del field["/AP"]
                return True
            kids = field.get("/Kids", None)
            if kids is not None:
                if _set_field_value_by_name(kids, field_name, value, handle):
                    return True
        except Exception:
            continue
    return False


def _parse_field_value(widget_type: WidgetType, raw_value) -> Any:
    """Convert a pikepdf field /V to a Python value."""
    if raw_value is None:
        return "" if widget_type == WidgetType.TEXT else False
    if widget_type == WidgetType.CHECKBOX:
        return str(raw_value).lstrip("/") == "Yes"
    if widget_type == WidgetType.RADIOBUTTON:
        return str(raw_value).lstrip("/")
    return str(raw_value)


def _flatten_name_tree(tree) -> list[tuple[str, Any]]:
    """Flatten a PDF Name tree into [(name, value), ...] pairs."""
    result = []
    try:
        names = tree.get("/Names", None)
        if names is not None:
            for i in range(0, len(names) - 1, 2):
                result.append((str(names[i]), names[i + 1]))
        kids = tree.get("/Kids", None)
        if kids is not None:
            for kid in kids:
                result.extend(_flatten_name_tree(kid))
    except Exception:
        pass
    return result
