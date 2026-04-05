"""Widget / form field dataclasses."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from openpdf.geometry import Rect
from openpdf.constants import WidgetType
from openpdf.backends.pike import PikeBackend

if TYPE_CHECKING:
    from openpdf.page import Page


class Widget:
    """PDF form field / widget annotation. Mirrors fitz.Widget."""

    def __init__(self, field_dict: dict, page: "Page") -> None:
        self._field = field_dict
        self._page = page

    @classmethod
    def from_field_dict(cls, field_dict: dict, page: "Page") -> "Widget":
        return cls(field_dict, page)

    # ---- Properties --------------------------------------------------------

    @property
    def field_name(self) -> str:
        return self._field.get("name", "")

    @property
    def field_label(self) -> str:
        return self._field.get("name", "")

    @property
    def field_value(self) -> Union[str, bool, list]:
        return self._field.get("value", "")

    @field_value.setter
    def field_value(self, value: Any) -> None:
        self._field["value"] = value

    @property
    def field_type(self) -> WidgetType:
        return self._field.get("type", WidgetType.UNKNOWN)

    @property
    def field_type_string(self) -> str:
        t = self.field_type
        _names = {
            WidgetType.TEXT: "Text",
            WidgetType.CHECKBOX: "CheckBox",
            WidgetType.RADIOBUTTON: "RadioButton",
            WidgetType.COMBOBOX: "ComboBox",
            WidgetType.LISTBOX: "ListBox",
            WidgetType.BUTTON: "Button",
            WidgetType.SIGNATURE: "Signature",
        }
        return _names.get(t, "Unknown")

    @property
    def field_flags(self) -> int:
        return self._field.get("flags", 0)

    @property
    def field_display(self) -> int:
        return 0

    @property
    def rect(self) -> Rect:
        return self._field.get("rect", Rect())

    @property
    def text_maxlen(self) -> int:
        obj = self._field.get("obj", None)
        if obj is not None:
            try:
                return int(obj.get("/MaxLen", 0))
            except Exception:
                pass
        return 0

    @property
    def text_format(self) -> int:
        return 0

    @property
    def choice_values(self) -> list[str]:
        return self._field.get("options") or []

    @property
    def is_signed(self) -> bool:
        if self.field_type != WidgetType.SIGNATURE:
            return False
        obj = self._field.get("obj", None)
        if obj is not None:
            v = obj.get("/V", None)
            return v is not None and str(v) not in ("/Off", "")
        return False

    @property
    def button_caption(self) -> str:
        obj = self._field.get("obj", None)
        if obj is not None:
            try:
                mk = obj.get("/MK", None)
                if mk:
                    return str(mk.get("/CA", ""))
            except Exception:
                pass
        return ""

    @property
    def script(self) -> str:
        return self._get_action_script("/A")

    @property
    def script_stroke(self) -> str:
        return self._get_action_script("/AA/K")

    @property
    def script_format(self) -> str:
        return self._get_action_script("/AA/F")

    @property
    def script_change(self) -> str:
        return self._get_action_script("/AA/V")

    @property
    def script_calc(self) -> str:
        return self._get_action_script("/AA/C")

    def _get_action_script(self, path: str) -> str:
        obj = self._field.get("obj", None)
        if obj is None:
            return ""
        try:
            parts = path.strip("/").split("/")
            curr = obj
            for part in parts:
                curr = curr.get(f"/{part}", None)
                if curr is None:
                    return ""
            return str(curr.get("/JS", ""))
        except Exception:
            return ""

    @property
    def is_read_only(self) -> bool:
        """True if the field has the read-only flag set (bit 0 of Ff)."""
        return bool(self.field_flags & 1)

    @property
    def xref(self) -> int:
        obj = self._field.get("obj", None)
        if obj is not None and hasattr(obj, "objgen"):
            return obj.objgen[0]
        return 0

    # ---- Setters -----------------------------------------------------------

    def set_field_value(self, value: Any) -> None:
        self._field["value"] = value

    def set_text_maxlen(self, maxlen: int) -> None:
        obj = self._field.get("obj", None)
        if obj is not None:
            obj["/MaxLen"] = maxlen

    def set_rect(self, rect: Rect) -> None:
        self._field["rect"] = rect

    def set_field_flags(self, flags: int) -> None:
        self._field["flags"] = flags

    def update(self) -> None:
        """Write field value back to PDF."""
        PikeBackend.set_form_field_value(
            self._page.parent._pike,
            self.field_name,
            self.field_value,
        )
        self._page.parent._mark_dirty()

    def __repr__(self) -> str:
        return f"Widget({self.field_name!r}, {self.field_type_string}, value={self.field_value!r})"
