"""Install a package from a GitLab repository archive."""

from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any

from remotes.github_remote import parse_git_repo
from remotes.gitlab_pat import gitlab_pat
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


def _quote(text: str) -> str:
    return urllib.parse.quote(str(text), safe="")


def gitlab_remote(
    repo: str,
    subdir: str | None = None,
    auth_token: str | None = None,
    sha: str | None = None,
    host: str = "gitlab.com",
    **_ignored: Any,
) -> Remote:
    meta = parse_git_repo(repo)
    ref = meta.get("ref") if meta.get("ref") not in (None, "") else "HEAD"
    repo_name = meta.get("repo") or ""
    spec_subdir = meta.get("subdir")
    if spec_subdir:
        repo_name = repo_name + "/" + spec_subdir
    return Remote(
        "gitlab",
        host=host,
        repo=repo_name,
        subdir=subdir,
        username=meta.get("username"),
        ref=ref,
        sha=sha,
        auth_token=auth_token,
    )


def _headers(remote: Any) -> dict[str, str]:
    token = getattr(remote, "auth_token", None)
    if token:
        return {"Private-Token": token}
    return {}


def _project_id(remote: Any) -> str:
    url = build_url(
        remote.host,
        "api",
        "v4",
        "projects",
        _quote(f"{remote.username}/{remote.repo}"),
        "repository",
        "commits",
        _quote(remote.ref or "HEAD"),
    )
    dest = _temp_file(".json")
    try:
        download(dest, url, headers=_headers(remote))
        with open(dest, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    return str(payload["project_id"])


def _download(remote: Remote, quiet: bool = False) -> str:
    dest = _temp_file(".tar.gz")
    try:
        os.unlink(dest)
    except OSError:
        pass
    project_id = _project_id(remote)
    src_root = build_url(remote.host, "api", "v4", "projects", project_id)
    src = src_root + "/repository/archive.tar.gz?sha=" + _quote(remote.ref)
    if not quiet:
        message(
            f"Downloading GitLab repo {remote.username}/{remote.repo}@{remote.ref}\nfrom URL {src}"
        )
    return download(dest, src, headers=_headers(remote))


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    if bundle is not None:
        extracted = git_extract_sha1_tar(bundle)
        if extracted:
            sha = extracted
    elif is_na(sha):
        sha = None
    return {
        "RemoteType": "gitlab",
        "RemoteHost": remote.host,
        "RemoteRepo": remote.repo,
        "RemoteUsername": remote.username,
        "RemoteRef": remote.ref,
        "RemoteSha": sha,
        "RemoteSubdir": remote.subdir,
    }


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    src_root = build_url(
        remote.host,
        "api",
        "v4",
        "projects",
        _quote(f"{remote.username}/{remote.repo}"),
        "repository",
    )
    desc = "DESCRIPTION" if not remote.subdir else _quote(remote.subdir + "/DESCRIPTION")
    src = src_root + "/files/" + desc + "/raw?ref=" + _quote(remote.ref)
    dest = _temp_file(".dcf")
    try:
        download(dest, src, headers=_headers(remote))
        return read_desc(dest).get("Package", remote.repo)
    except Exception:
        return remote.repo
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    url = build_url(
        remote.host,
        "api",
        "v4",
        "projects",
        _quote(f"{remote.username}/{remote.repo}"),
        "repository",
        "commits",
        _quote(remote.ref or "HEAD"),
    )
    dest = _temp_file(".json")
    try:
        download(dest, url, headers=_headers(remote))
        with open(dest, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    return payload.get("id", NA_CHARACTER)


def _format(_remote: Remote) -> str:
    return "GitLab"


register_remote(
    "gitlab",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_gitlab(
    repo: Any,
    subdir: str | None = None,
    auth_token: Any = _TOKEN,
    host: str = "gitlab.com",
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
    """Install GitLab repos. ``lib`` is the library directory.

    The default token is ``GITLAB_PAT`` when that variable is non-empty.
    """
    if auth_token is _TOKEN:
        auth_token = gitlab_pat(quiet=bool(quiet))
    specs = as_paths(repo)
    remotes = [
        gitlab_remote(spec, subdir=subdir, auth_token=auth_token, host=host) for spec in specs
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
