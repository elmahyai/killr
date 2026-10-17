"""Install a package from a Bitbucket repository archive."""

from __future__ import annotations

import json
import os
from typing import Any

from remotes.github_remote import parse_git_repo
from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    _temp_file,
    as_paths,
    build_url,
    call_install_remotes,
    download,
    git_extract_sha1_tar,
    is_na,
    message,
    read_desc,
    register_remote,
)
from remotes.standardise_dep import NA

_TOKEN = object()


def bitbucket_user() -> str | None:
    user = os.environ.get("BITBUCKET_USER")
    if user is None or user == "":
        return None
    return user


def bitbucket_password(quiet: bool = True) -> str | None:
    password = os.environ.get("BITBUCKET_PASSWORD")
    if password is None or password == "":
        return None
    if not quiet:
        message("Using bitbucket password from envvar BITBUCKET_PASSWORD")
    return password


def _or_missing(left: Any, right: Any) -> Any:
    if left is None or left == "":
        return right
    return left


def bitbucket_remote(
    repo: str,
    ref: str = "HEAD",
    subdir: str | None = None,
    auth_user: str | None = None,
    password: str | None = None,
    sha: str | None = None,
    host: str = "api.bitbucket.org/2.0",
    **_ignored: Any,
) -> Remote:
    meta = parse_git_repo(repo)
    return Remote(
        "bitbucket",
        repo=meta.get("repo"),
        subdir=_or_missing(meta.get("subdir"), subdir),
        username=meta.get("username"),
        ref=_or_missing(meta.get("ref"), ref),
        sha=sha,
        auth_user=auth_user,
        password=password,
        host=host,
    )


def basic_auth(remote: Any) -> dict[str, str] | None:
    if getattr(remote, "password", None):
        return {
            "user": remote.auth_user or remote.username,
            "password": remote.password,
        }
    return None


def _download_url(remote: Remote) -> str:
    url = build_url(remote.host, "repositories", remote.username, remote.repo)
    dest = _temp_file(".json")
    try:
        download(dest, url, basic_auth=basic_auth(remote))
        with open(dest, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    href = payload["links"]["html"]["href"]
    return build_url(href, "get", remote.ref) + ".tar.gz"


def _download(remote: Remote, quiet: bool = False) -> str:
    if not quiet:
        message(f"Downloading bitbucket repo {remote.username}/{remote.repo}@{remote.ref}")
    dest = _temp_file(".tar.gz")
    try:
        os.unlink(dest)
    except OSError:
        pass
    return download(dest, _download_url(remote), basic_auth=basic_auth(remote))


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    if bundle is not None:
        extracted = git_extract_sha1_tar(bundle)
        if extracted:
            sha = extracted
    elif is_na(sha):
        sha = None
    return {
        "RemoteType": "bitbucket",
        "RemoteHost": remote.host,
        "RemoteRepo": remote.repo,
        "RemoteUsername": remote.username,
        "RemoteRef": remote.ref,
        "RemoteSha": sha,
        "RemoteSubdir": remote.subdir,
    }


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    url = build_url(
        remote.host,
        "repositories",
        remote.username,
        remote.repo,
        "src",
        remote.ref,
        remote.subdir,
        "DESCRIPTION",
    )
    dest = _temp_file(".dcf")
    try:
        download(dest, url, basic_auth=basic_auth(remote))
        return read_desc(dest).get("Package", NA_CHARACTER)
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    url = build_url(remote.host, "repositories", remote.username, remote.repo, "commit", remote.ref)
    dest = _temp_file(".json")
    try:
        download(dest, url, basic_auth=basic_auth(remote))
        with open(dest, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    value = payload.get("hash")
    if value is None or value == "":
        return NA_CHARACTER
    return value


def _format(_remote: Remote) -> str:
    return "Bitbucket"


register_remote(
    "bitbucket",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_bitbucket(
    repo: Any,
    ref: str = "HEAD",
    subdir: str | None = None,
    auth_user: Any = _TOKEN,
    password: Any = _TOKEN,
    host: str = "api.bitbucket.org/2.0",
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
    """Install Bitbucket repos. ``lib`` is the library directory.

    The default user and password are ``BITBUCKET_USER`` and ``BITBUCKET_PASSWORD``.
    """
    if auth_user is _TOKEN:
        auth_user = bitbucket_user()
    if password is _TOKEN:
        password = bitbucket_password(quiet=bool(quiet))
    specs = as_paths(repo)
    remotes = [
        bitbucket_remote(
            spec,
            ref=ref,
            subdir=subdir,
            auth_user=auth_user,
            password=password,
            host=host,
        )
        for spec in specs
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
