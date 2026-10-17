"""Cache and fetch for the repository package database.

The key is the pair (repos, type). Names on either value are part of the
key, so a named repository vector and an unnamed one do not share an entry.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

_MISSING = object()
_cache: dict[tuple[Any, ...], Any] = {}

_COLUMNS = (
    "Package",
    "Version",
    "Priority",
    "Depends",
    "Imports",
    "LinkingTo",
    "Suggests",
    "Enhances",
    "License",
    "License_is_FOSS",
    "License_restricts_use",
    "OS_type",
    "Archs",
    "MD5sum",
    "NeedsCompilation",
    "File",
    "Repository",
)

_SPACE = re.compile(r"\s+")
_ARCH_SPLIT = re.compile(r"\s*,\s*")
_VERSION_SPLIT = re.compile(r"[.-]")
_R_VERSION: tuple[int, ...] | None = None


def _component(value: Any) -> tuple[Any, ...]:
    """Values and names of one cache-key element.

    A string or a list is an unnamed character vector. A dict is a named
    character vector: the keys are the names, in insertion order. None is NULL.
    """

    if value is None:
        return ("NULL",)
    if isinstance(value, str):
        return ("character", (value,), None)
    if isinstance(value, Mapping):
        return ("character", tuple(value.values()), tuple(value.keys()))
    if isinstance(value, (list, tuple)):
        return ("character", tuple(value), None)
    raise TypeError(
        "repos and type must be a string, a list of strings, or a dict of names"
    )


def available_packages_set(repos: Any, type: Any, db: Any) -> Any:
    """Return the database cached for this repository and package type.

    The first call for a pair stores db. A later call returns that stored
    database and leaves it in place. A stored None is not kept: R tests
    is.null, and a missing binding is NULL too, so the next call replaces it.
    """

    signature = (_component(repos), _component(type))
    stored = _cache.get(signature, _MISSING)
    # A stored None is a miss, matching is.null on an environment binding.
    if stored is _MISSING or stored is None:
        _cache[signature] = db
    return _cache[signature]


def available_packages_reset() -> None:
    """Remove every cached database and return None.

    R's rm() returns NULL invisibly, and available_packages_reset returns that.
    """

    _cache.clear()
    return None


class AvailablePackages:
    """Character matrix from available.packages, with package row names."""

    def __init__(
        self,
        columns: dict[str, list[str | None]],
        rownames: list[str],
    ) -> None:
        self.columns = columns
        self.rownames = rownames

    def __getitem__(self, name: str) -> list[str | None]:
        return self.columns[name]

    def __len__(self) -> int:
        return len(self.rownames)


def _r_version_text() -> str:
    """getRversion(), read from Rversion.h as major.minor."""

    header = None
    candidates = (
        "/usr/share/R/include/Rversion.h",
        "/usr/include/R/Rversion.h",
        "/usr/lib/R/include/Rversion.h",
    )
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as handle:
                header = handle.read()
        except OSError:
            continue
        break
    if header is None:
        raise RuntimeError("could not read the installed R version")
    major = re.search(r'#define\s+R_MAJOR\s+"([^"]*)"', header)
    minor = re.search(r'#define\s+R_MINOR\s+"([^"]*)"', header)
    if major is None or minor is None:
        raise RuntimeError("could not read the installed R version")
    return f"{major.group(1)}.{minor.group(1)}"


def _current_r_version() -> tuple[int, ...]:
    global _R_VERSION
    if _R_VERSION is None:
        _R_VERSION = _version_tuple(_r_version_text())
    return _R_VERSION


def _version_tuple(text: str) -> tuple[int, ...]:
    """package_version components. '.' and '-' both separate numbers."""

    return tuple(int(part) for part in _VERSION_SPLIT.split(text))


def _version_cmp(op: str, left: tuple[int, ...], right_text: str) -> bool:
    right = _version_tuple(right_text)
    width = max(len(left), len(right))
    a = left + (0,) * (width - len(left))
    b = right + (0,) * (width - len(right))
    if op == ">=":
        return a >= b
    if op == ">":
        return a > b
    if op == "<=":
        return a <= b
    if op == "<":
        return a < b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    raise ValueError("invalid 'filters' argument.")


def _repo_strings(repos: Any) -> list[str]:
    if repos is None:
        return []
    if isinstance(repos, str):
        values: list[Any] = [repos]
    elif isinstance(repos, Mapping):
        values = list(repos.values())
    elif isinstance(repos, (list, tuple)):
        values = list(repos)
    else:
        raise TypeError(
            "repos and type must be a string, a list of strings, or a dict of names"
        )
    texts: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(
                "repos and type must be a string, a list of strings, or a dict of names"
            )
        texts.append(value)
    return texts


def _resolve_type(type: str) -> tuple[str, str]:
    """resolvePkgType, then the mac.binary.* rewrite in contrib.url.

    Returns the switch kind and the macOS path segment.
    """

    if type == "both":
        type = "source"
    elif type == "binary":
        # .Platform$pkgType is source on this unix install, win.binary on Windows.
        type = "win.binary" if os.name == "nt" else "source"
    mac_path = "macosx"
    if type.startswith("mac.binary."):
        mac_path = "macosx/" + type[11:]
        type = "mac.binary"
    if type not in ("source", "mac.binary", "win.binary"):
        raise ValueError("invalid 'type'")
    return type, mac_path


def _contrib_urls(repos: Any, type: str) -> list[str]:
    """utils::contrib.url. A trailing slash on the repo is removed once."""

    if not isinstance(type, str):
        raise ValueError("'type' must be a character string")
    kind, mac_path = _resolve_type(type)
    values = _repo_strings(repos)
    if "@CRAN@" in values:
        raise ValueError("trying to use CRAN without setting a mirror")
    if kind == "source":
        suffix = "/src/contrib"
    else:
        text = _r_version_text()
        major, minor = text.split(".", 1)
        ver = major + "." + minor.split(".", 1)[0]
        if kind == "mac.binary":
            suffix = f"/bin/{mac_path}/contrib/{ver}"
        else:
            suffix = f"/bin/windows/contrib/{ver}"
    urls: list[str] = []
    seen: set[str] = set()
    for repo in values:
        base = repo[:-1] if repo.endswith("/") else repo
        url = base + suffix
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _download_packages(contrib: str) -> str:
    request = urllib.request.Request(
        contrib + "/PACKAGES",
        headers={"User-Agent": "R"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    return payload.decode("utf-8")


def _read_dcf(text: str) -> list[dict[str, str]]:
    """read.dcf. A whitespace-only line ends a record.

    A continuation starts with space or tab. Its leading whitespace is
    removed and the line is joined with a newline. The value after a colon
    loses its leading whitespace. An empty value stays an empty string.
    """

    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    field: str | None = None
    for line in text.splitlines():
        if line.strip(" \t") == "":
            if current:
                records.append(current)
            current = None
            field = None
            continue
        if line[0] in " \t":
            if current is None or field is None:
                raise ValueError("malformed DCF")
            current[field] = current[field] + "\n" + line.lstrip(" \t")
            continue
        if ":" not in line:
            raise ValueError("malformed DCF")
        name, raw_value = line.split(":", 1)
        if name == "" or name[0] in " \t":
            raise ValueError("malformed DCF")
        if current is None:
            current = {}
        field = name
        current[field] = raw_value.lstrip(" \t")
    if current:
        records.append(current)
    return records


def _rows_from_records(
    records: list[dict[str, str]], contrib: str
) -> list[dict[str, str | None]]:
    """Standard columns, plus Repository. Path is appended, then dropped.

    File is a required column. This index does not carry it, so the cell is
    missing. A Path cell that is present and not missing becomes
    contrib/Path; every other row keeps the contrib URL.
    """

    has_path = any("Path" in record for record in records)
    rows: list[dict[str, str | None]] = []
    for record in records:
        if has_path and "Path" in record:
            repository = contrib + "/" + record["Path"]
        else:
            repository = contrib
        row: dict[str, str | None] = {}
        for name in _COLUMNS:
            if name == "Repository":
                row[name] = repository
            elif name in record:
                row[name] = record[name]
            else:
                row[name] = None
        rows.append(row)
    return rows


def _filter_r_version(
    rows: list[dict[str, str | None]], current: tuple[int, ...]
) -> list[dict[str, str | None]]:
    """Drop a row unless every R(...) constraint in Depends holds.

    Whitespace is removed first, so a folded constraint is one token.
    The operator is the text from the third character through '=' when the
    fourth character is '=', and the version is the rest without the ')'.
    """

    drop: set[int] = set()
    for index, row in enumerate(rows):
        depends = row["Depends"] or ""
        compact = _SPACE.sub("", depends)
        tokens = [
            part for part in compact.split(",") if part.startswith("R(")
        ]
        if not tokens:
            continue
        failed = False
        for token in tokens:
            end = 3 + (token[3:4] == "=")
            op = token[2:end]
            version = token[end : len(token) - 1]
            if not _version_cmp(op, current, version):
                failed = True
                break
        if failed:
            drop.add(index)
    if not drop:
        return rows
    return [row for index, row in enumerate(rows) if index not in drop]


def _filter_os_type(
    rows: list[dict[str, str | None]], os_type: str
) -> list[dict[str, str | None]]:
    """Keep a missing OS_type and the platform OS type."""

    return [
        row
        for row in rows
        if row["OS_type"] is None or row["OS_type"] == os_type
    ]


def _filter_subarch(
    rows: list[dict[str, str | None]], arch: str
) -> list[dict[str, str | None]]:
    """Keep every row when this R has an empty r_arch.

    Otherwise a missing Archs cell is kept, and a listed arch must include
    the current one. An all-missing Archs column is left unchanged.
    """

    if arch == "":
        return rows
    if all(row["Archs"] is None for row in rows):
        return rows
    kept: list[dict[str, str | None]] = []
    for row in rows:
        archs = row["Archs"]
        if archs is None:
            kept.append(row)
            continue
        if arch in _ARCH_SPLIT.split(archs):
            kept.append(row)
    return kept


def _filter_duplicates(
    rows: list[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    """tools:::.remove_stale_dups.

    The highest version is kept. Equal versions keep the first row, which
    is the first repository. More than 100 extra copies collapse identical
    package-and-version pairs before that choice.
    """

    packages = [row["Package"] for row in rows]
    seen: set[str | None] = set()
    dup_names: list[str | None] = []
    for name in packages:
        if name in seen:
            dup_names.append(name)
        else:
            seen.add(name)
    if len(dup_names) > 100:
        seen_pair: set[tuple[str | None, str | None]] = set()
        collapsed: list[dict[str, str | None]] = []
        for row in rows:
            pair = (row["Package"], row["Version"])
            if pair in seen_pair:
                continue
            seen_pair.add(pair)
            collapsed.append(row)
        rows = collapsed
        packages = [row["Package"] for row in rows]
        seen = set()
        dup_names = []
        for name in packages:
            if name in seen:
                dup_names.append(name)
            else:
                seen.add(name)
    if not dup_names:
        return rows
    drop: set[int] = set()
    for name in dup_names:
        which = [index for index, pkg in enumerate(packages) if pkg == name]
        versions = [_version_tuple(rows[index]["Version"] or "") for index in which]
        keep_ver = max(versions)
        keep_at = versions.index(keep_ver)
        for offset, index in enumerate(which):
            if offset != keep_at:
                drop.add(index)
    if not drop:
        return rows
    return [row for index, row in enumerate(rows) if index not in drop]


def _empty_matrix() -> AvailablePackages:
    return AvailablePackages(
        {name: [] for name in _COLUMNS},
        [],
    )


def _matrix(rows: list[dict[str, str | None]]) -> AvailablePackages:
    if not rows:
        return _empty_matrix()
    columns = {
        name: [row[name] for row in rows]
        for name in _COLUMNS
    }
    rownames = [row["Package"] or "" for row in rows]
    return AvailablePackages(columns, rownames)


def _fetch_matrix(repos: Any, type: Any) -> AvailablePackages:
    """utils::available.packages for the contrib URLs, warnings suppressed.

    A repository that cannot be read is skipped. The default filters run in
    order: R_version, OS_type, subarch, duplicates.
    """

    if not isinstance(type, str):
        raise ValueError("'type' must be a character string")
    urls = _contrib_urls(repos, type)
    rows: list[dict[str, str | None]] = []
    for url in urls:
        try:
            text = _download_packages(url)
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        try:
            records = _read_dcf(text)
        except ValueError:
            continue
        rows.extend(_rows_from_records(records, url))
    if not rows:
        return _empty_matrix()
    os_type = "windows" if os.name == "nt" else "unix"
    rows = _filter_r_version(rows, _current_r_version())
    if rows:
        rows = _filter_os_type(rows, os_type)
    if rows:
        rows = _filter_subarch(rows, "")
    if rows:
        rows = _filter_duplicates(rows)
    return _matrix(rows)


def available_packages(repos: Any, type: Any = "source") -> Any:
    """Fetch the package index and cache it for this repository and type.

    The download is the db argument of available_packages_set. R does not
    evaluate that argument when the pair is already stored, so a later call
    returns the cached matrix and does not fetch PACKAGES again. A stored
    None is a miss, and the new matrix replaces it.
    """

    signature = (_component(repos), _component(type))
    stored = _cache.get(signature, _MISSING)
    if stored is not _MISSING and stored is not None:
        return available_packages_set(repos, type, stored)
    return available_packages_set(repos, type, _fetch_matrix(repos, type))
