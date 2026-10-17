"""Local stand-in for the Storage JSON paths cache_gcs uses."""

from __future__ import annotations

import json
import ssl
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

STORE: dict[str, dict[str, bytes]] = {}
LOCK = threading.Lock()


def _bucket_key(path: str) -> tuple[str, str, str]:
    parsed = urlparse(path)
    bits = [unquote(part) for part in parsed.path.split("/") if part]
    # /upload/storage/v1/b/<bucket>/o   or  /storage/v1/b/<bucket>/o/<key>
    if "b" not in bits:
        return "", "", parsed.path
    index = bits.index("b")
    bucket = bits[index + 1] if len(bits) > index + 1 else ""
    key = ""
    if "o" in bits[index + 2 :]:
        object_at = bits.index("o", index + 2)
        key = "/".join(bits[object_at + 1 :])
    return bucket, key, parsed.query


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, code: int, body: bytes = b"", content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _read(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or 0)
        return self.rfile.read(length) if length else b""

    def do_POST(self) -> None:
        bucket, key, query = _bucket_key(self.path)
        name = parse_qs(query).get("name", [key])[0]
        data = self._read()
        with LOCK:
            STORE.setdefault(bucket, {})[unquote(name)] = data
        self._reply(200, json.dumps({"name": unquote(name)}).encode())

    def do_GET(self) -> None:
        bucket, key, query = _bucket_key(self.path)
        params = parse_qs(query)
        if key and params.get("alt", [""])[0] == "media":
            with LOCK:
                blob = STORE.get(bucket, {}).get(key)
            if blob is None:
                self._reply(404, b"{}")
                return
            self._reply(200, blob, "application/octet-stream")
            return
        prefix = params.get("prefix", [""])[0]
        with LOCK:
            names = sorted(name for name in STORE.get(bucket, {}) if name.startswith(prefix))
        items = [
            {
                "name": name,
                "size": "1",
                "timeCreated": "2020-01-01T00:00:00.000Z",
                "updated": "2020-01-01T00:00:00.000Z",
            }
            for name in names
        ]
        body = {"items": items} if items else {}
        self._reply(200, json.dumps(body).encode())

    def do_DELETE(self) -> None:
        bucket, key, _query = _bucket_key(self.path)
        with LOCK:
            STORE.get(bucket, {}).pop(key, None)
        self._reply(204)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    ready = Path(sys.argv[1])
    folder = Path(tempfile.mkdtemp(prefix="memoise-gcs-"))
    cert = folder / "cert.pem"
    key = folder / "key.pem"
    subprocess.check_call(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key), "-out", str(cert), "-days", "2", "-nodes",
            "-subj", "/CN=www.googleapis.com",
            "-addext", "subjectAltName=DNS:www.googleapis.com,DNS:storage.googleapis.com,IP:127.0.0.1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    ready.write_text(json.dumps({"port": server.server_address[1], "cert": str(cert)}))
    server.serve_forever()


if __name__ == "__main__":
    main()
