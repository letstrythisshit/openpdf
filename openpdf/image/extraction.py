"""Embedded image extraction from PDF pages."""
from __future__ import annotations

import io

import pikepdf
from PIL import Image

from openpdf.exceptions import FileDataError


def extract_image_by_xref(pike_pdf: pikepdf.Pdf, xref: int) -> dict:
    """Extract an embedded image by its object xref number.

    Returns a dict matching fitz's extract_image() output:
    {"ext": "png", "width": w, "height": h, "image": bytes,
     "colorspace": int, "cs-name": str, "xres": int, "yres": int}
    """
    try:
        obj = pike_pdf.get_object((xref, 0))
        if obj is None:
            raise FileDataError(f"No object found with xref {xref}")

        # Ensure it's an image XObject
        subtype = str(obj.get("/Subtype", ""))
        if subtype != "/Image":
            raise FileDataError(f"Object {xref} is not an image XObject (subtype: {subtype})")

        w = int(obj.get("/Width", 0))
        h = int(obj.get("/Height", 0))
        bpc = int(obj.get("/BitsPerComponent", 8))
        cs_raw = obj.get("/ColorSpace", None)
        cs_name = _parse_colorspace_name(cs_raw)
        filt = str(obj.get("/Filter", ""))

        # Determine colorspace integer (fitz convention: 1=gray, 2=rgb, 3=cmyk)
        cs_int = _cs_name_to_int(cs_name)

        # Resolution
        xres = yres = 96
        try:
            res = obj.get("/Resolution", None)
            if res is not None:
                xres = yres = int(res)
        except Exception:
            pass

        # Get image bytes
        try:
            if "DCT" in filt or "JPEG" in filt:
                raw = obj.read_raw_bytes()
                ext = "jpeg"
                pil = Image.open(io.BytesIO(raw))
                out = io.BytesIO()
                pil.save(out, format="JPEG")
                image_bytes = out.getvalue()
            elif "JPX" in filt or "JPEG2000" in filt:
                raw = obj.read_raw_bytes()
                ext = "jp2"
                image_bytes = raw
            else:
                # Decode and re-encode as PNG
                decoded = obj.read_bytes()
                mode = _cs_to_pil_mode(cs_name, bpc)
                if w > 0 and h > 0:
                    try:
                        pil = Image.frombytes(mode, (w, h), decoded)
                    except Exception:
                        pil = Image.open(io.BytesIO(decoded))
                else:
                    pil = Image.open(io.BytesIO(decoded))
                out = io.BytesIO()
                pil.save(out, format="PNG")
                image_bytes = out.getvalue()
                ext = "png"
        except Exception:
            try:
                raw = obj.read_raw_bytes()
                image_bytes = raw
                ext = "raw"
            except Exception:
                image_bytes = b""
                ext = "raw"

        return {
            "ext": ext,
            "width": w,
            "height": h,
            "image": image_bytes,
            "colorspace": cs_int,
            "cs-name": cs_name,
            "xres": xres,
            "yres": yres,
        }

    except FileDataError:
        raise
    except Exception as exc:
        raise FileDataError(f"Failed to extract image xref {xref}: {exc}") from exc


def _parse_colorspace_name(cs_raw) -> str:
    if cs_raw is None:
        return "DeviceRGB"
    s = str(cs_raw)
    if "Gray" in s:
        return "DeviceGray"
    if "CMYK" in s:
        return "DeviceCMYK"
    if "Indexed" in s:
        return "Indexed"
    return "DeviceRGB"


def _cs_name_to_int(name: str) -> int:
    if "Gray" in name:
        return 1
    if "CMYK" in name:
        return 3
    return 2  # RGB


def _cs_to_pil_mode(cs_name: str, bpc: int) -> str:
    if "Gray" in cs_name:
        return "L"
    if "CMYK" in cs_name:
        return "CMYK"
    return "RGB"
