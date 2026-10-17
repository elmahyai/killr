"""Install one source version of a package from a CRAN-like repository."""

from __future__ import annotations

import os
import re
from typing import Any

from remotes.add_metadata import add_metadata
from remotes.install_core import (
    NA_CHARACTER,
    _TARBALL_VER,
    _VERSION_RE,
    _temp_file,
    available_packages,
    contrib_url,
    download,
    fix_repositories,
    is_na,
    message,
    session_lib_paths,
)
from remotes.install_url import install_url
from remotes.standardise_dep import NA

_COMPARE = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, "<": lambda a, b: a < b}


def _parts(text: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in re.split(r"[.-]", text) if piece != "")


def _cmp(left: str, right: str) -> int:
    a = _parts(left)
    b = _parts(right)
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def version_from_tarball(tarball_name: str | None) -> str | None:
    if not tarball_name:
        return None
    match = _TARBALL_VER.search(tarball_name)
    if match is None:
        return None
    return match.group(1)


def _parse_dep_spec(spec: str) -> tuple[str | None, str | None]:
    """One ``name(op version)`` piece. A bare name has no comparison."""
    match = re.search(r"\(\s*(\S+)\s+(\S*)\s*\)", spec)
    if match is None:
        return None, None
    compare = match.group(1)
    version = match.group(2)
    if compare not in _COMPARE:
        raise RuntimeError("Invalid comparison operator in dependency: " + compare)
    return compare, version


def version_criteria(criteria: Any) -> list[tuple[str | None, str | None]]:
    if criteria is None or (isinstance(criteria, str) and criteria == "") or is_na(criteria):
        return [(None, None)]
    if isinstance(criteria, str):
        pieces = [piece.strip() for piece in criteria.split(",")]
    elif isinstance(criteria, (list, tuple)):
        if len(criteria) == 1 and is_na(criteria[0]):
            return [(None, None)]
        pieces = [str(piece).strip() for piece in criteria]
    else:
        pieces = [str(criteria)]
    rows = []
    for piece in pieces:
        if piece == "" or is_na(piece):
            rows.append((None, None))
            continue
        if _VERSION_RE.match(piece):
            wrapped = f"p(== {piece})"
        else:
            wrapped = f"p({piece})"
        rows.append(_parse_dep_spec(wrapped))
    return rows or [(None, None)]


def version_satisfies_criteria(to_check: str | None, criteria: Any) -> bool:
    if to_check is None or is_na(to_check):
        return False
    for compare, version in version_criteria(criteria):
        if compare is None:
            continue
        if not _COMPARE[compare](_cmp(to_check, version or ""), 0):
            return False
    return True


def _archive_names(package: str, repo: str) -> list[str]:
    """Row names of archive.rds for package, oldest first. A missing file is no rows."""
    url = repo.rstrip("/") + "/src/contrib/Meta/archive.rds"
    dest = _temp_file(".rds")
    script = _temp_file(".R")
    try:
        download(dest, url)
        code = (
            f"info <- readRDS({_r(dest)})\n"
            f"block <- info[[{_r(package)}]]\n"
            "if (!is.null(block)) cat(paste(rownames(block), collapse='\n'))\n"
        )
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(code)
        import subprocess

        completed = subprocess.run(["Rscript", script], capture_output=True, text=True)
        if completed.returncode != 0:
            return []
        return [line for line in completed.stdout.splitlines() if line]
    except Exception:
        return []
    finally:
        for path in (dest, script):
            try:
                os.unlink(path)
            except OSError:
                pass


def _r(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def download_version_url(
    package: str,
    version: Any = None,
    repos: Any = None,
    type: str | None = "source",
    available: dict[str, dict[str, str]] | None = None,
    verbose: bool | None = None,
) -> str:
    """URL of a source tarball whose version satisfies the criteria."""
    fixed = fix_repositories(repos)
    if verbose is None:
        verbose = len(fixed) > 1
    if type not in (None, "source"):
        raise RuntimeError("`type` must be 'source' for `install_version()`")
    if available is None:
        available = available_packages(fixed, "source")
    package_exists = False
    record = available.get(package)
    if record is not None:
        package_exists = True
        if version_satisfies_criteria(record.get("Version"), version):
            repository = record.get("Repository", "").rstrip("/")
            return repository + "/" + package + "_" + record["Version"] + ".tar.gz"
    for repo in fixed:
        if verbose:
            message("Trying " + repo)
        names = _archive_names(package, repo)
        if not names:
            continue
        package_exists = True
        for path in reversed(names):
            found = version_from_tarball(os.path.basename(path))
            if found and version_satisfies_criteria(found, version):
                return repo.rstrip("/") + "/src/contrib/Archive/" + path.lstrip("/")
    if not package_exists:
        raise RuntimeError(f"couldn't find package '{package}'")
    raise RuntimeError(f"version '{version}' is invalid for package '{package}'")


def download_version(
    package: str,
    version: Any = None,
    repos: Any = None,
    type: str | None = "source",
    **_kwargs: Any,
) -> str:
    """Download one source tarball and return its path."""
    url = download_version_url(package, version, repos, type)
    dest = _temp_file(".tar.gz")
    try:
        os.unlink(dest)
    except OSError:
        pass
    return download(dest, url)


def install_version(
    package: Any,
    version: Any = None,
    dependencies: Any = NA,
    upgrade: Any = "default",
    force: bool = False,
    quiet: bool = False,
    build: bool = False,
    build_opts: list[str] | None = None,
    build_manual: bool = False,
    build_vignettes: bool = False,
    repos: Any = None,
    type: str = "source",
    **kwargs: Any,
) -> Any:
    """Install one source version, then drop the url remote fields from DESCRIPTION.

    ``package`` must be one name. ``lib`` is the library passed to ``install_url``.
    """
    if isinstance(package, (list, tuple)):
        if len(package) < 1:
            return None
        if len(package) > 1:
            raise RuntimeError(
                "install_version() must be called with a single 'package' argument - multiple packages given"
            )
        package = package[0]
    if package is None or package == "":
        return None
    if not isinstance(package, str):
        package = str(package)
    if type != "source":
        raise RuntimeError("`type` must be 'source' for `install_version()`")
    url = download_version_url(package, version, repos, type)
    res = install_url(
        url,
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
    lib = kwargs.get("lib")
    libraries: list[str]
    if lib is None:
        libraries = session_lib_paths()
    elif isinstance(lib, (list, tuple)):
        libraries = [os.fspath(item) for item in lib]
    else:
        libraries = [os.fspath(lib)]
    for directory in libraries:
        pkg_dir = os.path.join(directory, package)
        if os.path.isdir(pkg_dir):
            add_metadata(
                pkg_dir,
                {"RemoteType": None, "RemoteUrl": None, "RemoteSubdir": None},
            )
            break
    return res


# contrib.url is part of the search above; keep the import used.
_ = contrib_url
_ = NA_CHARACTER
