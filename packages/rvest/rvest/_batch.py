"""Selected rvest 1.0.5 translations.

The node objects are the finished xml2 ctypes/libxml2 objects.  Sessions use
requests.Session for cookies and retain a small browser-like URL history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests
from cssselect import GenericTranslator

from xml2 import (
    XmlDocument, XmlMissing, XmlNode, XmlNodeset, as_character, read_html,
    xml_attr, xml_find_all, xml_find_first, xml_name, xml_text,
)


def _selector(css=None, xpath=None):
    if (css is None) == (xpath is None):
        raise ValueError("Exactly one of css or xpath must be supplied")
    if xpath is not None:
        return xpath
    if not isinstance(css, str):
        raise TypeError("css must be a string")
    return GenericTranslator().css_to_xpath(css, prefix=".//")


def html_element(x, css=None, xpath=None):
    if isinstance(x, HtmlSession):
        x = x.document
    query = _selector(css, xpath)
    if isinstance(x, XmlNodeset):
        return XmlNodeset([html_element(item, xpath=query) for item in x])
    return xml_find_first(x, query)


def html_elements(x, css=None, xpath=None):
    if isinstance(x, HtmlSession):
        x = x.document
    return xml_find_all(x, _selector(css, xpath))


def html_node(x, css=None, xpath=None):
    return html_element(x, css=css, xpath=xpath)


def html_nodes(x, css=None, xpath=None):
    return html_elements(x, css=css, xpath=xpath)


def xml_node(x, css=None, xpath=None):
    return html_element(x, css=css, xpath=xpath)


def xml_nodes(x, css=None, xpath=None):
    return html_elements(x, css=css, xpath=xpath)


def html_name(x):
    return xml_name(x)


def xml_tag(x):
    return html_name(x)


@dataclass
class Field:
    type: str
    name: str | None
    value: object
    attr: dict[str, str]
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class Form:
    name: str
    method: str
    action: str
    enctype: str
    fields: dict[str, Field]


def _attrs(node):
    from xml2 import xml_attrs
    return dict(xml_attrs(node).items())


def _field(node):
    attrs = _attrs(node)
    tag = xml_name(node)
    if tag == "select":
        options = {}
        selected = []
        for option in html_elements(node, css="option"):
            oa = _attrs(option)
            name = xml_text(option)
            value = oa.get("value", name)
            options[name] = value
            if "selected" in oa:
                selected.append(value)
        return Field("select", attrs.get("name"), selected, attrs, options)
    if tag == "textarea":
        return Field("textarea", attrs.get("name"), xml_text(node), attrs)
    return Field(
        attrs.get("type", "text") if tag == "input" else "button",
        attrs.get("name"), attrs.get("value"), attrs,
    )


def _parse_form(x, base_url=None):
    if isinstance(x, (XmlDocument, XmlNode)):
        if isinstance(x, XmlDocument):
            forms = html_elements(x, css="form")
            return [_parse_form(node, base_url=base_url) for node in forms]
        if xml_name(x) != "form":
            raise ValueError("x must be a <form> element")
        attrs = _attrs(x)
        action = attrs.get("action", "")
        if base_url is None:
            from xml2 import xml_url
            base_url = xml_url(x) or ""
        fields = {}
        for node in html_elements(x, css="input, select, textarea, button"):
            item = _field(node)
            fields[item.name or ""] = item
        enctype = attrs.get("enctype", "application/x-www-form-urlencoded")
        enctype = "multipart" if enctype == "multipart/form-data" else "form"
        return Form(
            attrs.get("id", attrs.get("name", "<unnamed>")),
            attrs.get("method", "GET").upper(),
            urljoin(base_url, action),
            enctype, fields,
        )
    if isinstance(x, XmlNodeset):
        return [_parse_form(item, base_url=base_url) for item in x]
    raise TypeError("x must be an HTML node")


def html_form_set(form: Form, **values):
    if not isinstance(form, Form):
        raise TypeError("form must be a Form")
    for name, value in values.items():
        if name not in form.fields:
            raise ValueError(f"Unknown form field: {name}")
        form.fields[name].value = value
    return form


def set_values(form: Form, **values):
    return html_form_set(form, **values)


def _submission(form, submit=None):
    values = []
    buttons = []
    for name, item in form.fields.items():
        if item.type.lower() in ("submit", "image", "button"):
            buttons.append(item)
            continue
        if item.name is not None:
            vals = item.value if isinstance(item.value, (list, tuple)) else [item.value]
            values.extend((item.name, "" if v is None else str(v)) for v in vals)
    chosen = None
    if submit is None and buttons:
        chosen = buttons[0]
    elif isinstance(submit, int):
        chosen = buttons[submit - 1]
    elif isinstance(submit, str):
        chosen = next(b for b in buttons if b.name == submit)
    if chosen and chosen.name is not None:
        values.append((chosen.name, "" if chosen.value is None else str(chosen.value)))
    return values


@dataclass
class HtmlSession:
    client: requests.Session
    response: requests.Response
    url: str
    back_urls: list[str] = field(default_factory=list)
    forward_urls: list[str] = field(default_factory=list)
    _document: object = None

    @property
    def document(self):
        if self._document is None:
            self._document = read_html(self.response.content, base_url=self.url)
        return self._document


def _get(session, url):
    response = session.client.get(url)
    response.raise_for_status()
    session.response = response
    session.url = response.url
    session._document = None
    return session


def html_session(url, **kwargs):
    client = requests.Session()
    response = client.get(url, **kwargs)
    response.raise_for_status()
    session = HtmlSession(client, response, response.url)
    return session


def _check(session):
    if not isinstance(session, HtmlSession):
        raise TypeError("x must be an HtmlSession")


def jump_to(x, url, **kwargs):
    _check(x)
    target = urljoin(x.url, url)
    x.back_urls.insert(0, x.url)
    x.forward_urls.clear()
    return _get(x, target)


def back(x):
    _check(x)
    if not x.back_urls:
        raise ValueError("Can't go back any further.")
    x.forward_urls.insert(0, x.url)
    return _get(x, x.back_urls.pop(0))


def forward(x):
    _check(x)
    if not x.forward_urls:
        raise ValueError("Can't go forward any further.")
    x.back_urls.insert(0, x.url)
    return _get(x, x.forward_urls.pop(0))


def follow_link(x, i=None, css=None, xpath=None, **kwargs):
    _check(x)
    if i is not None:
        links = html_elements(x.document, css="a")
        if isinstance(i, int):
            link = links[i - 1]
        else:
            link = next(link for link in links if i in (xml_text(link) or ""))
    else:
        links = html_elements(x.document, css=css, xpath=xpath)
        if not links:
            raise ValueError("No links matched css/xpath")
        link = links[0]
    href = xml_attr(link, "href")
    if href is None:
        raise ValueError("Link has no href")
    return jump_to(x, href, **kwargs)


def submit_form(x, form, submit=None, **kwargs):
    _check(x)
    return _submit(x, form, submit, **kwargs)


def _submit(x, form, submit=None, **kwargs):
    data = _submission(form, submit)
    method = form.method if form.method in ("GET", "POST") else "GET"
    response = x.client.request(method, form.action, params=data if method == "GET" else None,
                                 data=data if method == "POST" else None, **kwargs)
    response.raise_for_status()
    x.back_urls.insert(0, x.url)
    x.forward_urls.clear()
    x.response, x.url, x._document = response, response.url, None
    return x
