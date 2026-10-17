"""Memory and filesystem caches used by memoise.

``cache_memory`` and ``cache_filesystem`` are the old-style caches. They carry
a ``digest`` method, and ``memoise`` uses that as the key function. The default
cache inside ``memoise`` is a dictionary with the same get/set/exists/remove
methods ``cachem::cache_mem`` provides to memoise.
"""

from __future__ import annotations

import bz2
import gzip
import lzma
import pickle
import time
from pathlib import Path
from typing import Any, Callable

from memoise._hash import hash_object


class KeyMissing:
    """Returned by ``get`` when the key is absent or older than ``max_age``."""


def _digest_call(algo: str, *args: Any, **kwargs: Any) -> str:
    if args:
        obj = args[0]
    elif "object" in kwargs:
        obj = kwargs["object"]
    else:
        raise TypeError("digest() missing the object to hash")
    return hash_object(obj, algo)


class CacheMem:
    """Dictionary cache. ``max_size`` is recorded and does not evict entries."""

    def __init__(
        self,
        max_size: int = 1024 * 1024**2,
        max_age: float | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.max_size = max_size
        self.max_age = max_age
        self._clock = clock or time.time
        self._data: dict[Any, Any] = {}
        self._when: dict[Any, float] = {}

    def reset(self) -> None:
        self._data.clear()
        self._when.clear()

    def set(self, key: Any, value: Any) -> None:
        self._data[key] = value
        self._when[key] = self._clock()

    def exists(self, key: Any) -> bool:
        if key not in self._data:
            return False
        if self.max_age is not None and self._clock() - self._when[key] > self.max_age:
            self.remove(key)
            return False
        return True

    def get(self, key: Any) -> Any:
        if not self.exists(key):
            return KeyMissing()
        return self._data[key]

    def remove(self, key: Any) -> None:
        self._data.pop(key, None)
        self._when.pop(key, None)

    def keys(self) -> list[Any]:
        return list(self._data)


class _OldCache:
    def __init__(self, algo: str) -> None:
        self.algo = algo
        self._data: dict[str, Any] = {}

    def digest(self, *args: Any, **kwargs: Any) -> str:
        return _digest_call(self.algo, *args, **kwargs)

    def reset(self) -> None:
        self._data.clear()

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str) -> Any:
        return self._data[key]

    def has_key(self, key: str) -> bool:
        return key in self._data

    def drop_key(self, key: str) -> None:
        del self._data[key]

    def keys(self) -> list[str]:
        return list(self._data)


class MemoryCache(_OldCache):
    """Session cache. The key hash uses ``algo`` (default ``sha512``)."""

    def __init__(self, algo: str = "sha512") -> None:
        super().__init__(algo)


class FilesystemCache:
    """Directory of pickled values. The file name is the cache key."""

    def __init__(self, path: str, algo: str = "xxhash64", compress: str | bool = False) -> None:
        folder = Path(path)
        if not folder.is_dir():
            folder.mkdir()
        self.path = folder.resolve()
        self.algo = algo
        self.compress = compress

    def digest(self, *args: Any, **kwargs: Any) -> str:
        return _digest_call(self.algo, *args, **kwargs)

    def _file(self, key: str) -> Path:
        if not key or key in {".", ".."} or "/" in key or "\\" in key:
            raise ValueError("cache key must be a file name")
        return self.path / key

    def reset(self) -> None:
        for item in self.path.iterdir():
            if item.is_file():
                item.unlink()

    def set(self, key: str, value: Any) -> None:
        blob = pickle.dumps(value, protocol=4)
        self._file(key).write_bytes(_compress(blob, self.compress))

    def get(self, key: str) -> Any:
        blob = _decompress(self._file(key).read_bytes(), self.compress)
        return pickle.loads(blob)

    def has_key(self, key: str) -> bool:
        return self._file(key).is_file()

    def drop_key(self, key: str) -> None:
        self._file(key).unlink()

    def keys(self) -> list[str]:
        return sorted(item.name for item in self.path.iterdir() if item.is_file())


def _compress(blob: bytes, compress: str | bool) -> bytes:
    if compress in (False, None):
        return blob
    if compress == "gzip":
        return gzip.compress(blob)
    if compress == "bzip2":
        return bz2.compress(blob)
    if compress == "xz":
        return lzma.compress(blob)
    raise ValueError('compress must be FALSE, "gzip", "bzip2", or "xz"')


def _decompress(blob: bytes, compress: str | bool) -> bytes:
    if compress in (False, None):
        return blob
    if compress == "gzip":
        return gzip.decompress(blob)
    if compress == "bzip2":
        return bz2.decompress(blob)
    if compress == "xz":
        return lzma.decompress(blob)
    raise ValueError('compress must be FALSE, "gzip", "bzip2", or "xz"')


def is_old_cache(cache: Any) -> bool:
    return all(callable(getattr(cache, name, None)) for name in ("digest", "set", "get", "has_key"))


class WrappedCache:
    """Old-style cache with ``get`` returning ``KeyMissing`` on a miss."""

    def __init__(self, cache: Any) -> None:
        if not is_old_cache(cache):
            raise ValueError("`x` must be an old-style cache.")
        self._cache = cache

    def digest(self, *args: Any, **kwargs: Any) -> str:
        return self._cache.digest(*args, **kwargs)

    def reset(self) -> None:
        self._cache.reset()

    def set(self, key: Any, value: Any) -> None:
        self._cache.set(key, value)

    def get(self, key: Any) -> Any:
        if not self._cache.has_key(key):
            return KeyMissing()
        return self._cache.get(key)

    def exists(self, key: Any) -> bool:
        return self._cache.has_key(key)

    def remove(self, key: Any) -> None:
        self._cache.drop_key(key)

    def keys(self) -> Any:
        return self._cache.keys()


def cache_memory(algo: str = "sha512") -> MemoryCache:
    return MemoryCache(algo)


def cache_filesystem(path: str, algo: str = "xxhash64", compress: str | bool = False) -> FilesystemCache:
    return FilesystemCache(path, algo=algo, compress=compress)
