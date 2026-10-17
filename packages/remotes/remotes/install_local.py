"""Install a package from a local directory or archive."""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any

from remotes.install_core import (
    NA,
    NA_CHARACTER,
    Remote,
    as_paths,
    call_install_remotes,
    description_field,
    is_binary_pkg,
    is_na,
    register_remote,
)
from remotes.standardise_dep import NA as _NA

_MISSING = object()


def local_remote(path: str, subdir: str | None = None, **_ignored: Any) -> Remote:
    return Remote("local", path=os.path.realpath(path), subdir=subdir)


def _download(remote: Remote, quiet: bool = False) -> str:
    bundle = tempfile.mkdtemp()
    source = remote.path
    try:
        if os.path.isdir(source):
            target = os.path.join(bundle, os.path.basename(source.rstrip(os.sep)) or "package")
            shutil.copytree(source, target)
        else:
            target = os.path.join(bundle, os.path.basename(source))
            shutil.copy2(source, target)
    except OSError as exc:
        raise RuntimeError(f"Could not copy `{source}` to `{bundle}`") from exc
    return target


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    return {
        "RemoteType": "local",
        "RemoteUrl": remote.path,
        "RemoteSubdir": remote.subdir,
    }


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    if not os.path.isdir(remote.path):
        return os.path.basename(remote.path).split("_", 1)[0]
    name = description_field(remote.path, "Package")
    if name is None:
        raise RuntimeError("Does not appear to be an R package (no DESCRIPTION)")
    return name


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    if not os.path.isdir(remote.path):
        return NA_CHARACTER
    version = description_field(remote.path, "Version")
    if version is None or is_na(version):
        return NA_CHARACTER
    return version


def _format(_remote: Remote) -> str:
    return "local"


register_remote(
    "local",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_local(
    path: Any = ".",
    subdir: str | None = None,
    dependencies: Any = _NA,
    upgrade: Any = "default",
    force: bool = False,
    quiet: bool = False,
    build: Any = _MISSING,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    repos: Any = None,
    type: str | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Install local directories or archives. ``lib`` is passed to R CMD INSTALL.

    A character vector of paths is a list. One string is one path. The return
    value is the package names, in that order.
    """
    paths = as_paths(path)
    if build is _MISSING:
        flags = [is_binary_pkg(item) for item in paths] or [False]
        build = False if any(flags) else True
        if len(flags) == 1:
            build = not flags[0]
    remotes = [local_remote(item, subdir=subdir) for item in paths]
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
