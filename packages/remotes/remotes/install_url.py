"""Install a package from a URL that points at a source archive."""

from __future__ import annotations

import os
import re
from typing import Any

from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    _temp_file,
    as_paths,
    call_install_remotes,
    download,
    file_ext,
    message,
    register_remote,
)
from remotes.standardise_dep import NA


def url_remote(url: str, subdir: str | None = None, **_ignored: Any) -> Remote:
    return Remote("url", url=url, subdir=subdir)


def _download(remote: Remote, quiet: bool = False) -> str:
    if not quiet:
        message("Downloading package from url: " + remote.url)
    if re.search(r"\.tar\.gz$", remote.url):
        ext = "tar.gz"
    else:
        ext = file_ext(remote.url)
    bundle = _temp_file("." + ext if ext else "")
    # download() writes the file. Drop the empty placeholder first.
    try:
        os.unlink(bundle)
    except OSError:
        pass
    return download(bundle, remote.url)


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    return {
        "RemoteType": "url",
        "RemoteUrl": remote.url,
        "RemoteSubdir": remote.subdir,
    }


def _package_name(_remote: Remote, **_kwargs: Any) -> Any:
    return NA_CHARACTER


def _sha(_remote: Remote, **_kwargs: Any) -> Any:
    return NA_CHARACTER


def _format(_remote: Remote) -> str:
    return "URL"


register_remote(
    "url",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_url(
    url: Any,
    subdir: str | None = None,
    dependencies: Any = NA,
    upgrade: Any = "default",
    force: bool = False,
    quiet: bool = False,
    build: bool = True,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    repos: Any = None,
    type: str | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Download each url and R CMD INSTALL it. ``lib`` is the library directory."""
    urls = as_paths(url)
    remotes = [url_remote(item, subdir=subdir) for item in urls]
    return call_install_remotes(
        remotes,
        dependencies=dependencies,
        upgrade=upgrade,
        force=force,
        quiet=quiet,
        build=build,
        build_opts=build_opts,
        build_manual=build_manual,
        build_vignettes=build_vignettes,
        repos=repos,
        type=type,
        **kwargs,
    )
