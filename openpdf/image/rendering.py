"""Pixmap — raster image container. Wraps PIL.Image internally."""
from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Union

from PIL import Image, ImageOps

from openpdf.geometry import IRect, Rect
from openpdf.constants import ColorSpace
from openpdf.exceptions import DependencyError


class Pixmap:
    """Raster image with pixel access. Mirrors fitz.Pixmap."""

    def __init__(
        self,
        source: Union[Image.Image, bytes, None] = None,
        colorspace: ColorSpace = ColorSpace.CS_RGB,
        width: int = 0,
        height: int = 0,
        alpha: bool = False,
    ) -> None:
        self._colorspace = colorspace
        self._alpha = alpha
        self._samples_cache: bytes | None = None

        if isinstance(source, Image.Image):
            self._img = source
        elif isinstance(source, (bytes, bytearray)):
            self._img = Image.open(io.BytesIO(source))
        elif source is None:
            mode = "RGBA" if alpha else _cs_to_mode(colorspace)
            self._img = Image.new(mode, (max(width, 1), max(height, 1)))
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")

        self._alpha = self._img.mode in ("RGBA", "LA")

    # ---- Properties --------------------------------------------------------

    @property
    def width(self) -> int:
        return self._img.width

    @property
    def height(self) -> int:
        return self._img.height

    @property
    def n(self) -> int:
        """Number of components per pixel."""
        mode_to_n = {"L": 1, "LA": 2, "RGB": 3, "RGBA": 4, "CMYK": 4, "P": 1}
        return mode_to_n.get(self._img.mode, 3)

    @property
    def alpha(self) -> bool:
        return self._alpha

    @property
    def stride(self) -> int:
        return self.width * self.n

    @property
    def irect(self) -> IRect:
        return IRect(0, 0, self.width, self.height)

    @property
    def samples(self) -> bytes:
        if self._samples_cache is None:
            self._samples_cache = self._img.tobytes()
        return self._samples_cache

    @property
    def samples_mv(self):
        return memoryview(self.samples)

    @property
    def size(self) -> int:
        return len(self.samples)

    @property
    def colorspace(self) -> ColorSpace:
        return self._colorspace

    @property
    def x(self) -> int:
        return 0

    @property
    def y(self) -> int:
        return 0

    @property
    def xres(self) -> int:
        try:
            return self._img.info.get("dpi", (96, 96))[0]
        except Exception:
            return 96

    @property
    def yres(self) -> int:
        try:
            return self._img.info.get("dpi", (96, 96))[1]
        except Exception:
            return 96

    @property
    def is_monochrome(self) -> bool:
        return self._img.mode in ("L", "1")

    @property
    def is_unicolor(self) -> bool:
        """True if all pixels have the same color."""
        extrema = self._img.getextrema()
        if isinstance(extrema, tuple) and isinstance(extrema[0], (int, float)):
            # Single channel
            return extrema[0] == extrema[1]
        return all(lo == hi for lo, hi in extrema)

    # ---- Pixel access ------------------------------------------------------

    def pixel(self, x: int, y: int) -> tuple:
        return self._img.getpixel((x, y))

    def set_pixel(self, x: int, y: int, color: tuple) -> None:
        self._img.putpixel((x, y), color)
        self._samples_cache = None

    # ---- Conversions -------------------------------------------------------

    def tobytes(self, output: str = "png") -> bytes:
        buf = io.BytesIO()
        fmt_map = {"png": "PNG", "jpeg": "JPEG", "jpg": "JPEG",
                   "ppm": "PPM", "psd": "PSD", "tga": "TGA", "pbm": "PPM"}
        fmt = fmt_map.get(output.lower(), output.upper())
        img = self._img
        # JPEG doesn't support RGBA
        if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(buf, format=fmt)
        return buf.getvalue()

    def save(self, filename: Union[str, Path], output: str | None = None) -> None:
        fmt = output or Path(str(filename)).suffix.lstrip(".")
        fmt_upper = fmt.upper()
        img = self._img
        if fmt_upper == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(str(filename), format=fmt_upper)

    def pil_image(self) -> Image.Image:
        return self._img

    # ---- Manipulation ------------------------------------------------------

    def set_alpha(self, alphavalues: bytes | None = None, premultiply: bool = True, opaque=None) -> None:
        self._samples_cache = None
        if alphavalues is None:
            if self._img.mode == "RGBA":
                self._img = self._img.convert("RGB")
            self._alpha = False
        else:
            if self._img.mode != "RGBA":
                self._img = self._img.convert("RGBA")
            alpha_img = Image.frombytes("L", (self.width, self.height), alphavalues)
            self._img.putalpha(alpha_img)
            self._alpha = True

    def clear_with(self, value: int = 255) -> None:
        self._samples_cache = None
        self._img = Image.new(self._img.mode, self._img.size, value)

    def tint_with(self, black: int, white: int) -> None:
        """Remap tonal range: black maps to gray value `black`, white maps to `white`."""
        self._samples_cache = None
        lut = [int(black + (white - black) * i / 255) for i in range(256)]
        if self._img.mode == "RGB":
            self._img = self._img.point(lut * 3)
        elif self._img.mode == "L":
            self._img = self._img.point(lut)

    def gamma_with(self, gamma: float) -> None:
        """Apply gamma correction."""
        self._samples_cache = None
        lut = [int(255 * (i / 255.0) ** (1.0 / gamma)) for i in range(256)]
        if self._img.mode in ("RGB", "RGBA"):
            r, g, b = self._img.split()[:3]
            r = r.point(lut); g = g.point(lut); b = b.point(lut)
            if self._img.mode == "RGBA":
                a = self._img.split()[3]
                self._img = Image.merge("RGBA", (r, g, b, a))
            else:
                self._img = Image.merge("RGB", (r, g, b))
        elif self._img.mode == "L":
            self._img = self._img.point(lut)

    def invert_irect(self, irect: IRect | None = None) -> None:
        """Invert pixels within irect (or entire image if None)."""
        self._samples_cache = None
        if irect is None:
            self._img = ImageOps.invert(self._img.convert("RGB"))
        else:
            region = self._img.crop((irect.x0, irect.y0, irect.x1, irect.y1))
            region = ImageOps.invert(region.convert("RGB"))
            self._img.paste(region, (irect.x0, irect.y0))

    def copy(self, source: "Pixmap", irect: IRect) -> None:
        """Blit source pixmap's irect region onto self at same position."""
        region = source._img.crop((irect.x0, irect.y0, irect.x1, irect.y1))
        self._img.paste(region, (irect.x0, irect.y0))
        self._samples_cache = None

    def set_rect(self, irect: IRect, color: tuple) -> None:
        """Fill a rectangle with the given color."""
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self._img)
        draw.rectangle([irect.x0, irect.y0, irect.x1 - 1, irect.y1 - 1], fill=color)
        self._samples_cache = None

    def shrink(self, factor: int) -> None:
        """Reduce image dimensions by integer factor."""
        self._samples_cache = None
        new_w = max(1, self.width // factor)
        new_h = max(1, self.height // factor)
        self._img = self._img.resize((new_w, new_h), Image.LANCZOS)

    def set_origin(self, x: int, y: int) -> None:
        pass  # Origin is always (0, 0) for PIL-backed pixmaps

    def set_resolution(self, xres: int, yres: int) -> None:
        self._img.info["dpi"] = (xres, yres)

    # ---- Color space conversion --------------------------------------------

    def to_rgb(self) -> "Pixmap":
        return Pixmap(source=self._img.convert("RGB"), colorspace=ColorSpace.CS_RGB)

    def to_gray(self) -> "Pixmap":
        return Pixmap(source=self._img.convert("L"), colorspace=ColorSpace.CS_GRAY)

    def to_cmyk(self) -> "Pixmap":
        return Pixmap(source=self._img.convert("CMYK"), colorspace=ColorSpace.CS_CMYK)

    # ---- OCR (optional) ----------------------------------------------------

    def ocr(self, language: str = "eng", tessdata: str | None = None) -> str:
        from openpdf.utils.ocr import ocr_pixmap
        return ocr_pixmap(self._img, language=language, tessdata=tessdata)

    # ---- Repr --------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Pixmap({self.width}x{self.height}, {self._img.mode})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cs_to_mode(cs: ColorSpace) -> str:
    if cs == ColorSpace.CS_GRAY:
        return "L"
    if cs == ColorSpace.CS_CMYK:
        return "CMYK"
    return "RGB"
