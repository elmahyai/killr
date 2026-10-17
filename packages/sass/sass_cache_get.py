"""Translation of sass::sass_cache_get."""

from .sass_cache_context_dir import sass_cache_context_dir
from .sass_cache_get_dir import sass_cache_get_dir
from ._common import FileCache


def sass_cache_get(cache=True):
    if cache is None or cache is False:
        return None
    if isinstance(cache, FileCache):
        return cache
    directory = cache if isinstance(cache, str) else sass_cache_context_dir()
    return sass_cache_get_dir(directory, create=True)
