"""Translation of sass::sass_cache_get_dir."""

from pathlib import Path
from ._common import _caches
from .sass_file_cache import sass_file_cache


def sass_cache_get_dir(dir, create=False):
    path = Path(dir).expanduser()
    if create:
        path.mkdir(parents=True, exist_ok=True)
        path = path.resolve(strict=True)
        key = str(path)
        if key not in _caches:
            _caches[key] = sass_file_cache(key)
        return _caches[key]
    if not path.is_dir():
        raise FileNotFoundError(f"`dir` does not exist.")
    return _caches.get(str(path.resolve(strict=True)))
