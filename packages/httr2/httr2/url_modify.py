"""Change selected pieces of a URL.

Omitted arguments stay as they are. ``None`` removes that piece. A string
URL is handed to ``url_build`` with the original text still attached, so
pieces that were not mentioned keep their original encoding. A parsed URL
is returned with those fields replaced.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
_CURL = str(_PACKAGES / "curl")
if _CURL not in sys.path:
    sys.path.insert(0, _CURL)

from curl import AsIs, curl_unescape
from httr2.url_build import url_build
from httr2.url_parse import Httr2Url


class _LeaveAsIs:
    def __repr__(self) -> str:
        return "as_is"


_AS_IS = _LeaveAsIs()


def _obj_type(value) -> str:
    if value is None:
        return "`NULL`"
    if isinstance(value, bool):
        return "`TRUE`" if value else "`FALSE`"
    if isinstance(value, str):
        return f'the string "{value}"'
    if isinstance(value, int):
        return f"the number {value}"
    if isinstance(value, float):
        if math.isnan(value):
            return "a numeric `NA`"
        if math.isinf(value):
            return "`Inf`" if value > 0 else "`-Inf`"
        if value.is_integer():
            return f"the number {int(value)}"
        return f"the number {value}"
    if isinstance(value, (list, tuple)):
        if len(value) > 1 and all(isinstance(item, str) for item in value):
            return "a character vector"
        if len(value) > 1 and all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        ):
            return "an integer vector"
        if len(value) > 1 and all(isinstance(item, float) for item in value):
            return "a double vector"
        return "a list"
    if isinstance(value, bytes):
        return "a raw vector"
    return "a list"


def _vector_kind(value) -> str:
    if value and all(isinstance(item, bool) for item in value):
        return "a logical vector"
    if value and all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        return "an integer vector"
    if value and all(isinstance(item, float) for item in value):
        return "a double vector"
    if value and all(isinstance(item, str) for item in value):
        return "a character vector"
    return "a list"


def _check_component(value, arg: str) -> None:
    if value is _AS_IS or value is None or isinstance(value, str):
        return
    raise ValueError(
        f"`{arg}` must be a single string or `NULL`, not {_obj_type(value)}."
    )


def _check_port(port):
    if port is _AS_IS or port is None:
        return port
    whole = (
        isinstance(port, int)
        and not isinstance(port, bool)
        or isinstance(port, float)
        and not math.isnan(port)
        and not math.isinf(port)
        and port.is_integer()
    )
    if not whole:
        raise ValueError(
            f"`port` must be a whole number or `NULL`, not {_obj_type(port)}."
        )
    number = int(port)
    if number < 1 or number > 65535:
        raise ValueError(
            "`port` must be a whole number between 1 and 65535 or `NULL`, "
            f"not {_obj_type(port)}."
        )
    return port


def _parse_delim(text: str, delim: str = "&", quote: str = '"') -> list[str]:
    """Split one line the way ``scan(strip.white = TRUE)`` does."""

    if text == "":
        return []
    fields: list[str] = []
    buf: list[str] = []
    quoted = False
    saw_delim = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quoted:
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quoted = False
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue
        if ch == quote:
            quoted = True
            i += 1
            continue
        if ch == delim:
            fields.append("".join(buf).strip())
            buf = []
            saw_delim = True
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if not saw_delim and tail == "":
        return []
    fields.append(tail)
    return fields


def _unescape(value: str) -> str:
    text = curl_unescape(value)
    if isinstance(text, list):
        return text[0] if text else ""
    return text


def _url_query_parse(query: str):
    if query.startswith("?"):
        query = query[1:]
    pieces = _parse_delim(query)
    if not pieces:
        return None
    pairs = []
    for piece in pieces:
        if "=" in piece:
            name, value = piece.split("=", 1)
        else:
            name, value = piece, ""
        pairs.append((_unescape(name), _unescape(value)))
    return pairs


def _is_named_query(query) -> bool:
    if isinstance(query, dict):
        return all(isinstance(key, str) and key != "" for key in query)
    if isinstance(query, (list, tuple)):
        if len(query) == 0:
            return True
        for item in query:
            if not (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], str)
                and item[0] != ""
            ):
                return False
        return True
    return False


def _check_query_value(value, name: str):
    arg = f"query${name}"
    if isinstance(value, AsIs):
        return value
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            raise ValueError(
                f"Query value `{arg}` must be a length-1 atomic vector, not an empty vector."
            )
        if len(value) > 1:
            raise ValueError(
                f"Query value `{arg}` must be a length-1 atomic vector, not {_vector_kind(value)}."
            )
        value = value[0]
    if value is None:
        raise ValueError(
            f"Query value `{arg}` must be a length-1 atomic vector, not `NULL`."
        )
    if isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError(
        f"Query value `{arg}` must be a length-1 atomic vector, not {_obj_type(value)}."
    )


def _query_pairs(query) -> list:
    if isinstance(query, dict):
        items = list(query.items())
    else:
        items = [tuple(item) for item in query]
    return [(_name, _check_query_value(value, _name)) for _name, value in items]


def _prepare_query(query):
    if query is _AS_IS or query is None:
        return query
    if isinstance(query, str):
        return _url_query_parse(query)
    if _is_named_query(query):
        return _query_pairs(query)
    raise ValueError(
        "`query` must be a character vector, named list, or NULL, "
        f"not {_obj_type(query)}."
    )


def _reject_unnamed(pairs) -> None:
    if any(not isinstance(name, str) or name == "" for name, _value in pairs):
        raise ValueError("`query` must be a named list, not a list.")


def _build_from_string(url: str, updates: dict) -> str:
    obj = Httr2Url(None, None, None, None, None, None, None, None)
    obj.url = url
    for name, value in updates.items():
        setattr(obj, name, value)
    return url_build(obj)


def _apply_parsed(url: Httr2Url, updates: dict) -> Httr2Url:
    query = None if url.query is None else list(url.query)
    obj = Httr2Url(
        url.scheme,
        url.hostname,
        url.username,
        url.password,
        url.port,
        url.path,
        query,
        url.fragment,
    )
    base = getattr(url, "url", None)
    if base is not None:
        obj.url = base
    for name, value in updates.items():
        if name == "query" and isinstance(value, list):
            value = list(value)
        setattr(obj, name, value)
    return obj


def url_modify(
    url,
    scheme=_AS_IS,
    hostname=_AS_IS,
    username=_AS_IS,
    password=_AS_IS,
    port=_AS_IS,
    path=_AS_IS,
    query=_AS_IS,
    fragment=_AS_IS,
):
    """Modify pieces of ``url``.

    ``url`` is a string or the object returned by ``url_parse``. Each of
    ``scheme``, ``hostname``, ``username``, ``password``, ``port``,
    ``path``, ``query``, and ``fragment`` is left unchanged when it is
    omitted. ``None`` removes that piece. ``port`` is a whole number from
    1 to 65535. ``query`` is either a query string or a named list; a
    string replaces the whole query. A string ``url`` comes back as a
    string, and a parsed ``url`` comes back parsed.
    """

    if not isinstance(url, str) and not isinstance(url, Httr2Url):
        raise ValueError(
            f"`url` must be a string or parsed URL, not {_obj_type(url)}."
        )
    for arg, value in (
        ("scheme", scheme),
        ("hostname", hostname),
        ("username", username),
        ("password", password),
        ("path", path),
        ("fragment", fragment),
    ):
        _check_component(value, arg)
    port = _check_port(port)
    query = _prepare_query(query)

    updates = {}
    for name, value in (
        ("scheme", scheme),
        ("hostname", hostname),
        ("username", username),
        ("password", password),
        ("port", port),
        ("path", path),
        ("query", query),
        ("fragment", fragment),
    ):
        if value is _AS_IS:
            continue
        updates[name] = value

    if isinstance(url, str):
        for name, value in list(updates.items()):
            if value is None:
                updates[name] = ""
        built_query = updates.get("query")
        if isinstance(built_query, list):
            _reject_unnamed(built_query)
        return _build_from_string(url, updates)
    return _apply_parsed(url, updates)
