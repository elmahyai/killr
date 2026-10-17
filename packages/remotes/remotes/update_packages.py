"""Update installed packages that are missing or behind the repository."""

from __future__ import annotations

import os
import warnings
from typing import Any

from remotes.install_core import (
    NA_CHARACTER,
    Remote,
    _base_packages,
    available_packages,
    dep_names,
    different_sha,
    find_deps,
    find_installed_description,
    fix_repositories,
    is_na,
    local_sha,
    package2remote,
    read_desc,
    remote_sha_of,
    resolve_upgrade,
    session_lib_paths,
)
from remotes.standardise_dep import NA, standardise_dep

UNINSTALLED = -2
BEHIND = -1
CURRENT = 0
AHEAD = 1
UNAVAILABLE = 2


class PackageDeps:
    """Rows of package, installed, available, diff, is_cran, and remote."""

    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self.rows = rows or []

    def __len__(self) -> int:
        return len(self.rows)


def _version_cmp(left: str, right: str) -> int:
    def parts(text: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in __import__("re").split(r"[.-]", text) if piece != "")

    a = parts(left)
    b = parts(right)
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def compare_versions(installed: Any, remote: Any, is_cran: bool) -> int:
    if not is_cran:
        if not is_na(installed) and not is_na(remote) and installed == remote:
            return CURRENT
        return BEHIND
    if is_na(remote):
        return UNAVAILABLE
    if is_na(installed):
        return UNINSTALLED
    order = _version_cmp(str(installed), str(remote))
    if order < 0:
        return BEHIND
    if order > 0:
        return AHEAD
    return CURRENT


def package_deps(
    packages: Any,
    dependencies: Any = NA,
    repos: Any = None,
    type: str | None = None,
) -> PackageDeps:
    """Dependency status against the repository. An empty package list has no rows."""
    if packages is True:
        names = _installed_names()
    elif packages is None:
        names = []
    elif isinstance(packages, str):
        names = [packages]
    else:
        names = [str(item) for item in packages]
    fixed = fix_repositories(repos)
    chosen = type or "source"
    cran = available_packages(fixed, chosen)
    deps = find_deps(names, cran, top_dep=dependencies)
    base = _base_packages()
    deps = [name for name in deps if name not in base]
    rows = []
    for name in deps:
        remote = package2remote(name, lib=session_lib_paths(), repos=fixed, type=chosen)
        # A package installed without RemoteType is a cran remote whose SHA is the version.
        if remote.kind != "cran":
            remote = _ensure_registered(remote)
        installed = local_sha(name)
        if remote.kind == "cran":
            record = cran.get(name)
            available = NA_CHARACTER if record is None else record.get("Version", NA_CHARACTER)
            is_cran = True
        else:
            available = remote_sha_of(remote)
            is_cran = False
        rows.append(
            {
                "package": name,
                "installed": installed,
                "available": available,
                "diff": compare_versions(installed, available, is_cran),
                "is_cran": is_cran,
                "remote": remote,
            }
        )
    return PackageDeps(rows)


def _installed_names() -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for lib in session_lib_paths():
        if not os.path.isdir(lib):
            continue
        for entry in sorted(os.listdir(lib)):
            if entry in seen:
                continue
            if os.path.isfile(os.path.join(lib, entry, "DESCRIPTION")):
                seen.add(entry)
                names.append(entry)
    return names


def _ensure_registered(remote: Remote) -> Remote:
    return remote


def local_package_deps(pkgdir: str = ".", dependencies: Any = NA) -> list[str]:
    """Dependency names from a local DESCRIPTION. ``FALSE`` selects none."""
    path = pkgdir
    if os.path.isfile(pkgdir):
        path = os.path.dirname(pkgdir)
    record = read_desc(os.path.join(path, "DESCRIPTION"))
    lowered = {key.lower(): value for key, value in record.items()}
    wanted = [name.lower() for name in standardise_dep(dependencies)]
    found: list[str] = []
    for field in wanted:
        if field in lowered:
            found.extend(dep_names(lowered[field]))
    return found


def dev_package_deps(
    pkgdir: str = ".",
    dependencies: Any = NA,
    repos: Any = None,
    type: str | None = None,
) -> PackageDeps:
    """Status of the dependencies of a local package. No dependencies is an empty table."""
    deps = local_package_deps(pkgdir, dependencies=dependencies)
    return package_deps(deps, dependencies=NA, repos=repos, type=type)


def _subset(rows: list[dict[str, Any]], keep: list[bool]) -> list[dict[str, Any]]:
    return [row for row, flag in zip(rows, keep) if flag]


def update(
    object: PackageDeps,
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
) -> None:
    """Install missing or outdated rows. ``upgrade="never"`` installs only missing packages.

    The return value is None, matching ``invisible()``.
    """
    standardise_dep(dependencies)
    choice = resolve_upgrade(upgrade)
    rows = object.rows
    uninstalled = [row["diff"] == UNINSTALLED for row in rows]
    behind = [row["diff"] == BEHIND for row in rows]
    if choice == "never":
        chosen = _subset(rows, uninstalled)
    elif choice == "always":
        chosen = list(rows)
    else:
        chosen = list(rows)
    unavailable = [
        row["diff"] == UNAVAILABLE and row["is_cran"] for row in chosen
    ]
    if any(unavailable) and not quiet:
        skipped = [row["package"] for row, flag in zip(chosen, unavailable) if flag]
        from remotes.install_core import message

        message("Skipping " + str(len(skipped)) + " packages not available: " + ", ".join(skipped))
    unknown = [
        row
        for row in chosen
        if row["diff"] in (UNAVAILABLE, UNINSTALLED) and not row["is_cran"]
    ]
    if unknown:
        _install_rows(unknown, dependencies, upgrade, force, quiet, build, build_opts, build_manual, build_vignettes, repos, type, kwargs)
    ahead = [row["diff"] == AHEAD and row["is_cran"] for row in chosen]
    if any(ahead) and not quiet:
        from remotes.install_core import message

        skipped = [row["package"] for row, flag in zip(chosen, ahead) if flag]
        message("Skipping " + str(len(skipped)) + " packages ahead of CRAN: " + ", ".join(skipped))
    ahead_remote = [row for row in chosen if row["diff"] == AHEAD and not row["is_cran"]]
    if ahead_remote:
        _install_rows(ahead_remote, dependencies, upgrade, force, quiet, build, build_opts, build_manual, build_vignettes, repos, type, kwargs)
    to_install = [
        row
        for row in chosen
        if is_na(row["installed"]) or row["diff"] < CURRENT
    ]
    cran_rows = [
        row
        for row in to_install
        if row["is_cran"] and not (row["diff"] == UNAVAILABLE and row["is_cran"])
    ]
    if cran_rows:
        from remotes.install_cran import install_packages

        remote = cran_rows[0]["remote"]
        install_packages(
            [row["package"] for row in cran_rows],
            repos=getattr(remote, "repos", repos),
            type=getattr(remote, "pkg_type", type) or "source",
            dependencies=dependencies,
            quiet=quiet,
            **kwargs,
        )
    other = [row for row in to_install if not row["is_cran"]]
    if other:
        _install_rows(other, dependencies, upgrade, force, quiet, build, build_opts, build_manual, build_vignettes, repos, type, kwargs)
    return None


def _install_rows(rows, dependencies, upgrade, force, quiet, build, build_opts, build_manual, build_vignettes, repos, type, kwargs) -> None:
    from remotes.install_core import call_install_remotes

    call_install_remotes(
        [row["remote"] for row in rows],
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


def update_packages(
    packages: Any = True,
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
) -> None:
    """Update packages. An empty list installs nothing. The return value is None.

    ``upgrade="never"`` does not upgrade a package that is already installed.
    ``lib`` is the library used if a package does need to be installed.
    ``force=True`` warns and has no effect.
    """
    if force is True:
        warnings.warn(
            "`update_packages(force = TRUE)` is deprecated and has no effect.",
            stacklevel=2,
        )
    if packages is True:
        packages = _installed_names()
    deps = package_deps(packages, repos=repos, type=type)
    # package_deps already applied the default dependency set. Pass the rows through.
    _ = different_sha
    _ = find_installed_description
    return update(
        deps,
        dependencies=dependencies,
        upgrade=upgrade,
        force=False,
        quiet=quiet,
        build=build,
        build_opts=build_opts,
        build_manual=build_manual,
        build_vignettes=build_vignettes,
        repos=repos,
        type=type,
        **kwargs,
    )
