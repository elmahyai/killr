"""Calls the system libxml2 that the installed R package xml2 links."""

from __future__ import annotations

import ctypes
import ctypes.util
from typing import Callable


def _load() -> ctypes.CDLL:
    path = ctypes.util.find_library("xml2")
    if not path:
        raise OSError("libxml2 was not found. xml2 needs the same library R uses.")
    lib = ctypes.CDLL(path)
    lib.xmlInitParser()
    return lib


lib = _load()

c_void = ctypes.c_void_p
c_char_p = ctypes.c_char_p
c_int = ctypes.c_int
c_long = ctypes.c_long
c_double = ctypes.c_double


class xmlNs(ctypes.Structure):
    pass


class xmlNode(ctypes.Structure):
    pass


class xmlAttr(ctypes.Structure):
    pass


xmlNs._fields_ = [
    ("next", ctypes.POINTER(xmlNs)),
    ("type", c_int),
    ("href", c_char_p),
    ("prefix", c_char_p),
    ("_private", c_void),
    ("context", c_void),
]

xmlNode._fields_ = [
    ("_private", c_void),
    ("type", c_int),
    ("name", c_char_p),
    ("children", ctypes.POINTER(xmlNode)),
    ("last", ctypes.POINTER(xmlNode)),
    ("parent", ctypes.POINTER(xmlNode)),
    ("next", ctypes.POINTER(xmlNode)),
    ("prev", ctypes.POINTER(xmlNode)),
    ("doc", c_void),
    ("ns", ctypes.POINTER(xmlNs)),
    ("content", c_char_p),
    ("properties", ctypes.POINTER(xmlAttr)),
    ("nsDef", ctypes.POINTER(xmlNs)),
    ("psvi", c_void),
    ("line", ctypes.c_ushort),
    ("extra", ctypes.c_ushort),
]

xmlAttr._fields_ = [
    ("_private", c_void),
    ("type", c_int),
    ("name", c_char_p),
    ("children", ctypes.POINTER(xmlNode)),
    ("last", ctypes.POINTER(xmlNode)),
    ("parent", ctypes.POINTER(xmlNode)),
    ("next", ctypes.POINTER(xmlAttr)),
    ("prev", ctypes.POINTER(xmlAttr)),
    ("doc", c_void),
    ("ns", ctypes.POINTER(xmlNs)),
]


class xmlDoc(ctypes.Structure):
    _fields_ = [
        ("_private", c_void),
        ("type", c_int),
        ("name", c_char_p),
        ("children", c_void),
        ("last", c_void),
        ("parent", c_void),
        ("next", c_void),
        ("prev", c_void),
        ("doc", c_void),
        ("compression", c_int),
        ("standalone", c_int),
        ("intSubset", c_void),
        ("extSubset", c_void),
        ("oldNs", c_void),
        ("version", c_char_p),
        ("encoding", c_char_p),
        ("ids", c_void),
        ("refs", c_void),
        ("URL", c_char_p),
        ("charset", c_int),
        ("dict", c_void),
        ("psvi", c_void),
        ("parseFlags", c_int),
        ("properties", c_int),
    ]


class xmlNodeSet(ctypes.Structure):
    _fields_ = [
        ("nodeNr", c_int),
        ("nodeMax", c_int),
        ("nodeTab", ctypes.POINTER(c_void)),
    ]


class xmlXPathObject(ctypes.Structure):
    _fields_ = [
        ("type", c_int),
        ("nodesetval", ctypes.POINTER(xmlNodeSet)),
        ("boolval", c_int),
        ("floatval", c_double),
        ("stringval", c_void),
    ]


class xmlXPathContextHead(ctypes.Structure):
    _fields_ = [
        ("doc", c_void),
        ("node", c_void),
    ]


class xmlURI(ctypes.Structure):
    _fields_ = [
        ("scheme", c_char_p),
        ("opaque", c_char_p),
        ("authority", c_char_p),
        ("server", c_char_p),
        ("user", c_char_p),
        ("port", c_int),
        ("path", c_char_p),
        ("query", c_char_p),
        ("fragment", c_char_p),
        ("cleanup", c_int),
        ("query_raw", c_char_p),
    ]


class xmlError(ctypes.Structure):
    _fields_ = [
        ("domain", c_int),
        ("code", c_int),
        ("message", c_char_p),
    ]


XML_ELEMENT_NODE = 1
XML_ATTRIBUTE_NODE = 2
XML_TEXT_NODE = 3
XML_CDATA_SECTION_NODE = 4
XML_ENTITY_REF_NODE = 5
XML_ENTITY_NODE = 6
XML_PI_NODE = 7
XML_COMMENT_NODE = 8
XML_DOCUMENT_NODE = 9
XML_DOCUMENT_TYPE_NODE = 10
XML_DOCUMENT_FRAG_NODE = 11
XML_NOTATION_NODE = 12
XML_HTML_DOCUMENT_NODE = 13
XML_DTD_NODE = 14
XML_ELEMENT_DECL = 15
XML_ATTRIBUTE_DECL = 16
XML_ENTITY_DECL = 17
XML_NAMESPACE_DECL = 18
XML_XINCLUDE_START = 19
XML_XINCLUDE_END = 20
XML_DOCB_DOCUMENT_NODE = 21

XML_DOC_HTML = 1 << 7

ELEMENT_TYPES = {
    1: "element",
    2: "attribute",
    3: "text",
    4: "cdata",
    5: "entity_ref",
    6: "entity",
    7: "pi",
    8: "comment",
    9: "document",
    10: "document_type",
    11: "document_frag",
    12: "notation",
    13: "html_document",
    14: "dtd",
    15: "element_decl",
    16: "attribute_decl",
    17: "entity_decl",
    18: "namespace_decl",
    19: "xinclude_start",
    20: "xinclude_end",
    21: "docb_document",
}

PARSE_OPTIONS = {
    "RECOVER": 1 << 0,
    "NOENT": 1 << 1,
    "DTDLOAD": 1 << 2,
    "DTDATTR": 1 << 3,
    "DTDVALID": 1 << 4,
    "NOERROR": 1 << 5,
    "NOWARNING": 1 << 6,
    "PEDANTIC": 1 << 7,
    "NOBLANKS": 1 << 8,
    "SAX1": 1 << 9,
    "XINCLUDE": 1 << 10,
    "NONET": 1 << 11,
    "NODICT": 1 << 12,
    "NSCLEAN": 1 << 13,
    "NOCDATA": 1 << 14,
    "NOXINCNODE": 1 << 15,
    "COMPACT": 1 << 16,
    "OLD10": 1 << 17,
    "NOBASEFIX": 1 << 18,
    "HUGE": 1 << 19,
    "OLDSAX": 1 << 20,
    "IGNORE_ENC": 1 << 21,
    "BIG_LINES": 1 << 22,
}

SAVE_OPTIONS = {
    "format": 1 << 0,
    "no_declaration": 1 << 1,
    "no_empty_tags": 1 << 2,
    "no_xhtml": 1 << 3,
    "require_xhtml": 1 << 4,
    "as_xml": 1 << 5,
    "as_html": 1 << 6,
    "format_whitespace": 1 << 7,
}

XPATH_NODESET = 1
XPATH_BOOLEAN = 2
XPATH_NUMBER = 3
XPATH_STRING = 4


def _sig(name: str, restype, argtypes: list) -> None:
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = argtypes


_sig("xmlReadMemory", c_void, [c_char_p, c_int, c_char_p, c_char_p, c_int])
_sig("xmlReadFile", c_void, [c_char_p, c_char_p, c_int])
_sig("htmlReadMemory", c_void, [c_char_p, c_int, c_char_p, c_char_p, c_int])
_sig("htmlReadFile", c_void, [c_char_p, c_char_p, c_int])
_sig("xmlFreeDoc", None, [c_void])
_sig("xmlFreeNs", None, [c_void])
# xmlFree is a function pointer in the libxml2 data section, not a function.
xml_free = ctypes.CFUNCTYPE(None, c_void).in_dll(lib, "xmlFree")
_sig("xmlDocGetRootElement", c_void, [c_void])
_sig("xmlDocSetRootElement", c_void, [c_void, c_void])
_sig("xmlNewDoc", c_void, [c_char_p])
_sig("xmlParseCharEncoding", c_int, [c_char_p])
_sig("xmlGetCharEncodingName", c_char_p, [c_int])
_sig("xmlStrdup", c_void, [c_char_p])
_sig("xmlNewNode", c_void, [c_void, c_char_p])
_sig("xmlNewTextLen", c_void, [c_char_p, c_int])
_sig("xmlNewCDataBlock", c_void, [c_void, c_char_p, c_int])
_sig("xmlNewComment", c_void, [c_char_p])
_sig("xmlNewDtd", c_void, [c_void, c_char_p, c_char_p, c_char_p])
_sig("xmlNewNs", c_void, [c_void, c_char_p, c_char_p])
_sig("xmlCopyNode", c_void, [c_void, c_int])
_sig("xmlAddChild", c_void, [c_void, c_void])
_sig("xmlAddPrevSibling", c_void, [c_void, c_void])
_sig("xmlAddNextSibling", c_void, [c_void, c_void])
_sig("xmlReplaceNode", c_void, [c_void, c_void])
_sig("xmlUnlinkNode", None, [c_void])
_sig("xmlFreeNode", None, [c_void])
_sig("xmlNodeGetContent", c_void, [c_void])
_sig("xmlNodeSetContentLen", None, [c_void, c_char_p, c_int])
_sig("xmlNodeAddContentLen", None, [c_void, c_char_p, c_int])
_sig("xmlNodeSetName", None, [c_void, c_char_p])
_sig("xmlGetNodePath", c_void, [c_void])
_sig("xmlGetProp", c_void, [c_void, c_char_p])
_sig("xmlGetNoNsProp", c_void, [c_void, c_char_p])
_sig("xmlGetNsProp", c_void, [c_void, c_char_p, c_char_p])
_sig("xmlSetProp", c_void, [c_void, c_char_p, c_char_p])
_sig("xmlSetNsProp", c_void, [c_void, c_void, c_char_p, c_char_p])
_sig("xmlUnsetProp", c_int, [c_void, c_char_p])
_sig("xmlUnsetNsProp", c_int, [c_void, c_void, c_char_p])
_sig("xmlSearchNs", c_void, [c_void, c_void, c_char_p])
_sig("xmlSearchNsByHref", c_void, [c_void, c_void, c_char_p])
_sig("xmlSetNs", None, [c_void, c_void])
_sig("xmlXPathNewContext", c_void, [c_void])
_sig("xmlXPathFreeContext", None, [c_void])
_sig("xmlXPathEval", c_void, [c_char_p, c_void])
_sig("xmlXPathFreeObject", None, [c_void])
_sig("xmlXPathRegisterNs", c_int, [c_void, c_char_p, c_char_p])
_sig("xmlBufferCreate", c_void, [])
_sig("xmlBufferFree", None, [c_void])
_sig("xmlBufferContent", c_char_p, [c_void])
_sig("xmlSaveToBuffer", c_void, [c_void, c_char_p, c_int])
_sig("xmlSaveToFilename", c_void, [c_char_p, c_char_p, c_int])
_sig("xmlSaveDoc", c_long, [c_void, c_void])
_sig("xmlSaveTree", c_long, [c_void, c_void])
_sig("xmlSaveClose", c_int, [c_void])
_sig("xmlSchemaNewDocParserCtxt", c_void, [c_void])
_sig("xmlSchemaParse", c_void, [c_void])
_sig("xmlSchemaNewValidCtxt", c_void, [c_void])
_sig("xmlSchemaValidateDoc", c_int, [c_void, c_void])
_sig("xmlSchemaFreeParserCtxt", None, [c_void])
_sig("xmlSchemaFreeValidCtxt", None, [c_void])
_sig("xmlSchemaFree", None, [c_void])
_sig("xmlSchemaSetParserStructuredErrors", None, [c_void, c_void, c_void])
_sig("xmlSchemaSetValidStructuredErrors", None, [c_void, c_void, c_void])
_sig("xmlBuildURI", c_void, [c_char_p, c_char_p])
_sig("xmlBuildRelativeURI", c_void, [c_char_p, c_char_p])
_sig("xmlParseURI", c_void, [c_char_p])
_sig("xmlFreeURI", None, [c_void])
_sig("xmlURIEscapeStr", c_void, [c_char_p, c_char_p])
_sig("xmlURIUnescapeString", c_void, [c_char_p, c_int, c_char_p])

StructuredError = ctypes.CFUNCTYPE(None, c_void, ctypes.POINTER(xmlError))


def bytes_of(text: str | None) -> bytes | None:
    if text is None:
        return None
    return text.encode("utf-8")


def text_of(ptr, free: bool = False) -> str | None:
    if not ptr:
        return None
    raw = ctypes.cast(ptr, c_char_p).value
    value = raw.decode("utf-8") if raw is not None else None
    if free:
        xml_free(ptr)
    return value


def node_view(ptr) -> xmlNode:
    return ctypes.cast(ptr, ctypes.POINTER(xmlNode)).contents


def ns_view(ptr) -> xmlNs:
    return ctypes.cast(ptr, ctypes.POINTER(xmlNs)).contents


def attr_view(ptr) -> xmlAttr:
    return ctypes.cast(ptr, ctypes.POINTER(xmlAttr)).contents


def doc_view(ptr) -> xmlDoc:
    return ctypes.cast(ptr, ctypes.POINTER(xmlDoc)).contents


def ptr_value(pointer) -> int | None:
    if not pointer:
        return None
    return ctypes.cast(pointer, c_void).value


def decode_field(raw: bytes | None) -> str | None:
    if raw is None:
        return None
    return raw.decode("utf-8")


def save_character(target, encoding: str, options: int, tree: bool) -> str:
    buffer = lib.xmlBufferCreate()
    if not buffer:
        raise RuntimeError("Error writing to buffer")
    ctx = lib.xmlSaveToBuffer(buffer, bytes_of(encoding), options)
    if tree:
        lib.xmlSaveTree(ctx, target)
    else:
        lib.xmlSaveDoc(ctx, target)
    if lib.xmlSaveClose(ctx) == -1:
        lib.xmlBufferFree(buffer)
        raise RuntimeError("Error writing to buffer")
    raw = lib.xmlBufferContent(buffer)
    text = raw.decode("utf-8") if raw else ""
    lib.xmlBufferFree(buffer)
    return text


def save_file(target, path: str, encoding: str, options: int, tree: bool) -> None:
    ctx = lib.xmlSaveToFilename(bytes_of(path), bytes_of(encoding), options)
    if not ctx:
        raise RuntimeError("Error closing file")
    if tree:
        lib.xmlSaveTree(ctx, target)
    else:
        lib.xmlSaveDoc(ctx, target)
    if lib.xmlSaveClose(ctx) == -1:
        raise RuntimeError("Error closing file")


def read_memory(payload: bytes, url: str, encoding: str, as_html: bool, options: int):
    url_b = bytes_of(url) if url else None
    enc_b = bytes_of(encoding) if encoding else None
    reader = lib.htmlReadMemory if as_html else lib.xmlReadMemory
    return reader(payload, len(payload), url_b, enc_b, options)


def read_file(path: str, encoding: str, as_html: bool, options: int):
    enc_b = bytes_of(encoding) if encoding else None
    reader = lib.htmlReadFile if as_html else lib.xmlReadFile
    return reader(bytes_of(path), enc_b, options)


def walk_subtree(tree, visit: Callable) -> None:
    """Depth-first walk used by xml2's namespace add and remove."""
    node = tree
    while node:
        view = node_view(node)
        visit(node, view)
        children = ptr_value(view.children)
        nxt = ptr_value(view.next)
        parent = ptr_value(view.parent)
        kind = view.type
        if children and kind != XML_ENTITY_REF_NODE:
            node = children
        elif node != tree and nxt:
            node = nxt
        elif node != tree:
            while node != tree:
                view = node_view(node)
                parent = ptr_value(view.parent)
                if parent:
                    node = parent
                view = node_view(node)
                nxt = ptr_value(view.next)
                if node != tree and nxt:
                    node = nxt
                    break
                if ptr_value(node_view(node).parent) is None:
                    node = None
                    break
            if node == tree:
                node = None
        else:
            break
