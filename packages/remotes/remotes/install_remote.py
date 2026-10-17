"""Install one remote or a list of remotes."""

from __future__ import annotations

from typing import Any

from remotes.install_core import install_one, install_remotes
from remotes.standardise_dep import NA

# Importing the install modules registers their remote methods.
import remotes.install_bioc  # noqa: F401
import remotes.install_bitbucket  # noqa: F401
import remotes.install_cran  # noqa: F401
import remotes.install_git  # noqa: F401
import remotes.install_github  # noqa: F401
import remotes.install_gitlab  # noqa: F401
import remotes.install_local  # noqa: F401
import remotes.install_svn  # noqa: F401
import remotes.install_url  # noqa: F401


def install_remote(
    remote: Any,
    dependencies: Any = NA,
    upgrade: Any = "default",
    force: bool = False,
    quiet: bool = False,
    build: Any = True,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    repos: Any = None,
    type: str | None = None,
    **kwargs: Any,
) -> Any:
    """Download one remote, record its metadata, and R CMD INSTALL it.

    A ``cran_remote`` is installed with ``install.packages``. ``lib`` is the
    library directory. The return value is the package name.
    """
    if build_opts is None:
        build_opts = ["--no-resave-data", "--no-manual", "--no-build-vignettes"]
    return install_one(
        remote,
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


__all__ = ["install_remote", "install_remotes"]
