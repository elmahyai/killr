"""Install packages from a CRAN-like repository via install.packages."""

from __future__ import annotations

from typing import Any

from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    as_paths,
    available_packages,
    call_install_remotes,
    fix_repositories,
    is_na,
    message,
    r_install_packages,
    register_remote,
    trim_ws,
)
from remotes.standardise_dep import NA


def cran_remote(pkg: str, repos: Any = None, type: str | None = "source", **_ignored: Any) -> Remote:
    return Remote("cran", name=pkg, repos=fix_repositories(repos), pkg_type=type or "source")


def _package_name(remote: Remote, **_kwargs: Any) -> Any:
    return remote.name


def _sha(remote: Remote, **_kwargs: Any) -> Any:
    cran = available_packages(remote.repos, remote.pkg_type)
    record = cran.get(remote.name)
    if record is None:
        return NA_CHARACTER
    return trim_ws(record.get("Version", NA_CHARACTER))


def _format(_remote: Remote) -> str:
    return "CRAN"


def _download(remote: Remote, quiet: bool = False) -> str:
    raise RuntimeError("cran_remote is installed with install.packages")


def _metadata(remote: Remote, bundle: str | None = None, source: str | None = None, sha: Any = None) -> dict[str, Any]:
    return {}


register_remote(
    "cran",
    download=_download,
    metadata=_metadata,
    package_name=_package_name,
    sha=_sha,
    fmt=_format,
)


def install_packages(
    packages: list[str],
    repos: Any = None,
    type: str | None = "source",
    dependencies: Any = False,
    quiet: bool | None = None,
    **kwargs: Any,
) -> None:
    """utils::install.packages. ``lib`` in kwargs is the library directory."""
    if quiet is None:
        quiet = type != "source"
    shown = [package for package in packages if package is not None and not is_na(package)]
    message("Installing " + str(len(shown)) + " packages: " + ", ".join(shown))
    r_install_packages(
        shown,
        repos=fix_repositories(repos),
        type=type or "source",
        dependencies=dependencies,
        quiet=bool(quiet),
        lib=kwargs.get("lib"),
        install_opts=kwargs.get("INSTALL_opts"),
    )


def install_cran(
    pkgs: Any,
    repos: Any = None,
    type: str | None = "source",
    dependencies: Any = NA,
    upgrade: Any = "default",
    force: bool = False,
    quiet: bool = False,
    build: bool = True,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    **kwargs: Any,
) -> list[Any]:
    """Install CRAN packages. One string is one package. ``lib`` selects the library."""
    names = as_paths(pkgs)
    remotes = [cran_remote(name, repos=repos, type=type) for name in names]
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
