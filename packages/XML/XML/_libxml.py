"""Calls the system libxml2 that the installed R package XML links.

xmlFree is a pointer in the data section. A newer libxml2 bundled in a wheel
does not match this parser.
"""

from __future__ import annotations

import ctypes
import ctypes.util

c_void = ctypes.c_void_p
c_char_p = ctypes.c_char_p
c_int = ctypes.c_int


def _load() -> ctypes.CDLL:
    path = ctypes.util.find_library("xml2")
    if not path:
        raise OSError("libxml2 was not found. XML needs the same library R uses.")
    lib = ctypes.CDLL(path)
    lib.xmlInitParser()
    return lib


lib = _load()


class xmlNode(ctypes.Structure):
    pass


class xmlNs(ctypes.Structure):
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
        ("floatval", ctypes.c_double),
        ("stringval", c_void),
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


XML_ELEMENT_NODE = 1
XML_TEXT_NODE = 3
XML_CDATA_SECTION_NODE = 4
XML_PI_NODE = 7
XML_COMMENT_NODE = 8
XML_DOCUMENT_NODE = 9
XML_HTML_DOCUMENT_NODE = 13
XPATH_NODESET = 1

XML_PARSE_NOBLANKS = 256
HTML_PARSE_RECOVER = 1
HTML_PARSE_NOERROR = 32
HTML_PARSE_NOWARNING = 64


def _sig(name: str, restype, argtypes: list) -> None:
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = argtypes


_sig("xmlReadMemory", c_void, [c_char_p, c_int, c_char_p, c_char_p, c_int])
_sig("htmlReadMemory", c_void, [c_char_p, c_int, c_char_p, c_char_p, c_int])
_sig("xmlFreeDoc", None, [c_void])
_sig("xmlDocGetRootElement", c_void, [c_void])
_sig("xmlDocSetRootElement", c_void, [c_void, c_void])
_sig("xmlNewDoc", c_void, [c_char_p])
_sig("xmlNewNode", c_void, [c_void, c_char_p])
_sig("xmlNewText", c_void, [c_char_p])
_sig("xmlNewCDataBlock", c_void, [c_void, c_char_p, c_int])
_sig("xmlNewComment", c_void, [c_char_p])
_sig("xmlAddChild", c_void, [c_void, c_void])
_sig("xmlDocCopyNode", c_void, [c_void, c_void, c_int])
_sig("xmlSetProp", c_void, [c_void, c_char_p, c_char_p])
_sig("xmlNodeGetContent", c_void, [c_void])
_sig("xmlXPathNewContext", c_void, [c_void])
_sig("xmlXPathFreeContext", None, [c_void])
_sig("xmlXPathEval", c_void, [c_char_p, c_void])
_sig("xmlXPathFreeObject", None, [c_void])
_sig("xmlDocDumpFormatMemoryEnc", None, [c_void, ctypes.POINTER(c_char_p), ctypes.POINTER(c_int), c_char_p, c_int])
_sig("htmlDocDumpMemory", None, [c_void, ctypes.POINTER(c_char_p), ctypes.POINTER(c_int)])
_sig("xmlBufferCreate", c_void, [])
_sig("xmlBufferFree", None, [c_void])
_sig("xmlBufferContent", c_char_p, [c_void])
_sig("xmlNodeDump", c_int, [c_void, c_void, c_void, c_int, c_int])
_sig("xmlParseURI", ctypes.POINTER(xmlURI), [c_char_p])
_sig("xmlFreeURI", None, [ctypes.POINTER(xmlURI)])
_sig("xmlHasFeature", c_int, [c_int])

xml_free = ctypes.CFUNCTYPE(None, c_void).in_dll(lib, "xmlFree")


def text_of(ptr, free: bool = False) -> str | None:
    if not ptr:
        return None
    raw = ctypes.cast(ptr, c_char_p).value
    value = raw.decode("utf-8") if raw is not None else None
    if free:
        xml_free(ptr)
    return value


def node_at(ptr) -> xmlNode:
    return ctypes.cast(ptr, ctypes.POINTER(xmlNode)).contents


def doc_at(ptr) -> xmlDoc:
    return ctypes.cast(ptr, ctypes.POINTER(xmlDoc)).contents


def parser_version() -> str:
    pointer = ctypes.c_char_p.in_dll(lib, "xmlParserVersion")
    raw = pointer.value
    return raw.decode("ascii") if raw else ""
