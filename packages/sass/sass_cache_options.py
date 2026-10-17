"""Deprecated sass::sass_cache_options compatibility function."""

import warnings


def sass_cache_options(cache=None, cache_dir=None):
    warnings.warn(
        "The function `sass_cache_options` is no longer used. "
        "Please see sass_cache_set_dir and sass_file_cache.",
        UserWarning,
        stacklevel=2,
    )
    return None
