"""Dependency status for a CRAN package and for a local DESCRIPTION.

``package_deps`` walks Depends, Imports, and LinkingTo the way
``tools::package_dependencies`` does, then drops installed packages whose
Priority is base or recommended. The CRAN index is the source PACKAGES file
after the default ``available.packages`` filters. Versions compare as
``package_version``.
"""

from __future__ import annotations

import gzip
import os
import re
import tarfile
import urllib.request
from collections import defaultdict

from remotes.standardise_dep import NA, standardise_dep

# -2 not installed, but on CRAN. -1 installed and behind. 0 current.
# 1 ahead of CRAN. 2 not on CRAN.
UNINSTALLED = -2
BEHIND = -1
CURRENT = 0
AHEAD = 1
UNAVAILABLE = 2

_WHICH_FIELDS = ("Depends", "Imports", "LinkingTo", "Suggests", "Enhances")
_VALID_OPS = frozenset({">", ">=", "==", "<=", "<"})
_ASCII_SPACE = " \f\n\r\t\v"
_BLANK_LINE = re.compile(rf"^[{_ASCII_SPACE}]*$")
_ESCAPED_BLANK = re.compile(rf"^[{_ASCII_SPACE}]+\.[{_ASCII_SPACE}]*$")
_TAG_LINE = re.compile(r"^([^ \t][^:]*):(.*)$", re.DOTALL)
_LEADING_SPACE = re.compile(rf"^[{_ASCII_SPACE}]*")
_TRAILING_SPACE = re.compile(rf"[{_ASCII_SPACE}]*$")
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9.]*")
_VERSION_RE = re.compile(r"^(?:[0-9]+[.-])+[0-9]+$")
_SPLIT_COMMA = re.compile(rf"[{_ASCII_SPACE}]*,[{_ASCII_SPACE}]*")
_PAREN_GROUP = re.compile(r"[ \f\n\r\t\v]*\(.*?\)")
_HAS_PAREN = re.compile(r"\(.*\)")
_OP_RE = re.compile(rf".*\([{_ASCII_SPACE}]*(\S+)[{_ASCII_SPACE}]+.*[{_ASCII_SPACE}]*\).*")
_VER_RE = re.compile(
    rf".*\([{_ASCII_SPACE}]*\S+[{_ASCII_SPACE}]+(\S*)[{_ASCII_SPACE}]*\).*"
)
_EXTRA_SPLIT = re.compile(rf"[,{_ASCII_SPACE}]+")

# ICU root collation, which is what R 4.5 uses for sort() of package names.
# Case is a tie-break: a primary letter is shared, then lowercase precedes
# uppercase. A dot precedes digits, and digits precede letters.
_PUNCT_WEIGHT = {
    " ": 0,
    "_": 1,
    "-": 2,
    ".": 3,
    "(": 4,
    ")": 5,
    "/": 6,
    "+": 7,
}

_db_cache: dict[tuple, _Available] = {}
_installed_cache: _Installed | None = None


class _Available:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.by_name: dict[str, dict[str, object]] = {}
        self.order: list[str] = []
        for row in rows:
            name = row.get("Package")
            if not name or name in self.by_name:
                continue
            fields = {
                field: _dep_names(row.get(field))
                for field in _WHICH_FIELDS
            }
            version = row.get("Version")
            self.by_name[name] = {"version": version, "fields": fields}
            self.order.append(name)
        self._closure_cache: dict[tuple[str, ...], dict[str, list[int]]] = {}

    def version_of(self, name: str) -> str | None:
        row = self.by_name.get(name)
        if row is None:
            return None
        version = row["version"]
        if not isinstance(version, str):
            return None
        return _trim(version)

    def deps_of(self, name: str, which: list[str]) -> list[str] | None:
        row = self.by_name.get(name)
        if row is None:
            return None
        fields = row["fields"]
        assert isinstance(fields, dict)
        seen: set[str] = set()
        out: list[str] = []
        for field in which:
            names = fields.get(field) or []
            assert isinstance(names, list)
            for dep in names:
                if dep not in seen:
                    seen.add(dep)
                    out.append(dep)
        return out


class _Installed:
    def __init__(self) -> None:
        self.base: set[str] = set()
        # First library that contains the directory. None means the directory
        # was found but its Package field did not match, which packageDescription
        # treats as not installed.
        self.descriptions: dict[str, dict[str, str] | None] = {}


def local_package_deps(pkgdir: str = ".", dependencies: object = NA) -> list[str]:
    """Dependency names from a local DESCRIPTION, with R removed.

    Field names are lowercased. ``dependencies`` selects fields the way
    ``standardise_dep`` does, then only fields present in the file are read.
    Each field is parsed by splitting on commas and dropping the version in
    parentheses. The default selection is Depends, Imports, and LinkingTo.
    """

    pkg = _load_pkg_description(pkgdir)
    selected = [name.lower() for name in standardise_dep(dependencies)]
    names = []
    for field in selected:
        if field not in pkg:
            continue
        names.extend(_parse_dep_names(pkg[field]))
    return names


def package_deps(
    packages: str | list[str] | tuple[str, ...],
    dependencies: object = NA,
    repos: str | list[str] | tuple[str, ...] | dict[str, str] | None = None,
    type: str = "source",
) -> list[dict[str, object]]:
    """Status of ``packages`` and their dependencies against CRAN.

    Each row has package, installed, available, diff, and is_cran. ``diff``
    is -2 when the package is not installed, -1 when it is behind CRAN, 0 when
    it matches, 1 when the installed version is newer, and 2 when CRAN has no
    such package. Base and recommended packages are omitted.
    """

    names, urls = _normalize_repos(repos)
    del names
    db = _available(urls, type)
    deps = _find_deps(packages, db, dependencies)
    base = _installed().base
    deps = [name for name in deps if name not in base]
    rows = []
    for name in deps:
        installed, available, is_cran = _status(name, db)
        rows.append(
            {
                "package": name,
                "installed": installed,
                "available": available,
                "diff": _compare_one(installed, available, is_cran),
                "is_cran": is_cran,
            }
        )
    return rows


def dev_package_deps(
    pkgdir: str = ".",
    dependencies: object = NA,
    repos: str | list[str] | tuple[str, ...] | dict[str, str] | None = None,
    type: str = "source",
) -> list[dict[str, object]]:
    """Status of the dependencies declared in a local package.

    Reads the DESCRIPTION with ``local_package_deps``, then calls
    ``package_deps``. A missing Remotes field adds no GitHub packages.
    """

    pkg = _load_pkg_description(pkgdir)
    names, urls = _normalize_repos(repos)
    extra = _parse_additional_repositories(pkg)
    if extra:
        names.extend([None] * len(extra))
        urls.extend(extra)
    if "biocviews" in pkg:
        names, urls = _merge_bioc(names, urls)
    deps = local_package_deps(pkgdir, dependencies)
    rows = package_deps(deps, repos=urls, type=type)
    rows = _combine_remote_deps(rows, _extra_deps(pkg, "remotes"))
    for field in _get_extra_deps(pkg, dependencies):
        rows = _combine_rows(rows, _extra_deps(pkg, field))
    return _dedup_last(rows)


def _find_deps(packages: object, db: _Available, top_dep: object) -> list[str]:
    if _as_packages(packages) == [] or top_dep is False:
        return []
    names = _as_packages(packages)
    top_which = standardise_dep(top_dep)
    rec_which = standardise_dep(NA)
    top = _package_dependencies(names, db, top_which, recursive=False)
    top_flat = _flatten(top)
    if rec_which and top_flat:
        rec = _package_dependencies(top_flat, db, rec_which, recursive=True)
        rec_flat = _flatten(rec)
    else:
        rec_flat = []
    combined = list(names)
    combined.extend(top_flat)
    combined.extend(rec_flat)
    seen: set[str] = set()
    out: list[str] = []
    for name in reversed(combined):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _package_dependencies(
    packages: list[str],
    db: _Available,
    which: list[str],
    recursive: bool,
) -> list[list[str] | None]:
    if not recursive:
        out: list[list[str] | None] = []
        for name in packages:
            out.append(db.deps_of(name, which))
        return out

    # A name that is not a CRAN package has no outgoing edges. The recursive
    # result is empty, including when that name is only mentioned by something
    # else. Building the whole graph cannot add edges from it.
    if all(name not in db.by_name for name in dict.fromkeys(packages)):
        return [[] for _ in packages]

    tab, all_packages, name_to_idx = _graph(db, which)
    packages1 = list(dict.fromkeys(packages))
    pos: list[tuple[int, int]] = []
    for name in packages1:
        src = name_to_idx.get(name)
        if src is None:
            continue
        for dst in tab[src]:
            pos.append((src, dst))
    pos = _close(pos, tab)
    grouped: dict[str, list[str]] = defaultdict(list)
    for src, dst in pos:
        grouped[all_packages[src]].append(all_packages[dst])
    return [list(grouped.get(name, ())) for name in packages]


def _graph(
    db: _Available, which: list[str]
) -> tuple[list[list[int]], list[str], dict[str, int]]:
    key = tuple(which)
    cached = db._closure_cache.get(key)
    if cached is not None:
        tab = cached["tab"]
        all_packages = cached["all_packages"]
        name_to_idx = cached["name_to_idx"]
        assert isinstance(tab, list)
        assert isinstance(all_packages, list)
        assert isinstance(name_to_idx, dict)
        return tab, all_packages, name_to_idx

    edges: list[tuple[str, list[str]]] = []
    names: set[str] = set()
    for name in db.order:
        deps = db.deps_of(name, which) or []
        edges.append((name, deps))
        names.add(name)
        names.update(deps)
    all_packages = sorted(names, key=_cran_sort_key)
    name_to_idx = {name: index for index, name in enumerate(all_packages)}
    tab = [[] for _ in all_packages]
    for name, deps in edges:
        src = name_to_idx[name]
        tab[src] = [name_to_idx[dep] for dep in deps]
    db._closure_cache[key] = {
        "tab": tab,
        "all_packages": all_packages,
        "name_to_idx": name_to_idx,
    }
    return tab, all_packages, name_to_idx


def _close(pos: list[tuple[int, int]], tab: list[list[int]]) -> list[tuple[int, int]]:
    while True:
        groups: dict[int, list[int]] = defaultdict(list)
        for src, dst in pos:
            groups[dst].append(src)
        new: list[tuple[int, int]] = []
        for dst in sorted(groups):
            sources = groups[dst]
            for dep in tab[dst]:
                for source in sources:
                    new.append((source, dep))
        new = _unique_pairs(new)
        grown = _unique_pairs(pos + new)
        if len(grown) == len(pos):
            return pos
        pos = grown


def _unique_pairs(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, int]] = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def _flatten(groups: list[list[str] | None]) -> list[str]:
    out: list[str] = []
    for group in groups:
        if group:
            out.extend(group)
    return out


def _as_packages(packages: object) -> list[str]:
    if isinstance(packages, str):
        return [packages]
    if packages is None:
        return []
    if isinstance(packages, (list, tuple)):
        out = []
        for item in packages:
            if not isinstance(item, str):
                raise TypeError("packages must be a string or a list of strings")
            out.append(item)
        return out
    raise TypeError("packages must be a string or a list of strings")


def _status(name: str, db: _Available) -> tuple[str | None, str | None, bool]:
    remote = _package_to_remote(name)
    installed = remote["sha"]
    if remote["is_cran"]:
        available = db.version_of(name)
    else:
        available = None
    return installed, available, bool(remote["is_cran"])


def _package_to_remote(name: str) -> dict[str, object]:
    desc = _installed().descriptions.get(name, _MISSING)
    if desc is _MISSING or desc is None:
        return {"sha": None, "is_cran": True}
    remote_type = desc.get("RemoteType")
    if remote_type is None or remote_type in ("cran", "standard", "any"):
        return {"sha": desc.get("Version"), "is_cran": True}
    return {"sha": desc.get("RemoteSha"), "is_cran": False}


_MISSING = object()


def _compare_one(installed: str | None, available: str | None, is_cran: bool) -> int:
    if not is_cran:
        if installed == available:
            return CURRENT
        return BEHIND
    if available is None:
        return UNAVAILABLE
    if installed is None:
        return UNINSTALLED
    cmp = _version_cmp(installed, available)
    if cmp < 0:
        return BEHIND
    if cmp > 0:
        return AHEAD
    return CURRENT


def _version_cmp(left: str, right: str) -> int:
    return _version_cmp_parts(_parse_version(left), _parse_version(right))


def _version_cmp_parts(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    for index in range(width):
        a = left[index] if index < len(left) else 0
        b = right[index] if index < len(right) else 0
        if a != b:
            return -1 if a < b else 1
    return 0


def _parse_version(text: str) -> tuple[int, ...]:
    if not isinstance(text, str) or _VERSION_RE.fullmatch(text) is None:
        shown = text if isinstance(text, str) else type(text).__name__
        raise ValueError(f"invalid version specification {shown}")
    return tuple(int(part) for part in re.split(r"[.-]", text))


def _cran_sort_key(text: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    primary = []
    tertiary = []
    for char in text:
        if char in _PUNCT_WEIGHT:
            primary.append(_PUNCT_WEIGHT[char])
        elif char.isdigit():
            primary.append(10 + ord(char))
        elif char.isalpha():
            primary.append(40 + ord(char.lower()))
        else:
            primary.append(200 + ord(char))
        tertiary.append(1 if char.isupper() else 0)
    return (tuple(primary), tuple(tertiary))


def _dep_names(text: object) -> list[str]:
    if not isinstance(text, str) or text == "":
        return []
    return [match.group(0) for match in _NAME_RE.finditer(text) if match.group(0) != "R"]


def _parse_dep_names(text: object) -> list[str]:
    if text is None:
        return []
    if not isinstance(text, str):
        raise TypeError("dependency field must be a string")
    if re.match(rf"^[{_ASCII_SPACE}]*$", text):
        return []
    pieces = _split_deps(text)
    names = []
    operators = []
    for piece in pieces:
        name = _PAREN_GROUP.sub("", piece)
        name = _LEADING_SPACE.sub("", name)
        name = _TRAILING_SPACE.sub("", name)
        if _HAS_PAREN.search(piece) is None:
            operators.append(None)
        else:
            op_match = _OP_RE.fullmatch(piece)
            if op_match is None:
                operators.append(piece)
            else:
                operators.append(op_match.group(1))
        names.append(name)
    invalid = [op for op in operators if op is not None and op not in _VALID_OPS]
    if invalid:
        raise ValueError(
            "Invalid comparison operator in dependency: " + ", ".join(invalid)
        )
    return [name for name in names if name != "R"]


def _split_deps(text: str) -> list[str]:
    """``strsplit`` on commas, dropping a trailing empty piece."""

    pieces = _SPLIT_COMMA.split(text)
    while len(pieces) > 1 and pieces[-1] == "":
        pieces.pop()
    return pieces


def _trim(text: str) -> str:
    return _LEADING_SPACE.sub("", _TRAILING_SPACE.sub("", text))


def _normalize_repos(
    repos: str | list[str] | tuple[str, ...] | dict[str, str] | None,
) -> tuple[list[str | None], list[str]]:
    if repos is None:
        urls: list[str] = ["https://cloud.r-project.org"]
        names: list[str | None] = [None]
    elif isinstance(repos, str):
        urls = [repos]
        names = [None]
    elif isinstance(repos, dict):
        names = list(repos.keys())
        urls = [repos[key] for key in names]
    else:
        urls = list(repos)
        names = [None] * len(urls)
    fixed = []
    for url in urls:
        if url == "@CRAN@":
            url = "https://cloud.r-project.org"
        fixed.append(url)
    return names, fixed


def _available(urls: list[str], type: str) -> _Available:
    if type != "source":
        raise ValueError("invalid 'type'")
    key = (tuple(urls), type)
    cached = _db_cache.get(key)
    if cached is not None:
        return cached
    rows: list[dict[str, str]] = []
    for url in urls:
        if not url:
            continue
        contrib = url.rstrip("/") + "/src/contrib"
        text = _fetch_packages(contrib)
        rows.extend(_read_dcf_text(text, keep_white=False))
    r_version = _r_version()
    rows = [row for row in rows if _r_version_ok(row.get("Depends"), r_version)]
    os_type = "windows" if os.name == "nt" else "unix"
    rows = [
        row
        for row in rows
        if row.get("OS_type") in (None, os_type)
    ]
    rows = _remove_stale_dups(rows)
    db = _Available(rows)
    _db_cache[key] = db
    return db


def _fetch_packages(contrib: str) -> str:
    for url, compressed in (
        (contrib + "/PACKAGES.gz", True),
        (contrib + "/PACKAGES", False),
    ):
        request = urllib.request.Request(url, headers={"User-Agent": "killr-remotes"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
        except Exception:
            continue
        if compressed:
            payload = gzip.decompress(payload)
        return payload.decode("utf-8", errors="surrogateescape")
    raise RuntimeError(f"unable to access index for repository {contrib}")


def _version_from_description(path: str) -> tuple[int, ...] | None:
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        text = handle.read().decode("utf-8", errors="surrogateescape")
    records = _read_dcf_text(text, keep_white=False)
    if records and records[0].get("Version"):
        return _parse_version(records[0]["Version"])
    return None


def _r_version() -> tuple[int, ...]:
    direct = _version_from_description(
        os.path.join(_r_home(), "library", "base", "DESCRIPTION")
    )
    if direct is not None:
        return direct
    for lib in _lib_paths():
        found = _version_from_description(os.path.join(lib, "base", "DESCRIPTION"))
        if found is not None:
            return found
    raise RuntimeError("cannot find the base package version")


def _r_version_ok(depends: str | None, r_version: tuple[int, ...]) -> bool:
    if not depends:
        return True
    compact = "".join(char for char in depends if char not in _ASCII_SPACE)
    tokens = [part for part in compact.split(",") if part.startswith("R(")]
    if not tokens:
        return True
    for token in tokens:
        if len(token) < 3:
            return False
        end = 4 if len(token) >= 4 and token[3] == "=" else 3
        op = token[2:end]
        version = token[end : len(token) - 1]
        if op not in _VALID_OPS:
            raise ValueError(f"invalid comparison operator in R dependency: {op}")
        cmp = _version_cmp_parts(r_version, _parse_version(version))
        ok = {
            ">": cmp > 0,
            ">=": cmp >= 0,
            "==": cmp == 0,
            "<=": cmp <= 0,
            "<": cmp < 0,
        }[op]
        if not ok:
            return False
    return True


def _remove_stale_dups(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    names = [row.get("Package", "") for row in rows]
    seen: set[str] = set()
    dup_names: list[str] = []
    for name in names:
        if name in seen:
            dup_names.append(name)
        else:
            seen.add(name)
    if len(dup_names) > 100:
        seen_pair: set[tuple[str, str | None]] = set()
        reduced = []
        for row in rows:
            pair = (row.get("Package", ""), row.get("Version"))
            if pair in seen_pair:
                continue
            seen_pair.add(pair)
            reduced.append(row)
        rows = reduced
        names = [row.get("Package", "") for row in rows]
        seen = set()
        dup_names = []
        for name in names:
            if name in seen:
                dup_names.append(name)
            else:
                seen.add(name)
    if not dup_names:
        return rows
    positions: dict[str, list[int]] = defaultdict(list)
    dup_set = set(dup_names)
    for index, name in enumerate(names):
        if name in dup_set:
            positions[name].append(index)
    drop: set[int] = set()
    for indexes in positions.values():
        if len(indexes) < 2:
            continue
        versions = [rows[index].get("Version", "") for index in indexes]
        best = versions[0]
        for version in versions[1:]:
            if _version_cmp(version, best) > 0:
                best = version
        keep_at = 0
        for offset, version in enumerate(versions):
            if _version_cmp(version, best) == 0:
                keep_at = offset
                break
        for offset, index in enumerate(indexes):
            if offset != keep_at:
                drop.add(index)
    return [row for index, row in enumerate(rows) if index not in drop]


def _installed() -> _Installed:
    global _installed_cache
    if _installed_cache is not None:
        return _installed_cache
    found = _Installed()
    for lib in _lib_paths():
        if not os.path.isdir(lib):
            continue
        try:
            entries = os.listdir(lib)
        except OSError:
            continue
        for entry in entries:
            if entry.startswith("."):
                continue
            pkgpath = os.path.join(lib, entry)
            if not os.path.isdir(pkgpath) or not os.access(pkgpath, os.X_OK):
                continue
            desc_path = os.path.join(pkgpath, "DESCRIPTION")
            if not os.path.isfile(desc_path):
                continue
            try:
                with open(desc_path, "rb") as handle:
                    text = handle.read().decode("utf-8", errors="surrogateescape")
                records = _read_dcf_text(text, keep_white=False)
            except (OSError, ValueError):
                continue
            if not records:
                continue
            record = records[0]
            if record.get("Priority") in ("base", "recommended"):
                found.base.add(entry)
            if entry not in found.descriptions:
                if record.get("Package") != entry:
                    found.descriptions[entry] = None
                else:
                    found.descriptions[entry] = record
    _installed_cache = found
    return found


def _lib_paths() -> list[str]:
    """``.libPaths()`` after prepending ``~/R/library``, with duplicates removed.

    The comparison session prepends the user library. The remaining paths are
    R's startup list: the versioned user library, then the site libraries from
    ``Renviron``, then the system library.
    """

    raw: list[str] = [os.path.expanduser("~/R/library")]
    r_libs = os.environ.get("R_LIBS", "")
    if r_libs:
        raw.extend(_split_env_paths(r_libs))
    else:
        raw.extend(_startup_lib_paths())
    out: list[str] = []
    seen: set[str] = set()
    for path in raw:
        if not path:
            continue
        normal = os.path.normpath(os.path.expanduser(path))
        if normal not in seen:
            seen.add(normal)
            out.append(normal)
    return out


def _startup_lib_paths() -> list[str]:
    r_home = _r_home()
    platform = os.environ.get("R_PLATFORM") or _renviron_default(r_home, "R_PLATFORM") or "x86_64-pc-linux-gnu"
    version = _r_version_text()
    major_minor = ".".join(version.split(".")[:2])
    user = os.environ.get("R_LIBS_USER")
    if not user:
        user = os.path.expanduser(f"~/R/{platform}-library/{major_minor}")
    site = os.environ.get("R_LIBS_SITE")
    if not site:
        site_token = os.path.join(r_home, "site-library")
        site = _renviron_site_libs(r_home).replace("%S", site_token)
    paths = _split_env_paths(user)
    paths.extend(_split_env_paths(site))
    paths.append(os.path.join(r_home, "library"))
    return paths


def _r_home() -> str:
    env = os.environ.get("R_HOME")
    if env and os.path.isdir(env):
        return env
    for candidate in ("/usr/lib/R", "/usr/local/lib/R"):
        if os.path.isdir(os.path.join(candidate, "library", "base")):
            return candidate
    return "/usr/lib/R"


def _r_version_text() -> str:
    parts = _r_version()
    return ".".join(str(part) for part in parts)


def _renviron_default(r_home: str, name: str) -> str | None:
    path = os.path.join(r_home, "etc", "Renviron")
    if not os.path.isfile(path):
        return None
    pattern = re.compile(rf"^{name}=\${{{name}-'([^']*)'}}$")
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = pattern.match(line.strip())
            if match:
                return match.group(1)
    return None


def _renviron_site_libs(r_home: str) -> str:
    """Expand Debian's ``R_LIBS_SITE`` the way the site Renviron does.

    ``%S`` is left in place for the caller to replace with the site library.
    """

    base = "/usr/local/lib/R/site-library:%S"
    site_file = os.path.join(r_home, "etc", "Renviron.site")
    if not os.path.isfile(site_file):
        return base
    with open(site_file, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("R_LIBS_SITE="):
                continue
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            value = value.replace("${R_LIBS_SITE}", base)
            return value
    return base


def _split_env_paths(text: str) -> list[str]:
    return [part for part in text.split(os.pathsep) if part]


def _load_pkg_description(path: str) -> dict[str, str]:
    path = os.path.realpath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if os.path.isdir(path):
        desc_path = os.path.join(path, "DESCRIPTION")
        with open(desc_path, "rb") as handle:
            text = handle.read().decode("utf-8", errors="surrogateescape")
        stored = path
    else:
        text = _description_from_tarball(path)
        stored = path
    records = _read_dcf_text(text, keep_white=True)
    if not records:
        raise ValueError("DESCRIPTION file is corrupt")
    desc = {key.lower(): value for key, value in records[0].items()}
    desc["path"] = stored
    return desc


def _description_from_tarball(path: str) -> str:
    with tarfile.open(path, "r:*") as archive:
        chosen = None
        for name in archive.getnames():
            if re.match(r"^[^/]+/DESCRIPTION$", name):
                chosen = name
                break
        if chosen is None:
            raise ValueError("No 'DESCRIPTION' file in package")
        extracted = archive.extractfile(chosen)
        if extracted is None:
            raise ValueError("No 'DESCRIPTION' file in package")
        return extracted.read().decode("utf-8", errors="surrogateescape")


def _read_dcf_text(text: str, keep_white: bool) -> list[dict[str, str]]:
    lines = _split_lines(text)
    records = []
    current: list[str] = []
    for line in lines:
        if _BLANK_LINE.fullmatch(line):
            if current:
                records.append(_parse_record(current, keep_white))
                current = []
            continue
        current.append(line)
    if current:
        records.append(_parse_record(current, keep_white))
    return records


def _split_lines(text: str) -> list[str]:
    if text == "":
        return []
    lines = re.split(r"\r\n|\n|\r", text)
    if lines and lines[-1] == "" and text[-1] in "\n\r":
        lines.pop()
    return lines


def _parse_record(lines: list[str], keep_white: bool) -> dict[str, str]:
    if not lines or _TAG_LINE.match(lines[0]) is None:
        _bad_line(lines[0] if lines else "", start=True)
    order: list[str] = []
    values: dict[str, str] = {}
    index = 0
    total = len(lines)
    while index < total:
        match = _TAG_LINE.match(lines[index])
        if match is None:
            _bad_line(lines[index], start=True)
        assert match is not None
        tag = match.group(1)
        parts = [_LEADING_SPACE.sub("", match.group(2), count=1)]
        index += 1
        while index < total and _TAG_LINE.match(lines[index]) is None:
            continuation = lines[index]
            if continuation[:1] not in " \t":
                _bad_line(continuation, start=False)
            if _ESCAPED_BLANK.fullmatch(continuation):
                parts.append("")
            else:
                parts.append(continuation)
            index += 1
        if not keep_white:
            parts = [_strip_ends(part) for part in parts]
            value = _strip_ends("\n".join(parts))
        else:
            value = "\n".join(parts)
        if tag not in values:
            order.append(tag)
            values[tag] = value
    return {key: values[key] for key in order}


def _strip_ends(text: str) -> str:
    return _TRAILING_SPACE.sub("", _LEADING_SPACE.sub("", text))


def _bad_line(line: str, start: bool) -> None:
    shown = line[:20]
    if start and line[:1] in " \t":
        raise ValueError(
            f"Found continuation line starting '{shown} ...' at begin of record."
        )
    raise ValueError(f"Line starting '{shown} ...' is malformed!")


def _parse_additional_repositories(pkg: dict[str, str]) -> list[str]:
    if "additional_repositories" not in pkg:
        return []
    text = _trim(pkg["additional_repositories"])
    if text == "":
        return []
    return [part for part in _EXTRA_SPLIT.split(text) if part]


def _merge_bioc(
    names: list[str | None], urls: list[str]
) -> tuple[list[str | None], list[str]]:
    from remotes.bioc import bioc_install_repos

    have = {name for name in names if name}
    for bioc_name, bioc_url in bioc_install_repos():
        if bioc_name not in have:
            names.append(bioc_name)
            urls.append(bioc_url)
            have.add(bioc_name)
    return names, urls


def _extra_deps(pkg: dict[str, str], field: str) -> list[dict[str, object]]:
    if field not in pkg:
        return []
    # A Remotes field would name GitHub and other hosts. This check has none.
    raise ValueError(
        f"field {field} needs a remote lookup, and this module does not fetch GitHub"
    )


def _get_extra_deps(pkg: dict[str, str], dependencies: object) -> list[str]:
    lowered = _tolower_dependencies(dependencies)
    present = [name for name in lowered if name in pkg]
    standard = {
        name.lower()
        for name in standardise_dep(
            ["Depends", "Imports", "LinkingTo", "Suggests", "Enhances"]
        )
    }
    return [name for name in present if name not in standard]


def _tolower_dependencies(dependencies: object) -> list[str]:
    if dependencies is NA:
        return []
    if dependencies is True:
        return ["true"]
    if dependencies is False:
        return ["false"]
    if isinstance(dependencies, str):
        return [dependencies.lower()]
    if isinstance(dependencies, (list, tuple)):
        out = []
        for item in dependencies:
            if isinstance(item, str):
                out.append(item.lower())
        return out
    raise ValueError("Dependencies must be a boolean or a character vector")


def _combine_remote_deps(
    cran_rows: list[dict[str, object]], remote_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    if not cran_rows:
        return cran_rows
    cran_names = {row["package"] for row in cran_rows}
    remote_rows = [
        row
        for row in remote_rows
        if row["package"] is None or row["package"] in cran_names
    ]
    remote_names = {row["package"] for row in remote_rows}
    cran_rows = [row for row in cran_rows if row["package"] not in remote_names]
    return remote_rows + cran_rows


def _combine_rows(
    left: list[dict[str, object]], right: list[dict[str, object]]
) -> list[dict[str, object]]:
    return left + right


def _dedup_last(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    last: dict[object, int] = {}
    for index, row in enumerate(rows):
        if row["package"] is not None:
            last[row["package"]] = index
    kept = []
    for index, row in enumerate(rows):
        package = row["package"]
        if package is None or last[package] == index:
            kept.append(row)
    return kept

