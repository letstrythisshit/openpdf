"""Tests for openpdf.geometry — Point, Rect, IRect, Matrix, Quad."""
from __future__ import annotations

import math
import pytest

from openpdf.geometry import Point, Rect, IRect, Matrix, Quad


class TestMatrix:
    def test_identity(self):
        m = Matrix()
        assert m.a == 1.0 and m.d == 1.0
        assert m.b == 0.0 and m.c == 0.0
        assert m.e == 0.0 and m.f == 0.0

    def test_from_values(self):
        m = Matrix(2, 0, 0, 3, 10, 20)
        assert m.a == 2.0
        assert m.d == 3.0
        assert m.e == 10.0
        assert m.f == 20.0

    def test_multiply_identity(self):
        m = Matrix(2, 0, 0, 3, 10, 20)
        result = m * Matrix()
        assert result.a == m.a
        assert result.d == m.d
        assert result.e == m.e
        assert result.f == m.f

    def test_multiply_two_matrices(self):
        # Scale then translate
        scale = Matrix(2, 0, 0, 2, 0, 0)
        translate = Matrix(1, 0, 0, 1, 10, 20)
        result = scale * translate
        # Row-vector convention: point * scale * translate
        assert result.a == 2.0
        assert result.d == 2.0
        assert result.e == 10.0
        assert result.f == 20.0

    def test_rotation_matrix(self):
        angle = math.pi / 2  # 90 degrees
        m = Matrix.rotate(90)
        # cos(90)≈0, sin(90)≈1
        assert abs(m.a) < 1e-10
        assert abs(m.b - 1.0) < 1e-10
        assert abs(m.c + 1.0) < 1e-10
        assert abs(m.d) < 1e-10

    def test_scale_matrix(self):
        m = Matrix.scale(3, 4)
        assert m.a == 3.0
        assert m.d == 4.0
        assert m.e == 0.0
        assert m.f == 0.0

    def test_is_rectilinear(self):
        assert Matrix().is_rectilinear
        assert Matrix.scale(2, 3).is_rectilinear
        assert not Matrix.rotate(45).is_rectilinear

    def test_determinant(self):
        m = Matrix(2, 0, 0, 3, 0, 0)
        assert m.determinant == pytest.approx(6.0)

    def test_invert_identity(self):
        inv = Matrix().invert()
        assert inv is not None
        assert inv.a == pytest.approx(1.0)
        assert inv.d == pytest.approx(1.0)

    def test_invert_scale(self):
        m = Matrix.scale(2, 4)
        inv = m.invert()
        assert inv is not None
        assert inv.a == pytest.approx(0.5)
        assert inv.d == pytest.approx(0.25)

    def test_singular_matrix_invert_returns_none(self):
        m = Matrix(0, 0, 0, 0, 0, 0)
        result = m.invert()
        assert result is None

    def test_repr(self):
        m = Matrix(1, 0, 0, 1, 5, 6)
        r = repr(m)
        assert "Matrix" in r


class TestPoint:
    def test_basic(self):
        p = Point(3, 4)
        assert p.x == 3.0
        assert p.y == 4.0

    def test_add(self):
        p = Point(1, 2) + Point(3, 4)
        assert p.x == 4.0
        assert p.y == 6.0

    def test_sub(self):
        p = Point(5, 7) - Point(2, 3)
        assert p.x == 3.0
        assert p.y == 4.0

    def test_mul_scalar(self):
        p = Point(2, 3) * 2
        assert p.x == 4.0
        assert p.y == 6.0

    def test_abs(self):
        p = Point(3, 4)
        assert abs(p) == pytest.approx(5.0)

    def test_transform(self):
        p = Point(1, 0)
        m = Matrix.scale(2, 3)
        q = p.transform(m)
        assert q.x == pytest.approx(2.0)
        assert q.y == pytest.approx(0.0)

    def test_distance_to(self):
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        assert p1.distance_to(p2) == pytest.approx(5.0)

    def test_repr(self):
        assert "Point" in repr(Point(1, 2))


class TestRect:
    def test_basic(self):
        r = Rect(1, 2, 3, 4)
        assert r.x0 == 1.0
        assert r.y0 == 2.0
        assert r.x1 == 3.0
        assert r.y1 == 4.0

    def test_width_height(self):
        r = Rect(0, 0, 10, 20)
        assert r.width == 10.0
        assert r.height == 20.0

    def test_area(self):
        r = Rect(0, 0, 4, 5)
        assert r.get_area() == pytest.approx(20.0)

    def test_is_empty(self):
        assert Rect(0, 0, 0, 0).is_empty
        assert not Rect(0, 0, 1, 1).is_empty

    def test_contains_point(self):
        r = Rect(0, 0, 10, 10)
        assert r.contains(Point(5, 5))
        assert not r.contains(Point(15, 5))

    def test_contains_rect(self):
        r = Rect(0, 0, 10, 10)
        assert r.contains(Rect(2, 2, 8, 8))
        assert not r.contains(Rect(2, 2, 12, 8))

    def test_intersects(self):
        r1 = Rect(0, 0, 5, 5)
        r2 = Rect(3, 3, 8, 8)
        r3 = Rect(10, 10, 15, 15)
        assert r1.intersects(r2)
        assert not r1.intersects(r3)

    def test_intersection(self):
        r1 = Rect(0, 0, 5, 5)
        r2 = Rect(3, 3, 8, 8)
        inter = r1 & r2
        assert inter.x0 == 3.0
        assert inter.y0 == 3.0
        assert inter.x1 == 5.0
        assert inter.y1 == 5.0

    def test_union(self):
        r1 = Rect(0, 0, 5, 5)
        r2 = Rect(3, 3, 8, 8)
        union = r1 | r2
        assert union.x0 == 0.0
        assert union.y0 == 0.0
        assert union.x1 == 8.0
        assert union.y1 == 8.0

    def test_normalize(self):
        r = Rect(5, 8, 2, 1)
        n = r.normalize()
        assert n.x0 <= n.x1
        assert n.y0 <= n.y1

    def test_round_outward(self):
        """Rect.round() must round outward: floor min, ceil max."""
        r = Rect(1.2, 2.3, 4.7, 5.8)
        ir = r.round()
        assert isinstance(ir, IRect)
        assert ir.x0 == 1  # floor(1.2)
        assert ir.y0 == 2  # floor(2.3)
        assert ir.x1 == 5  # ceil(4.7)
        assert ir.y1 == 6  # ceil(5.8)

    def test_round_already_integer(self):
        r = Rect(1.0, 2.0, 3.0, 4.0)
        ir = r.round()
        assert ir.x0 == 1
        assert ir.y0 == 2
        assert ir.x1 == 3
        assert ir.y1 == 4

    def test_transform_via_quad(self):
        r = Rect(0, 0, 2, 2)
        m = Matrix.scale(3, 3)
        t = r.transform(m)
        assert t.x0 == pytest.approx(0.0)
        assert t.y0 == pytest.approx(0.0)
        assert t.x1 == pytest.approx(6.0)
        assert t.y1 == pytest.approx(6.0)

    def test_transform_translate(self):
        r = Rect(1, 2, 3, 4)
        m = Matrix(1, 0, 0, 1, 10, 20)  # translate by (10, 20)
        t = r.transform(m)
        assert t.x0 == pytest.approx(11.0)
        assert t.y0 == pytest.approx(22.0)
        assert t.x1 == pytest.approx(13.0)
        assert t.y1 == pytest.approx(24.0)

    def test_repr(self):
        assert "Rect" in repr(Rect(0, 0, 1, 1))

    def test_top_left_bottom_right(self):
        r = Rect(1, 2, 3, 4)
        assert r.top_left == Point(1, 2)
        assert r.bottom_right == Point(3, 4)


class TestIRect:
    def test_basic(self):
        ir = IRect(1, 2, 3, 4)
        assert ir.x0 == 1
        assert ir.y0 == 2
        assert ir.x1 == 3
        assert ir.y1 == 4

    def test_to_rect(self):
        ir = IRect(1, 2, 3, 4)
        r = ir.to_rect()
        assert isinstance(r, Rect)
        assert r.x0 == 1.0

    def test_repr(self):
        assert "IRect" in repr(IRect(0, 0, 5, 5))


class TestQuad:
    def test_from_rect(self):
        r = Rect(0, 0, 4, 4)
        q = Quad(r)
        assert q.ul == Point(0, 0)
        assert q.ur == Point(4, 0)
        assert q.ll == Point(0, 4)
        assert q.lr == Point(4, 4)

    def test_rect_property(self):
        r = Rect(0, 0, 4, 4)
        q = Quad(r)
        assert q.rect.x0 == pytest.approx(0.0)
        assert q.rect.y0 == pytest.approx(0.0)
        assert q.rect.x1 == pytest.approx(4.0)
        assert q.rect.y1 == pytest.approx(4.0)

    def test_transform(self):
        r = Rect(0, 0, 2, 2)
        q = Quad(r)
        m = Matrix.scale(2, 2)
        tq = q.transform(m)
        assert tq.lr.x == pytest.approx(4.0)
        assert tq.lr.y == pytest.approx(4.0)

    def test_morph(self):
        r = Rect(0, 0, 4, 4)
        q = Quad(r)
        pivot = Point(2, 2)
        m = Matrix.scale(2, 2)
        morphed = q.morph(pivot, m)
        # After morph: translate to origin, scale 2x, translate back
        # ul: (0,0) -> (-2,-2) -> (-4,-4) -> (-2,-2) -> nope
        # Actually: (p - pivot) * m + pivot
        # ul = (0,0): (0-2, 0-2) = (-2,-2), scaled by 2 = (-4,-4), +pivot=(2,2) = (-2,-2)
        assert morphed.ul.x == pytest.approx(-2.0)
        assert morphed.ul.y == pytest.approx(-2.0)

    def test_is_rectangular(self):
        r = Rect(0, 0, 4, 4)
        q = Quad(r)
        assert q.is_rectangular

    def test_repr(self):
        assert "Quad" in repr(Quad(Rect(0, 0, 1, 1)))
