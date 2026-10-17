"""Install the development repository named in a CRAN package DESCRIPTION."""

from __future__ import annotations

import os
import re
from typing import Any

from remotes.install_bitbucket import install_bitbucket
from remotes.install_core import _temp_file, build_url, download, read_desc
from remotes.install_github import install_github
from remotes.install_gitlab import install_gitlab

_REF = re.compile(r"^(?P<pkg>[^@#]+)(?P<ref>[@#].*)?$")
_DEV = re.compile(
    r"^https?://(?P<domain>github\.com|gitlab\.com|bitbucket\.org)/(?P<username>[^/]+)/(?P<repo>[^/@#]+)(?:/(?P<subdir>[^/@$ ]+))?"
)


def dev_split_ref(package: str) -> tuple[str, str]:
    """Package name and an optional ``@ref`` or ``#ref``. A missing ref is empty."""
    match = _REF.match(package)
    if match is None:
        return package, ""
    ref = match.group("ref")
    return match.group("pkg"), "" if ref is None else ref


def install_dev(package: str, cran_url: str | None = None, **kwargs: Any) -> Any:
    """Read the CRAN DESCRIPTION and install the GitHub, GitLab, or Bitbucket repo.

    ``cran_url`` defaults to https://cloud.r-project.org. Further arguments,
    including ``lib``, are passed to the chosen install function.
    """
    if cran_url is None or cran_url == "@CRAN@":
        cran_url = "https://cloud.r-project.org"
    name, ref = dev_split_ref(package)
    url = build_url(cran_url, "web", "packages", name, "DESCRIPTION")
    dest = _temp_file(".dcf")
    try:
        download(dest, url)
        desc = read_desc(dest)
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    fields = [desc.get("URL"), desc.get("BugReports")]
    fields = [field for field in fields if field]
    if not fields:
        raise RuntimeError("Could not determine development repository")
    urls: list[str] = []
    for field in fields:
        urls.extend(re.split(r"\s*,\s*", field))
    urls = [re.sub(r"/issues/?$", "", item) for item in urls]
    seen: list[tuple[str, str, str, str]] = []
    for item in urls:
        match = _DEV.match(item)
        if match is None:
            continue
        row = (
            match.group("domain"),
            match.group("username"),
            match.group("repo"),
            match.group("subdir") or "",
        )
        if row not in seen:
            seen.append(row)
    if len(seen) != 1:
        raise RuntimeError("Could not determine development repository")
    domain, username, repo, subdir = seen[0]
    parts = [username, repo]
    if subdir:
        parts.append(subdir)
    full_ref = "/".join(parts) + ref
    if domain == "github.com":
        return install_github(full_ref, **kwargs)
    if domain == "gitlab.com":
        return install_gitlab(full_ref, **kwargs)
    return install_bitbucket(full_ref, **kwargs)
