"""Install the dependencies of a local package."""

from __future__ import annotations

from typing import Any

from remotes.standardise_dep import NA
from remotes.update_packages import dev_package_deps, update


def install_deps(
    pkgdir: str = ".",
    dependencies: Any = NA,
    repos: Any = None,
    type: str | None = None,
    upgrade: Any = "default",
    quiet: bool = False,
    build: Any = True,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    **kwargs: Any,
) -> None:
    """Install dependencies of a local package. ``FALSE`` selects none and installs nothing.

    The return value is None. ``lib`` is used only when a dependency is installed.
    """
    packages = dev_package_deps(pkgdir, dependencies=dependencies, repos=repos, type=type)
    dep_deps = NA if dependencies is True else dependencies
    return update(
        packages,
        dependencies=dep_deps,
        quiet=quiet,
        upgrade=upgrade,
        build=build is True,
        build_opts=build_opts,
        build_manual=build_manual,
        build_vignettes=build_vignettes,
        repos=repos,
        type=type,
        **kwargs,
    )
