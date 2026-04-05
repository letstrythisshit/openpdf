"""Geometric primitives: Point, Rect, IRect, Matrix, Quad.

All types mirror the fitz (PyMuPDF) equivalents and use the same
top-left-origin coordinate convention (y increases downward).
"""
from __future__ import annotations

import math
from typing import Iterator, Sequence, Union

# ---------------------------------------------------------------------------
# Forward declarations handled via TYPE_CHECKING-free approach:
# Matrix is defined before Point/Rect so Point.transform() can reference it.
# ---------------------------------------------------------------------------


class Matrix:
    """3×3 affine transformation matrix in row-vector convention.

    The matrix layout is:
        | a  b  0 |
        | c  d  0 |
        | e  f  1 |

    A point [x, y, 1] is transformed as [x, y, 1] · M.
    Concatenation: m1 * m2 means "apply m1 first, then m2".
    """

    __slots__ = ("a", "b", "c", "d", "e", "f")

    def __init__(
        self,
        a: float = 1.0,
        b: float = 0.0,
        c: float = 0.0,
        d: float = 1.0,
        e: float = 0.0,
        f: float = 0.0,
    ) -> None:
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)
        self.e = float(e)
        self.f = float(f)

    # ---- Factories ---------------------------------------------------------

    @classmethod
    def identity(cls) -> "Matrix":
        return cls(1, 0, 0, 1, 0, 0)

    @classmethod
    def rotation(cls, degrees: float) -> "Matrix":
        rad = math.radians(degrees)
        c = math.cos(rad)
        s = math.sin(rad)
        return cls(c, s, -s, c, 0, 0)

    # Alias used by fitz and some tests
    rotate = rotation

    @classmethod
    def scale(cls, sx: float, sy: float) -> "Matrix":
        return cls(sx, 0, 0, sy, 0, 0)

    @classmethod
    def translation(cls, tx: float, ty: float) -> "Matrix":
        return cls(1, 0, 0, 1, tx, ty)

    @classmethod
    def shear(cls, sx: float, sy: float) -> "Matrix":
        return cls(1, sy, sx, 1, 0, 0)

    # ---- Arithmetic --------------------------------------------------------

    def __mul__(self, other: "Matrix") -> "Matrix":
        """Concatenate: self applied first, other second (row-vector convention)."""
        a = self.a * other.a + self.b * other.c
        b = self.a * other.b + self.b * other.d
        c = self.c * other.a + self.d * other.c
        d = self.c * other.b + self.d * other.d
        e = self.e * other.a + self.f * other.c + other.e
        f = self.e * other.b + self.f * other.d + other.f
        return Matrix(a, b, c, d, e, f)

    def __invert__(self) -> "Matrix | None":
        """Return the inverse matrix, or None if singular."""
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-12:
            return None
        inv_det = 1.0 / det
        a =  self.d * inv_det
        b = -self.b * inv_det
        c = -self.c * inv_det
        d =  self.a * inv_det
        e = (self.c * self.f - self.d * self.e) * inv_det
        f = (self.b * self.e - self.a * self.f) * inv_det
        return Matrix(a, b, c, d, e, f)

    def invert(self) -> "Matrix | None":
        """Return inverse of this matrix, or None if singular."""
        return ~self

    def concat(self, other: "Matrix") -> "Matrix":
        """Return self · other (other applied after self)."""
        return self * other

    def prerotate(self, degrees: float) -> "Matrix":
        return Matrix.rotation(degrees) * self

    def prescale(self, sx: float, sy: float) -> "Matrix":
        return Matrix.scale(sx, sy) * self

    def pretranslate(self, tx: float, ty: float) -> "Matrix":
        return Matrix.translation(tx, ty) * self

    # ---- Properties --------------------------------------------------------

    @property
    def determinant(self) -> float:
        """Determinant of the 2×2 linear part."""
        return self.a * self.d - self.b * self.c

    @property
    def is_rectilinear(self) -> bool:
        """True if the matrix has no rotation/shear component (only scale/translate)."""
        return abs(self.b) < 1e-8 and abs(self.c) < 1e-8

    # ---- Sequence protocol -------------------------------------------------

    def __iter__(self) -> Iterator[float]:
        yield self.a; yield self.b; yield self.c
        yield self.d; yield self.e; yield self.f

    def __len__(self) -> int:
        return 6

    def __getitem__(self, idx: int) -> float:
        return (self.a, self.b, self.c, self.d, self.e, self.f)[idx]

    # ---- Repr / eq ---------------------------------------------------------

    def __repr__(self) -> str:
        return f"Matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Matrix):
            return NotImplemented
        return (
            abs(self.a - other.a) < 1e-9 and abs(self.b - other.b) < 1e-9
            and abs(self.c - other.c) < 1e-9 and abs(self.d - other.d) < 1e-9
            and abs(self.e - other.e) < 1e-9 and abs(self.f - other.f) < 1e-9
        )


# ---------------------------------------------------------------------------
# Point
# ---------------------------------------------------------------------------


class Point:
    """2-D point / vector."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        if isinstance(x, (list, tuple)) and y == 0.0:
            # Point((x, y)) form
            self.x = float(x[0])
            self.y = float(x[1])
        elif isinstance(x, Point):
            self.x = x.x
            self.y = x.y
        else:
            self.x = float(x)
            self.y = float(y)

    # ---- Arithmetic --------------------------------------------------------

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Point":
        return Point(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Point":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Point":
        return Point(self.x / scalar, self.y / scalar)

    def __neg__(self) -> "Point":
        return Point(-self.x, -self.y)

    def __abs__(self) -> float:
        return math.hypot(self.x, self.y)

    # ---- Properties --------------------------------------------------------

    @property
    def norm(self) -> float:
        return abs(self)

    @property
    def unit(self) -> "Point":
        n = abs(self)
        if n < 1e-12:
            return Point(0.0, 0.0)
        return Point(self.x / n, self.y / n)

    def distance_to(self, other: "Point") -> float:
        return abs(self - other)

    def transform(self, m: Matrix) -> "Point":
        """Apply affine Matrix to this point."""
        return Point(
            self.x * m.a + self.y * m.c + m.e,
            self.x * m.b + self.y * m.d + m.f,
        )

    # ---- Sequence protocol -------------------------------------------------

    def __len__(self) -> int:
        return 2

    def __getitem__(self, idx: int) -> float:
        return (self.x, self.y)[idx]

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    # ---- Repr / eq ---------------------------------------------------------

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __hash__(self) -> int:
        return hash((round(self.x, 6), round(self.y, 6)))


# ---------------------------------------------------------------------------
# Rect
# ---------------------------------------------------------------------------

# Sentinel for "infinite rect" (matches fitz convention)
_INF = 1e20


class Rect:
    """Axis-aligned rectangle with float coordinates.

    Convention: top-left origin, y increases downward (same as fitz).
    x0 = left, y0 = top, x1 = right, y1 = bottom.
    """

    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(
        self,
        x0: Union[float, "Rect", Sequence] = 0.0,
        y0: float = 0.0,
        x1: float = 0.0,
        y1: float = 0.0,
    ) -> None:
        if isinstance(x0, Rect):
            self.x0, self.y0, self.x1, self.y1 = x0.x0, x0.y0, x0.x1, x0.y1
        elif isinstance(x0, (list, tuple)):
            self.x0 = float(x0[0]); self.y0 = float(x0[1])
            self.x1 = float(x0[2]); self.y1 = float(x0[3])
        elif isinstance(x0, Point) and isinstance(y0, Point):  # type: ignore[arg-type]
            # Rect(top_left, bottom_right)
            tl: Point = x0  # type: ignore[assignment]
            br: Point = y0  # type: ignore[assignment]
            self.x0 = tl.x; self.y0 = tl.y; self.x1 = br.x; self.y1 = br.y
        else:
            self.x0 = float(x0); self.y0 = float(y0)
            self.x1 = float(x1); self.y1 = float(y1)

    # ---- Properties --------------------------------------------------------

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def top_left(self) -> Point:
        return Point(self.x0, self.y0)

    @property
    def top_right(self) -> Point:
        return Point(self.x1, self.y0)

    @property
    def bottom_left(self) -> Point:
        return Point(self.x0, self.y1)

    @property
    def bottom_right(self) -> Point:
        return Point(self.x1, self.y1)

    @property
    def quad(self) -> "Quad":
        return Quad(self.top_left, self.top_right, self.bottom_left, self.bottom_right)

    @property
    def is_empty(self) -> bool:
        return self.x1 <= self.x0 or self.y1 <= self.y0

    @property
    def is_infinite(self) -> bool:
        return self.x0 <= -_INF * 0.9 and self.y0 <= -_INF * 0.9

    # ---- Geometric operations ----------------------------------------------

    def contains(self, other: Union[Point, "Rect"]) -> bool:
        if isinstance(other, Point):
            return self.x0 <= other.x <= self.x1 and self.y0 <= other.y <= self.y1
        return (
            self.x0 <= other.x0 and self.y0 <= other.y0
            and self.x1 >= other.x1 and self.y1 >= other.y1
        )

    def intersects(self, other: "Rect") -> bool:
        return (
            self.x0 < other.x1 and self.x1 > other.x0
            and self.y0 < other.y1 and self.y1 > other.y0
        )

    def intersect(self, other: "Rect") -> "Rect":
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        if x1 <= x0 or y1 <= y0:
            return Rect(0, 0, 0, 0)
        return Rect(x0, y0, x1, y1)

    def include_point(self, p: Point) -> "Rect":
        return Rect(
            min(self.x0, p.x), min(self.y0, p.y),
            max(self.x1, p.x), max(self.y1, p.y),
        )

    def include_rect(self, other: "Rect") -> "Rect":
        return Rect(
            min(self.x0, other.x0), min(self.y0, other.y0),
            max(self.x1, other.x1), max(self.y1, other.y1),
        )

    def get_area(self, unit: str = "") -> float:
        """Return the area of the rectangle."""
        return self.width * self.height

    def __and__(self, other: "Rect") -> "Rect":
        """Intersection of two rectangles."""
        return self.intersect(other)

    def __or__(self, other: "Rect") -> "Rect":
        """Union (bounding box) of two rectangles."""
        return self.include_rect(other)

    def normalize(self) -> "Rect":
        return Rect(
            min(self.x0, self.x1), min(self.y0, self.y1),
            max(self.x0, self.x1), max(self.y0, self.y1),
        )

    def transform(self, m: Matrix) -> "Rect":
        """Apply matrix; return bounding rect of all 4 transformed corners."""
        return self.quad.transform(m).rect

    def round(self) -> "IRect":
        """Round outward to integer coordinates (floor min, ceil max)."""
        return IRect(
            math.floor(self.x0), math.floor(self.y0),
            math.ceil(self.x1), math.ceil(self.y1),
        )

    def morph(self, fixpoint: Point, m: Matrix) -> "Quad":
        """Morph rect around a fixpoint using matrix m."""
        return self.quad.morph(fixpoint, m)

    # ---- Sequence protocol -------------------------------------------------

    def __len__(self) -> int:
        return 4

    def __getitem__(self, idx: int) -> float:
        return (self.x0, self.y0, self.x1, self.y1)[idx]

    def __iter__(self) -> Iterator[float]:
        yield self.x0; yield self.y0; yield self.x1; yield self.y1

    # ---- Repr / eq ---------------------------------------------------------

    def __repr__(self) -> str:
        return f"Rect({self.x0}, {self.y0}, {self.x1}, {self.y1})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return NotImplemented
        return (
            abs(self.x0 - other.x0) < 1e-9 and abs(self.y0 - other.y0) < 1e-9
            and abs(self.x1 - other.x1) < 1e-9 and abs(self.y1 - other.y1) < 1e-9
        )

    def __bool__(self) -> bool:
        return not self.is_empty


# ---------------------------------------------------------------------------
# IRect
# ---------------------------------------------------------------------------


class IRect:
    """Integer rectangle — pixel coordinates for rendered bitmaps."""

    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(
        self,
        x0: Union[int, "IRect", Sequence] = 0,
        y0: int = 0,
        x1: int = 0,
        y1: int = 0,
    ) -> None:
        if isinstance(x0, IRect):
            self.x0, self.y0, self.x1, self.y1 = x0.x0, x0.y0, x0.x1, x0.y1
        elif isinstance(x0, (list, tuple)):
            self.x0 = int(x0[0]); self.y0 = int(x0[1])
            self.x1 = int(x0[2]); self.y1 = int(x0[3])
        else:
            self.x0 = int(x0); self.y0 = int(y0)
            self.x1 = int(x1); self.y1 = int(y1)

    @property
    def rect(self) -> Rect:
        return Rect(self.x0, self.y0, self.x1, self.y1)

    def to_rect(self) -> Rect:
        """Convert to Rect (float coordinates)."""
        return self.rect

    @property
    def width(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> int:
        return max(0, self.y1 - self.y0)

    @property
    def is_empty(self) -> bool:
        return self.x1 <= self.x0 or self.y1 <= self.y0

    @property
    def top_left(self) -> Point:
        return Point(self.x0, self.y0)

    @property
    def bottom_right(self) -> Point:
        return Point(self.x1, self.y1)

    def contains(self, other: Union[Point, "IRect"]) -> bool:
        if isinstance(other, Point):
            return self.x0 <= other.x <= self.x1 and self.y0 <= other.y <= self.y1
        return (
            self.x0 <= other.x0 and self.y0 <= other.y0
            and self.x1 >= other.x1 and self.y1 >= other.y1
        )

    def intersect(self, other: "IRect") -> "IRect":
        x0 = max(self.x0, other.x0); y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1); y1 = min(self.y1, other.y1)
        if x1 <= x0 or y1 <= y0:
            return IRect(0, 0, 0, 0)
        return IRect(x0, y0, x1, y1)

    def __len__(self) -> int:
        return 4

    def __getitem__(self, idx: int) -> int:
        return (self.x0, self.y0, self.x1, self.y1)[idx]

    def __iter__(self) -> Iterator[int]:
        yield self.x0; yield self.y0; yield self.x1; yield self.y1

    def __repr__(self) -> str:
        return f"IRect({self.x0}, {self.y0}, {self.x1}, {self.y1})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IRect):
            return NotImplemented
        return self.x0 == other.x0 and self.y0 == other.y0 and self.x1 == other.x1 and self.y1 == other.y1


# ---------------------------------------------------------------------------
# Quad
# ---------------------------------------------------------------------------


class Quad:
    """Arbitrary quadrilateral defined by four corner points."""

    __slots__ = ("ul", "ur", "ll", "lr")

    def __init__(
        self,
        ul=None,
        ur=None,
        ll=None,
        lr=None,
    ) -> None:
        # Accept a single Rect to build the axis-aligned quad
        if isinstance(ul, Rect) and ur is None and ll is None and lr is None:
            r = ul
            self.ul = Point(r.x0, r.y0)
            self.ur = Point(r.x1, r.y0)
            self.ll = Point(r.x0, r.y1)
            self.lr = Point(r.x1, r.y1)
            return
        self.ul = ul if ul is not None else Point()
        self.ur = ur if ur is not None else Point()
        self.ll = ll if ll is not None else Point()
        self.lr = lr if lr is not None else Point()

    @property
    def rect(self) -> Rect:
        xs = [self.ul.x, self.ur.x, self.ll.x, self.lr.x]
        ys = [self.ul.y, self.ur.y, self.ll.y, self.lr.y]
        return Rect(min(xs), min(ys), max(xs), max(ys))

    @property
    def is_rectangular(self) -> bool:
        """True if the quad is axis-aligned (i.e., it is effectively a Rect)."""
        return (
            abs(self.ul.y - self.ur.y) < 1e-6
            and abs(self.ll.y - self.lr.y) < 1e-6
            and abs(self.ul.x - self.ll.x) < 1e-6
            and abs(self.ur.x - self.lr.x) < 1e-6
        )

    @property
    def is_convex(self) -> bool:
        """True if all cross-products have the same sign."""
        def cross(o: Point, a: Point, b: Point) -> float:
            return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
        pts = [self.ul, self.ur, self.lr, self.ll]
        signs = [cross(pts[i], pts[(i+1)%4], pts[(i+2)%4]) >= 0 for i in range(4)]
        return all(signs) or not any(signs)

    def transform(self, m: Matrix) -> "Quad":
        return Quad(
            self.ul.transform(m),
            self.ur.transform(m),
            self.ll.transform(m),
            self.lr.transform(m),
        )

    def morph(self, fixpoint: Point, m: Matrix) -> "Quad":
        """Morph around fixpoint: translate to origin, apply m, translate back."""
        t_in = Matrix.translation(-fixpoint.x, -fixpoint.y)
        t_out = Matrix.translation(fixpoint.x, fixpoint.y)
        combined = t_in * m * t_out
        return self.transform(combined)

    def __repr__(self) -> str:
        return f"Quad({self.ul!r}, {self.ur!r}, {self.ll!r}, {self.lr!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quad):
            return NotImplemented
        return (
            self.ul == other.ul and self.ur == other.ur
            and self.ll == other.ll and self.lr == other.lr
        )
