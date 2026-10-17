"""Python translation of the non-form rvest helpers in rvest 1.0.5."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urljoin

import requests
from xml2 import (
    XmlDocument, XmlMissing, XmlNode, XmlNodeset, read_html, url_absolute,
    xml_attr, xml_children, xml_contents, xml_find_all, xml_name, xml_text,
)


def minimal_html(html: str, title: str = ""):
    return read_html(f"<!doctype html>\n<meta charset=utf-8>\n<title>{title}</title>\n{html}")


def _nodes(x):
    if isinstance(x, XmlNodeset):
        return list(x)
    if isinstance(x, (XmlNode, XmlDocument, XmlMissing)):
        return [x]
    return list(x)


def _xpath_for_css(css: str) -> str:
    # Covers the selectors used by rvest: tags, #id, .class, descendants,
    # child combinators, and simple attribute predicates.
    bits = re.split(r"\s*(>)\s*|\s+", css.strip())
    bits = [b for b in bits if b]
    out, direct = [], False
    for bit in bits:
        if bit == ">":
            direct = True
            continue
        tag = re.match(r"^[A-Za-z_][\w-]*|\*", bit)
        name = tag.group(0) if tag else "*"
        pred = []
        for kind, value in re.findall(r"([#.])([\w-]+)", bit):
            pred.append(f"@id='{value}'" if kind == "#" else
                        f"contains(concat(' ', normalize-space(@class), ' '), ' {value} ')")
        attrs = re.findall(r"\[([\w-]+)(?:=['\"]?([^'\"\]]+)['\"]?)?\]", bit)
        for key, value in attrs:
            pred.append(f"@{key}" if not value else f"@{key}='{value}'")
        out.append(("/" if direct else "//") + name + ("[" + " and ".join(pred) + "]" if pred else ""))
        direct = False
    return "".join(out) or "//*"


def html_elements(x, css=None, xpath=None):
    if css is not None and xpath is not None:
        raise ValueError("Supply exactly one of css or xpath")
    if css is None and xpath is None:
        raise ValueError("Supply css or xpath")
    return xml_find_all(x, xpath or _xpath_for_css(css))


def html_element(x, css=None, xpath=None):
    found = html_elements(x, css, xpath)
    return found[0] if found else XmlMissing()


def html_name(x):
    return xml_name(x)


def html_attr(x, name, default=None):
    value = xml_attr(x, name, default=default)
    return value


def html_text(x, trim=False):
    return xml_text(x, trim=trim)


_BLOCK = {"address", "article", "aside", "blockquote", "details", "dialog", "dd",
          "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
          "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "li",
          "main", "nav", "ol", "p", "pre", "section", "table", "ul", "caption"}


def _collapse(s, preserve_nbsp=False):
    s = re.sub(r"^[ \t\n]+|[ \t\n]+$", "", s)
    return re.sub(r"[\t\n \u00a0]+" if not preserve_nbsp else r"[\t\n ]+", " ", s)


def _text2(node, preserve_nbsp=False):
    if isinstance(node, XmlMissing):
        return None
    if not isinstance(node, XmlNode):
        return ""
    name = xml_name(node)
    children = list(xml_contents(node))
    if not children:
        return ""
    if all(isinstance(c, XmlNode) and xml_name(c) not in (_BLOCK | {"tr", "td", "th"})
           for c in children):
        pieces, line = [], []
        for c in children:
            if xml_name(c) == "br":
                pieces.append(_collapse("".join(line), preserve_nbsp)); pieces.append("\n"); line = []
            else:
                line.append(xml_text(c))
        pieces.append(_collapse("".join(line), preserve_nbsp))
        return "".join(pieces) if name != "pre" else "".join(pieces)
    out = []
    for i, child in enumerate(children):
        cname = xml_name(child) if isinstance(child, XmlNode) else ""
        margin = 2 if cname == "p" else (1 if cname in _BLOCK else 0)
        if out and margin:
            out.append("\n" * margin)
        out.append(_text2(child, preserve_nbsp) if cname else _collapse(xml_text(child), preserve_nbsp))
        if cname == "br":
            out.append("\n")
        elif cname == "td" and i != len(children) - 1:
            out.append("\t")
        elif cname == "tr" and i != len(children) - 1:
            out.append("\n")
        if margin and i != len(children) - 1:
            out.append("\n" * margin)
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip("\n")


def html_text2(x, preserve_nbsp=False):
    if isinstance(x, XmlDocument):
        x = html_element(x, "body")
    if isinstance(x, XmlNodeset):
        return [_text2(n, preserve_nbsp) for n in x]
    return _text2(x, preserve_nbsp)


def _convert(value, dec, na_strings):
    if value in na_strings:
        return None
    value = value.replace(dec, ".", 1) if dec != "." else value
    try:
        return int(value) if re.fullmatch(r"[+-]?\d+", value) else float(value)
    except ValueError:
        return value


def html_table(x, header=None, trim=True, fill=None, dec=".", na_strings=("NA",), convert=True):
    if isinstance(x, XmlDocument):
        tables = xml_find_all(x, ".//table")
        return [html_table(t, header, trim, fill, dec, na_strings, convert) for t in tables]
    if isinstance(x, XmlNodeset):
        return [html_table(t, header, trim, fill, dec, na_strings, convert) for t in x]
    rows = xml_find_all(x, ".//tr")
    grid, spans = [], {}
    for ri, row in enumerate(rows):
        values = []
        cells = xml_find_all(row, "./td|./th")
        ci = 0
        while ci in spans:
            values.append(spans.pop(ci)[0]); ci += 1
        for cell in cells:
            while ci in spans:
                values.append(spans.pop(ci)[0]); ci += 1
            text = xml_text(cell, trim=trim)
            cs = int(xml_attr(cell, "colspan", default="1") or 1)
            rs = int(xml_attr(cell, "rowspan", default="1") or 1)
            values.extend([text] * cs)
            if rs > 1:
                for c in range(ci, ci + cs):
                    spans[c] = (text, rs - 1)
            ci += cs
        grid.append(values)
        for c in list(spans):
            val, left = spans[c]
            if left <= 1: spans.pop(c)
            else: spans[c] = (val, left - 1)
    width = max((len(r) for r in grid), default=0)
    grid = [r + [None] * (width - len(r)) for r in grid]
    use_header = bool(grid and all(xml_name(c) == "th" for c in xml_find_all(rows[0], "./td|./th"))) if header is None else header
    names = grid.pop(0) if use_header else [f"X{i}" for i in range(1, width + 1)]
    data = [[_convert(v, dec, set(na_strings)) if convert and v is not None else v for v in r] for r in grid]
    try:
        import polars as pl
        return pl.DataFrame({str(n): [r[i] for r in data] for i, n in enumerate(names)})
    except ImportError:
        return {"columns": [str(n) for n in names], "data": data}


@dataclass
class Session:
    url: str
    response: requests.Response | None = None
    back: list[str] = field(default_factory=list)
    forward: list[str] = field(default_factory=list)
    client: requests.Session = field(default_factory=requests.Session)
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self._get(self.url)

    def _get(self, url, **kwargs):
        self.response = self.client.get(url, **kwargs)
        self.response.raise_for_status()
        self.url = self.response.url
        self.cache = {}
        return self

    def __repr__(self):
        return f"<session> {self.url}\n  Status: {self.response.status_code}\n"


def session(url, **kwargs):
    s = Session.__new__(Session)
    s.url, s.response, s.back, s.forward, s.client, s.cache = url, None, [], [], requests.Session(), {}
    s._get(url, **kwargs)
    return s


def is_session(x): return isinstance(x, Session)
def session_jump_to(x, url, **kwargs):
    old = x.url; x._get(urljoin(x.url, url), **kwargs); x.back.insert(0, old); x.forward.clear(); return x
def session_back(x):
    if not x.back: raise ValueError("Can't go back any further.")
    old, x.back = x.back[0], x.back[1:]; cur = x.url; x._get(old); x.forward.insert(0, cur); return x
def session_forward(x):
    if not x.forward: raise ValueError("Can't go forward any further.")
    nxt, x.forward = x.forward[0], x.forward[1:]; cur = x.url; x._get(nxt); x.back.insert(0, cur); return x
def session_history(x): return [*reversed(x.back), x.url, *x.forward]
def session_follow_link(x, i=None, css=None, xpath=None, **kwargs):
    doc = read_html(x.response.content)
    links = html_elements(doc, css=css, xpath=xpath) if (css or xpath) else html_elements(doc, css="a")
    link = links[i - 1] if isinstance(i, int) else next(n for n in links if i in html_text(n))
    return session_jump_to(x, xml_attr(link, "href"), **kwargs)
def session_submit(x, form, submit=None, **kwargs):
    raise NotImplementedError("html_form/session_submit requires the rvest form translation")
def google_form(x):
    return read_html(requests.get(f"https://docs.google.com/forms/d/{x}/viewform").content)
