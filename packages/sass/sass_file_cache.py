"""Translation of sass::sass_file_cache."""

from ._common import FileCache


def sass_file_cache(dir, max_size=40 * 1024**2, max_age=float("inf")):
    return FileCache(dir, max_size=max_size, max_age=max_age)
