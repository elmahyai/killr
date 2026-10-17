"""xml2's R functions, calling the same libxml2 the installed package uses."""

from __future__ import annotations

import bz2
import gzip
import lzma
import os
import re
import warnings
import zipfile
from pathlib import Path

from xml2 import _libxml as C

NA = None  # R's NA. A missing node is XmlMissing, not this value.

_SPACE = re.compile(r"^[\t\n\v\f\r \u00a0]+")
_SPACE_END = re.compile(r"[\t\n\v\f\r \u00a0]+$")
_INT = re.compile(r"[+-]?\d+\Z")

options = {"width": 80}


class XmlError(ValueError):
    pass


def _abort(message: str) -> None:
    raise XmlError(message)


def _check_string(value, name: str = "x") -> str:
    if not isinstance(value, str):
        _abort(f"`{name}` must be a single string.")
    return value


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _bytes_len(text: str) -> bytes:
    return text.encode("utf-8")


def pmatch(arg: str, choices: list[str]) -> int | None:
    exact = [i for i, choice in enumerate(choices) if choice == arg]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    partial = [i for i, choice in enumerate(choices) if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    return None


def match_arg(arg: str, choices: list[str]) -> str:
    index = pmatch(arg, choices)
    if index is None:
        _abort(f"'{arg}' does not match any of the choices.")
    return choices[index]


def parse_options(arg, table: dict[str, int]) -> int:
    if isinstance(arg, bool):
        _abort("options must be a name or an integer.")
    if isinstance(arg, int) and not isinstance(arg, bool):
        return int(arg)
    if isinstance(arg, float):
        return int(arg)
    if arg is None:
        return 0
    if isinstance(arg, str):
        arg = [arg]
    names = [item for item in arg if item]
    if not names:
        return 0
    indexes = []
    for name in names:
        index = pmatch(str(name), list(table))
        if index is None:
            _abort(f"options '{name}' is not a valid option.")
        indexes.append(index)
    total = 0
    for index in dict.fromkeys(indexes):
        total += list(table.values())[index]
    return total


def make_unique(names: list[str], sep: str = ".") -> list[str]:
    counts: dict[str, int] = {}
    original = set(names)
    used: set[str] = set()
    out = []
    for name in names:
        if name not in counts:
            counts[name] = 0
            out.append(name)
            used.add(name)
            continue
        while True:
            counts[name] += 1
            candidate = f"{name}{sep}{counts[name]}"
            if candidate not in original and candidate not in used:
                break
        out.append(candidate)
        used.add(candidate)
    return out


def _recycle(values, size: int):
    if size == 0:
        return []
    if not isinstance(values, (list, tuple)):
        values = [values]
    if len(values) == 0:
        return [None] * size
    if len(values) == 1:
        return list(values) * size
    if len(values) == size:
        return list(values)
    out = []
    for i in range(size):
        out.append(values[i % len(values)])
    return out


class Owner:
    """Owns one xmlDoc. Nodes keep this alive."""

    def __init__(self, ptr):
        self.ptr = ptr

    def close(self) -> None:
        ptr = self.ptr
        self.ptr = None
        if ptr:
            C.lib.xmlFreeDoc(ptr)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class XmlMissing:
    def __len__(self) -> int:
        return 0

    def __getitem__(self, index):
        if index == 0 or index == 1:
            return self
        _abort("subscript out of bounds")

    def __str__(self) -> str:
        return "{xml_missing}\n<NA>"

    def __repr__(self) -> str:
        return "{xml_missing}\n<NA>"


class XmlNamespace(dict):
    def __str__(self) -> str:
        if not self:
            return ""
        width = max(len(key) for key in self)
        lines = [f"{key.ljust(width)} <-> {value}" for key, value in self.items()]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return str(self)


class RList(list):
    def __init__(self, items=None, names=None, attrs=None):
        super().__init__(items or [])
        self.names = list(names) if names is not None else [""] * len(self)
        self.attrs = dict(attrs or {})


class UrlFrame:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def __eq__(self, other) -> bool:
        return isinstance(other, UrlFrame) and self.rows == other.rows

    def __str__(self) -> str:
        return _format_frame(self.rows)

    def __repr__(self) -> str:
        return str(self)


class ValidateResult:
    def __init__(self, ok: bool, errors: list[str]):
        self.ok = ok
        self.errors = errors

    def __bool__(self) -> bool:
        return self.ok

    def __eq__(self, other) -> bool:
        if isinstance(other, ValidateResult):
            return self.ok == other.ok and self.errors == other.errors
        if isinstance(other, bool):
            return self.ok == other
        return False

    def __str__(self) -> str:
        return "TRUE" if self.ok else "FALSE"

    def __repr__(self) -> str:
        return str(self)


class Serialized:
    def __init__(self, kind: str, xml: str, doc_type: str | None = None):
        self.kind = kind
        self.xml = xml
        self.doc_type = doc_type

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Serialized)
            and self.kind == other.kind
            and self.xml == other.xml
            and self.doc_type == other.doc_type
        )


class XmlNode:
    def __init__(self, ptr, owner: Owner):
        self.ptr = ptr
        self.owner = owner

    def __str__(self) -> str:
        return _print_node(self)

    def __repr__(self) -> str:
        return str(self)


class XmlDocument(XmlNode):
    def __str__(self) -> str:
        return _print_document(self)

    def __repr__(self) -> str:
        return str(self)


class BareDocument:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.ptr = None

    def __str__(self) -> str:
        return "{xml_document}"

    def __repr__(self) -> str:
        return str(self)


class XmlNodeset(list):
    def __str__(self) -> str:
        return _print_nodeset(self)

    def __repr__(self) -> str:
        return str(self)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return XmlNodeset(super().__getitem__(index))
        return super().__getitem__(index)


def _is_node(value) -> bool:
    return isinstance(value, XmlNode)


def _is_document(value) -> bool:
    return isinstance(value, (XmlDocument, BareDocument))


def _is_missing(value) -> bool:
    return isinstance(value, XmlMissing)


def _is_nodeset(value) -> bool:
    return isinstance(value, XmlNodeset)


def _owner_of(value) -> Owner:
    if isinstance(value, (XmlNode, BareDocument)):
        return value.owner
    _abort("x is not an xml node")
    raise AssertionError


def _doc_ptr(value) -> int:
    return _owner_of(value).ptr


def _wrap_node(ptr, owner: Owner) -> XmlNode:
    if not ptr:
        return XmlMissing()
    return XmlNode(ptr, owner)


def _as_document(owner: Owner):
    root = C.lib.xmlDocGetRootElement(owner.ptr)
    if root:
        return XmlDocument(root, owner)
    return BareDocument(owner)


def _doc_is_html(owner: Owner) -> bool:
    if owner is None or not owner.ptr:
        return False
    return bool(C.doc_view(owner.ptr).properties & C.XML_DOC_HTML)


def _doc_type(value) -> str:
    owner = getattr(value, "owner", None)
    if owner is None or not owner.ptr:
        return "xml"
    return "html" if _doc_is_html(owner) else "xml"


def _node_type_code(ptr) -> int:
    return C.node_view(ptr).type


def _node_name_raw(ptr) -> str:
    raw = C.node_view(ptr).name
    return raw.decode("utf-8") if raw else ""


def _ns_href(ns_ptr) -> str | None:
    if not ns_ptr:
        return None
    href = C.ns_view(ns_ptr).href
    return href.decode("utf-8") if href else None


def _ns_prefix(ns_ptr) -> str | None:
    if not ns_ptr:
        return None
    prefix = C.ns_view(ns_ptr).prefix
    if prefix is None:
        return None
    return prefix.decode("utf-8")


def _node_ns_ptr(ptr):
    return C.ptr_value(C.node_view(ptr).ns)


def xml_missing() -> XmlMissing:
    return XmlMissing()


def is_na(x):
    if _is_missing(x):
        return True
    if _is_nodeset(x):
        return [is_na(item) for item in x]
    if _is_node(x):
        return False
    return x is NA


def _nodes_of(x) -> list:
    if _is_missing(x):
        return [x]
    if _is_nodeset(x):
        return list(x)
    if _is_node(x):
        return [x]
    if isinstance(x, BareDocument):
        return []
    _abort("Unexpected node type")
    return []


def _one_or_many(nodes: list, values: list):
    if len(nodes) == 1 and not _is_nodeset(nodes[0]) and not isinstance(nodes, XmlNodeset):
        return values[0]
    return values


def xml_nodeset(nodes=None, deduplicate: bool = True) -> XmlNodeset:
    nodes = list(nodes or [])
    if deduplicate:
        seen = set()
        kept = []
        for node in nodes:
            if _is_missing(node):
                kept.append(node)
                continue
            key = node.ptr
            if key in seen:
                continue
            seen.add(key)
            kept.append(node)
        nodes = kept
    return XmlNodeset(nodes)


def _qualified_name(ptr, ns: XmlNamespace | None) -> str:
    name = _node_name_raw(ptr)
    if not ns:
        return name
    ns_ptr = _node_ns_ptr(ptr)
    if not ns_ptr:
        return name
    href = _ns_href(ns_ptr)
    prefix = _find_prefix(ns, href)
    return f"{prefix}:{name}"


def xml_name(x, ns=None):
    mapping = _as_ns(ns)
    nodes = _nodes_of(x)
    if _is_missing(x):
        return NA
    out = []
    for node in nodes:
        if _is_missing(node):
            out.append(NA)
        else:
            out.append(_qualified_name(node.ptr, mapping))
    if _is_nodeset(x):
        return out
    return out[0] if out else NA


def xml_set_name(x, value, ns=None):
    return xml_name_assign(x, value, ns)


def xml_name_assign(x, value, ns=None):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = _recycle(value, len(x))
        for node, item in zip(x, values):
            xml_name_assign(node, item, ns)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    C.lib.xmlNodeSetName(x.ptr, C.bytes_of(str(value)))
    return x


def xml_text(x, trim: bool = False):
    if _is_missing(x):
        return NA
    nodes = _nodes_of(x)
    out = []
    for node in nodes:
        if _is_missing(node):
            out.append(NA)
        else:
            out.append(C.text_of(C.lib.xmlNodeGetContent(node.ptr), free=True) or "")
    if trim is True:
        out = [_trim(item) if isinstance(item, str) else item for item in out]
    if _is_nodeset(x):
        return out
    return out[0]


def _trim(text: str) -> str:
    return _SPACE_END.sub("", _SPACE.sub("", text))


def xml_set_text(x, value):
    return xml_text_assign(x, value)


def xml_text_assign(x, value):
    if _is_missing(x):
        return NA
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = _recycle(value, len(x))
        for node, item in zip(reversed(x), reversed(values)):
            xml_text_assign(node, item)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    text = "" if value is None else _as_text(value)
    payload = _bytes_len(text)
    if xml_type(x) != "text":
        text_child = xml_find_first(x, ".//text()[1]", ns=XmlNamespace())
        if _is_missing(text_child):
            C.lib.xmlNodeAddContentLen(x.ptr, payload, len(payload))
        else:
            C.lib.xmlNodeSetContentLen(text_child.ptr, payload, len(payload))
    else:
        C.lib.xmlNodeSetContentLen(x.ptr, payload, len(payload))
    return x


def xml_double(x):
    text = xml_text(x)
    if _is_nodeset(x):
        return [_as_numeric(item) for item in text]
    return _as_numeric(text)


def xml_integer(x):
    text = xml_text(x)
    if _is_nodeset(x):
        return [_as_integer(item) for item in text]
    return _as_integer(text)


def _as_numeric(text):
    if text is NA:
        return NA
    stripped = text.strip()
    if stripped in ("", "NA"):
        return NA
    try:
        return float(stripped)
    except ValueError:
        return NA


def _as_integer(text):
    if text is NA:
        return NA
    stripped = text.strip()
    if _INT.fullmatch(stripped):
        return int(stripped)
    return NA


def xml_type(x):
    if _is_missing(x):
        return NA
    nodes = _nodes_of(x)
    out = []
    for node in nodes:
        if _is_missing(node):
            out.append(NA)
        else:
            out.append(C.ELEMENT_TYPES.get(_node_type_code(node.ptr), "element"))
    if _is_nodeset(x):
        return out
    return out[0]


def xml_path(x):
    if _is_missing(x):
        return NA
    nodes = _nodes_of(x)
    out = []
    for node in nodes:
        if _is_missing(node):
            out.append(NA)
        else:
            out.append(C.text_of(C.lib.xmlGetNodePath(node.ptr), free=True))
    if _is_nodeset(x):
        return out
    return out[0]


def xml_url(x):
    if _is_missing(x):
        return NA
    if _is_nodeset(x):
        return [xml_url(item) for item in x]
    if isinstance(x, BareDocument) or _is_node(x):
        url = C.doc_view(x.owner.ptr).URL
        if url is None:
            return NA
        return url.decode("utf-8")
    _abort("Unexpected node type")
    return NA


def _children(ptr, only_elements: bool) -> list[int]:
    out = []
    current = C.ptr_value(C.node_view(ptr).children)
    while current:
        view = C.node_view(current)
        if not (only_elements and view.type != C.XML_ELEMENT_NODE):
            out.append(current)
        current = C.ptr_value(view.next)
    return out


def _apply_nodeset(x, fun) -> XmlNodeset:
    if _is_missing(x):
        return xml_nodeset()
    if isinstance(x, BareDocument):
        return xml_nodeset()
    if _is_nodeset(x):
        if len(x) == 0:
            return xml_nodeset()
        gathered = []
        owner = x[0].owner if not _is_missing(x[0]) else None
        for node in x:
            if _is_missing(node):
                gathered.append(xml_missing())
                continue
            owner = node.owner
            for ptr in fun(node):
                gathered.append(_wrap_node(ptr, owner))
        return xml_nodeset(gathered)
    if _is_node(x):
        found = fun(x)
        return xml_nodeset([_wrap_node(ptr, x.owner) for ptr in found])
    _abort("Unexpected node type")
    return xml_nodeset()


def xml_children(x) -> XmlNodeset:
    return _apply_nodeset(x, lambda node: _children(node.ptr, True))


def xml_contents(x) -> XmlNodeset:
    return _apply_nodeset(x, lambda node: _children(node.ptr, False))


def xml_siblings(x) -> XmlNodeset:
    def siblings(node: XmlNode):
        parent = C.ptr_value(C.node_view(node.ptr).parent)
        if not parent:
            return []
        out = []
        for ptr in _children(parent, True):
            if ptr != node.ptr:
                out.append(ptr)
        return out

    return _apply_nodeset(x, siblings)


def xml_parents(x) -> XmlNodeset:
    def parents(node: XmlNode):
        out = []
        current = C.ptr_value(C.node_view(node.ptr).parent)
        while current:
            if C.node_view(current).type == C.XML_ELEMENT_NODE:
                out.append(current)
            current = C.ptr_value(C.node_view(current).parent)
        return out

    return _apply_nodeset(x, parents)


def xml_parent(x):
    if _is_missing(x):
        return xml_missing()
    if _is_nodeset(x):
        found = []
        for node in x:
            if _is_missing(node):
                found.append(xml_missing())
            else:
                found.append(xml_parent(node))
        return xml_nodeset(found)
    if not _is_node(x):
        _abort("Unexpected node type")
    parent = C.ptr_value(C.node_view(x.ptr).parent)
    if not parent:
        _abort("Parent does not exist")
    return _wrap_node(parent, x.owner)


def xml_length(x, only_elements: bool = True):
    if _is_missing(x):
        return 0
    if _is_nodeset(x):
        if len(x) == 0:
            return 0
        return [xml_length(node, only_elements) for node in x]
    if not _is_node(x):
        _abort("Unexpected node type")
    return len(_children(x.ptr, only_elements))


def xml_root(x):
    if _is_nodeset(x):
        if len(x) == 0:
            return None
        return xml_root(x[0])
    if not (_is_node(x) or isinstance(x, BareDocument)):
        _abort("x is not an xml node")
    if not C.lib.xmlDocGetRootElement(x.owner.ptr):
        return xml_missing()
    return _as_document(x.owner)


def xml_child(x, search=1, ns=None):
    if isinstance(search, (list, tuple)) or (
        not isinstance(search, (int, float, str))
    ):
        _abort(f"{search} must be of length 1.")
    if ns is None:
        ns = xml_ns(x)
    if isinstance(search, (int, float)) and not isinstance(search, bool):
        children = xml_children(x)
        index = int(search) - 1
        if index < 0 or index >= len(children):
            _abort("subscript out of bounds")
        return children[index]
    if isinstance(search, str):
        return xml_find_first(x, "./" + search, ns=ns)
    _abort("search must be numeric or character.")
    return xml_missing()


def _attr_nodes(ptr) -> list:
    if C.node_view(ptr).type != C.XML_ELEMENT_NODE:
        return []
    out = []
    current = C.ptr_value(C.node_view(ptr).properties)
    while current:
        out.append(current)
        current = C.ptr_value(C.attr_view(current).next)
    return out


def _ns_defs(ptr) -> list:
    if C.node_view(ptr).type != C.XML_ELEMENT_NODE:
        return []
    out = []
    current = C.ptr_value(C.node_view(ptr).nsDef)
    while current:
        out.append(current)
        current = C.ptr_value(C.ns_view(current).next)
    return out


def _ns_definition(ptr, prefix: str | None) -> str | None:
    for ns_ptr in _ns_defs(ptr):
        current = _ns_prefix(ns_ptr)
        if prefix is None and current is None:
            return _ns_href(ns_ptr)
        if prefix is not None and current == prefix:
            return _ns_href(ns_ptr)
    return None


def _as_ns(ns) -> XmlNamespace | None:
    if ns is None:
        return None
    if isinstance(ns, XmlNamespace):
        return ns if len(ns) else None
    if isinstance(ns, dict):
        if not ns:
            return None
        return XmlNamespace(ns)
    _abort("ns must be a namespace map")
    return None


def _find_url(ns: XmlNamespace, prefix: str) -> str:
    if prefix not in ns:
        _abort(f"Couldn't find url for prefix {prefix}")
    return ns[prefix]


def _find_prefix(ns: XmlNamespace, url: str | None) -> str:
    for prefix, href in ns.items():
        if href == url:
            return prefix
    _abort(f"Couldn't find prefix for url {url}")
    return ""


def _one_attr(ptr, name: str, default, ns: XmlNamespace | None):
    if name == "xmlns":
        found = _ns_definition(ptr, None)
        return default if found is None else found
    if name.startswith("xmlns:"):
        found = _ns_definition(ptr, name[6:])
        return default if found is None else found
    if not ns:
        found = C.text_of(C.lib.xmlGetProp(ptr, C.bytes_of(name)), free=True)
    else:
        colon = name.find(":")
        if colon < 0:
            found = C.text_of(C.lib.xmlGetNoNsProp(ptr, C.bytes_of(name)), free=True)
        else:
            prefix = name[:colon]
            attr = name[colon + 1 :]
            url = _find_url(ns, prefix)
            found = C.text_of(
                C.lib.xmlGetNsProp(ptr, C.bytes_of(attr), C.bytes_of(url)),
                free=True,
            )
    return default if found is None else found


def xml_attr(x, attr, ns=None, default=NA):
    mapping = _as_ns(ns)
    if not isinstance(attr, str):
        _abort("attr must be a string")
    if _is_missing(x):
        return NA
    nodes = _nodes_of(x)
    out = []
    for node in nodes:
        if _is_missing(node):
            out.append(NA)
        else:
            out.append(_one_attr(node.ptr, attr, default, mapping))
    if _is_nodeset(x):
        return out
    return out[0]


def xml_has_attr(x, attr, ns=None):
    found = xml_attr(x, attr, ns=ns)
    if isinstance(found, list):
        return [item is not NA for item in found]
    return found is not NA


class NamedChars:
    """A named character vector. Names may repeat, in document order."""

    def __init__(self, pairs=None):
        self.pairs = [(str(name), "" if value is None else str(value)) for name, value in (pairs or [])]

    def __iter__(self):
        return iter(dict(self.pairs))

    def __len__(self) -> int:
        return len(self.pairs)

    def __bool__(self) -> bool:
        return bool(self.pairs)

    def __contains__(self, key) -> bool:
        return any(name == key for name, _value in self.pairs)

    def __eq__(self, other) -> bool:
        if isinstance(other, NamedChars):
            return self.pairs == other.pairs
        if isinstance(other, dict):
            return self.pairs == list(other.items())
        return False

    def items(self):
        return list(self.pairs)

    def keys(self):
        return [name for name, _value in self.pairs]

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.pairs[key][1]
        for name, value in self.pairs:
            if name == key:
                return value
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


def _one_attrs(ptr, ns: XmlNamespace | None) -> NamedChars:
    if C.node_view(ptr).type != C.XML_ELEMENT_NODE:
        return NamedChars()
    pairs = []
    for attr_ptr in _attr_nodes(ptr):
        attr = C.attr_view(attr_ptr)
        if ns:
            name = _qualified_name(attr_ptr, ns)
        else:
            name = attr.name.decode("utf-8") if attr.name else ""
        ns_ptr = C.ptr_value(attr.ns)
        if ns_ptr is None:
            if ns:
                value = C.text_of(C.lib.xmlGetNoNsProp(ptr, attr.name), free=True)
            else:
                value = C.text_of(C.lib.xmlGetProp(ptr, attr.name), free=True)
        else:
            href = C.ns_view(ns_ptr).href
            value = C.text_of(C.lib.xmlGetNsProp(ptr, attr.name, href), free=True)
        pairs.append((name, "" if value is None else value))
    for ns_ptr in _ns_defs(ptr):
        prefix = _ns_prefix(ns_ptr)
        key = "xmlns" if prefix is None else f"xmlns:{prefix}"
        pairs.append((key, _ns_href(ns_ptr) or ""))
    return NamedChars(pairs)


def xml_attrs(x, ns=None):
    mapping = _as_ns(ns)
    if _is_missing(x):
        return NA
    if _is_nodeset(x):
        return [
            NA if _is_missing(node) else _one_attrs(node.ptr, mapping) for node in x
        ]
    if not _is_node(x):
        _abort("Unexpected node type")
    return _one_attrs(x.ptr, mapping)


def _named(value) -> bool:
    return isinstance(value, dict)


def xml_set_attr(x, attr, value, ns=None):
    # The R function ends in `xml_attr<-`, so the call returns the assigned value.
    xml_attr_assign(x, attr, value, ns)
    return value


def xml_attr_assign(x, attr, value, ns=None):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = value if isinstance(value, list) else [value]
        if len(values) == 0:
            values = [values]
        values = _recycle(values, len(x))
        for node, item in zip(x, values):
            xml_attr_assign(node, attr, item, ns)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    _set_one_attr(x, attr, value, _as_ns(ns))
    return x


def _set_one_attr(node: XmlNode, name: str, value, ns: XmlNamespace | None) -> None:
    if value is None:
        _remove_one_attr(node, name, ns)
        return
    text = _as_text(value)
    if name == "xmlns":
        ns_ptr = C.lib.xmlNewNs(node.ptr, C.bytes_of(text), None)
        _add_namespace(node.ptr, ns_ptr)
        return
    if name.startswith("xmlns:"):
        prefix = name[6:]
        _remove_ns(node.ptr, prefix)
        ns_ptr = C.lib.xmlNewNs(node.ptr, C.bytes_of(text), C.bytes_of(prefix))
        _add_namespace(node.ptr, ns_ptr)
        return
    if not ns or ":" not in name:
        C.lib.xmlSetProp(node.ptr, C.bytes_of(name), C.bytes_of(text))
        return
    prefix, attr = name.split(":", 1)
    url = _find_url(ns, prefix)
    found = C.lib.xmlSearchNsByHref(node.owner.ptr, node.ptr, C.bytes_of(url))
    C.lib.xmlSetNsProp(node.ptr, found, C.bytes_of(attr), C.bytes_of(text))


def _remove_one_attr(node: XmlNode, name: str, ns: XmlNamespace | None) -> None:
    if name == "xmlns":
        _remove_ns(node.ptr, None)
        return
    if name.startswith("xmlns:"):
        _remove_ns(node.ptr, name[6:])
        return
    if not ns or ":" not in name:
        if ns and ":" not in name:
            C.lib.xmlUnsetNsProp(node.ptr, None, C.bytes_of(name))
        else:
            C.lib.xmlUnsetProp(node.ptr, C.bytes_of(name))
        return
    prefix, attr = name.split(":", 1)
    url = _find_url(ns, prefix)
    found = C.lib.xmlSearchNsByHref(node.owner.ptr, node.ptr, C.bytes_of(url))
    C.lib.xmlUnsetNsProp(node.ptr, found, C.bytes_of(attr))


def _add_namespace(tree, ns_ptr) -> None:
    if not ns_ptr or _ns_prefix(ns_ptr) is not None:
        return

    def visit(node, view) -> None:
        if C.ptr_value(view.ns) is None:
            view.ns = ctypes_ns(ns_ptr)

    C.walk_subtree(tree, visit)


def ctypes_ns(ns_ptr):
    return ctypes_cast_ns(ns_ptr)


def ctypes_cast_ns(ns_ptr):
    import ctypes

    return ctypes.cast(ns_ptr, ctypes.POINTER(C.xmlNs))


def _remove_ns(node, prefix: str | None) -> None:
    import ctypes

    first = C.ptr_value(C.node_view(node).nsDef)
    if not first:
        return
    prev = first
    if _ns_prefix(prev) == prefix or (prefix is None and _ns_prefix(prev) is None):
        nxt = C.ptr_value(C.ns_view(prev).next)
        C.node_view(node).nsDef = (
            ctypes.cast(nxt, ctypes.POINTER(C.xmlNs)) if nxt else None
        )
        _clear_ns(node, prev)
        C.lib.xmlFreeNs(prev)
        return
    while True:
        current = C.ptr_value(C.ns_view(prev).next)
        if not current:
            return
        if _ns_prefix(current) == prefix or (
            prefix is None and _ns_prefix(current) is None
        ):
            nxt = C.ptr_value(C.ns_view(current).next)
            C.ns_view(prev).next = (
                ctypes.cast(nxt, ctypes.POINTER(C.xmlNs)) if nxt else None
            )
            _clear_ns(node, current)
            C.lib.xmlFreeNs(current)
            return
        prev = current


def _clear_ns(tree, ns_ptr) -> None:
    prefix = _ns_prefix(ns_ptr)

    def visit(node, view) -> None:
        if C.ptr_value(view.ns) == ns_ptr:
            view.ns = None
        if prefix is not None and view.type == C.XML_ELEMENT_NODE:
            attr = C.ptr_value(view.properties)
            while attr:
                attr_obj = C.attr_view(attr)
                if C.ptr_value(attr_obj.ns) == ns_ptr:
                    attr_obj.ns = None
                attr = C.ptr_value(attr_obj.next)

    C.walk_subtree(tree, visit)


def xml_set_attrs(x, value, ns=None):
    # The R function ends in `xml_attrs<-`, so the call returns the assigned value.
    xml_attrs_assign(x, value, ns)
    return value


def xml_attrs_assign(x, value, ns=None):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = value if isinstance(value, list) else [value]
        namespaces = ns if isinstance(ns, list) else [ns]
        values = _recycle(values, len(x))
        namespaces = _recycle(namespaces, len(x))
        for node, item, item_ns in zip(x, values, namespaces):
            if not _named(item) and item is not None:
                _abort("value must be a list of named character vectors.")
            xml_attrs_assign(node, item, item_ns)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    if value is not None and not _named(value):
        _abort("value must be a named character vector or NULL")
    mapping = _as_ns(ns)
    incoming = {} if value is None else {str(key): _as_text(item) for key, item in value.items()}
    current = list(_one_attrs(x.ptr, mapping))
    existing = [name for name in current if name in incoming]
    new = [name for name in incoming if name not in current]
    removed = [name for name in current if name not in incoming]
    for name in existing + new:
        _set_one_attr(x, name, incoming[name], mapping)
    for name in removed:
        _remove_one_attr(x, name, mapping)
    return x


def _cache_namespaces(ptr, pairs: list[tuple[str, str]]) -> None:
    for ns_ptr in _ns_defs(ptr):
        prefix = _ns_prefix(ns_ptr) or ""
        pairs.append((prefix, _ns_href(ns_ptr) or ""))
    current = C.ptr_value(C.node_view(ptr).children)
    while current and C.node_view(current).type != C.XML_ENTITY_DECL:
        _cache_namespaces(current, pairs)
        current = C.ptr_value(C.node_view(current).next)


def xml_ns(x) -> XmlNamespace:
    if _is_missing(x):
        return XmlNamespace()
    if _is_nodeset(x):
        if len(x) == 0:
            return XmlNamespace()
        return xml_ns(x[0])
    if isinstance(x, BareDocument):
        return XmlNamespace()
    if not _is_node(x):
        _abort("Unexpected node type")
    root = C.lib.xmlDocGetRootElement(x.owner.ptr)
    if not root:
        return XmlNamespace()
    pairs: list[tuple[str, str]] = []
    _cache_namespaces(root, pairs)
    pairs.sort(key=lambda item: item[0])
    prefixes = [prefix for prefix, _url in pairs]
    urls = [url for _prefix, url in pairs]
    default = 0
    renamed = []
    for prefix in prefixes:
        if prefix == "":
            default += 1
            renamed.append(f"d{default}")
        else:
            renamed.append(prefix)
    renamed = make_unique(renamed, "")
    return XmlNamespace(zip(renamed, urls))


def xml_ns_rename(old, **new) -> XmlNamespace:
    if not isinstance(old, XmlNamespace):
        old = XmlNamespace(old)
    missing = [name for name in new if name not in old]
    if missing:
        _abort(f"Some prefixes [{', '.join(missing)}] don't already exist.")
    renamed = []
    for name, url in old.items():
        renamed.append((new.get(name, name), url))
    return XmlNamespace(renamed)


def xml_ns_strip(x):
    nodes = xml_find_all(x, "//namespace::*[name()='']/parent::*")
    xml_attr_assign(nodes, "xmlns", None)
    return x


def xml_set_namespace(x, prefix: str = "", uri: str = ""):
    if not _is_node(x):
        _abort("x is not an xml node")
    if uri:
        found = C.lib.xmlSearchNsByHref(x.owner.ptr, x.ptr, C.bytes_of(uri))
    elif prefix:
        found = C.lib.xmlSearchNs(x.owner.ptr, x.ptr, C.bytes_of(prefix))
    else:
        found = C.lib.xmlSearchNs(x.owner.ptr, x.ptr, None)
    if uri and not found:
        _abort(f"No namespace with URI `{uri}` found")
    if prefix and not uri and not found:
        _abort(f"No namespace with prefix `{prefix}` found")
    C.lib.xmlSetNs(x.ptr, found)
    return x


def _register_ns(ctx, ns: XmlNamespace | None) -> None:
    if not ns:
        return
    for prefix, url in ns.items():
        if C.lib.xmlXPathRegisterNs(ctx, C.bytes_of(prefix), C.bytes_of(url)) != 0:
            _abort(f"Failed to register namespace ({prefix} <-> {url})")


def _xpath(node: XmlNode, xpath: str, ns, limit: float):
    if not isinstance(xpath, str):
        _abort("XPath must be a string")
    ctx = C.lib.xmlXPathNewContext(node.owner.ptr)
    if not ctx:
        return ("missing", None)
    try:
        head = __import__("ctypes").cast(ctx, __import__("ctypes").POINTER(C.xmlXPathContextHead))
        head.contents.node = node.ptr
        _register_ns(ctx, _as_ns(ns))
        obj = C.lib.xmlXPathEval(C.bytes_of(xpath), ctx)
        if not obj:
            return ("missing", None)
        try:
            view = __import__("ctypes").cast(obj, __import__("ctypes").POINTER(C.xmlXPathObject)).contents
            if view.type == C.XPATH_NODESET:
                nodeset = view.nodesetval
                if not nodeset:
                    return ("nodes", [])
                count = nodeset.contents.nodeNr
                if count <= 0:
                    return ("nodes", [])
                cap = count if limit == float("inf") else min(count, int(limit))
                pointers = []
                for i in range(cap):
                    pointers.append(nodeset.contents.nodeTab[i])
                return ("nodes", pointers)
            if view.type == C.XPATH_NUMBER:
                return ("number", view.floatval)
            if view.type == C.XPATH_BOOLEAN:
                return ("bool", bool(view.boolval))
            if view.type == C.XPATH_STRING:
                return ("string", C.text_of(view.stringval, free=False) or "")
            _abort(f"XPath result type: {view.type} not supported")
        finally:
            C.lib.xmlXPathFreeObject(obj)
    finally:
        C.lib.xmlXPathFreeContext(ctx)
    return ("missing", None)


def xml_find_all(x, xpath, ns=None, flatten: bool = True):
    if ns is None:
        ns = xml_ns(x)
    if _is_missing(x):
        return xml_nodeset()
    if _is_nodeset(x):
        if len(x) == 0:
            return xml_nodeset()
        groups = []
        for node in x:
            groups.append(xml_find_all(node, xpath, ns=ns))
        if flatten:
            flat = []
            for group in groups:
                flat.extend(group)
            return xml_nodeset(flat)
        return groups
    if not _is_node(x):
        _abort("Unexpected node type")
    kind, value = _xpath(x, xpath, ns, float("inf"))
    if kind != "nodes":
        return value
    return xml_nodeset([_wrap_node(ptr, x.owner) for ptr in value])


def xml_find_first(x, xpath, ns=None):
    if ns is None:
        ns = xml_ns(x)
    if _is_missing(x):
        return xml_missing()
    if _is_nodeset(x):
        if len(x) == 0:
            return xml_nodeset()
        return xml_nodeset(
            [xml_find_first(node, xpath, ns=ns) for node in x],
            deduplicate=False,
        )
    if not _is_node(x):
        _abort("Unexpected node type")
    kind, value = _xpath(x, xpath, ns, 1)
    if kind == "nodes":
        if not value:
            return xml_missing()
        return _wrap_node(value[0], x.owner)
    if kind == "missing":
        return xml_missing()
    return value


def xml_find_one(x, xpath, ns=None):
    warnings.warn("xml_find_one is deprecated; use xml_find_first", DeprecationWarning, stacklevel=2)
    return xml_find_first(x, xpath, ns=ns)


def _scalar_find(x, xpath, ns, kind_expected: str):
    if _is_missing(x):
        return {"number": [], "int": [], "string": [], "bool": []}[kind_expected]
    if _is_nodeset(x):
        if len(x) == 0:
            return []
        return [_scalar_find(node, xpath, ns, kind_expected) for node in x]
    kind, value = _xpath(x, xpath, ns, float("inf"))
    label = f"Element at path `{xpath}`"
    if kind_expected == "number":
        if kind == "number" and value != value:
            return value
        if kind != "number":
            _abort(f"{label} must be a number")
        return value
    if kind_expected == "int":
        if kind != "number" or value != int(value):
            _abort(f"{label} must be a whole number")
        return int(value)
    if kind_expected == "string":
        if kind != "string":
            _abort(f"{label} must be a string")
        return value
    if kind != "bool":
        _abort(f"{label} must be a logical")
    return value


def xml_find_num(x, xpath, ns=None):
    if ns is None:
        ns = xml_ns(x)
    return _scalar_find(x, xpath, ns, "number")


def xml_find_int(x, xpath, ns=None):
    if ns is None:
        ns = xml_ns(x)
    return _scalar_find(x, xpath, ns, "int")


def xml_find_chr(x, xpath, ns=None):
    if ns is None:
        ns = xml_ns(x)
    return _scalar_find(x, xpath, ns, "string")


def xml_find_lgl(x, xpath, ns=None):
    if ns is None:
        ns = xml_ns(x)
    return _scalar_find(x, xpath, ns, "bool")


def _copy_node(node: XmlNode) -> XmlNode:
    copied = C.lib.xmlCopyNode(node.ptr, 1)
    return XmlNode(copied, node.owner)


def xml_cdata(content: str) -> str:
    return _Marked(content, "cdata")


def xml_comment(content: str):
    return _Marked(content, "comment")


def xml_dtd(name: str = "", external_id: str = "", system_id: str = ""):
    return _Dtd(name, external_id, system_id)


class _Marked:
    def __init__(self, content: str, kind: str):
        self.content = content
        self.kind = kind


class _Dtd:
    def __init__(self, name: str, external_id: str, system_id: str):
        self.name = name
        self.external_id = external_id
        self.system_id = system_id


def _create_node(value, parent, copy: bool, attrs: dict, text_parts: list):
    if _is_node(value):
        node = _copy_node(value) if copy else value
        return node
    if isinstance(value, _Marked) and value.kind == "cdata":
        payload = _bytes_len(value.content)
        ptr = C.lib.xmlNewCDataBlock(parent.owner.ptr, payload, len(payload))
        return XmlNode(ptr, parent.owner)
    if isinstance(value, _Marked) and value.kind == "comment":
        ptr = C.lib.xmlNewComment(C.bytes_of(value.content))
        return XmlNode(ptr, parent.owner)
    if isinstance(value, _Dtd):
        name = C.bytes_of(value.name) if value.name else None
        external = C.bytes_of(value.external_id) if value.external_id else None
        system = C.bytes_of(value.system_id) if value.system_id else None
        dtd = C.lib.xmlNewDtd(parent.owner.ptr, name, external, system)
        C.lib.xmlAddChild(parent.owner.ptr, dtd)
        return None
    if not isinstance(value, str):
        _abort(".value must be a string or a node")
    parts = value.split(":")
    parent_ptr = parent.ptr if _is_node(parent) else None
    if len(parts) == 2 and parent_ptr:
        ns_ptr = C.lib.xmlSearchNs(parent.owner.ptr, parent_ptr, C.bytes_of(parts[0]))
        if not ns_ptr:
            _abort(f"No namespace with prefix `{parts[0]}` found")
        ptr = C.lib.xmlNewNode(ns_ptr, C.bytes_of(parts[1]))
    else:
        ptr = C.lib.xmlNewNode(None, C.bytes_of(value))
    node = XmlNode(ptr, parent.owner)
    if attrs:
        xml_attrs_assign(node, attrs)
    xml_text_assign(node, "".join(_as_text(part) for part in text_parts))
    return node


def _insert_child(parent: XmlNode, node: XmlNode, where) -> None:
    if node is None:
        return
    if where is None or where == float("inf"):
        C.lib.xmlAddChild(parent.ptr, node.ptr)
        return
    where = int(where)
    if where == 0:
        if _children(parent.ptr, True):
            first = _children(parent.ptr, False)[0]
            C.lib.xmlAddPrevSibling(first, node.ptr)
        else:
            C.lib.xmlAddChild(parent.ptr, node.ptr)
        return
    if where >= xml_length(parent):
        C.lib.xmlAddChild(parent.ptr, node.ptr)
        return
    target = xml_child(parent, where)
    C.lib.xmlAddNextSibling(target.ptr, node.ptr)


def xml_add_child(x, value, *text, where=None, copy=None, **attrs):
    if copy is None:
        copy = True
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = value if isinstance(value, list) and value and _is_node(value[0]) else [value]
        if _is_node(value):
            values = [value]
        values = _recycle(values, len(x))
        made = []
        for node, item in zip(x, values):
            made.append(xml_add_child(node, item, *text, where=where, copy=copy, **attrs))
        return xml_nodeset(made)
    if isinstance(x, BareDocument):
        node = _create_node(value, x, copy, attrs, list(text))
        if node is not None:
            if not C.lib.xmlDocGetRootElement(x.owner.ptr):
                C.lib.xmlDocSetRootElement(x.owner.ptr, node.ptr)
            root = C.lib.xmlDocGetRootElement(x.owner.ptr)
            C.lib.xmlAddChild(root, node.ptr)
        return _as_document(x.owner)
    if not _is_node(x):
        _abort("Unexpected node type")
    node = _create_node(value, x, copy if copy is not None else _is_node(value), attrs, list(text))
    if node is None:
        return None
    _insert_child(x, node, where)
    return node


def xml_add_sibling(x, value, *text, where: str = "after", copy=None, **attrs):
    if copy is None:
        copy = True
    where = match_arg(where, ["after", "before"])
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = [value] if not isinstance(value, list) else value
        if _is_node(value):
            values = [value]
        values = _recycle(values, len(x))
        for node, item in zip(reversed(list(x)), reversed(values)):
            xml_add_sibling(node, item, *text, where=where, copy=copy, **attrs)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    node = _create_node(value, x, copy, attrs, list(text))
    if node is None:
        return x
    if where == "before":
        C.lib.xmlAddPrevSibling(x.ptr, node.ptr)
    else:
        C.lib.xmlAddNextSibling(x.ptr, node.ptr)
    return x


def xml_add_parent(x, value, *text, **attrs):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = [value] if _is_node(value) or not isinstance(value, list) else value
        values = _recycle(values, len(x))
        made = [xml_add_parent(node, item, *text, **attrs) for node, item in zip(x, values)]
        return xml_nodeset(made)
    if not _is_node(x):
        _abort("Unexpected node type")
    new_parent = xml_replace(x, value, *text, copy=False, **attrs)
    return xml_add_child(new_parent, x, copy=False)


def xml_replace(x, value, *text, copy: bool = True, **attrs):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        values = [value] if _is_node(value) or not isinstance(value, list) else value
        values = _recycle(values, len(x))
        return [xml_replace(node, item, *text, copy=copy, **attrs) for node, item in zip(x, values)]
    if not _is_node(x):
        _abort("Unexpected node type")
    node = _create_node(value, x, copy, attrs, list(text))
    C.lib.xmlReplaceNode(x.ptr, node.ptr)
    return node


def xml_remove(x, free: bool = False):
    if _is_missing(x):
        return x
    if _is_nodeset(x):
        if len(x) == 0:
            return x
        for node in reversed(list(x)):
            xml_remove(node, free=free)
        return x
    if not _is_node(x):
        _abort("Unexpected node type")
    C.lib.xmlUnlinkNode(x.ptr)
    if free:
        C.lib.xmlFreeNode(x.ptr)
        x.ptr = None
    return x


def xml_new_document(version: str = "1.0", encoding: str = "UTF-8"):
    enc = C.lib.xmlParseCharEncoding(C.bytes_of(encoding))
    if enc < 0:
        _abort(f"Requested unsupported encoding '{encoding}'")
    doc = C.lib.xmlNewDoc(C.bytes_of(version))
    name = C.lib.xmlGetCharEncodingName(enc)
    if name:
        encoding_ptr = C.lib.xmlStrdup(name)
        C.doc_view(doc).encoding = __import__("ctypes").cast(
            encoding_ptr, __import__("ctypes").c_char_p
        )
    return BareDocument(Owner(doc))


def xml_new_root(value, *text, copy=None, version: str = "1.0", encoding: str = "UTF-8", **attrs):
    if copy is None:
        copy = _is_node(value)
    return xml_add_child(
        xml_new_document(version, encoding),
        value,
        *text,
        copy=copy,
        **attrs,
    )


def _read_compressed(path: str) -> bytes | None:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext == "gz":
        with gzip.open(path, "rb") as handle:
            return handle.read()
    if ext == "bz2":
        with bz2.open(path, "rb") as handle:
            return handle.read()
    if ext == "xz":
        with lzma.open(path, "rb") as handle:
            return handle.read()
    if ext == "zip":
        with zipfile.ZipFile(path) as handle:
            names = handle.namelist()
            if len(names) > 1:
                print(f"Multiple files in zip: reading '{names[0]}'")
            return handle.read(names[0])
    return None


def _is_url(path: str) -> bool:
    return re.match(r"^(http|ftp)s?://", path) is not None


def _fetch_url(path: str) -> bytes:
    from urllib.request import urlopen

    with urlopen(path) as handle:
        return handle.read()


def read_xml(x, encoding: str = "", as_html: bool = False, options="NOBLANKS", base_url: str = "", **_ignored):
    if isinstance(x, (bytes, bytearray)):
        return _read_raw(bytes(x), encoding, base_url, as_html, options)
    if hasattr(x, "read"):
        payload = x.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        return _read_raw(payload, encoding, base_url, as_html, options)
    text = _check_string(x)
    if re.search(r"<|>", text):
        return _read_raw(text.encode("utf-8"), "UTF-8", base_url, as_html, options)
    if _is_url(text):
        payload = _fetch_url(text)
        return _read_raw(payload, encoding, text, as_html, options)
    path = os.path.abspath(text)
    if not os.path.exists(path):
        _abort(f"'{path}' does not exist in current working directory ('{os.getcwd()}').")
    compressed = _read_compressed(path)
    flags = parse_options(options, C.PARSE_OPTIONS)
    if compressed is None:
        doc = C.read_file(path, encoding, as_html, flags)
        if not doc:
            _abort(f"Failed to parse {path}")
        return _as_document(Owner(doc))
    return _read_raw(compressed, encoding, path, as_html, options)


def _read_raw(payload: bytes, encoding: str, base_url: str, as_html: bool, options) -> XmlDocument:
    flags = parse_options(options, C.PARSE_OPTIONS)
    doc = C.read_memory(payload, base_url or "", encoding, as_html, flags)
    if not doc:
        _abort("Failed to parse text")
    return _as_document(Owner(doc))


def read_html(x, encoding: str = "UTF-8", options=None, **kwargs):
    if options is None:
        options = ["RECOVER", "NOERROR", "NOBLANKS", "HUGE"]
    return read_xml(x, encoding=encoding, as_html=True, options=options, **kwargs)


def _character(x, options="format", encoding: str = "UTF-8") -> str:
    flags = parse_options(options, C.SAVE_OPTIONS)
    if isinstance(x, XmlDocument):
        return C.save_character(x.owner.ptr, encoding, flags, tree=False)
    if isinstance(x, BareDocument):
        return C.save_character(x.owner.ptr, encoding, flags, tree=False)
    if _is_missing(x):
        return NA
    if _is_nodeset(x):
        return [_character(node, options, encoding) for node in x]
    if _is_node(x):
        return C.save_character(x.ptr, encoding, flags, tree=True)
    _abort("Unexpected node type")
    return ""


def as_character(x, options="format", encoding: str = "UTF-8"):
    return _character(x, options, encoding)


def write_xml(x, file, options="format", encoding: str = "UTF-8", **_ignored):
    _write(x, file, options, encoding)


def write_html(x, file, options="format", encoding: str = "UTF-8", **_ignored):
    _write(x, file, options, encoding)


def _write(x, file, options, encoding: str) -> None:
    if _is_missing(x):
        _abort("Missing data cannot be written.")
    flags = parse_options(options, C.SAVE_OPTIONS)
    target = x
    tree = True
    if _is_nodeset(x):
        if len(x) != 1:
            _abort("Can only save length 1 node sets.")
        target = x[0]
    if isinstance(target, (XmlDocument, BareDocument)):
        tree = False
        ptr = target.owner.ptr
    else:
        ptr = target.ptr
    if hasattr(file, "write"):
        text = C.save_character(ptr, encoding, flags, tree=tree)
        file.write(text)
        return
    path = _check_string(file, "file")
    directory = os.path.dirname(path) or "."
    if not os.path.exists(os.path.abspath(directory)):
        _abort(f"'{path}' does not exist.")
    C.save_file(ptr, path, encoding, flags, tree=tree)


def xml_structure(x, indent: int = 2, file: str = ""):
    _tree_structure(x, indent, False, file)


def html_structure(x, indent: int = 2, file: str = ""):
    _tree_structure(x, indent, True, file)


def _emit(text: str, file: str) -> None:
    if file:
        with open(file, "a", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text, end="")


def _tree_structure(x, indent: int, html: bool, file: str) -> None:
    if _is_missing(x):
        return
    if _is_nodeset(x):
        for i, node in enumerate(x, start=1):
            _emit(f"[[{i}]]\n", file)
            _print_structure(node, 0, indent, html, file)
            _emit("\n", file)
        return
    if _is_node(x):
        _print_structure(x, 0, indent, html, file)


def _print_structure(x, prefix: int, indent: int, html: bool, file: str) -> None:
    padding = " " * prefix
    kind = xml_type(x)
    if kind == "element":
        attr = xml_attrs(x) or {}
        attr_str = ""
        if html:
            pieces = []
            if "id" in attr:
                pieces.append("#" + attr["id"])
                attr = {key: value for key, value in attr.items() if key != "id"}
            if "class" in attr:
                pieces.append("." + attr["class"].replace(" ", "."))
                attr = {key: value for key, value in attr.items() if key != "class"}
            attr_str = "".join(pieces) if False else " ".join(pieces)
        if attr:
            attr_str = attr_str + " [" + ", ".join(attr) + "]"
        _emit(f"{padding}<{xml_name(x)}{attr_str}>\n", file)
        for child in xml_contents(x):
            _print_structure(child, prefix + indent, indent, html, file)
    else:
        _emit(f"{padding}{{{kind}}}\n", file)


_SPECIAL_ATTRS = ("class", "comment", "dim", "dimnames", "names", "row.names", "tsp")


def as_list(x, ns=None):
    if _is_missing(x):
        return RList()
    if isinstance(x, XmlDocument):
        inner = _as_list_node(x, ns)
        return RList([inner], names=[xml_name(x, ns)])
    if isinstance(x, BareDocument):
        return RList()
    if _is_nodeset(x):
        return RList([as_list(node, ns) for node in x])
    if _is_node(x):
        return _as_list_node(x, ns)
    _abort("Unexpected node type")
    return RList()


def _as_list_node(x: XmlNode, ns):
    contents = xml_contents(x)
    if len(contents) == 0:
        kind = xml_type(x)
        if kind in ("text", "cdata"):
            return xml_text(x)
        if kind not in ("element", "document"):
            return f"[ {kind} ]"
        out = RList()
    else:
        items = [as_list(child, ns) for child in contents]
        names = []
        types = xml_type(contents)
        element_names = xml_name(contents, ns)
        for kind, name in zip(types, element_names):
            names.append(name if kind == "element" else "")
        out = RList(items, names=names if any(names) else None)
        if any(names):
            out.names = names
    attrs = xml_attrs(x, ns) or {}
    for key, value in list(attrs.items()):
        if key in _SPECIAL_ATTRS:
            attrs["." + key] = attrs.pop(key)
    out.attrs = attrs
    return out


def as_xml_document(x, root=None, **attrs):
    if isinstance(x, (str, bytes, bytearray)) or hasattr(x, "read"):
        return read_xml(x)
    if isinstance(x, XmlDocument):
        return x
    if _is_node(x):
        return xml_new_root(x, copy=True, **attrs)
    if _is_nodeset(x):
        doc = xml_new_root(root, copy=True, **attrs)
        for node in x:
            xml_add_child(doc, node, copy=True)
        return doc
    if isinstance(x, (list, RList)):
        return _list_to_xml(x)
    _abort("no method for this object")
    return None


def _list_to_xml(x):
    if not isinstance(x, RList):
        x = RList(list(x), names=[""] * len(x))
    if len(x) > 1:
        _abort("Root nodes must be of length 1.")
    doc = xml_new_document()

    def add(item, parent, tag):
        if not isinstance(item, (list, RList)):
            payload = _bytes_len(_as_text(item))
            if _is_node(parent):
                C.lib.xmlAddChild(parent.ptr, C.lib.xmlNewTextLen(payload, len(payload)))
            return
        if tag:
            parent = xml_add_child(parent, tag)
            if isinstance(item, RList):
                for key, value in _r_attrs_to_xml(item.attrs).items():
                    xml_set_attr(parent, key, value)
        if isinstance(item, RList):
            for child, name in zip(item, item.names):
                add(child, parent, name or None)
        else:
            for child in item:
                add(child, parent, None)

    add(x, doc, None)
    return xml_root(doc)


def _r_attrs_to_xml(attrs: dict) -> dict:
    out = {}
    for key, value in attrs.items():
        if key in _SPECIAL_ATTRS or key == "names":
            continue
        name = key[1:] if key in {f".{item}" for item in _SPECIAL_ATTRS} else key
        out[name] = value
    return out


def xml_validate(x, schema) -> ValidateResult:
    if not isinstance(x, (XmlDocument, BareDocument)):
        _abort("x is not an xml document")
    if not isinstance(schema, (XmlDocument, BareDocument)):
        _abort("schema is not an xml document")
    errors: list[str] = []

    @C.StructuredError
    def on_error(_user, err):
        if err and err.contents.message:
            message = err.contents.message.decode("utf-8", errors="replace")
            if message.endswith("\n"):
                message = message[:-1]
            errors.append(message)

    parser = C.lib.xmlSchemaNewDocParserCtxt(schema.owner.ptr)
    C.lib.xmlSchemaSetParserStructuredErrors(parser, on_error, None)
    parsed = C.lib.xmlSchemaParse(parser)
    valid = C.lib.xmlSchemaNewValidCtxt(parsed)
    C.lib.xmlSchemaSetValidStructuredErrors(valid, on_error, None)
    ok = C.lib.xmlSchemaValidateDoc(valid, x.owner.ptr) == 0
    C.lib.xmlSchemaFreeParserCtxt(parser)
    C.lib.xmlSchemaFreeValidCtxt(valid)
    C.lib.xmlSchemaFree(parsed)
    # Keep the callback alive until libxml2 has returned.
    del on_error
    return ValidateResult(ok, errors)


def xml_serialize(obj, connection=None, **kwargs) -> Serialized:
    if isinstance(obj, XmlDocument):
        kind = "document"
        xml = as_character(obj, **kwargs)
        doc_type = _doc_type(obj)
    elif _is_nodeset(obj):
        kind = "nodeset"
        xml = as_character(as_xml_document(obj, "root"), **kwargs)
        doc_type = None
    elif _is_node(obj):
        kind = "node"
        xml = as_character(as_xml_document(obj), **kwargs)
        doc_type = None
    else:
        _abort("Unexpected node type")
    payload = Serialized(kind, xml, doc_type)
    if isinstance(connection, str):
        Path(connection).write_bytes(_dump_serialized(payload))
    return payload


def xml_unserialize(connection, **kwargs):
    if isinstance(connection, str):
        payload = _load_serialized(Path(connection).read_bytes())
    elif isinstance(connection, Serialized):
        payload = connection
    elif isinstance(connection, (bytes, bytearray)):
        payload = _load_serialized(bytes(connection))
    else:
        _abort("Not a serialized xml2 object.")
        return None
    if payload.kind == "nodeset":
        doc = read_xml(payload.xml, **kwargs)
        return xml_find_all(doc, "/*/node()")
    if payload.kind == "node":
        doc = read_xml(payload.xml, **kwargs)
        return xml_find_first(doc, "/node()")
    if payload.kind == "document":
        as_html = payload.doc_type == "html"
        if "as_html" in kwargs:
            as_html = kwargs.pop("as_html")
        return read_xml(payload.xml, as_html=as_html, **kwargs)
    _abort("Not a serialized xml2 object.")
    return None


def _dump_serialized(payload: Serialized) -> bytes:
    header = f"xml2-1\n{payload.kind}\n{payload.doc_type or ''}\n".encode("utf-8")
    return header + payload.xml.encode("utf-8")


def _load_serialized(blob: bytes) -> Serialized:
    if not blob.startswith(b"xml2-1\n"):
        _abort("Not a serialized xml2 object.")
    rest = blob[len(b"xml2-1\n") :]
    kind, doc_type, xml = rest.decode("utf-8").split("\n", 2)
    return Serialized(kind, xml, doc_type or None)


def _vector(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def url_absolute(x, base: str):
    if not isinstance(base, str):
        _abort("Base URL must be length 1")
    out = []
    for item in _vector(x):
        built = C.lib.xmlBuildURI(C.bytes_of(item), C.bytes_of(base))
        out.append(C.text_of(built, free=True) or "")
    return out[0] if isinstance(x, str) else out


def url_relative(x, base: str):
    if not isinstance(base, str):
        _abort("Base URL must be length 1")
    out = []
    for item in _vector(x):
        built = C.lib.xmlBuildRelativeURI(C.bytes_of(item), C.bytes_of(base))
        out.append(C.text_of(built, free=True) or "")
    return out[0] if isinstance(x, str) else out


def url_escape(x, reserved: str = ""):
    if not isinstance(reserved, str):
        _abort("`reserved` must be character vector of length 1")
    out = []
    for item in _vector(x):
        built = C.lib.xmlURIEscapeStr(C.bytes_of(item), C.bytes_of(reserved))
        out.append(C.text_of(built, free=True) or "")
    return out[0] if isinstance(x, str) else out


def url_unescape(x):
    out = []
    for item in _vector(x):
        built = C.lib.xmlURIUnescapeString(C.bytes_of(item), 0, None)
        if not built:
            out.append(NA)
        else:
            out.append(C.text_of(built, free=True))
    return out[0] if isinstance(x, str) else out


def url_parse(x) -> UrlFrame:
    rows = []
    for item in _vector(x):
        parsed = C.lib.xmlParseURI(C.bytes_of(item))
        row = {
            "scheme": "",
            "server": "",
            "port": NA,
            "user": "",
            "path": "",
            "query": "",
            "fragment": "",
        }
        if parsed:
            view = __import__("ctypes").cast(parsed, __import__("ctypes").POINTER(C.xmlURI)).contents
            row["scheme"] = view.scheme.decode("utf-8") if view.scheme else ""
            row["server"] = view.server.decode("utf-8") if view.server else ""
            row["port"] = NA if view.port == 0 else int(view.port)
            row["user"] = view.user.decode("utf-8") if view.user else ""
            row["path"] = view.path.decode("utf-8") if view.path else ""
            raw = view.query_raw.decode("utf-8") if view.query_raw else ""
            row["query"] = raw
            row["fragment"] = view.fragment.decode("utf-8") if view.fragment else ""
            C.lib.xmlFreeURI(parsed)
        rows.append(row)
    return UrlFrame(rows)


def xml2_example(path: str | None = None) -> str | list[str]:
    folder = Path(__file__).resolve().parent / "extdata"
    if path is None:
        return sorted(item.name for item in folder.iterdir() if item.is_file())
    target = folder / path
    if not target.is_file():
        _abort(f"'{path}' does not exist in the xml2 examples.")
    return str(target)


def download_xml(url, file=None, quiet: bool = True, mode: str = "wb", handle=None):
    """Download `url` into `file`. `handle` is the curl handle xml2 accepts; it is unused."""
    from urllib.parse import urlparse
    from urllib.request import urlopen

    _check_string(url, "url")
    if file is None:
        file = os.path.basename(urlparse(url).path) or "download"
    with urlopen(url) as response:
        payload = response.read()
    binary = "b" in mode
    if binary:
        with open(file, "ab" if "a" in mode else "wb") as handle_out:
            handle_out.write(payload)
    else:
        with open(file, mode) as handle_out:
            handle_out.write(payload.decode("utf-8"))
    return file


def download_html(url, file=None, quiet: bool = True, mode: str = "wb", handle=None):
    return download_xml(url, file=file, quiet=quiet, mode=mode, handle=handle)


def _encode_string(text: str) -> str:
    pieces = []
    for char in text:
        code = ord(char)
        if char == "\\":
            pieces.append("\\\\")
        elif char == "\n":
            pieces.append("\\n")
        elif char == "\r":
            pieces.append("\\r")
        elif char == "\t":
            pieces.append("\\t")
        elif char == "\a":
            pieces.append("\\a")
        elif char == "\b":
            pieces.append("\\b")
        elif char == "\f":
            pieces.append("\\f")
        elif char == "\v":
            pieces.append("\\v")
        elif code < 32 or code == 127:
            pieces.append(f"\\x{code:02x}")
        else:
            pieces.append(char)
    return "".join(pieces)


def _encode_with_width(text: str, width: int) -> str:
    if len(text) > width:
        text = text[: width - 3]
        truncated = True
    else:
        truncated = False
    encoded = _encode_string(text)
    if truncated or len(encoded) > width:
        encoded = encoded[: width - 3] + " ..."
    return encoded


def _format_node(node: XmlNode) -> str:
    if _is_missing(node):
        return "<NA>"
    attrs = xml_attrs(node) or {}
    parts = [xml_name(node)]
    for key, value in attrs.items():
        parts.append(f'{key}="{value}"')
    return "<" + " ".join(parts) + ">"


def _show_nodes(nodes: XmlNodeset, width: int, max_n: int) -> str:
    if len(nodes) == 0:
        return ""
    shown = list(nodes)
    truncated = len(shown) > max_n
    if truncated:
        shown = shown[:max_n]
    labels = [f"[{i}]" for i in range(1, len(shown) + 1)]
    width_label = max(len(label) for label in labels)
    lines = []
    for label, node in zip(labels, shown):
        body = as_character(node) or ""
        lines.append(_encode_with_width(f"{label.rjust(width_label)} {body}", width))
    if truncated:
        lines.append("...")
    return "\n".join(lines)


def _print_node(node: XmlNode) -> str:
    kind = _doc_type(node)
    lines = [f"{{{kind}_node}}", _format_node(node)]
    children = _show_nodes(xml_children(node), options["width"], 20)
    if children:
        lines.append(children)
    return "\n".join(lines)


def _print_document(doc: XmlDocument) -> str:
    kind = _doc_type(doc)
    lines = [f"{{{kind}_document}}", _format_node(doc)]
    children = _show_nodes(xml_children(doc), options["width"], 20)
    if children:
        lines.append(children)
    return "\n".join(lines)


def _print_nodeset(nodes: XmlNodeset) -> str:
    kind = "xml"
    if nodes:
        for node in nodes:
            if not _is_missing(node):
                kind = _doc_type(node)
                break
    lines = [f"{{{kind}_nodeset ({len(nodes)})}}"]
    body = _show_nodes(nodes, options["width"], 20)
    if body:
        lines.append(body)
    return "\n".join(lines)


def _format_frame(rows: list[dict]) -> str:
    columns = ["scheme", "server", "port", "user", "path", "query", "fragment"]

    def cell(row, name) -> str:
        value = row[name]
        if value is NA:
            return "NA" if name == "port" else ""
        return str(value)

    widths = {
        name: max(len(name), *(len(cell(row, name)) for row in rows))
        for name in columns
    }
    row_width = len(str(len(rows)))
    header = " " * row_width + " " + " ".join(name.rjust(widths[name]) for name in columns)
    body = []
    for index, row in enumerate(rows, start=1):
        pieces = [cell(row, name).rjust(widths[name]) for name in columns]
        body.append(str(index).rjust(row_width) + " " + " ".join(pieces))
    return "\n".join([header, *body])
