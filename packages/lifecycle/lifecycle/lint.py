"""Lifecycle linters. The search needs lintr, which is not translated."""

from __future__ import annotations

from .rd import LifecycleError, match_which, require_r_packages

_PATTERN = "(?i)[.](r|rmd|qmd|rnw|rhtml|rrst|rtex|rtxt)$"


def lifecycle_linter(packages=None, which=None, symbol_is_undesirable=False):
    """Stop with rlang's message until lintr and xml2 are installed in R."""
    match_which(which)
    require_r_packages(["lintr", "vctrs", "xml2"])
    raise LifecycleError("lintr is not translated.")


def lint_lifecycle(
    packages,
    path=".",
    pattern=_PATTERN,
    which=None,
    symbol_is_undesirable=False,
):
    """Stop with rlang's message until lintr and xml2 are installed in R."""
    match_which(which)
    require_r_packages(["lintr", "vctrs", "xml2"])
    raise LifecycleError("lintr is not translated.")


def lint_tidyverse_lifecycle(
    path=".",
    pattern=_PATTERN,
    which=None,
    symbol_is_undesirable=False,
):
    """Stop with rlang's message until lintr, xml2, and tidyverse are installed."""
    match_which(which)
    require_r_packages(["lintr", "vctrs", "xml2", "tidyverse"])
    return lint_lifecycle(
        packages=None,
        path=path,
        pattern=pattern,
        which=which,
        symbol_is_undesirable=symbol_is_undesirable,
    )
