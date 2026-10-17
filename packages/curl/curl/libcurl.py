"""Calls the system libcurl the R package curl is linked against."""

from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_uint, c_void_p

_path = ctypes.util.find_library("curl")
if not _path:
    raise RuntimeError("libcurl was not found")
lib = ctypes.CDLL(_path)

lib.curl_version.restype = c_char_p
lib.curl_getdate.argtypes = [c_char_p, c_void_p]
lib.curl_getdate.restype = c_long
lib.curl_easy_init.restype = c_void_p
lib.curl_easy_cleanup.argtypes = [c_void_p]
lib.curl_easy_reset.argtypes = [c_void_p]
lib.curl_easy_escape.argtypes = [c_void_p, c_char_p, c_int]
lib.curl_easy_escape.restype = c_void_p
lib.curl_easy_unescape.argtypes = [c_void_p, c_char_p, c_int, POINTER(c_int)]
lib.curl_easy_unescape.restype = c_void_p
lib.curl_free.argtypes = [c_void_p]
lib.curl_url.restype = c_void_p
lib.curl_url_cleanup.argtypes = [c_void_p]
lib.curl_url_set.argtypes = [c_void_p, c_int, c_char_p, c_uint]
lib.curl_url_set.restype = c_int
lib.curl_url_get.argtypes = [c_void_p, c_int, POINTER(c_char_p), c_uint]
lib.curl_url_get.restype = c_int
lib.curl_url_strerror.argtypes = [c_int]
lib.curl_url_strerror.restype = c_char_p
lib.curl_easy_setopt.restype = c_int
lib.curl_easy_perform.argtypes = [c_void_p]
lib.curl_easy_perform.restype = c_int
lib.curl_easy_strerror.argtypes = [c_int]
lib.curl_easy_strerror.restype = c_char_p
lib.curl_easy_option_next.argtypes = [c_void_p]
lib.curl_easy_option_next.restype = c_void_p
lib.curl_version_info.argtypes = [c_int]
lib.curl_version_info.restype = c_void_p
lib.curl_multi_init.restype = c_void_p
lib.curl_multi_cleanup.argtypes = [c_void_p]
lib.curl_multi_add_handle.argtypes = [c_void_p, c_void_p]
lib.curl_multi_add_handle.restype = c_int
lib.curl_multi_remove_handle.argtypes = [c_void_p, c_void_p]
lib.curl_multi_remove_handle.restype = c_int
lib.curl_multi_perform.argtypes = [c_void_p, POINTER(c_int)]
lib.curl_multi_perform.restype = c_int
lib.curl_multi_timeout.argtypes = [c_void_p, POINTER(c_long)]
lib.curl_multi_timeout.restype = c_int

CURLUE_OK = 0
CURLUE_NO_SCHEME = 10
CURLUE_NO_USER = 11
CURLUE_NO_PASSWORD = 12
CURLUE_NO_HOST = 14
CURLUE_NO_PORT = 15
CURLUE_NO_QUERY = 16
CURLUE_NO_FRAGMENT = 17

CURLUPART_URL = 0
CURLUPART_SCHEME = 1
CURLUPART_USER = 2
CURLUPART_PASSWORD = 3
CURLUPART_HOST = 5
CURLUPART_PORT = 6
CURLUPART_PATH = 7
CURLUPART_QUERY = 8
CURLUPART_FRAGMENT = 9

CURLU_DEFAULT_SCHEME = 1 << 2
CURLU_NON_SUPPORT_SCHEME = 1 << 3
CURLU_URLENCODE = 1 << 7

CURL_VERSION_IPV6 = 1 << 0
CURL_VERSION_IDN = 1 << 10
CURL_VERSION_HTTP2 = 1 << 16
CURLOT_FLAG_ALIAS = 1 << 0

WRITEFUNCTION = ctypes.CFUNCTYPE(ctypes.c_size_t, c_void_p, ctypes.c_size_t, ctypes.c_size_t, c_void_p)


class _CurlVersion(ctypes.Structure):
    _fields_ = [
        ("age", c_int),
        ("version", c_char_p),
        ("version_num", c_uint),
        ("host", c_char_p),
        ("features", c_int),
        ("ssl_version", c_char_p),
        ("ssl_version_num", c_long),
        ("libz_version", c_char_p),
        ("protocols", POINTER(c_char_p)),
        ("ares", c_char_p),
        ("ares_num", c_int),
        ("libidn", c_char_p),
        ("iconv_ver_num", c_int),
        ("libssh_version", c_char_p),
    ]


class _EasyOption(ctypes.Structure):
    _fields_ = [
        ("name", c_char_p),
        ("id", c_int),
        ("type", c_int),
        ("flags", c_uint),
    ]


def _text(ptr: c_char_p | bytes | None) -> str | None:
    if not ptr:
        return None
    if isinstance(ptr, bytes):
        return ptr.decode("utf-8")
    return ptr.decode("utf-8")


def version_info() -> dict:
    raw = lib.curl_version_info(13)
    data = ctypes.cast(raw, POINTER(_CurlVersion)).contents
    protocols = []
    index = 0
    while data.protocols[index]:
        protocols.append(data.protocols[index].decode("utf-8"))
        index += 1
    features = data.features
    return {
        "version": _text(data.version),
        "ssl_version": _text(data.ssl_version),
        "libz_version": _text(data.libz_version),
        "libssh_version": _text(data.libssh_version),
        "libidn_version": _text(data.libidn),
        "host": _text(data.host),
        "protocols": protocols,
        "ipv6": bool(features & CURL_VERSION_IPV6),
        "http2": bool(features & CURL_VERSION_HTTP2),
        "idn": bool(features & CURL_VERSION_IDN),
        "url_parser": True,
    }


def option_table() -> list[tuple[str, int, int]]:
    rows = []
    current = None
    while True:
        current = lib.curl_easy_option_next(current)
        if not current:
            break
        opt = ctypes.cast(current, POINTER(_EasyOption)).contents
        if opt.flags & CURLOT_FLAG_ALIAS:
            continue
        name = opt.name.decode("utf-8") if opt.name else "???"
        rows.append((name.lower(), int(opt.id), int(opt.type)))
    return rows


def escape(text: str, unescape: bool) -> str:
    handle = lib.curl_easy_init()
    raw = text.encode("utf-8")
    if unescape:
        ptr = lib.curl_easy_unescape(handle, raw, 0, None)
    else:
        ptr = lib.curl_easy_escape(handle, raw, 0)
    if not ptr:
        lib.curl_easy_cleanup(handle)
        return ""
    value = ctypes.cast(ptr, c_char_p).value.decode("utf-8")
    lib.curl_free(ptr)
    lib.curl_easy_cleanup(handle)
    return value


def _fail_url(code: int) -> None:
    if code == CURLUE_OK:
        return
    message = lib.curl_url_strerror(code)
    detail = message.decode("utf-8") if message else str(code)
    raise RuntimeError(f"Failed to parse URL: {detail}")


def url_set(handle, part: int, value: str | None, flags: int) -> None:
    if value is None:
        _fail_url(lib.curl_url_set(handle, part, None, flags))
        return
    _fail_url(lib.curl_url_set(handle, part, value.encode("utf-8"), flags))


def url_get(handle, part: int, missing: int) -> str | None:
    out = c_char_p()
    code = lib.curl_url_get(handle, part, byref(out), 0)
    if code == missing and code != CURLUE_OK:
        if out:
            lib.curl_free(out)
        return None
    _fail_url(code)
    value = out.value.decode("utf-8") if out.value is not None else None
    lib.curl_free(out)
    return value


def url_new():
    return lib.curl_url()


def url_cleanup(handle) -> None:
    lib.curl_url_cleanup(handle)
