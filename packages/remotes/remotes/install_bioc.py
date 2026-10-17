"""Install a development package from the Bioconductor git repository."""

from __future__ import annotations

import os
import re
from typing import Any

from remotes.bioc import _devel_version, _release_version
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

_BIOC = re.compile(
    r"^(?:(?:(?P<username>[^:]+):(?P<password>[^:@]+)@)?"
    r"(?:(?P<release>devel|release|[0-9.]+)/)?"
    r"(?P<repo>[^/@#]+)"
    r"(?:#(?P<commit>[a-zA-Z0-9]+))?|(?P<invalid>.*))$"
)


def parse_bioc_repo(path: str) -> dict[str, str]:
    """``[username:password@][release/]repo[#commit]``."""
    match = _BIOC.match(path)
    if match is None:
        raise RuntimeError(f"Invalid bioc repo: {path}")
    invalid = match.group("invalid")
    if invalid:
        raise RuntimeError(f"Invalid bioc repo: {path}")
    params = {
        name: match.group(name)
        for name in ("username", "password", "release", "repo", "commit")
        if match.group(name)
    }
    if "release" in params and "commit" in params:
        raise RuntimeError("release and commit should not both be specified")
    return params


def bioconductor_branch(release: str | None, sha: str | None) -> str:
    """Branch name. A commit stored as sha wins. Callers pass the parsed sha, which is unset."""
    if sha is not None:
        return sha
    if release is None:
        release = os.environ.get("R_BIOC_VERSION", "release") or "release"
    if release == "release":
        release = str(_release_version())
    elif release == str(_devel_version()):
        release = "devel"
    if release.lower() == "devel":
        return "HEAD"
    return "RELEASE_" + release.replace(".", "_")


def _bioc_remote(repo: str, mirror: str, kind: str) -> Remote:
    meta = parse_bioc_repo(repo)
    # R passes meta$sha, which this parser does not set, so the commit is not the branch.
    branch = bioconductor_branch(meta.get("release"), meta.get("sha"))
    return Remote(
        kind,
        mirror=mirror,
        repo=meta.get("repo"),
        release=meta.get("release") or "release",
        sha=meta.get("commit"),
        branch=branch,
        credentials=None,
        args=None,
    )


def bioc_remote(repo: str, mirror: str, git: str = "external", **_ignored: Any) -> Remote:
    if git == "git2r":
        return _bioc_remote(repo, mirror, "bioc_git2r")
    return _bioc_remote(repo, mirror, "bioc_xgit")


def _clone(remote: Remote, quiet: bool) -> str:
    url = remote.mirror.rstrip("/") + "/" + remote.repo
    if not quiet:
        message("Downloading Bioconductor repo " + url)
    parent = __import__("tempfile").mkdtemp()
    bundle = os.path.join(parent, "repo")
    args = ["clone", "--depth", "1", "--no-hardlinks"]
    if remote.branch and remote.branch != "HEAD":
        args.extend(["--branch", remote.branch])
    extra = getattr(remote, "args", None)
    if extra:
        args.extend(str(item) for item in extra)
    args.extend([url, bundle])
    run_git(args, quiet=quiet)
    return bundle


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    if is_na(sha):
        sha = None
    meta = {
        "RemoteType": "bioc_xgit" if remote.kind == "bioc_xgit" else "bioc_git2r",
        "RemoteMirror": remote.mirror,
        "RemoteRepo": remote.repo,
        "RemoteRelease": remote.release,
        "RemoteSha": sha,
        "RemoteBranch": remote.branch,
    }
    args = getattr(remote, "args", None)
    if remote.kind == "bioc_xgit":
        meta["RemoteArgs"] = " ".join(str(item) for item in args) if args else None
    return meta


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    return remote.repo


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    url = remote.mirror.rstrip("/") + "/" + remote.repo
    try:
        lines = run_git(["ls-remote", url, remote.branch or "HEAD"], quiet=True)
    except RuntimeError:
        return NA_CHARACTER
    if not lines:
        return NA_CHARACTER
    sha = lines[0].split("\t", 1)[0].strip()
    return sha or NA_CHARACTER


def _format(_remote: Remote) -> str:
    return "Bioc"


def _download_git2r(remote: Remote, quiet: bool = False) -> str:
    raise RuntimeError("git2r is not installed; use git = \"external\"")


register_remote("bioc_xgit", download=_clone, metadata=_metadata, package_name=_package_name, sha=_sha, fmt=_format)
register_remote(
    "bioc_git2r",
    download=_download_git2r,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def _default_mirror() -> str:
    mirror = os.environ.get("BioC_git")
    if mirror:
        return mirror
    return "https://git.bioconductor.org/packages"


def install_bioc(
    repo: Any,
    mirror: str | None = None,
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
    """Clone Bioconductor git repos and R CMD INSTALL them. ``lib`` is the library.

    ``git = "auto"`` uses an external git client. The release branch comes from
    the Bioconductor config when the specification does not name one.
    """
    if mirror is None:
        mirror = _default_mirror()
    chosen = match_arg(git, ["auto", "git2r", "external"])
    if chosen == "auto":
        chosen = "external"
    specs = as_paths(repo)
    remotes = [bioc_remote(spec, mirror=mirror, git=chosen) for spec in specs]
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
