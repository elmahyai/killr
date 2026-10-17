"""S3 and Google Cloud Storage caches.

``cache_s3`` speaks the S3 REST calls memoise makes: create the bucket, store a
serialized value, read it back, list keys, and delete the bucket when a key is
dropped. ``drop_key`` deletes the bucket because ``delete_bucket(key, bucket = name)``
binds the bucket twice and the name wins. ``cache_gcs`` deletes one object.
"""

from __future__ import annotations

import json
import os
import pickle
import ssl
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from memoise._cache import _compress, _decompress, _digest_call


def _endpoint(env_name: str, default: str) -> str:
    raw = os.environ.get(env_name, default).strip()
    for prefix in ("https://", "http://"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
    return raw.rstrip("/")


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    bundle = os.environ.get("CURL_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if bundle:
        context.load_verify_locations(bundle)
    return context


def _request(method: str, url: str, data: bytes | None = None, content_type: str | None = None) -> tuple[int, bytes]:
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, context=_ssl_context()) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


class S3Cache:
    """Bucket of serialized values. The file name is the cache key."""

    def __init__(self, cache_name: str, algo: str = "sha512", compress: str | bool = False) -> None:
        self.cache_name = cache_name
        self.algo = algo
        self.compress = compress
        self._tmp = Path(tempfile.mkdtemp(prefix="memoise-"))
        if not self._bucket_exists():
            self._put_bucket()

    def digest(self, *args: Any, **kwargs: Any) -> str:
        return _digest_call(self.algo, *args, **kwargs)

    def _url(self, key: str | None = None) -> str:
        host = _endpoint("AWS_S3_ENDPOINT", "s3.amazonaws.com")
        url = f"https://{host}/{quote(self.cache_name, safe='')}/"
        if key:
            url += quote(key, safe="")
        return url

    def _bucket_exists(self) -> bool:
        status, _ = _request("HEAD", self._url())
        return status == 200

    def _put_bucket(self) -> None:
        status, body = _request("PUT", self._url(), b"")
        if status >= 300:
            raise RuntimeError(body.decode("utf-8", "replace") or f"put bucket failed ({status})")

    def set(self, key: str, value: Any) -> None:
        blob = _compress(pickle.dumps(value, protocol=4), self.compress)
        path = self._tmp / key
        path.write_bytes(blob)
        try:
            status, body = _request("PUT", self._url(key), blob, "application/octet-stream")
            if status >= 300:
                raise RuntimeError(body.decode("utf-8", "replace") or f"put object failed ({status})")
        finally:
            path.unlink(missing_ok=True)

    def get(self, key: str) -> Any:
        status, body = _request("GET", self._url(key))
        if status >= 300:
            raise RuntimeError(body.decode("utf-8", "replace") or f"get object failed ({status})")
        return pickle.loads(_decompress(body, self.compress))

    def has_key(self, key: str) -> bool:
        status, _ = _request("HEAD", self._url(key))
        return status == 200

    def drop_key(self, key: str) -> None:
        # memoise calls delete_bucket(key, bucket = cache_name). The name wins,
        # so the bucket is removed and the key is ignored.
        del key
        _request("DELETE", self._url())

    def reset(self) -> None:
        for key in self.keys():
            self.drop_key(key)

    def keys(self) -> list[str]:
        status, body = _request("GET", self._url())
        if status >= 300:
            raise RuntimeError(body.decode("utf-8", "replace") or f"list bucket failed ({status})")
        root = ET.fromstring(body)
        found = []
        for element in root.iter():
            if element.tag.endswith("Key") and element.text:
                found.append(element.text)
        return found


class GCSCache:
    """Bucket of serialized values on the Google Cloud Storage JSON API."""

    def __init__(self, cache_name: str, algo: str = "sha512", compress: str | bool = False) -> None:
        if not cache_name:
            raise ValueError("cache_name is required")
        self.cache_name = cache_name
        self.algo = algo
        self.compress = compress
        self._tmp = Path(tempfile.mkdtemp(prefix="memoise-"))

    def digest(self, *args: Any, **kwargs: Any) -> str:
        return _digest_call(self.algo, *args, **kwargs)

    def _host(self) -> str:
        return _endpoint("GCS_API_HOST", "www.googleapis.com")

    def set(self, key: str, value: Any) -> None:
        blob = _compress(pickle.dumps(value, protocol=4), self.compress)
        path = self._tmp / key
        path.write_bytes(blob)
        try:
            url = (
                f"https://{self._host()}/upload/storage/v1/b/{quote(self.cache_name, safe='')}/o"
                f"?uploadType=media&name={quote(key, safe='')}"
            )
            status, body = _request("POST", url, blob, "application/octet-stream")
            if status >= 300:
                raise RuntimeError(body.decode("utf-8", "replace") or f"upload failed ({status})")
        finally:
            path.unlink(missing_ok=True)

    def get(self, key: str) -> Any:
        url = (
            f"https://{self._host()}/storage/v1/b/{quote(self.cache_name, safe='')}/o/"
            f"{quote(key, safe='')}?alt=media"
        )
        status, body = _request("GET", url)
        if status >= 300:
            raise RuntimeError(body.decode("utf-8", "replace") or f"download failed ({status})")
        return pickle.loads(_decompress(body, self.compress))

    def has_key(self, key: str) -> bool:
        return key in self.keys(prefix=key)

    def drop_key(self, key: str) -> None:
        url = (
            f"https://{self._host()}/storage/v1/b/{quote(self.cache_name, safe='')}/o/"
            f"{quote(key, safe='')}"
        )
        status, body = _request("DELETE", url)
        if status >= 300 and status != 404:
            raise RuntimeError(body.decode("utf-8", "replace") or f"delete failed ({status})")

    def reset(self) -> None:
        for key in list(self.keys()):
            self.drop_key(key)

    def keys(self, prefix: str | None = None) -> list[str]:
        url = f"https://{self._host()}/storage/v1/b/{quote(self.cache_name, safe='')}/o"
        if prefix:
            url += "?prefix=" + quote(prefix, safe="")
        status, body = _request("GET", url)
        if status >= 300:
            raise RuntimeError(body.decode("utf-8", "replace") or f"list failed ({status})")
        payload = json.loads(body.decode() or "{}")
        names = []
        for item in payload.get("items", []):
            name = item.get("name")
            if name:
                names.append(name)
        return names


def cache_s3(cache_name: str, algo: str = "sha512", compress: str | bool = False) -> S3Cache:
    return S3Cache(cache_name, algo=algo, compress=compress)


def cache_gcs(cache_name: str, algo: str = "sha512", compress: str | bool = False) -> GCSCache:
    return GCSCache(cache_name, algo=algo, compress=compress)
