"""Parse a remote git repo specification.

The patterns are the Perl expressions in R/parse-git.R. A named group that
does not participate is an empty string. Stripping a trailing ``.git`` uses
the end of the string, which is ``\\Z`` in Python.
"""

from __future__ import annotations

import re

_SPEC_FIELDS = (
    "package",
    "username",
    "repo",
    "subdir",
    "ref",
    "pull",
    "release",
)
_URL_FIELDS = ("username", "repo", "ref", "pull", "release")


def _perl(pattern: str) -> str:
    """PCRE named groups and the POSIX classes this pattern uses."""
    pattern = pattern.replace("[[:alnum:].]", "[A-Za-z0-9.]")
    pattern = pattern.replace("[[:alpha:]]", "[A-Za-z]")
    pattern = pattern.replace("[[:alnum:]]", "[A-Za-z0-9]")
    return re.sub(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>", r"(?P<\1>", pattern)


def _spec_pattern() -> str:
    package_name_rx = "(?:(?<package>[[:alpha:]][[:alnum:].]*[[:alnum:]])=)?"
    username_rx = "(?:(?<username>[^/]+)/)"
    repo_rx = "(?<repo>[^/@#]+)"
    subdir_rx = "(?:/(?<subdir>[^@#]*[^@#/])/?)?"
    ref_rx = "(?:@(?<ref>[^*].*))"
    pull_rx = "(?:#(?<pull>[0-9]+))"
    release_rx = "(?:@(?<release>[*]release))"
    ref_or_pull_or_release_rx = f"(?:{ref_rx}|{pull_rx}|{release_rx})?"
    return _perl(
        f"^{package_name_rx}{username_rx}{repo_rx}{subdir_rx}{ref_or_pull_or_release_rx}$"
    )


def _url_pattern() -> str:
    prefix_rx = "(?:github[^/:]+[/:])"
    username_rx = "(?:(?<username>[^/]+)/)"
    repo_rx = "(?<repo>[^/@#]+)"
    ref_rx = "(?:(?:tree|commit|releases/tag)/(?<ref>.+$))"
    pull_rx = "(?:pull/(?<pull>.+$))"
    release_rx = "(?:releases/)(?<release>.+$)"
    ref_or_pull_or_release_rx = f"(?:/({ref_rx}|{pull_rx}|{release_rx}))?"
    return _perl(f"{prefix_rx}{username_rx}{repo_rx}{ref_or_pull_or_release_rx}")


_SPEC = re.compile(_spec_pattern())
_URL = re.compile(_url_pattern())


def _fields(match: re.Match[str], names: tuple[str, ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in names:
        value = match.group(name)
        found[name] = "" if value is None else value
    return found


def parse_repo_spec(repo: str) -> dict[str, str]:
    """Parse ``[package=]username/repo[/subdir][#pull|@ref|@*release]``.

    The seven members are always present. A piece the shorthand omits is
    an empty string. ``foo/bar/baz/`` and ``foo/bar/baz`` are the same.
    """
    match = _SPEC.search(repo)
    if match is None:
        raise ValueError(f"Invalid git repo specification: '{repo}'")
    return _fields(match, _SPEC_FIELDS)


parse_github_repo_spec = parse_repo_spec


def parse_github_url(repo: str) -> dict[str, str]:
    """Parse an HTTPS, SSH, or browser GitHub URL.

    ``ref``, ``pull``, and ``release`` are empty strings when that part of
    the URL is absent. A trailing ``.git`` is removed only in that case.
    ``releases/latest`` is stored as ``*release``.
    """
    match = _URL.search(repo)
    if match is None:
        raise ValueError(f"Invalid GitHub URL: '{repo}'")
    params = _fields(match, _URL_FIELDS)
    if params["ref"] == "" and params["pull"] == "" and params["release"] == "":
        params["repo"] = re.sub(r"\.git\Z", "", params["repo"])
    if params["release"] == "latest":
        params["release"] = "*release"
    return params
