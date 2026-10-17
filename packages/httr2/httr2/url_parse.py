"""Parse a URL into the pieces httr2 stores on an httr2_url.

The resolver is curl's URL parser. Query pairs keep every repeated name,
and a value is the text after the first equals sign only, which is what
``as.list(curl_parse_url(...)$params)`` returns.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
_CURL = str(_PACKAGES / "curl")
if _CURL not in sys.path:
    sys.path.insert(0, _CURL)

from curl import AsIs, curl_escape, curl_modify_url, curl_parse_url, curl_unescape


def _check_string(value, *, allow_null: bool, arg: str):
    tail = " or `NULL`" if allow_null else ""
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            raise ValueError(
                f"`{arg}` must be a single string{tail}, not an empty character vector."
            )
        if len(value) > 1:
            raise ValueError(
                f"`{arg}` must be a single string{tail}, not a character vector."
            )
        value = value[0]
    if value is None:
        if allow_null:
            return None
        raise ValueError(f"`{arg}` must be a single string, not `NULL`.")
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        shown = "`TRUE`" if value else "`FALSE`"
        raise ValueError(f"`{arg}` must be a single string{tail}, not {shown}.")
    if isinstance(value, int):
        raise ValueError(f"`{arg}` must be a single string{tail}, not the number {value}.")
    if isinstance(value, float):
        if value != value:
            raise ValueError(f"`{arg}` must be a single string{tail}, not `NA`.")
        shown = str(int(value)) if value.is_integer() else str(value)
        raise ValueError(f"`{arg}` must be a single string{tail}, not the number {shown}.")
    raise ValueError(f"`{arg}` must be a single string{tail}.")


def _decode(value):
    if value is None:
        return None
    return curl_unescape(value)


def _query_pairs(query: str | None) -> list[tuple[str, str]]:
    if query is None:
        return []
    # application/x-www-form-urlencoded uses + for a space, before each
    # name and value is unescaped. Splitting on every '=' makes the value
    # the second piece, so "x=y=z" is "y" and "x==" is empty.
    query = query.replace("+", " ")
    pairs = []
    for piece in query.split("&"):
        parts = [curl_unescape(part) for part in piece.split("=")]
        parts.append("")
        pairs.append((parts[0], parts[1]))
    return pairs


class Httr2Url:
    """The S3 list ``url_parse`` returns, class ``httr2_url``."""

    def __init__(
        self,
        scheme,
        hostname,
        username,
        password,
        port,
        path,
        query,
        fragment,
    ):
        self.scheme = scheme
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment

    def __str__(self) -> str:
        return _format(self)


def _rebuild(url: Httr2Url) -> str:
    if url.query is None:
        query = None
    elif len(url.query) == 0:
        query = ""
    else:
        query = AsIs(
            "&".join(f"{curl_escape(name)}={curl_escape(value)}" for name, value in url.query)
        )
    built = curl_modify_url(
        scheme=url.scheme,
        host=url.hostname,
        user=url.username,
        password=url.password,
        port=None if url.port is None else str(url.port),
        path=url.path,
        query=query,
        fragment=url.fragment,
    )
    # curl percent-encodes a colon in the path. httr2 puts the colon back.
    if built and "%3A" in built:
        path = curl_parse_url(built, decode=False)["path"]
        if path is not None:
            built = curl_modify_url(built, path=AsIs(path.replace("%3A", ":")))
    return built


def _format(url: Httr2Url) -> str:
    lines = [f"<httr2_url> {_rebuild(url)}"]
    fields = (
        ("scheme", url.scheme),
        ("hostname", url.hostname),
        ("username", url.username),
        ("password", url.password),
        ("port", url.port),
        ("path", url.path),
    )
    for name, value in fields:
        if value is not None:
            lines.append(f"* {name}: {value}")
    if url.query is not None:
        lines.append("* query:")
        for name, value in url.query:
            lines.append(f"  * {name}: {value}")
    if url.fragment is not None:
        lines.append(f"* fragment: {url.fragment}")
    return "\n".join(lines)


def url_parse(url, base_url=None) -> Httr2Url:
    """Parse ``url``, resolving it against ``base_url`` when it is relative.

    ``base_url`` may be omitted. The result has ``scheme``, ``hostname``,
    ``username``, ``password``, ``port``, ``path``, ``query``, and
    ``fragment``. ``query`` is ``None`` when the URL has no parameters,
    and otherwise a list of ``(name, value)`` pairs in query order.
    """

    url = _check_string(url, allow_null=False, arg="url")
    base_url = _check_string(base_url, allow_null=True, arg="base_url")
    parsed = curl_parse_url(url, baseurl=base_url, params=False, decode=False)
    pairs = _query_pairs(parsed.get("query"))
    return Httr2Url(
        scheme=parsed.get("scheme"),
        hostname=parsed.get("host"),
        username=_decode(parsed.get("user")),
        password=_decode(parsed.get("password")),
        port=parsed.get("port"),
        path=_decode(parsed.get("path")),
        query=pairs if pairs else None,
        fragment=_decode(parsed.get("fragment")),
    )
