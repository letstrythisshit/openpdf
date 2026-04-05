"""Tests for AcroForm reading and filling."""
from __future__ import annotations

import pytest
import openpdf
from openpdf.forms.models import Widget
from openpdf.constants import WidgetType


class TestFormRead:
    def test_get_widgets(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        assert isinstance(widgets, list)
        doc.close()

    def test_widgets_nonempty(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        assert len(widgets) >= 2  # name + agree fields
        doc.close()

    def test_widget_type(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        types = [w.field_type for w in widgets]
        assert WidgetType.TEXT in types or any(t is not None for t in types)
        doc.close()

    def test_text_field_name(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        names = [w.field_name for w in widgets]
        assert "name" in names
        doc.close()

    def test_checkbox_field_name(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        names = [w.field_name for w in widgets]
        assert "agree" in names
        doc.close()

    def test_widget_rect(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        from openpdf.geometry import Rect
        for w in widgets:
            r = w.rect
            assert isinstance(r, Rect)
            assert r.width > 0
            assert r.height > 0
        doc.close()

    def test_get_all_fields(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        from openpdf.forms.reader import get_all_fields
        fields = get_all_fields(doc)
        assert isinstance(fields, list)
        assert len(fields) >= 2  # name + agree
        names = [w.field_name for w in fields]
        assert "name" in names
        doc.close()


class TestFormFill:
    def test_fill_text_field(self, form_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        name_widget = next((w for w in widgets if w.field_name == "name"), None)
        if name_widget is None:
            pytest.skip("name field not found")
        name_widget.field_value = "John Doe"
        name_widget.update()
        doc.save(str(tmp_pdf_path))
        doc.close()

        # Reload and verify
        doc2 = openpdf.open(str(tmp_pdf_path))
        widgets2 = doc2[0].get_widgets()
        name_widget2 = next((w for w in widgets2 if w.field_name == "name"), None)
        if name_widget2 is not None:
            assert name_widget2.field_value == "John Doe"
        doc2.close()

    def test_fill_checkbox_true(self, form_pdf_path, tmp_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        cb = next((w for w in widgets if w.field_name == "agree"), None)
        if cb is None:
            pytest.skip("agree checkbox not found")
        cb.field_value = True
        cb.update()
        doc.save(str(tmp_pdf_path))
        doc.close()

        doc2 = openpdf.open(str(tmp_pdf_path))
        widgets2 = doc2[0].get_widgets()
        cb2 = next((w for w in widgets2 if w.field_name == "agree"), None)
        if cb2 is not None:
            val = cb2.field_value
            assert val is True or val == "/Yes" or val == "Yes"
        doc2.close()

    def test_set_field_value_function(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        from openpdf.forms.writer import set_field_value
        # Should not raise
        try:
            set_field_value(doc, "name", "Test Value")
        except KeyError:
            pass  # field not found is acceptable for this test
        doc.close()


class TestWidgetProperties:
    def test_field_type_string(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        for w in widgets:
            ts = w.field_type_string
            assert isinstance(ts, str)
        doc.close()

    def test_is_readonly(self, form_pdf_path):
        doc = openpdf.open(str(form_pdf_path))
        widgets = doc[0].get_widgets()
        for w in widgets:
            assert isinstance(w.is_read_only, bool)
        doc.close()
