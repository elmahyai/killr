"""Selected rvest translations built on the repository's xml2 ctypes binding."""
from __future__ import annotations

import codecs
import re
import warnings
from dataclasses import dataclass, field
from typing import Any

from xml2 import (
    NA, XmlDocument, XmlNode, XmlNodeset, as_character, read_html, xml_attr,
    xml_attrs, xml_children, xml_find_all, xml_name, xml_text, url_absolute,
)


def _vec(x):
    return list(x) if isinstance(x, (list, tuple, XmlNodeset)) else [x]


def html_name(x):
    return xml_name(x)


def html_attr(x, name, default=NA):
    if not isinstance(name, str):
        raise ValueError("name must be a single string")
    return xml_attr(x, name, default=default)


def html_attrs(x):
    return xml_attrs(x)


def html_children(x):
    return xml_children(x)


def _css_nodes(root, selector):
    """Small CSS subset needed by rvest forms and local HTML proofs."""
    out = []
    for part in (p.strip() for p in selector.split(",")):
        if not part:
            continue
        # Convert common CSS selectors to XPath. Attribute predicates are enough
        # for form controls and preserve document order for each selector.
        bits = [b for b in re.split(r"\s+", part) if b]
        path = "."
        for bit in bits:
            m = re.match(r"^([A-Za-z][\w-]*)?", bit)
            tag = (m.group(0) if m and m.group(0) else "*")
            predicates = []
            for kind, value in re.findall(r"([.#])([\w-]+)", bit):
                predicates.append(
                    f"@{'class' if kind == '.' else 'id'}='{value}'"
                    if kind == "#" else
                    f"contains(concat(' ', normalize-space(@class), ' '), ' {value} ')"
                )
            for attr, op, value in re.findall(
                r"\[([\w:-]+)(?:\s*([~|^$*]?=)\s*['\"]?([^'\"\]]+)['\"]?)?\]", bit
            ):
                predicates.append(f"@{attr}" if not op else
                                  (f"@{attr}='{value}'" if op == "=" else
                                   f"contains(@{attr}, '{value}')"))
            path += "//" + tag + (("[" + " and ".join(predicates) + "]") if predicates else "")
        try:
            found = xml_find_all(root, path)
        except Exception:
            found = XmlNodeset()
        for node in found:
            if node not in out:
                out.append(node)
    return XmlNodeset(out)


def _elements(root, selector):
    return _css_nodes(root, selector)


@dataclass
class RvestField:
    type: str
    name: Any
    value: Any
    attr: Any
    extra: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return getattr(self, key) if hasattr(self, key) else self.extra.get(key)


@dataclass
class RvestForm:
    name: str
    method: str
    action: str
    enctype: str
    fields: dict[str, RvestField]


def _convert_enctype(value):
    if value in (None, "application/x-www-form-urlencoded"):
        return "form"
    if value == "multipart/form-data":
        return "multipart"
    warnings.warn(f"Unknown enctype ({value}). Defaulting to form encoded.")
    return "form"


def _attrs(node):
    a = xml_attrs(node)
    return dict(a.items()) if hasattr(a, "items") else (a or {})


def _field(node):
    a = _attrs(node)
    tag = xml_name(node)
    if tag == "textarea":
        return RvestField("textarea", a.get("name"), xml_text(node), a)
    if tag == "select":
        options = _elements(node, "option")
        values = [xml_attr(o, "value", default=xml_text(o)) for o in options]
        names = [xml_text(o) for o in options]
        selected = [v for o, v in zip(options, values) if xml_attr(o, "selected", default=None) is not None]
        return RvestField("select", a.get("name"), selected, a, {"options": dict(zip(names, values))})
    if tag == "button":
        return RvestField("button", a.get("name"), a.get("value"), a)
    return RvestField(a.get("type", "text"), a.get("name"), a.get("value"), a)


def html_form(x, base_url=None):
    if isinstance(x, XmlDocument):
        return [html_form(n, base_url) for n in xml_find_all(x, ".//form")]
    if isinstance(x, XmlNodeset) or isinstance(x, list):
        return [html_form(n, base_url) for n in x]
    if xml_name(x) != "form":
        raise ValueError("x must be a <form> element")
    a = _attrs(x)
    fields = {}
    for node in _elements(x, "input, select, textarea, button"):
        f = _field(node)
        fields[f.name or ""] = f
    base = base_url
    if base is None:
        try:
            from xml2 import xml_url
            base = xml_url(x)
        except Exception:
            base = ""
    action = url_absolute(a.get("action", ""), base or "")
    return RvestForm(a.get("id", a.get("name", "<unnamed>")),
                     a.get("method", "GET").upper(), action,
                     _convert_enctype(a.get("enctype")), fields)


def html_form_set(form, **values):
    if not isinstance(form, RvestForm):
        raise ValueError("form must be an rvest form")
    for name, value in values.items():
        if name not in form.fields:
            raise ValueError(f"Can't set value of field that doesn't exist: {name}")
        if form.fields[name].type == "submit":
            raise ValueError(f"Can't change value of input with type submit: {name}")
        form.fields[name].value = value
    return form


def _is_button(f):
    return f.type.lower() in ("submit", "image", "button")


def _submission_values(form, submit=None):
    buttons = [f for f in form.fields.values() if _is_button(f)]
    chosen = None
    if submit is None:
        chosen = buttons[0] if buttons else None
    elif isinstance(submit, (int, float)):
        chosen = buttons[int(submit) - 1]
    else:
        chosen = next((f for f in buttons if f.name == submit), None)
        if chosen is None:
            raise ValueError(f"No input found with name {submit}")
    values = []
    for f in form.fields.values():
        if not _is_button(f) and f.name is not None:
            vals = f.value if isinstance(f.value, (list, tuple)) else [f.value]
            values.extend((f.name, "" if v is None else str(v)) for v in vals)
    if chosen is not None and chosen.name is not None:
        values.append((chosen.name, "" if chosen.value is None else str(chosen.value)))
    return values


def html_form_submit(form, submit=None):
    import requests
    values = _submission_values(form, submit)
    method = form.method if form.method in ("GET", "POST") else "GET"
    kwargs = {"params": values} if method == "GET" else (
        {"files": values} if form.enctype == "multipart" else {"data": values})
    return requests.request(method, form.action, **kwargs)


def _encoding_rows(text):
    raw = text.encode("utf-8", errors="replace")
    candidates = ["UTF-8", "UTF-16", "ISO-8859-1", "ISO-8859-2", "windows-1252"]
    rows = []
    for enc in candidates:
        try:
            raw.decode(enc)
            confidence = 1.0 if enc == "UTF-8" and "�" not in text else (0.5 if enc == "UTF-8" else 0.1)
            rows.append({"encoding": enc, "language": "", "confidence": confidence})
        except (LookupError, UnicodeError):
            pass
    return rows


def html_encoding_guess(x):
    text = "".join(str(v) for v in _vec(x))
    return _encoding_rows(text)


def guess_encoding(x):
    warnings.warn("guess_encoding() is deprecated; use html_encoding_guess()", DeprecationWarning)
    return html_encoding_guess(x)


def repair_encoding(x, from_=None, **kwargs):
    source = from_ if from_ is not None else "UTF-8"
    return [bytes(str(v), "latin1").decode(source, errors="replace") for v in _vec(x)]


def read_html_live(*args, **kwargs):
    raise NotImplementedError("read_html_live requires the chromote browser runtime")
