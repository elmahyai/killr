"""Python translation of the R package XML.

Documents, nodes, and XPath call the system libxml2 through ctypes, the
library the installed package links. A one-line chart is not involved.
The old list-shaped XMLNode tree, SAX handlers, schemas, and DTDs are not
built here. Internal nodes answer the same name, value, attribute, and
XPath questions.
"""

from __future__ import annotations

import ctypes
import os
from typing import Any, Callable

from XML import _libxml as C

RECOVER = 1
NOENT = 2
DTDLOAD = 4
DTDATTR = 8
DTDVALID = 16
NOERROR = 32
NOWARNING = 64
PEDANTIC = 128
NOBLANKS = 256
SAX1 = 512
XINCLUDE = 1024
NONET = 2048
NODICT = 4096
NSCLEAN = 8192
NOCDATA = 16384
NOXINCNODE = 32768
COMPACT = 65536
OLD10 = 131072
NOBASEFIX = 262144
HUGE = 524288
OLDSAX = 1048576

_KIND_NAME = {
    C.XML_TEXT_NODE: "text",
    C.XML_CDATA_SECTION_NODE: "cdata",
    C.XML_COMMENT_NODE: "comment",
    C.XML_PI_NODE: "pi",
}

_FEATURES = (
    "THREAD",
    "TREE",
    "OUTPUT",
    "PUSH",
    "READER",
    "PATTERN",
    "WRITER",
    "SAX1",
    "FTP",
    "HTTP",
    "VALID",
    "HTML",
    "LEGACY",
    "C14N",
    "CATALOG",
    "XPATH",
    "XPTR",
    "XINCLUDE",
    "ICONV",
    "ISO8859X",
    "UNICODE",
    "REGEXP",
    "AUTOMATA",
    "EXPR",
    "SCHEMAS",
    "SCHEMATRON",
    "MODULES",
    "DEBUG",
    "DEBUG_MEM",
    "DEBUG_RUN",
    "ZLIB",
)


class XMLInternalDocument:
    """A libxml2 document. The pointer stays alive while this object does."""

    def __init__(self, ptr, html: bool = False) -> None:
        self.ptr = ptr
        self.html = html

    def __del__(self) -> None:
        ptr = getattr(self, "ptr", None)
        if ptr:
            C.lib.xmlFreeDoc(ptr)
            self.ptr = None


class XMLInternalNode:
    """One node in a document. ``owner`` keeps the document from being freed."""

    def __init__(self, ptr, owner: XMLInternalDocument) -> None:
        self.ptr = ptr
        self.owner = owner

    def _view(self) -> C.xmlNode:
        return C.node_at(self.ptr)


class URI(dict):
    """The eight fields R's parseURI returns. Port 0 is missing."""


def libxmlVersion(run_time: bool = False) -> dict[str, str]:
    """Major, minor, and patch of the libxml2 this package calls."""
    del run_time
    digits = C.parser_version()
    return {
        "major": digits[0],
        "minor": digits[1:3],
        "patch": digits[3:5],
    }


def supportsLibxml() -> bool:
    """This build of the R package is linked to libxml2."""
    return True


def supportsExpat() -> bool:
    """This build of the R package was configured without expat."""
    return False


def libxmlFeatures() -> dict[str, bool]:
    """Which libxml2 features this library was built with."""
    return {name: bool(C.lib.xmlHasFeature(index)) for index, name in enumerate(_FEATURES, start=1)}


def _read(text: str, html: bool) -> XMLInternalDocument:
    raw = text.encode("utf-8")
    if html:
        flags = C.HTML_PARSE_RECOVER | C.HTML_PARSE_NOERROR | C.HTML_PARSE_NOWARNING
        ptr = C.lib.htmlReadMemory(raw, len(raw), b"", None, flags)
    else:
        ptr = C.lib.xmlReadMemory(raw, len(raw), b"", None, C.XML_PARSE_NOBLANKS)
    if not ptr:
        raise ValueError("XML parse failed")
    return XMLInternalDocument(ptr, html=html)


def _prepare(file: Any, as_text: bool) -> str:
    if isinstance(file, (list, tuple)):
        file = "\n".join(str(part) for part in file)
        as_text = True
    text = str(file)
    if as_text or "<" in text:
        return text
    with open(text, encoding="utf-8") as handle:
        return handle.read()


def xmlParse(file: Any, as_text: bool = False, **_unused: Any) -> XMLInternalDocument:
    """Parse XML into an internal document. A string that contains < is markup."""
    del _unused
    return _read(_prepare(file, as_text), html=False)


def xmlInternalTreeParse(file: Any, as_text: bool = False, use_internal_nodes: bool = True, **_unused: Any) -> XMLInternalDocument:
    """The internal-node parser. ``use_internal_nodes`` stays the document libxml2 built."""
    del use_internal_nodes, _unused
    return xmlParse(file, as_text=as_text)


xmlNativeTreeParse = xmlInternalTreeParse


def xmlTreeParse(file: Any, as_text: bool = False, use_internal_nodes: bool = False, **_unused: Any) -> XMLInternalDocument:
    """Parse a document. The accessors are the internal-node ones either way."""
    del use_internal_nodes, _unused
    return xmlParse(file, as_text=as_text)


def htmlParse(file: Any, as_text: bool = False, **_unused: Any) -> XMLInternalDocument:
    """Parse HTML with libxml2 recovery."""
    del _unused
    return _read(_prepare(file, as_text), html=True)


htmlTreeParse = htmlParse


def _root_ptr(doc: XMLInternalDocument):
    return C.lib.xmlDocGetRootElement(doc.ptr)


def xmlRoot(doc: Any) -> XMLInternalNode:
    """The document element. A node yields the document element of its owner."""
    if isinstance(doc, XMLInternalNode):
        doc = doc.owner
    ptr = _root_ptr(doc)
    if not ptr:
        raise ValueError("document has no root")
    return XMLInternalNode(ptr, doc)


def _kind(node: XMLInternalNode) -> int:
    return int(node._view().type)


def xmlName(node: XMLInternalNode) -> str:
    """The element tag, or text, cdata, comment, or pi for the other node kinds."""
    kind = _kind(node)
    if kind in _KIND_NAME:
        return _KIND_NAME[kind]
    raw = node._view().name
    return raw.decode("utf-8") if raw else ""


def xmlValue(node: XMLInternalNode) -> str:
    """Descendant text, the way xmlNodeGetContent concatenates it."""
    return C.text_of(C.lib.xmlNodeGetContent(node.ptr), free=True) or ""


def xmlAttrs(node: XMLInternalNode) -> dict[str, str]:
    """Attributes in document order."""
    attrs: dict[str, str] = {}
    prop = node._view().properties
    while prop:
        item = prop.contents
        name = item.name.decode("utf-8") if item.name else ""
        value = ""
        child = item.children
        if child:
            content = child.contents.content
            value = content.decode("utf-8") if content else ""
        attrs[name] = value
        prop = item.next
    return attrs


def xmlGetAttr(node: XMLInternalNode, name: str, default: Any = None) -> Any:
    """One attribute, or ``default`` when it is absent."""
    attrs = xmlAttrs(node)
    if name in attrs:
        return attrs[name]
    return default


def _address(pointer) -> int | None:
    if not pointer:
        return None
    return ctypes.cast(pointer, C.c_void).value


def _child_ptrs(node: XMLInternalNode) -> list:
    child = node._view().children
    found = []
    while child:
        found.append(_address(child))
        child = child.contents.next
    return found


def xmlChildren(node: XMLInternalNode) -> list[XMLInternalNode]:
    """Child nodes, including text nodes. Blank text was dropped at parse time."""
    return [XMLInternalNode(ptr, node.owner) for ptr in _child_ptrs(node) if ptr]


def xmlSize(node: XMLInternalNode) -> int:
    """How many children the node has."""
    return len(xmlChildren(node))


def xml_node_names(node: XMLInternalNode) -> list[str]:
    """Names of the children. A text child is named text."""
    return [xmlName(child) for child in xmlChildren(node)]


def _owner_doc(node: Any) -> XMLInternalDocument:
    if isinstance(node, XMLInternalDocument):
        return node
    return node.owner


def getNodeSet(doc: Any, path: str) -> list[XMLInternalNode]:
    """Nodes an XPath expression selects. An attribute's value is xmlValue."""
    owner = _owner_doc(doc)
    context = C.lib.xmlXPathNewContext(owner.ptr)
    if not context:
        raise ValueError("XPath context failed")
    try:
        if isinstance(doc, XMLInternalNode):
            head = ctypes.cast(context, ctypes.POINTER(_XPathHead))
            head.contents.node = doc.ptr
        found = C.lib.xmlXPathEval(path.encode("utf-8"), context)
        if not found:
            return []
        try:
            view = ctypes.cast(found, ctypes.POINTER(C.xmlXPathObject)).contents
            if view.type != C.XPATH_NODESET or not view.nodesetval:
                return []
            nodeset = view.nodesetval.contents
            return [XMLInternalNode(nodeset.nodeTab[i], owner) for i in range(nodeset.nodeNr) if nodeset.nodeTab[i]]
        finally:
            C.lib.xmlXPathFreeObject(found)
    finally:
        C.lib.xmlXPathFreeContext(context)


def xpathApply(doc: Any, path: str, fun: Callable[..., Any] = xmlValue) -> list[Any]:
    """Apply ``fun`` to each node the path selects."""
    return [fun(node) for node in getNodeSet(doc, path)]


def xpathSApply(doc: Any, path: str, fun: Callable[..., Any] = xmlValue) -> list[Any]:
    """The same application. A character result is the simplified form R prints."""
    return xpathApply(doc, path, fun)


def xmlElementsByTagName(node: XMLInternalNode, name: str, recursive: bool = False) -> list[XMLInternalNode]:
    """Element children with this tag. ``recursive`` walks descendants."""
    found: list[XMLInternalNode] = []
    for child in xmlChildren(node):
        if _kind(child) == C.XML_ELEMENT_NODE and xmlName(child) == name:
            found.append(child)
        if recursive and _kind(child) == C.XML_ELEMENT_NODE:
            found.extend(xmlElementsByTagName(child, name, True))
    return found


class _XPathHead(ctypes.Structure):
    _fields_ = [("doc", C.c_void), ("node", C.c_void)]


def _dump_doc(doc: XMLInternalDocument) -> str:
    mem = C.c_char_p()
    size = C.c_int()
    if doc.html:
        C.lib.htmlDocDumpMemory(doc.ptr, ctypes.byref(mem), ctypes.byref(size))
    else:
        C.lib.xmlDocDumpFormatMemoryEnc(doc.ptr, ctypes.byref(mem), ctypes.byref(size), None, 1)
    raw = mem.value or b""
    text = raw.decode("utf-8")
    if mem:
        C.xml_free(mem)
    return text


def _dump_node(node: XMLInternalNode) -> str:
    buffer = C.lib.xmlBufferCreate()
    try:
        C.lib.xmlNodeDump(buffer, node.owner.ptr, node.ptr, 0, 0)
        raw = C.lib.xmlBufferContent(buffer) or b""
        return raw.decode("utf-8")
    finally:
        C.lib.xmlBufferFree(buffer)


def saveXML(node: Any) -> str:
    """Serialize a document with indentation, or one node without a declaration."""
    if isinstance(node, XMLInternalDocument):
        return _dump_doc(node)
    return _dump_node(node)


def toString_XMLNode(node: XMLInternalNode) -> str:
    """The node serialization saveXML returns."""
    return saveXML(node)


def _fresh(name: str | None = None) -> tuple[XMLInternalDocument, Any]:
    ptr = C.lib.xmlNewDoc(b"1.0")
    doc = XMLInternalDocument(ptr)
    return doc, ptr


def _node(ptr, doc: XMLInternalDocument) -> XMLInternalNode:
    return XMLInternalNode(ptr, doc)


def newXMLDoc() -> XMLInternalDocument:
    """An empty document with version 1.0."""
    doc, _ptr = _fresh()
    return doc


def newHTMLDoc() -> XMLInternalDocument:
    """An HTML document with the HTML 4 loose doctype and an empty head and body."""
    skeleton = (
        '<!DOCTYPE html SYSTEM "http://www.w3.org/TR/html4/loose.dtd">'
        "<html><head></head><body></body></html>"
    )
    return htmlParse(skeleton, as_text=True)


def newXMLTextNode(text: str, doc: XMLInternalDocument | None = None) -> XMLInternalNode:
    """A text node. A missing document gets a fresh one so the node can be saved."""
    owner = doc or newXMLDoc()
    ptr = C.lib.xmlNewText(text.encode("utf-8"))
    return _node(ptr, owner)


def newXMLCommentNode(text: str, doc: XMLInternalDocument | None = None) -> XMLInternalNode:
    """A comment node."""
    owner = doc or newXMLDoc()
    ptr = C.lib.xmlNewComment(text.encode("utf-8"))
    return _node(ptr, owner)


def newXMLCDataNode(text: str, doc: XMLInternalDocument | None = None) -> XMLInternalNode:
    """A CDATA node."""
    owner = doc or newXMLDoc()
    raw = text.encode("utf-8")
    ptr = C.lib.xmlNewCDataBlock(owner.ptr, raw, len(raw))
    return _node(ptr, owner)


def addAttributes(node: XMLInternalNode, attrs: dict[str, str] | None = None, **more: str) -> XMLInternalNode:
    """Set attributes on an element."""
    values = dict(attrs or {})
    values.update(more)
    for name, value in values.items():
        C.lib.xmlSetProp(node.ptr, str(name).encode("utf-8"), str(value).encode("utf-8"))
    return node


def addChildren(node: XMLInternalNode, *children: Any) -> XMLInternalNode:
    """Append text and nodes. A node from another document is copied, so freeing that document cannot free this child."""
    for child in children:
        if isinstance(child, XMLInternalNode):
            if child.owner is node.owner:
                C.lib.xmlAddChild(node.ptr, child.ptr)
            else:
                copied = C.lib.xmlDocCopyNode(child.ptr, node.owner.ptr, 1)
                C.lib.xmlAddChild(node.ptr, copied)
        else:
            text = C.lib.xmlNewText(str(child).encode("utf-8"))
            C.lib.xmlAddChild(node.ptr, text)
    return node


def newXMLNode(
    name: str,
    *content: Any,
    attrs: dict[str, str] | None = None,
    parent: XMLInternalNode | None = None,
    doc: XMLInternalDocument | None = None,
) -> XMLInternalNode:
    """An element. Strings become text children. A node without a parent is the document root."""
    owner = doc or (parent.owner if parent is not None else newXMLDoc())
    ptr = C.lib.xmlNewNode(None, name.encode("utf-8"))
    node = _node(ptr, owner)
    if attrs:
        addAttributes(node, attrs)
    if content:
        addChildren(node, *content)
    if parent is not None:
        C.lib.xmlAddChild(parent.ptr, ptr)
    elif C.lib.xmlDocGetRootElement(owner.ptr) is None and _kind(node) == C.XML_ELEMENT_NODE:
        C.lib.xmlDocSetRootElement(owner.ptr, ptr)
    return node


def xmlApply(node: XMLInternalNode, fun: Callable[..., Any]) -> list[Any]:
    """Apply ``fun`` to each child."""
    return [fun(child) for child in xmlChildren(node)]


def xmlSApply(node: XMLInternalNode, fun: Callable[..., Any]) -> list[Any]:
    """The simplified apply. Names and values are the list R prints as a vector."""
    return xmlApply(node, fun)


def getChildrenStrings(node: XMLInternalNode) -> list[str]:
    """xmlValue of each child."""
    return [xmlValue(child) for child in xmlChildren(node)]


def xmlParent(node: XMLInternalNode) -> XMLInternalNode | None:
    """The element parent. The document node is not an element."""
    parent = node._view().parent
    if not parent:
        return None
    if int(parent.contents.type) != C.XML_ELEMENT_NODE:
        return None
    address = _address(parent)
    if address is None:
        return None
    return XMLInternalNode(address, node.owner)


def xmlAncestors(node: XMLInternalNode) -> list[XMLInternalNode]:
    """The element chain from the document element down to this node."""
    chain = [node]
    current = xmlParent(node)
    while current is not None:
        chain.append(current)
        current = xmlParent(current)
    chain.reverse()
    return chain


def getLineNumber(node: XMLInternalNode) -> int:
    """The line libxml2 recorded for the node."""
    return int(node._view().line)


def docName(doc: Any) -> str | None:
    """The document URL. A string parsed in memory has none."""
    owner = _owner_doc(doc)
    url = C.doc_at(owner.ptr).URL
    if not url:
        return None
    return url.decode("utf-8")


def getEncoding(doc: Any) -> str | None:
    """The encoding libxml2 stored. UTF-8 input often leaves it empty."""
    owner = _owner_doc(doc)
    encoding = C.doc_at(owner.ptr).encoding
    if not encoding:
        return None
    return encoding.decode("utf-8")


def xmlNamespace(node: XMLInternalNode) -> dict[str, str]:
    """The namespace as a named value: the prefix names the URI."""
    ns = node._view().ns
    if not ns:
        return {}
    item = ns.contents
    prefix = item.prefix.decode("utf-8") if item.prefix else ""
    href = item.href.decode("utf-8") if item.href else ""
    return {prefix: href}


def getHTMLLinks(doc: Any, external_only: bool = True, xp_query: str = "//a/@href") -> list[str]:
    """href values of the anchors. A leading # is dropped when external_only is true."""
    if isinstance(doc, str):
        doc = htmlParse(doc, as_text=True)
    links = [xmlValue(node) for node in getNodeSet(doc, xp_query)]
    if external_only:
        links = [link for link in links if not link.startswith("#")]
    return links


def parseURI(uri: str) -> URI:
    """scheme, authority, server, user, path, query, fragment, and port."""
    if uri is None:
        raise ValueError("cannot parse URI")
    parsed = C.lib.xmlParseURI(str(uri).encode("utf-8"))
    if not parsed:
        raise ValueError(f"cannot parse URI {uri}")
    try:
        item = parsed.contents
        port = int(item.port)
        return URI(
            scheme=_field(item.scheme),
            authority=_field(item.authority),
            server=_field(item.server),
            user=_field(item.user),
            path=_field(item.path),
            query=_field(item.query),
            fragment=_field(item.fragment),
            port=None if port == 0 else port,
        )
    finally:
        C.lib.xmlFreeURI(parsed)


def _field(raw) -> str:
    if not raw:
        return ""
    return raw.decode("utf-8")


def _simplify_path(path: str) -> str:
    elements = [part for part in path.split("/") if part != "."]
    go_on = True
    while go_on and ".." in elements:
        index = elements.index("..")
        position = index + 1
        if position == 1:
            break
        if all(part == ".." for part in elements[:position]):
            break
        if position == 2 and elements[0] == "..":
            break
        del elements[index - 1 : index + 1]
    return "/".join(elements)


def _uri_character(uri: URI) -> str:
    query = f"?{uri['query']}" if uri["query"] else ""
    fragment = f"#{uri['fragment']}" if uri["fragment"] else ""
    if uri["scheme"] == "":
        return f"{uri['path']}{query}{fragment}"
    user = uri["user"]
    at = "@" if user else ""
    port = f":{int(uri['port'])}" if uri["port"] is not None else ""
    return f"{uri['scheme']}://{user}{at}{uri['server']}{port}{uri['path']}{query}{fragment}"


def getRelativeURL(u: str, base_url: str, sep: str = "/", add_base: bool = True, simplify: bool = True) -> str:
    """Resolve a relative URL against a base. An absolute URL is returned unchanged."""
    parsed = parseURI(u)
    if parsed["scheme"] == "" and add_base:
        base = parseURI(base_url)
        base["query"] = ""
        if parsed["path"].startswith("/"):
            base["path"] = u
            return _uri_character(base)
        ends = base["path"].endswith("/")
        relative = u[2:] if ends and u.startswith("./") else u
        directory = base["path"] if ends else os.path.dirname(base["path"])
        joiner = "" if ends else sep
        base["path"] = f"{directory}{joiner}{relative}"
        if simplify and ".." in base["path"]:
            base["path"] = _simplify_path(base["path"])
        return _uri_character(base)
    return u


# R's names.XMLNode is this child-name vector.
names_XMLNode = xml_node_names
from XML.append_xmlNode import append_xmlNode
from XML.append_XMLNode import append_XMLNode
from XML.Doctype import Doctype
from XML.asXMLNode import asXMLNode
from XML.comment_SAX import comment_SAX
from XML.endElement_SAX import endElement_SAX
