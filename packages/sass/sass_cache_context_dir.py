"""Translation of sass::sass_cache_context_dir.

The hosted Shiny/R-session branch has no Python equivalent; this preserves the
ordinary user cache path and its directory-creation/fallback behavior.
"""

from ._common import cache_context_dir


def sass_cache_context_dir():
    return cache_context_dir()
