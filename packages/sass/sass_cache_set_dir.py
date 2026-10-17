"""Translation of sass::sass_cache_set_dir."""

from pathlib import Path
from ._common import _caches, FileCache


def sass_cache_set_dir(dir, cache):
    if cache is not None and not isinstance(cache, FileCache):
        raise TypeError("`cache` must be a FileCache object or NULL.")
    path = Path(dir).expanduser()
    if not path.is_dir():
        raise FileNotFoundError("`dir` does not exist.")
    key = str(path.resolve(strict=True))
    if cache is None:
        _caches.pop(key, None)
        return None
    if key != str(Path(cache.dir()).resolve(strict=True)):
        raise ValueError("`dir` and the cache object's directory do not match.")
    _caches[key] = cache
    return cache
