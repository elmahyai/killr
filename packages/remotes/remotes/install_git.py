"""Install a package by cloning a git repository."""

from __future__ import annotations

import os
import re
import warnings
from typing import Any

from remotes.git_credentials import git_credentials
from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    as_paths,
    call_install_remotes,
    is_na,
    match_arg,
    message,
    register_remote,
    run_git,
)
from remotes.standardise_dep import NA

_URL = re.compile(
    r"(?P<protocol>[^/]*://)?(?P<authhost>[^/]+)(?P<path>[^@]*)(@(?P<ref>.*))?"
)


def _parse_git_url(url: str) -> tuple[str, str | None]:
    """The same groups as git_remote. A leading slash is not part of authhost."""
    match = _URL.search(url)
    if match is None:
        return url, None
    protocol = match.group("protocol") or ""
    authhost = match.group("authhost") or ""
    path = match.group("path") or ""
    ref = match.group("ref")
    if ref == "":
        ref = None
    return protocol + authhost + path, ref


def git_remote(
    url: str,
    subdir: str | None = None,
    ref: str | None = None,
    credentials: Any = None,
    git: str = "external",
    **_ignored: Any,
) -> Remote:
    parsed, url_ref = _parse_git_url(url)
    chosen = ref if ref is not None else url_ref
    if git == "git2r":
        return Remote("git2r", url=parsed, subdir=subdir, ref=chosen, credentials=credentials)
    return Remote("xgit", url=parsed, subdir=subdir, ref=chosen, args=None)


def _download_xgit(remote: Remote, quiet: bool = False) -> str:
    if not quiet:
        message("Downloading git repo " + remote.url)
    parent = __import__("tempfile").mkdtemp()
    bundle = os.path.join(parent, "repo")
    args = ["clone", "--depth", "1", "--no-hardlinks", remote.url, bundle]
    run_git(args, quiet=quiet)
    if remote.ref is not None:
        run_git(["fetch", "origin", remote.ref], quiet=quiet, path=bundle)
        run_git(["checkout", "FETCH_HEAD"], quiet=quiet, path=bundle)
    return bundle


def _metadata_xgit(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    if is_na(sha):
        sha = None
    args = getattr(remote, "args", None)
    return {
        "RemoteType": "xgit",
        "RemoteUrl": remote.url,
        "RemoteSubdir": remote.subdir,
        "RemoteRef": remote.ref,
        "RemoteSha": sha,
        "RemoteArgs": " ".join(args) if args else None,
    }


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    # The DESCRIPTION lookup over the network is skipped when the clone will
    # supply the name. An unknown name is NA, and install() reads DESCRIPTION.
    return NA_CHARACTER


def _sha_xgit(remote: Remote, **_kwargs: Any) -> Any:
    ref = remote.ref
    args = ["ls-remote", remote.url]
    if ref is not None:
        args.append(ref)
    try:
        lines = run_git(args, quiet=True)
    except RuntimeError:
        return remote.ref if remote.ref is not None else NA_CHARACTER
    if not lines:
        return remote.ref if remote.ref is not None else NA_CHARACTER
    sha = lines[0].split("\t", 1)[0].strip()
    return sha or NA_CHARACTER


def _format(_remote: Remote) -> str:
    return "Git"


def _download_git2r(remote: Remote, quiet: bool = False) -> str:
    raise RuntimeError("git2r is not installed; use git = \"external\"")


register_remote(
    "xgit",
    download=_download_xgit,
    metadata=_metadata_xgit,
    package_name=_package_name,
    sha=_sha_xgit,
    fmt=_format,
)
register_remote(
    "git2r",
    download=_download_git2r,
    metadata=_metadata_xgit,
    package_name=_package_name,
    sha=_sha_xgit,
    fmt=_format,
)


def _git2r_installed() -> bool:
    for lib in __import__("remotes.install_core", fromlist=["session_lib_paths"]).session_lib_paths():
        if os.path.isfile(os.path.join(lib, "git2r", "DESCRIPTION")):
            return True
    return False


def install_git(
    url: Any,
    subdir: str | None = None,
    ref: str | None = None,
    branch: Any = None,
    credentials: Any = None,
    git: str = "auto",
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
    """Clone git urls and R CMD INSTALL them. ``lib`` is the library directory.

    ``branch`` is the deprecated name of ``ref``. ``git = "auto"`` uses an
    external git client when the git2r package is not installed.
    """
    if branch is not None:
        warnings.warn("`branch` is deprecated, please use `ref`", stacklevel=2)
        ref = branch
    if credentials is None:
        credentials = git_credentials()
    chosen = match_arg(git, ["auto", "git2r", "external"])
    if chosen == "auto":
        chosen = "git2r" if _git2r_installed() else "external"
    if credentials is not None and chosen != "git2r":
        raise RuntimeError('`credentials` can only be used with `git = "git2r"`')
    urls = as_paths(url)
    remotes = [
        git_remote(item, subdir=subdir, ref=ref, credentials=credentials, git=chosen)
        for item in urls
    ]
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
