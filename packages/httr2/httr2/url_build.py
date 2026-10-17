"""Build a URL string from the object ``url_parse`` returns.

This is the inverse of ``url_parse``. Query values are escaped the way
``url_query_build`` escapes them, and a colon that libcurl percent-encodes
in the path is written back as a colon.
"""

from __future__ import annotations

import math
import sys
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
_CURL = str(_PACKAGES / "curl")
if _CURL not in sys.path:
    sys.path.insert(0, _CURL)

from curl import AsIs, curl_escape, curl_modify_url, curl_parse_url
from httr2.url_parse import Httr2Url


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
            return "`NA`"
        if math.isinf(value):
            shown = "Inf" if value > 0 else "-Inf"
        elif value.is_integer():
            shown = str(int(value))
        else:
            shown = _format_number(value)
        return f"the number {shown}"
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "a list"
        if len(value) > 1 and all(isinstance(item, str) for item in value):
            return "a character vector"
        if len(value) > 1 and all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            return "an integer vector"
        return "a list"
    return "a list"


def _format_number(value: float, digits: int = 7) -> str:
    """R ``format(x, scientific = FALSE, trim = TRUE, justify = "none")``."""

    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    exponent = math.floor(math.log10(magnitude))
    quantum = Decimal(10) ** (exponent - (digits - 1))
    with localcontext() as ctx:
        ctx.prec = max(digits + 8, 28)
        rounded = Decimal(magnitude).quantize(quantum, rounding=ROUND_HALF_EVEN)
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "":
        text = "0"
    return sign + text


def _format_query_value(value, name: str) -> str:
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, AsIs)):
        if len(value) > 1:
            raise ValueError(
                "All vector elements of `query` must be length 1.\n"
                "\u2139 Use `.multi` to choose a strategy for handling vectors."
            )
        if len(value) == 0:
            raise ValueError(
                f"Query value `{name}` must be a length-1 atomic vector, not an empty vector."
            )
        value = value[0]
    if isinstance(value, AsIs):
        return str(value)
    if isinstance(value, bool):
        text = "TRUE" if value else "FALSE"
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, float):
        text = _format_number(value)
    elif isinstance(value, str):
        text = value
    else:
        raise ValueError(
            f"Query value `{name}` must be a length-1 atomic vector, not a list."
        )
    escaped = curl_escape(text)
    if isinstance(escaped, list):
        return escaped[0]
    return escaped


def _query_pairs(query):
    if isinstance(query, dict):
        return list(query.items())
    if isinstance(query, (list, tuple)):
        pairs = []
        for item in query:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], str)
            ):
                pairs.append((item[0], item[1]))
                continue
            raise ValueError("`query` must be a named list, not a list.")
        return pairs
    raise ValueError(f"`query` must be a named list, not {_obj_type(query)}.")


def _build_query(query):
    if query is None:
        return None
    if query == "":
        return ""
    if isinstance(query, (list, tuple, dict)) and len(query) == 0:
        return ""
    pairs = _query_pairs(query)
    kept = [(name, value) for name, value in pairs if value is not None]
    if not kept:
        raise ValueError("attempt to set an attribute on NULL")
    parts = []
    for name, value in kept:
        length = 1
        if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, AsIs)):
            length = len(value)
        if length > 1:
            raise ValueError(
                "All vector elements of `query` must be length 1.\n"
                "\u2139 Use `.multi` to choose a strategy for handling vectors."
            )
        encoded = _format_query_value(value, name)
        name_text = curl_escape(name)
        if isinstance(name_text, list):
            name_text = name_text[0]
        parts.append(f"{name_text}={encoded}")
    return AsIs("&".join(parts))


def _port_text(port):
    if port is None or isinstance(port, str):
        return port
    if isinstance(port, bool):
        return "TRUE" if port else "FALSE"
    if isinstance(port, int):
        return str(port)
    if isinstance(port, float):
        if math.isnan(port):
            return "NA"
        if math.isinf(port):
            return "Inf" if port > 0 else "-Inf"
        if port.is_integer():
            return str(int(port))
        return str(port)
    return str(port)


def _restore_path_colons(built: str) -> str:
    # libcurl percent-encodes a colon in the path. httr2 writes it back.
    if not built or "%3A" not in built:
        return built
    path = curl_parse_url(built, decode=False).get("path")
    if path is None:
        return built
    return curl_modify_url(built, path=AsIs(path.replace("%3A", ":")))


def url_build(url) -> str:
    """Turn a parsed URL back into a string.

    ``url`` is the object returned by ``url_parse``. A missing component
    stays omitted. An empty query list or an empty query string clears the
    query. Each query name and value is percent-encoded, except a value
    marked with ``curl.AsIs``, which is inserted as written.
    """

    if not isinstance(url, Httr2Url):
        raise ValueError(f"`url` must be a parsed URL, not {_obj_type(url)}.")
    built = curl_modify_url(
        url=getattr(url, "url", None),
        scheme=url.scheme,
        host=url.hostname,
        user=url.username,
        password=url.password,
        port=_port_text(url.port),
        path=url.path,
        query=_build_query(url.query),
        fragment=url.fragment,
    )
    return _restore_path_colons(built)
