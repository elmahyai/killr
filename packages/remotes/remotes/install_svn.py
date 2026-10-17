"""Install a package from a Subversion repository."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any

from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    as_paths,
    call_install_remotes,
    is_na,
    message,
    read_desc,
    register_remote,
    svn_binary,
)
from remotes.standardise_dep import NA


def svn_remote(
    url: str,
    svn_subdir: str | None = None,
    revision: str | None = None,
    args: Any = None,
    **_ignored: Any,
) -> Remote:
    return Remote(
        "svn",
        url=url,
        svn_subdir=svn_subdir,
        revision=revision,
        args=list(args) if args else [],
    )


def full_svn_url(remote: Remote) -> str:
    url = remote.url
    if remote.svn_subdir:
        url = url.rstrip("/") + "/" + str(remote.svn_subdir).strip("/")
    return url


def _svn_revision(url: str | None = None) -> str:
    binary = svn_binary()
    command = [binary, "info", "--xml"]
    if url:
        command.append(url)
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError("There was a problem retrieving the current SVN revision")
    text = completed.stdout
    match = re.search(r'<commit\s+revision="([0-9]+)">', text)
    if match is None:
        raise RuntimeError("There was a problem retrieving the current SVN revision")
    return match.group(1)


def _download(remote: Remote, quiet: bool = False) -> str:
    if not quiet:
        message("Downloading svn repo " + remote.url)
    binary = svn_binary()
    bundle = tempfile.mkdtemp()
    # svn checkout wants the destination to be the bundle itself.
    os.rmdir(bundle)
    args = ["co"]
    if remote.revision is not None:
        args.extend(["-r", str(remote.revision)])
    if remote.args:
        args.extend(str(item) for item in remote.args)
    args.extend([full_svn_url(remote), bundle])
    if not quiet:
        message(binary + " " + " ".join(args))
    completed = subprocess.run([binary, *args], capture_output=True, text=True)
    if completed.returncode > 0:
        raise RuntimeError("There seems to be a problem retrieving this SVN-URL.")
    return bundle


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    revision = sha
    if bundle is not None:
        revision = _svn_revision(bundle if os.path.isdir(bundle) else None)
    args = remote.args
    return {
        "RemoteType": "svn",
        "RemoteUrl": remote.url,
        "RemoteSubdir": remote.svn_subdir,
        "RemoteArgs": " ".join(str(item) for item in args) if args else None,
        "RemoteSha": revision,
    }


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    binary = svn_binary()
    dest = tempfile.mktemp()
    completed = subprocess.run(
        [binary, "cat", full_svn_url(remote).rstrip("/") + "/DESCRIPTION"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return NA_CHARACTER
    with open(dest, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(completed.stdout)
    try:
        return read_desc(dest).get("Package", NA_CHARACTER)
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    try:
        return _svn_revision(full_svn_url(remote))
    except RuntimeError:
        raise


def _format(_remote: Remote) -> str:
    return "SVN"


register_remote(
    "svn",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_svn(
    url: Any,
    subdir: str | None = None,
    args: Any = None,
    revision: str | None = None,
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
    """Check out Subversion urls and R CMD INSTALL them. ``lib`` is the library.

    ``svn`` must be on ``PATH``. The package name is read with ``svn cat``
    before the checkout.
    """
    if args is None:
        args = []
    urls = as_paths(url)
    remotes = [
        svn_remote(item, svn_subdir=subdir, revision=revision, args=args) for item in urls
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
