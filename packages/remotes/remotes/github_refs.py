"""Pull-request and release markers used as a GitHub ref."""

from __future__ import annotations


def _r_print(shown: str, r_class: str) -> str:
    """print.default of a length-one atomic vector with one class."""
    return f'[1] {shown}\nattr(,"class")\n[1] "{r_class}"'


def _shown_pull(pull) -> str:
    if isinstance(pull, str):
        escaped = pull.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return str(pull)


class GithubPull:
    """A pull id with class github_pull."""

    def __init__(self, pull) -> None:
        self.pull = pull
        self.r_class = "github_pull"

    def __str__(self) -> str:
        return _r_print(_shown_pull(self.pull), self.r_class)

    def __repr__(self) -> str:
        return str(self)


class GithubRelease:
    """NA_integer_ with class github_release.

    ``value`` is None, the Python form of an integer NA. ``na`` records that
    R's value is NA_integer_, which is neither a logical NA nor NaN.
    """

    def __init__(self) -> None:
        self.value = None
        self.integer_na = True
        self.na = "NA_integer_"
        self.r_class = "github_release"

    def __str__(self) -> str:
        return _r_print("NA", self.r_class)

    def __repr__(self) -> str:
        return str(self)


def github_pull(pull):
    """structure(pull, class = "github_pull")."""
    return GithubPull(pull)


def github_release():
    """structure(NA_integer_, class = "github_release")."""
    return GithubRelease()
