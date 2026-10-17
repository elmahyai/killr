"""The httr2 slice of the R package curl, calling system libcurl."""

from __future__ import annotations

import ctypes
import re
import socket
from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_void_p

from curl import libcurl

_OPTION_TYPES = (
    "long",
    "values",
    "off_t",
    "object",
    "string",
    "slist",
    "cbptr",
    "blob",
    "function",
)
_SET_FLAGS = libcurl.CURLU_NON_SUPPORT_SCHEME | libcurl.CURLU_URLENCODE
_ENCODED = re.compile(r"(%..)")
_HEADER_BREAK = re.compile(r"\r\n\r\n|\n\n|\r\r")
_LINE_BREAK = re.compile(r"\r\n|\n|\r")


class AsIs(str):
    """A URL piece that must not be encoded again. This is R's I()."""


class FormFile:
    def __init__(self, path: str, type: str | None = None, name: str | None = None):
        self.path = path
        self.type = type
        self.name = name


class FormData:
    def __init__(self, value: bytes, type: str | None = None):
        self.value = value
        self.type = type


class Handle:
    def __init__(self):
        self._easy = libcurl.lib.curl_easy_init()
        self._slist = None
        self._writers = []
        self._options: dict[str, object] = {}
        self.response: dict | None = None

    def __del__(self):
        if getattr(self, "_easy", None):
            libcurl.lib.curl_easy_cleanup(self._easy)
            self._easy = None


class Pool:
    def __init__(self):
        self._multi = libcurl.lib.curl_multi_init()
        self.pending: list[tuple[Handle, object, object]] = []

    def __del__(self):
        if getattr(self, "_multi", None):
            libcurl.lib.curl_multi_cleanup(self._multi)
            self._multi = None


def _one_or_many(values: list[str]):
    if len(values) == 1:
        return values[0]
    return values


def curl_escape(url):
    items = [url] if isinstance(url, str) else list(url)
    return _one_or_many([libcurl.escape(str(item), False) for item in items])


def curl_unescape(url):
    items = [url] if isinstance(url, str) else list(url)
    return _one_or_many([libcurl.escape(str(item), True) for item in items])


def _upper_encoding(value: str | None) -> str | None:
    if value is None:
        return None
    return _ENCODED.sub(lambda match: match.group(1).upper(), value)


def _normalize(value: str | None, decode: bool) -> str | None:
    if value is None:
        return None
    if decode:
        return curl_unescape(value)
    return _upper_encoding(value)


def _parse_query(query: str | None) -> dict[str, str]:
    if not query:
        return {}
    query = query.replace("+", " ")
    values = {}
    for piece in query.split("&"):
        if "=" in piece:
            name, value = piece.split("=", 1)
        else:
            name, value = piece, ""
        values[curl_unescape(name)] = curl_unescape(value)
    return values


def _build_query(params: dict) -> str:
    parts = []
    for name, value in params.items():
        encoded = curl_escape(str(value)).replace("%20", "+")
        parts.append(f"{curl_escape(str(name))}={encoded}")
    return "&".join(parts)


def curl_parse_url(url, baseurl=None, decode=True, params=True, default_scheme=False):
    if not isinstance(url, str) or not isinstance(url, str):
        pass
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    if baseurl and url.startswith("#"):
        url = re.sub(r"(#.*)?$", url, baseurl)
    handle = libcurl.url_new()
    flags = _SET_FLAGS | (libcurl.CURLU_DEFAULT_SCHEME if default_scheme else 0)
    try:
        if baseurl:
            libcurl.url_set(handle, libcurl.CURLUPART_URL, str(baseurl), flags)
        libcurl.url_set(handle, libcurl.CURLUPART_URL, url, flags)
        result = {
            "url": _upper_encoding(libcurl.url_get(handle, libcurl.CURLUPART_URL, libcurl.CURLUE_OK)),
            "scheme": libcurl.url_get(handle, libcurl.CURLUPART_SCHEME, libcurl.CURLUE_NO_SCHEME),
            "host": libcurl.url_get(handle, libcurl.CURLUPART_HOST, libcurl.CURLUE_NO_HOST),
            "port": libcurl.url_get(handle, libcurl.CURLUPART_PORT, libcurl.CURLUE_NO_PORT),
            "path": libcurl.url_get(handle, libcurl.CURLUPART_PATH, libcurl.CURLUE_OK),
            "query": libcurl.url_get(handle, libcurl.CURLUPART_QUERY, libcurl.CURLUE_NO_QUERY),
            "fragment": libcurl.url_get(handle, libcurl.CURLUPART_FRAGMENT, libcurl.CURLUE_NO_FRAGMENT),
            "user": libcurl.url_get(handle, libcurl.CURLUPART_USER, libcurl.CURLUE_NO_USER),
            "password": libcurl.url_get(handle, libcurl.CURLUPART_PASSWORD, libcurl.CURLUE_NO_PASSWORD),
        }
    finally:
        libcurl.url_cleanup(handle)
    if params:
        try:
            result["params"] = _parse_query(result["query"])
            result["query"] = None
        except Exception:
            result["params"] = {}
    for field in ("path", "query", "fragment", "user", "password"):
        result[field] = _normalize(result.get(field), decode)
    return result


def curl_modify_url(
    url=None,
    scheme=None,
    host=None,
    port=None,
    path=None,
    query=None,
    fragment=None,
    user=None,
    password=None,
    params=None,
):
    if isinstance(url, dict):
        return curl_modify_url(**url)
    if params is not None:
        query = AsIs(_build_query(params))
    handle = libcurl.url_new()
    pieces = (
        (libcurl.CURLUPART_URL, url),
        (libcurl.CURLUPART_SCHEME, scheme),
        (libcurl.CURLUPART_HOST, host),
        (libcurl.CURLUPART_PORT, None if port is None else str(port)),
        (libcurl.CURLUPART_PATH, path),
        (libcurl.CURLUPART_QUERY, query),
        (libcurl.CURLUPART_FRAGMENT, fragment),
        (libcurl.CURLUPART_USER, user),
        (libcurl.CURLUPART_PASSWORD, password),
    )
    try:
        for part, value in pieces:
            if value is None:
                continue
            text = str(value)
            if text == "":
                libcurl.url_set(handle, part, None, 0)
            elif isinstance(value, AsIs):
                libcurl.url_set(handle, part, text, 0)
            else:
                libcurl.url_set(handle, part, text, _SET_FLAGS)
        return _upper_encoding(libcurl.url_get(handle, libcurl.CURLUPART_URL, libcurl.CURLUE_OK))
    finally:
        libcurl.url_cleanup(handle)


def _rsplit(pattern, text):
    parts = pattern.split(text)
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def parse_headers(txt, multiple=False):
    if txt is None or txt == b"" or txt == "":
        return None
    if isinstance(txt, (bytes, bytearray)):
        txt = bytes(txt).decode("utf-8", "replace")
    if isinstance(txt, (list, tuple)):
        if not txt:
            return None
        txt = "\n".join(txt)
    if not isinstance(txt, str):
        raise TypeError("txt must be raw or character")
    sets = _rsplit(_HEADER_BREAK, txt)
    headers = [_rsplit(_LINE_BREAK, item) for item in sets]
    if multiple:
        return headers
    return headers[-1]


def parse_headers_list(txt):
    headers = [line for line in (parse_headers(txt) or []) if ":" in line]
    values = {}
    for line in headers:
        name, value = line.split(":", 1)
        values[name.lower()] = value.strip()
    return values


def parse_date(datestring):
    when = libcurl.lib.curl_getdate(str(datestring).encode("utf-8"), None)
    if when < 0:
        raise RuntimeError(f"Failed to parse date: {datestring}")
    return int(when)


def curl_version():
    info = libcurl.version_info()
    info["headers"] = info["version"]
    return info


def curl_options(filter=""):
    pattern = re.compile(filter, re.IGNORECASE)
    return {
        name: value
        for name, value, _type in libcurl.option_table()
        if pattern.search(name)
    }


def curl_options_table(filter=""):
    pattern = re.compile(filter, re.IGNORECASE)
    rows = []
    for name, value, kind in libcurl.option_table():
        if pattern.search(name):
            rows.append({"name": name, "value": value, "type": _OPTION_TYPES[kind]})
    return rows


def _option_map():
    return {name: (value, kind) for name, value, kind in libcurl.option_table()}


def new_handle(**options):
    handle = Handle()
    if options:
        handle_setopt(handle, **options)
    return handle


def _setopt(handle: Handle, option: int, kind: int, value) -> None:
    easy = handle._easy
    if kind in (0, 1):
        libcurl.lib.curl_easy_setopt.argtypes = [c_void_p, c_int, c_long]
        number = 1 if value is True else 0 if value is False else int(value)
        code = libcurl.lib.curl_easy_setopt(easy, option, c_long(number))
    elif kind == 4:
        libcurl.lib.curl_easy_setopt.argtypes = [c_void_p, c_int, c_char_p]
        raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        code = libcurl.lib.curl_easy_setopt(easy, option, raw)
    elif kind == 5:
        libcurl.lib.curl_slist_append.argtypes = [c_void_p, c_char_p]
        libcurl.lib.curl_slist_append.restype = c_void_p
        slist = None
        for item in value:
            slist = libcurl.lib.curl_slist_append(slist, str(item).encode("utf-8"))
        handle._slist = slist
        libcurl.lib.curl_easy_setopt.argtypes = [c_void_p, c_int, c_void_p]
        code = libcurl.lib.curl_easy_setopt(easy, option, slist)
    else:
        raise RuntimeError(f"unsupported curl option type {kind}")
    if code != 0:
        raise RuntimeError(libcurl.lib.curl_easy_strerror(code).decode())


def handle_setopt(handle, _list=None, **options):
    if not isinstance(handle, Handle):
        raise TypeError("handle must be a curl handle")
    values = dict(options)
    if _list:
        values.update(_list)
    table = _option_map()
    unknown = [name.lower() for name in values if name.lower() not in table]
    if unknown:
        label = "s: " if len(unknown) > 1 else ": "
        raise RuntimeError("Unknown option" + label + ", ".join(unknown))
    for name, value in values.items():
        option, kind = table[name.lower()]
        _setopt(handle, option, kind, value)
        handle._options[name.lower()] = value
    return handle


def handle_setheaders(handle, _list=None, **headers):
    values = dict(headers)
    if _list:
        values.update(_list)
    if not all(isinstance(item, str) for item in values.values()):
        raise RuntimeError("All headers must be strings.")
    values.setdefault("Expect", "")
    lines = []
    for name, value in values.items():
        if value.strip() == "" and value != "":
            lines.append(f"{name};")
        else:
            lines.append(f"{name}: {value}" if value else f"{name}:")
    return handle_setopt(handle, httpheader=lines)


def _collect(easy) -> bytes:
    chunks: list[bytes] = []

    @libcurl.WRITEFUNCTION
    def write(ptr, size, nmemb, _userdata):
        count = size * nmemb
        chunks.append(ctypes_string(ptr, count))
        return count

    # Keep the callback alive for the perform call.
    easy_id = id(write)
    del easy_id
    libcurl.lib.curl_easy_setopt.argtypes = [c_void_p, c_int, c_void_p]
    write_option = _option_map()["writefunction"][0]
    libcurl.lib.curl_easy_setopt(easy, write_option, write)
    code = libcurl.lib.curl_easy_perform(easy)
    if code != 0:
        message = libcurl.lib.curl_easy_strerror(code).decode()
        raise RuntimeError(message)
    return b"".join(chunks), write


def ctypes_string(ptr, count: int) -> bytes:
    return ctypes.string_at(ptr, count)


def _info_long(easy, option: int) -> int:
    out = c_long()
    libcurl.lib.curl_easy_getinfo.argtypes = [c_void_p, c_int, POINTER(c_long)]
    libcurl.lib.curl_easy_getinfo.restype = c_int
    libcurl.lib.curl_easy_getinfo(easy, option, byref(out))
    return int(out.value)


def _info_str(easy, option: int) -> str | None:
    out = c_char_p()
    libcurl.lib.curl_easy_getinfo.argtypes = [c_void_p, c_int, POINTER(c_char_p)]
    libcurl.lib.curl_easy_getinfo(easy, option, byref(out))
    if not out.value:
        return None
    return out.value.decode("utf-8", "replace")


def handle_data(handle: Handle) -> dict:
    if not isinstance(handle, Handle):
        raise TypeError("handle must be a curl handle")
    table = _option_map()
    easy = handle._easy
    data = {
        "url": _info_str(easy, table["url"][0] if False else 0x100000 + 1),
        "status_code": _info_long(easy, 0x200000 + 2),
        "content": None,
    }
    # CURLINFO_EFFECTIVE_URL = CURLINFO_STRING + 1, RESPONSE_CODE = CURLINFO_LONG + 2
    data["url"] = _info_str(easy, 0x100000 + 1)
    return data


def curl_fetch_memory(url, handle=None):
    handle = handle or new_handle()
    handle_setopt(handle, url=url)
    body, writer = _collect(handle._easy)
    handle._writers.append(writer)
    data = handle_data(handle)
    data["content"] = body
    handle.response = data
    return data


def curl_fetch_disk(url, path, handle=None):
    result = curl_fetch_memory(url, handle)
    with open(path, "wb") as out:
        out.write(result["content"])
    result["content"] = path
    return result


def form_file(path, type=None, name=None):
    return FormFile(path, type, name)


def form_data(value, type=None):
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, (bytes, bytearray)):
        raise RuntimeError("Argument 'value' must be string or raw vector")
    return FormData(bytes(value), type)


def handle_setform(handle, _list=None, **fields):
    values = dict(fields)
    if _list:
        values.update(_list)
    handle._options["form"] = values
    return handle


def nslookup(host, ipv4_only=False, multiple=False, error=True):
    if not isinstance(host, str):
        raise TypeError("host must be a string")
    if "://" in host:
        raise RuntimeError("This looks like a URL, not a hostname")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        infos = []
    addresses = []
    for info in infos:
        ip = info[4][0]
        if ipv4_only and ":" in ip:
            continue
        if ip not in addresses:
            addresses.append(ip)
    if error and not addresses:
        raise RuntimeError(f"Unable to resolve host: {host}")
    if not addresses:
        return None
    if multiple:
        return addresses
    return addresses[0]


def file_writer(path, append=False):
    state = {"handle": None}

    def writer(data=b"", close=False):
        if not isinstance(data, (bytes, bytearray)):
            raise RuntimeError("data must be raw")
        if state["handle"] is None:
            state["handle"] = open(path, "ab" if append else "wb")
        if data:
            state["handle"].write(bytes(data))
            state["handle"].flush()
        if close and state["handle"] is not None:
            state["handle"].close()
            state["handle"] = None
        return None

    return writer


def curl_download(url, destfile, handle=None):
    curl_fetch_disk(url, destfile, handle)
    return destfile


def curl_fetch_stream(url, fun, handle=None):
    result = curl_fetch_memory(url, handle)
    if result["content"]:
        fun(result["content"])
    result["content"] = None
    return result


def find_port(port_range=None):
    import random
    ports = [int(port) for port in port_range] if port_range else random.sample(list(range(1024, 49152)), 200)
    for port in ports:
        sock = socket.socket()
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        else:
            return port
        finally:
            sock.close()
    raise RuntimeError("Failed to find an open port")


def ie_proxy_info():
    return None


def ie_get_proxy_for_url(target):
    return None


def handle_reset(handle):
    if not isinstance(handle, Handle):
        raise TypeError("handle must be a curl handle")
    libcurl.lib.curl_easy_reset(handle._easy)
    handle._options.clear()
    handle.response = None
    return handle


def handle_cookies(handle):
    return {
        "domain": [],
        "flag": [],
        "path": [],
        "secure": [],
        "expiration": [],
        "name": [],
        "value": [],
    }


def multi_list(pool):
    return [item[0] for item in pool.pending]


def multi_set(total_con=50, host_con=6, max_streams=10, multiplex=True, pool=None):
    pool = pool or new_pool()
    pool.limits = {
        "total_con": total_con,
        "host_con": host_con,
        "max_streams": max_streams,
        "multiplex": multiplex,
    }
    return pool


def has_internet() -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo("dns.google.com", None)}
    except OSError:
        addresses = set()
    return "8.8.8.8" in addresses or "8.8.4.4" in addresses


def new_pool():
    return Pool()


def multi_add(handle, done=None, fail=None, pool=None):
    pool = pool or new_pool()
    if "url" not in handle._options:
        raise RuntimeError("handle has no url")
    code = libcurl.lib.curl_multi_add_handle(pool._multi, handle._easy)
    if code != 0:
        raise RuntimeError(f"multi_add failed ({code})")
    handle._pool = pool
    pool.pending.append((handle, done, fail))
    return handle


def multi_cancel(handle):
    pool = getattr(handle, "_pool", None)
    if pool is None:
        return handle
    libcurl.lib.curl_multi_remove_handle(pool._multi, handle._easy)
    pool.pending = [item for item in pool.pending if item[0] is not handle]
    return handle


def multi_fdset(pool):
    timeout = c_long()
    libcurl.lib.curl_multi_timeout(pool._multi, byref(timeout))
    return {"reads": [], "writes": [], "exceptions": [], "timeout": int(timeout.value)}


def _arm_writer(handle: Handle) -> list[bytes]:
    chunks: list[bytes] = []

    @libcurl.WRITEFUNCTION
    def write(ptr, size, nmemb, _userdata):
        count = size * nmemb
        chunks.append(ctypes.string_at(ptr, count))
        return count

    handle._writers.append(write)
    write_option = _option_map()["writefunction"][0]
    libcurl.lib.curl_easy_setopt.argtypes = [c_void_p, c_int, c_void_p]
    libcurl.lib.curl_easy_setopt(handle._easy, write_option, write)
    return chunks


def multi_run(pool=None, timeout=None):
    pool = pool or Pool()
    bodies = [(handle, done, fail, _arm_writer(handle)) for handle, done, fail in pool.pending]
    running = c_int(1)
    while True:
        code = libcurl.lib.curl_multi_perform(pool._multi, byref(running))
        if code not in (0, 1) or running.value == 0:
            break
    finished = []
    for handle, done, fail, chunks in bodies:
        try:
            data = handle_data(handle)
            data["content"] = b"".join(chunks)
            handle.response = data
            if done:
                done(data)
            finished.append(data)
        except Exception as exc:
            if fail:
                fail(str(exc))
            else:
                raise
    pool.pending.clear()
    return finished


def curl(url="https://hb.cran.dev/get", open="", handle=None):
    handle = handle or new_handle()
    fetched = curl_fetch_memory(url, handle)
    return fetched["content"]
from curl.curl_symbols import curl_symbols
