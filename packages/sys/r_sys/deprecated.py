"""Deprecated forks. They now live in the unix package, which is not translated."""

import warnings

_UNIX = "there is no package called \u2018unix\u2019"


def _deprecated(name):
    warnings.warn(
        f"'{name}' is deprecated.\n"
        f"Use 'unix::{name}' instead.\n"
        'See help("Deprecated") and help("sys-deprecated").',
        stacklevel=3,
    )
    raise RuntimeError(_UNIX)


def eval_safe(*_args, **_kwargs):
    """Deprecated. The unix package is not translated."""
    _deprecated("eval_safe")


def eval_fork(*_args, **_kwargs):
    """Deprecated. The unix package is not translated."""
    _deprecated("eval_fork")
