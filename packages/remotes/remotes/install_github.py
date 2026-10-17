"""Install a package from a GitHub repository archive."""

from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any

from remotes.github_remote import github_remote
from remotes.install_core import (
    NA_CHARACTER,
    _temp_file,
    as_paths,
    build_url,
    call_install_remotes,
    download,
    find_installed_description,
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


def _download(remote: Any, quiet: bool = False) -> str:
    if not quiet:
        message(f"Downloading GitHub repo {remote.username}/{remote.repo}@{remote.ref}")
    dest = _temp_file(".tar.gz")
    try:
        os.unlink(dest)
    except OSError:
        pass
    src_root = build_url(remote.host, "repos", remote.username, remote.repo)
    src = src_root + "/tarball/" + _quote(remote.ref)
    token = remote.auth_token if remote.auth_token else None
    return download(dest, src, auth_token=token)


def _metadata(remote: Any, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    if bundle is not None:
        extracted = git_extract_sha1_tar(bundle)
        if extracted:
            sha = extracted
    elif is_na(sha):
        sha = None
    return {
        "RemoteType": "github",
        "RemoteHost": remote.host,
        "RemotePackage": getattr(remote, "package", None),
        "RemoteRepo": remote.repo,
        "RemoteUsername": remote.username,
        "RemoteRef": remote.ref,
        "RemoteSha": sha,
        "RemoteSubdir": remote.subdir,
        "GithubRepo": remote.repo,
        "GithubUsername": remote.username,
        "GithubRef": remote.ref,
        "GithubSHA1": sha,
        "GithubSubdir": remote.subdir,
    }


def _package_name(remote: Any, **_kwargs: Any) -> Any:
    if getattr(remote, "package", None):
        return remote.package
    installed = find_installed_description(remote.repo)
    if installed is not None and installed.get("Package"):
        return installed["Package"]
    try:
        text = _github_description(remote)
    except Exception:
        return NA_CHARACTER
    if not text:
        return NA_CHARACTER
    path = _temp_file(".dcf")
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text if text.endswith("\n") else text + "\n")
        return read_desc(path).get("Package", NA_CHARACTER)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _github_description(remote: Any) -> str:
    subdir = remote.subdir
    url = build_url(remote.host, "repos", remote.username, remote.repo, "contents", subdir, "DESCRIPTION")
    url = url + "?ref=" + _quote(remote.ref or "HEAD")
    dest = _temp_file(".json")
    token = remote.auth_token if remote.auth_token else None
    try:
        download(dest, url, auth_token=token, headers={"Accept": "application/vnd.github.v3.raw"})
        with open(dest, "rb") as handle:
            payload = handle.read()
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    text = payload.decode("utf-8", errors="replace")
    if text.lstrip().startswith("{"):
        parsed = json.loads(text)
        content = parsed.get("content")
        if isinstance(content, str):
            import base64

            return base64.b64decode(content).decode("utf-8", errors="replace")
    return text


def _sha(remote: Any, **_kwargs: Any) -> Any:
    url = build_url(remote.host, "repos", remote.username, remote.repo, "commits", _quote(remote.ref or "HEAD"))
    dest = _temp_file(".sha")
    token = remote.auth_token if remote.auth_token else None
    try:
        download(
            dest,
            url,
            auth_token=token,
            headers={"Accept": "application/vnd.github.v3.sha"},
        )
        with open(dest, "rb") as handle:
            payload = handle.read()
    except RuntimeError as exc:
        status = getattr(exc, "status", None)
        if status == 422:
            return NA_CHARACTER
        raise
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass
    text = payload.decode("utf-8", errors="replace").strip()
    if text.startswith("{") or text.startswith("["):
        parsed = json.loads(text)
        if isinstance(parsed, dict) and parsed.get("sha"):
            return str(parsed["sha"])
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and parsed[0].get("sha"):
            return str(parsed[0]["sha"])
    if text:
        return text.splitlines()[0].strip().strip('"')
    return NA_CHARACTER


def _format(_remote: Any) -> str:
    return "GitHub"


register_remote(
    "github",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def _default_token(quiet: bool) -> str | None:
    """GITHUB_PAT, then GITHUB_TOKEN. The git credential store is not used."""
    for name in ("GITHUB_PAT", "GITHUB_TOKEN"):
        pat = os.environ.get(name)
        if isinstance(pat, str) and len(pat) > 0:
            if not quiet:
                message(
                    f"Using github PAT from envvar {name}. "
                    "Use `gitcreds::gitcreds_set()` and unset "
                    f"{name} in .Renviron (or elsewhere) if you want to use the more "
                    "secure git credential store instead."
                )
            return pat
    return None


def install_github(
    repo: Any,
    ref: str = "HEAD",
    subdir: str | None = None,
    auth_token: Any = _TOKEN,
    host: str = "api.github.com",
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
    """Install GitHub repos. ``repo`` may be a string or a list of specifications.

    The default token is ``GITHUB_PAT``, then ``GITHUB_TOKEN``. Pass
    ``auth_token=None`` to ignore those variables. ``lib`` is the library.
    """
    if auth_token is _TOKEN:
        auth_token = _default_token(bool(quiet))
    specs = as_paths(repo)
    remotes = [
        github_remote(spec, ref=ref, subdir=subdir, auth_token=auth_token, host=host)
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
