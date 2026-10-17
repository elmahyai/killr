"""Local S3 stand-in used by the cache_s3 check.

Ignores signatures. Stores each object's bytes and deletes the whole bucket
on DELETE of the bucket URL.
"""

from __future__ import annotations

import json
import ssl
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

STORE: dict[str, dict[str, bytes]] = {}
LOCK = threading.Lock()


def _parts(path: str) -> tuple[str, str]:
    parsed = urlparse(path)
    bits = [unquote(part) for part in parsed.path.split("/") if part]
    bucket = bits[0] if bits else ""
    key = "/".join(bits[1:])
    return bucket, key


def _list_xml(bucket: str) -> bytes:
    with LOCK:
        keys = sorted(STORE.get(bucket, {}))
    contents = "".join(f"<Contents><Key>{key}</Key><Size>1</Size></Contents>" for key in keys)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Name>{bucket}</Name><IsTruncated>false</IsTruncated>{contents}"
        "</ListBucketResult>"
    )
    return xml.encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, code: int, body: bytes = b"", content_type: str = "application/xml") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        bucket, key = _parts(self.path)
        with LOCK:
            exists = bucket in STORE and (not key or key in STORE[bucket])
        self._reply(200 if exists else 404)

    def do_PUT(self) -> None:
        bucket, key = _parts(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        data = self.rfile.read(length) if length else b""
        with LOCK:
            STORE.setdefault(bucket, {})
            if key:
                STORE[bucket][key] = data
        self._reply(200)

    def do_GET(self) -> None:
        bucket, key = _parts(self.path)
        with LOCK:
            missing = bucket not in STORE
            blob = None if missing or not key else STORE[bucket].get(key)
        if missing or (key and blob is None):
            self._reply(404, b"<Error><Code>NoSuchKey</Code></Error>")
            return
        if key:
            self._reply(200, blob or b"", "application/octet-stream")
            return
        self._reply(200, _list_xml(bucket))

    def do_DELETE(self) -> None:
        bucket, key = _parts(self.path)
        with LOCK:
            if key:
                STORE.get(bucket, {}).pop(key, None)
            else:
                STORE.pop(bucket, None)
        self._reply(204)

    def log_message(self, fmt: str, *args) -> None:
        return


def _certificate(folder: Path) -> tuple[Path, Path]:
    cert = folder / "cert.pem"
    key = folder / "key.pem"
    subprocess.check_call(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key), "-out", str(cert), "-days", "2", "-nodes",
            "-subj", "/CN=127.0.0.1",
            "-addext", "subjectAltName=IP:127.0.0.1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cert, key


def main() -> None:
    ready = Path(sys.argv[1])
    folder = Path(tempfile.mkdtemp(prefix="memoise-s3-"))
    cert, key = _certificate(folder)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    ready.write_text(json.dumps({"port": server.server_address[1], "cert": str(cert)}))
    server.serve_forever()


if __name__ == "__main__":
    main()
