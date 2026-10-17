"""Return the URL of httr2's cached example app.

``example_url`` asks whether webfakes is installed, then keeps one app
process and joins ``path`` the way that process's ``url()`` method does:
``http://127.0.0.1``, the listening port, and the path text unchanged.
webfakes is a suggested package and is not part of this translation, so a
missing install is the same rlang error R raises. The ``/iris`` route is
the one httr2 adds on top of httpbin.
"""

from __future__ import annotations

import json
import math
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_PACKAGES = Path(__file__).resolve().parents[2]
_RLANG = str(_PACKAGES / "rlang")
if _RLANG not in sys.path:
    sys.path.insert(0, _RLANG)

from rlang import Env, check_installed, env_cache, null_or

the = Env()

_COLUMNS = (
    "Sepal.Length",
    "Sepal.Width",
    "Petal.Length",
    "Petal.Width",
    "Species",
)

# datasets::iris, in row order. Whole numbers stay integers so JSON matches
# jsonlite's auto-unboxed doubles.
_IRIS = (
    (5.1, 3.5, 1.4, 0.2, "setosa"),
    (4.9, 3, 1.4, 0.2, "setosa"),
    (4.7, 3.2, 1.3, 0.2, "setosa"),
    (4.6, 3.1, 1.5, 0.2, "setosa"),
    (5, 3.6, 1.4, 0.2, "setosa"),
    (5.4, 3.9, 1.7, 0.4, "setosa"),
    (4.6, 3.4, 1.4, 0.3, "setosa"),
    (5, 3.4, 1.5, 0.2, "setosa"),
    (4.4, 2.9, 1.4, 0.2, "setosa"),
    (4.9, 3.1, 1.5, 0.1, "setosa"),
    (5.4, 3.7, 1.5, 0.2, "setosa"),
    (4.8, 3.4, 1.6, 0.2, "setosa"),
    (4.8, 3, 1.4, 0.1, "setosa"),
    (4.3, 3, 1.1, 0.1, "setosa"),
    (5.8, 4, 1.2, 0.2, "setosa"),
    (5.7, 4.4, 1.5, 0.4, "setosa"),
    (5.4, 3.9, 1.3, 0.4, "setosa"),
    (5.1, 3.5, 1.4, 0.3, "setosa"),
    (5.7, 3.8, 1.7, 0.3, "setosa"),
    (5.1, 3.8, 1.5, 0.3, "setosa"),
    (5.4, 3.4, 1.7, 0.2, "setosa"),
    (5.1, 3.7, 1.5, 0.4, "setosa"),
    (4.6, 3.6, 1, 0.2, "setosa"),
    (5.1, 3.3, 1.7, 0.5, "setosa"),
    (4.8, 3.4, 1.9, 0.2, "setosa"),
    (5, 3, 1.6, 0.2, "setosa"),
    (5, 3.4, 1.6, 0.4, "setosa"),
    (5.2, 3.5, 1.5, 0.2, "setosa"),
    (5.2, 3.4, 1.4, 0.2, "setosa"),
    (4.7, 3.2, 1.6, 0.2, "setosa"),
    (4.8, 3.1, 1.6, 0.2, "setosa"),
    (5.4, 3.4, 1.5, 0.4, "setosa"),
    (5.2, 4.1, 1.5, 0.1, "setosa"),
    (5.5, 4.2, 1.4, 0.2, "setosa"),
    (4.9, 3.1, 1.5, 0.2, "setosa"),
    (5, 3.2, 1.2, 0.2, "setosa"),
    (5.5, 3.5, 1.3, 0.2, "setosa"),
    (4.9, 3.6, 1.4, 0.1, "setosa"),
    (4.4, 3, 1.3, 0.2, "setosa"),
    (5.1, 3.4, 1.5, 0.2, "setosa"),
    (5, 3.5, 1.3, 0.3, "setosa"),
    (4.5, 2.3, 1.3, 0.3, "setosa"),
    (4.4, 3.2, 1.3, 0.2, "setosa"),
    (5, 3.5, 1.6, 0.6, "setosa"),
    (5.1, 3.8, 1.9, 0.4, "setosa"),
    (4.8, 3, 1.4, 0.3, "setosa"),
    (5.1, 3.8, 1.6, 0.2, "setosa"),
    (4.6, 3.2, 1.4, 0.2, "setosa"),
    (5.3, 3.7, 1.5, 0.2, "setosa"),
    (5, 3.3, 1.4, 0.2, "setosa"),
    (7, 3.2, 4.7, 1.4, "versicolor"),
    (6.4, 3.2, 4.5, 1.5, "versicolor"),
    (6.9, 3.1, 4.9, 1.5, "versicolor"),
    (5.5, 2.3, 4, 1.3, "versicolor"),
    (6.5, 2.8, 4.6, 1.5, "versicolor"),
    (5.7, 2.8, 4.5, 1.3, "versicolor"),
    (6.3, 3.3, 4.7, 1.6, "versicolor"),
    (4.9, 2.4, 3.3, 1, "versicolor"),
    (6.6, 2.9, 4.6, 1.3, "versicolor"),
    (5.2, 2.7, 3.9, 1.4, "versicolor"),
    (5, 2, 3.5, 1, "versicolor"),
    (5.9, 3, 4.2, 1.5, "versicolor"),
    (6, 2.2, 4, 1, "versicolor"),
    (6.1, 2.9, 4.7, 1.4, "versicolor"),
    (5.6, 2.9, 3.6, 1.3, "versicolor"),
    (6.7, 3.1, 4.4, 1.4, "versicolor"),
    (5.6, 3, 4.5, 1.5, "versicolor"),
    (5.8, 2.7, 4.1, 1, "versicolor"),
    (6.2, 2.2, 4.5, 1.5, "versicolor"),
    (5.6, 2.5, 3.9, 1.1, "versicolor"),
    (5.9, 3.2, 4.8, 1.8, "versicolor"),
    (6.1, 2.8, 4, 1.3, "versicolor"),
    (6.3, 2.5, 4.9, 1.5, "versicolor"),
    (6.1, 2.8, 4.7, 1.2, "versicolor"),
    (6.4, 2.9, 4.3, 1.3, "versicolor"),
    (6.6, 3, 4.4, 1.4, "versicolor"),
    (6.8, 2.8, 4.8, 1.4, "versicolor"),
    (6.7, 3, 5, 1.7, "versicolor"),
    (6, 2.9, 4.5, 1.5, "versicolor"),
    (5.7, 2.6, 3.5, 1, "versicolor"),
    (5.5, 2.4, 3.8, 1.1, "versicolor"),
    (5.5, 2.4, 3.7, 1, "versicolor"),
    (5.8, 2.7, 3.9, 1.2, "versicolor"),
    (6, 2.7, 5.1, 1.6, "versicolor"),
    (5.4, 3, 4.5, 1.5, "versicolor"),
    (6, 3.4, 4.5, 1.6, "versicolor"),
    (6.7, 3.1, 4.7, 1.5, "versicolor"),
    (6.3, 2.3, 4.4, 1.3, "versicolor"),
    (5.6, 3, 4.1, 1.3, "versicolor"),
    (5.5, 2.5, 4, 1.3, "versicolor"),
    (5.5, 2.6, 4.4, 1.2, "versicolor"),
    (6.1, 3, 4.6, 1.4, "versicolor"),
    (5.8, 2.6, 4, 1.2, "versicolor"),
    (5, 2.3, 3.3, 1, "versicolor"),
    (5.6, 2.7, 4.2, 1.3, "versicolor"),
    (5.7, 3, 4.2, 1.2, "versicolor"),
    (5.7, 2.9, 4.2, 1.3, "versicolor"),
    (6.2, 2.9, 4.3, 1.3, "versicolor"),
    (5.1, 2.5, 3, 1.1, "versicolor"),
    (5.7, 2.8, 4.1, 1.3, "versicolor"),
    (6.3, 3.3, 6, 2.5, "virginica"),
    (5.8, 2.7, 5.1, 1.9, "virginica"),
    (7.1, 3, 5.9, 2.1, "virginica"),
    (6.3, 2.9, 5.6, 1.8, "virginica"),
    (6.5, 3, 5.8, 2.2, "virginica"),
    (7.6, 3, 6.6, 2.1, "virginica"),
    (4.9, 2.5, 4.5, 1.7, "virginica"),
    (7.3, 2.9, 6.3, 1.8, "virginica"),
    (6.7, 2.5, 5.8, 1.8, "virginica"),
    (7.2, 3.6, 6.1, 2.5, "virginica"),
    (6.5, 3.2, 5.1, 2, "virginica"),
    (6.4, 2.7, 5.3, 1.9, "virginica"),
    (6.8, 3, 5.5, 2.1, "virginica"),
    (5.7, 2.5, 5, 2, "virginica"),
    (5.8, 2.8, 5.1, 2.4, "virginica"),
    (6.4, 3.2, 5.3, 2.3, "virginica"),
    (6.5, 3, 5.5, 1.8, "virginica"),
    (7.7, 3.8, 6.7, 2.2, "virginica"),
    (7.7, 2.6, 6.9, 2.3, "virginica"),
    (6, 2.2, 5, 1.5, "virginica"),
    (6.9, 3.2, 5.7, 2.3, "virginica"),
    (5.6, 2.8, 4.9, 2, "virginica"),
    (7.7, 2.8, 6.7, 2, "virginica"),
    (6.3, 2.7, 4.9, 1.8, "virginica"),
    (6.7, 3.3, 5.7, 2.1, "virginica"),
    (7.2, 3.2, 6, 1.8, "virginica"),
    (6.2, 2.8, 4.8, 1.8, "virginica"),
    (6.1, 3, 4.9, 1.8, "virginica"),
    (6.4, 2.8, 5.6, 2.1, "virginica"),
    (7.2, 3, 5.8, 1.6, "virginica"),
    (7.4, 2.8, 6.1, 1.9, "virginica"),
    (7.9, 3.8, 6.4, 2, "virginica"),
    (6.4, 2.8, 5.6, 2.2, "virginica"),
    (6.3, 2.8, 5.1, 1.5, "virginica"),
    (6.1, 2.6, 5.6, 1.4, "virginica"),
    (7.7, 3, 6.1, 2.3, "virginica"),
    (6.3, 3.4, 5.6, 2.4, "virginica"),
    (6.4, 3.1, 5.5, 1.8, "virginica"),
    (6, 3, 4.8, 1.8, "virginica"),
    (6.9, 3.1, 5.4, 2.1, "virginica"),
    (6.7, 3.1, 5.6, 2.4, "virginica"),
    (6.9, 3.1, 5.1, 2.3, "virginica"),
    (5.8, 2.7, 5.1, 1.9, "virginica"),
    (6.8, 3.2, 5.9, 2.3, "virginica"),
    (6.7, 3.3, 5.7, 2.5, "virginica"),
    (6.7, 3, 5.2, 2.3, "virginica"),
    (6.3, 2.5, 5, 1.9, "virginica"),
    (6.5, 3, 5.2, 2, "virginica"),
    (6.2, 3.4, 5.4, 2.3, "virginica"),
    (5.9, 3, 5.1, 1.8, "virginica"),
)


def _as_integer(value):
    """R ``as.integer`` for a query value, with missing as None."""

    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(math.trunc(value))
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if math.isnan(number) or math.isinf(number):
            return None
        return int(math.trunc(number))
    return None


def _seq2(start, end):
    """``rlang::seq2``: an empty integer vector when ``start`` is past ``end``."""

    if start is None or end is None or start > end:
        return []
    return list(range(start, end + 1))


def _iris_body(page, page_size) -> dict:
    """The ``/iris`` payload: one page of iris, the row count, and the page count."""

    n = len(_IRIS)
    if page is None or page_size is None:
        rows = []
        pages = None
    else:
        start = (page - 1) * page_size + 1
        end = start + page_size - 1
        ids = _seq2(start, end)
        kept = [index for index in ids if 1 <= index <= n]
        rows = [_IRIS[index - 1] for index in kept]
        if page_size == 0:
            pages = math.inf
        else:
            pages = math.ceil(n / page_size)
    data = [dict(zip(_COLUMNS, row)) for row in rows]
    return {"data": data, "count": n, "pages": pages}


def _json_text(payload: dict) -> str:
    """``jsonlite::toJSON(..., auto_unbox = TRUE, pretty = TRUE)`` for this object."""

    def _number(value):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, float):
            if math.isnan(value):
                return "NaN"
            if math.isinf(value):
                return "Inf" if value > 0 else "-Inf"
            if value == math.trunc(value) and abs(value) < 2**53:
                return str(int(value))
            return json.dumps(value)
        return json.dumps(value)

    lines = ["{", '  "data": [']
    rows = payload["data"]
    for index, row in enumerate(rows):
        comma = "," if index < len(rows) - 1 else ""
        lines.append("    {")
        items = list(row.items())
        for item_index, (name, value) in enumerate(items):
            item_comma = "," if item_index < len(items) - 1 else ""
            lines.append(f"      {json.dumps(name)}: {_number(value)}{item_comma}")
        lines.append("    }" + comma)
    lines.append("  ],")
    lines.append(f'  "count": {_number(payload["count"])},')
    lines.append(f'  "pages": {_number(payload["pages"])}')
    lines.append("}")
    return "\n".join(lines)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path != "/iris":
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        query = parse_qs(parts.query, keep_blank_values=True)
        page_text = query["page"][0] if "page" in query and query["page"] else None
        limit_text = query["limit"][0] if "limit" in query and query["limit"] else None
        page = _as_integer(null_or(page_text, 1))
        page_size = _as_integer(null_or(limit_text, 20))
        text = _json_text(_iris_body(page, page_size)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(text)))
        self.end_headers()
        self.wfile.write(text)


class _AppProcess:
    """A local stand-in for ``webfakes::new_app_process``."""

    def __init__(self):
        self._httpd = None
        self._thread = None
        self._port = None
        self._lock = threading.Lock()

    def get_state(self) -> str:
        if self._httpd is None:
            return "not running"
        return "running"

    def url(self, path="/", query=None, https=False, domain="127.0.0.1") -> str:
        """Join a URL the way webfakes ``url()`` pastes its pieces."""

        if self.get_state() == "not running":
            self._start()
        if https:
            raise RuntimeError("Web server does support HTTPS")
        if query is not None:
            pairs = "&".join(f"{name}={value}" for name, value in query.items())
            query_text = "?" + pairs
        else:
            query_text = ""
        if path is None:
            path_text = ""
        elif isinstance(path, str):
            path_text = path
        elif isinstance(path, bool):
            path_text = "TRUE" if path else "FALSE"
        else:
            path_text = str(path)
        return f"http://{domain}:{self._port}{path_text}{query_text}"

    def _start(self):
        with self._lock:
            if self._httpd is not None:
                return
            server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            self._port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._httpd = server
            self._thread = thread


def _example_app() -> _AppProcess:
    """Build the cached app. The ``/iris`` route is registered before listen."""

    return _AppProcess()


def example_url(path="/") -> str:
    """Return the example app URL for ``path``.

    The app is created once and reused. ``path`` is appended as written,
    including a leading slash. The default path is ``"/"``.
    """

    check_installed("webfakes")
    env_cache(the, "test_app", _example_app)
    return the["test_app"].url(path)
