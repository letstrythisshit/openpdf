"""Tests for openpdf.constants."""
from __future__ import annotations

from openpdf.constants import (
    AnnotationType, LinkType, WidgetType, ColorSpace, Permission,
    TEXT_PRESERVE_LIGATURES, TEXT_PRESERVE_WHITESPACE,
    TEXT_PRESERVE_IMAGES, TEXT_INHIBIT_SPACES, TEXT_DEHYPHENATE,
    TEXT_PRESERVE_SPANS,
)


class TestPermission:
    def test_is_int_flag(self):
        """Permission is IntFlag, allowing bitwise operations."""
        combined = Permission.PRINT | Permission.COPY
        assert combined & Permission.PRINT
        assert combined & Permission.COPY
        assert not (combined & Permission.MODIFY)

    def test_all_contains_common_permissions(self):
        """ALL should include PRINT, COPY, MODIFY."""
        assert Permission.ALL & Permission.PRINT
        assert Permission.ALL & Permission.COPY
        assert Permission.ALL & Permission.MODIFY

    def test_none_is_zero(self):
        assert int(Permission.NONE) == 0

    def test_bitwise_or_returns_int_flag(self):
        combo = Permission.PRINT | Permission.MODIFY
        assert isinstance(combo, Permission)


class TestAnnotationType:
    def test_enum_members(self):
        assert AnnotationType.TEXT.value >= 0
        assert AnnotationType.HIGHLIGHT.value >= 0
        assert AnnotationType.UNDERLINE.value >= 0
        assert AnnotationType.STRIKEOUT.value >= 0
        assert AnnotationType.SQUIGGLY.value >= 0
        assert AnnotationType.FREE_TEXT.value >= 0
        assert AnnotationType.INK.value >= 0
        assert AnnotationType.POLYGON.value >= 0
        assert AnnotationType.POLYLINE.value >= 0
        assert AnnotationType.SQUARE.value >= 0
        assert AnnotationType.CIRCLE.value >= 0
        assert AnnotationType.LINE.value >= 0
        assert AnnotationType.STAMP.value >= 0
        assert AnnotationType.CARET.value >= 0
        assert AnnotationType.FILE_ATTACHMENT.value >= 0
        assert AnnotationType.REDACT.value >= 0
        assert AnnotationType.LINK.value >= 0

    def test_unique_values(self):
        values = [m.value for m in AnnotationType]
        assert len(values) == len(set(values))

    def test_integer_comparable(self):
        from openpdf.constants import _ANNOT_SUBTYPE_TO_INT, _ANNOT_INT_TO_NAME
        # Round-trip: /Name -> int -> Name (without leading slash)
        for subtype_name, int_val in _ANNOT_SUBTYPE_TO_INT.items():
            expected = subtype_name.lstrip("/")
            assert _ANNOT_INT_TO_NAME[int_val] == expected


class TestWidgetType:
    def test_enum_members(self):
        assert WidgetType.TEXT.value >= 0
        assert WidgetType.CHECKBOX.value >= 0
        assert WidgetType.RADIOBUTTON.value >= 0
        assert WidgetType.LISTBOX.value >= 0
        assert WidgetType.COMBOBOX.value >= 0
        assert WidgetType.SIGNATURE.value >= 0

    def test_ft_mapping(self):
        from openpdf.constants import _WIDGET_FT_TO_TYPE
        assert _WIDGET_FT_TO_TYPE["/Tx"] == WidgetType.TEXT
        assert _WIDGET_FT_TO_TYPE["/Btn"] in (
            WidgetType.CHECKBOX, WidgetType.RADIOBUTTON, WidgetType.BUTTON
        )
        assert _WIDGET_FT_TO_TYPE["/Ch"] in (
            WidgetType.LISTBOX, WidgetType.COMBOBOX
        )


class TestLinkType:
    def test_enum_members(self):
        assert LinkType.NONE.value >= 0
        assert LinkType.GOTO.value >= 0
        assert LinkType.URI.value >= 0
        assert LinkType.LAUNCH.value >= 0
        assert LinkType.NAMED.value >= 0
        assert LinkType.GOTOR.value >= 0


class TestColorSpace:
    def test_enum_members(self):
        assert ColorSpace.CS_GRAY.value >= 0
        assert ColorSpace.CS_RGB.value >= 0
        assert ColorSpace.CS_CMYK.value >= 0


class TestTextFlags:
    def test_flags_are_integers(self):
        assert isinstance(TEXT_PRESERVE_LIGATURES, int)
        assert isinstance(TEXT_PRESERVE_WHITESPACE, int)
        assert isinstance(TEXT_PRESERVE_IMAGES, int)
        assert isinstance(TEXT_INHIBIT_SPACES, int)
        assert isinstance(TEXT_DEHYPHENATE, int)
        assert isinstance(TEXT_PRESERVE_SPANS, int)

    def test_flags_are_powers_of_two(self):
        """Each flag should be a distinct power of 2 (or 0)."""
        flags = [
            TEXT_PRESERVE_LIGATURES, TEXT_PRESERVE_WHITESPACE,
            TEXT_PRESERVE_IMAGES, TEXT_INHIBIT_SPACES,
            TEXT_DEHYPHENATE, TEXT_PRESERVE_SPANS,
        ]
        non_zero = [f for f in flags if f != 0]
        assert len(non_zero) == len(set(non_zero)), "Flags must have distinct values"
        for f in non_zero:
            assert f & (f - 1) == 0, f"Flag {f} is not a power of 2"
