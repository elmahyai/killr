"""Download one version of a CRAN package.

``download_version`` resolves a tarball URL and writes it to a temporary
file. The current row comes from the source ``PACKAGES`` index. An older
version is the last matching row of ``src/contrib/Meta/archive.rds``.
"""

from __future__ import annotations

import base64
import gzip
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any

_NUMERIC_VERSION = re.compile(r"^(?:[0-9]+[.-])*[0-9]+$")
_PACKAGE_VERSION = re.compile(r".+_((?:[0-9]+[.-]){1,}[0-9]+)\.tar\.gz$")
_OPS = (">", ">=", "==", "<=", "<")

_HAS_ATTR = 1 << 9
_HAS_TAG = 1 << 10
_VECSXP = 19
_STRSXP = 16
_CHARSXP = 9
_SYMSXP = 1
_LISTSXP = 2
_NIL = 254
_REF = 255

_available_cache: dict[str, list[dict[str, str]]] = {}
_archive_cache: dict[tuple[str, str], list[str] | None] = {}
_r_version: str | None = None


class _Obj:
    __slots__ = ("data", "attrs")

    def __init__(self, data: Any, attrs: dict[str, Any] | None) -> None:
        self.data = data
        self.attrs = attrs


class _Pair:
    __slots__ = ("tag", "value", "cdr")

    def __init__(self, tag: str | None, value: Any, cdr: Any) -> None:
        self.tag = tag
        self.value = value
        self.cdr = cdr


class _Reader:
    """XDR version-2 reader for the fields archive.rds needs.

    Repeated symbols are stored as one integer, ``(index << 8) | 255``.
    Character strings are written out in full.
    """

    def __init__(self, data: bytes) -> None:
        if data[:2] != b"X\n":
            raise ValueError("RDS is not an XDR serialization")
        self.buf = data
        self.i = 2
        version = self._s32()
        self._s32()
        self._s32()
        if version != 2:
            raise ValueError(f"RDS serialization version {version} is not 2")
        self.refs: list[Any] = [None]

    def _u32(self) -> int:
        value = int.from_bytes(self.buf[self.i : self.i + 4], "big")
        self.i += 4
        return value

    def _s32(self) -> int:
        value = self._u32()
        if value >= 0x80000000:
            return value - 0x100000000
        return value

    def _length(self) -> int:
        length = self._s32()
        if length == -1:
            high = self._u32()
            low = self._u32()
            return (high << 32) + low
        if length < 0:
            raise ValueError(f"negative RDS length {length}")
        return length

    def read_item(self, keep_strings: bool = False) -> Any:
        flags = self._u32()
        return self._body(flags, keep_strings)

    def _body(self, flags: int, keep_strings: bool) -> Any:
        kind = flags & 0xFF
        if kind == _REF:
            return self.refs[flags >> 8]
        if kind == _NIL:
            return None
        if kind == _SYMSXP:
            name = self.read_item(True)
            if not isinstance(name, str):
                raise ValueError("RDS symbol name is not a string")
            self.refs.append(name)
            return name
        if kind == _CHARSXP:
            return self._chars(flags, keep_strings)
        if kind == _LISTSXP:
            if flags & _HAS_ATTR:
                self.read_item(False)
            tag = self.read_item(True) if flags & _HAS_TAG else None
            value = self.read_item(tag == "row.names")
            cdr = self.read_item(False)
            return _Pair(tag if isinstance(tag, str) else None, value, cdr)
        if kind in (10, 13, 14, 15, 16, 19, 20, 24):
            return self._vector(flags, kind, keep_strings)
        raise ValueError(f"unsupported RDS type {kind} at byte {self.i}")

    def _chars(self, flags: int, keep: bool) -> str | None:
        length = self._s32()
        if length < 0:
            return None
        raw = self.buf[self.i : self.i + length]
        self.i += length
        if not keep:
            return None
        levels = flags >> 12
        if levels & (1 << 2) and not (levels & ((1 << 3) | (1 << 6))):
            return raw.decode("latin-1")
        return raw.decode("utf-8")

    def _vector(self, flags: int, kind: int, keep_strings: bool) -> Any:
        length = self._length()
        data: Any = None
        if kind == _STRSXP:
            values: list[str | None] = []
            for _ in range(length):
                item_flags = self._u32()
                item_kind = item_flags & 0xFF
                if item_kind == _REF:
                    values.append(self.refs[item_flags >> 8])
                elif item_kind == _CHARSXP:
                    values.append(self._chars(item_flags, keep_strings))
                else:
                    raise ValueError(f"unsupported CHARSXP type {item_kind}")
            if keep_strings:
                data = values
        elif kind in (10, 13):
            self.i += 4 * length
        elif kind == 14:
            self.i += 8 * length
        elif kind == 15:
            self.i += 16 * length
        elif kind == 24:
            self.i += length
        elif kind in (19, 20):
            data = [self.read_item(False) for _ in range(length)]
        attrs = self._attributes() if flags & _HAS_ATTR else None
        if kind in (19, 20) or (kind == _STRSXP and keep_strings):
            return _Obj(data, attrs)
        return None

    def _attributes(self) -> dict[str, Any]:
        node = self.read_item(False)
        out: dict[str, Any] = {}
        while isinstance(node, _Pair):
            if node.tag == "row.names":
                out["row.names"] = node.value
            node = node.cdr
        return out

    def rownames(self, package: str) -> list[str] | None:
        flags = self._u32()
        if (flags & 0xFF) != _VECSXP:
            raise ValueError("archive.rds root is not a list")
        count = self._length()
        for _ in range(count):
            frame = self.read_item(False)
            paths = _row_paths(frame)
            if paths and paths[0].split("/", 1)[0] == package:
                return paths
        return None


def _row_paths(obj: Any) -> list[str] | None:
    if not isinstance(obj, _Obj) or not obj.attrs:
        return None
    value = obj.attrs.get("row.names")
    if not isinstance(value, _Obj) or not value.data:
        return None
    paths: list[str] = []
    for item in value.data:
        if not isinstance(item, str):
            return None
        paths.append(item)
    return paths


def _installed_r_version() -> str:
    global _r_version
    if _r_version is not None:
        return _r_version
    candidates = []
    r_home = os.environ.get("R_HOME")
    if r_home:
        candidates.append(os.path.join(r_home, "library", "base", "DESCRIPTION"))
    candidates.append("/usr/lib/R/library/base/DESCRIPTION")
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("Version:"):
                    _r_version = line.split(":", 1)[1].strip()
                    return _r_version
    raise RuntimeError("cannot find the installed R version")


def _r_minor() -> str:
    parts = _installed_r_version().split(".")
    return f"{parts[0]}.{parts[1]}"


def _resolve_type(kind: str) -> str:
    if kind == "both":
        return "source"
    if kind == "binary":
        # Linux .Platform$pkgType. Windows binary is a separate contrib tree.
        if sys.platform.startswith("win"):
            return "win.binary"
        return "source"
    return kind


def _repo_urls(repos: Any) -> list[str]:
    if repos is None:
        return []
    if isinstance(repos, str):
        urls = [repos]
    elif isinstance(repos, dict):
        urls = [str(value) for value in repos.values()]
    elif isinstance(repos, (list, tuple)):
        urls = [str(value) for value in repos]
    else:
        raise TypeError("repos must be a string, a list of strings, or a dict")
    if "@CRAN@" in urls:
        raise RuntimeError("trying to use CRAN without setting a mirror")
    return urls


def _contrib_urls(repos: Any, kind: str) -> list[str]:
    if not isinstance(kind, str):
        raise RuntimeError("'type' must be a character string")
    resolved = _resolve_type(kind)
    minor = _r_minor()
    mac_path = "macosx"
    if resolved.startswith("mac.binary."):
        mac_path = "macosx/" + resolved[11:]
        resolved = "mac.binary"
    urls = []
    seen: set[str] = set()
    for repo in _repo_urls(repos):
        base = repo.rstrip("/")
        if resolved == "source":
            url = f"{base}/src/contrib"
        elif resolved == "mac.binary":
            url = f"{base}/bin/{mac_path}/contrib/{minor}"
        elif resolved == "win.binary":
            url = f"{base}/bin/windows/contrib/{minor}"
        else:
            raise RuntimeError("invalid 'type'")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _dcf_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    record: dict[str, str] = {}
    key: str | None = None
    for line in text.splitlines():
        if line == "":
            if record:
                records.append(record)
                record = {}
                key = None
            continue
        if line[0] in " \t" and key is not None:
            record[key] = record[key] + "\n" + line.strip()
            continue
        name, sep, value = line.partition(":")
        if not sep:
            continue
        key = name
        record[key] = value[1:] if value.startswith(" ") else value
    if record:
        records.append(record)
    return records


def _cmp_version(left: str, right: str) -> int:
    def parts(text: str) -> list[int]:
        return [int(piece) for piece in re.split(r"[.-]", text) if piece != ""]

    aa = parts(left)
    bb = parts(right)
    width = max(len(aa), len(bb))
    aa.extend([0] * (width - len(aa)))
    bb.extend([0] * (width - len(bb)))
    if aa < bb:
        return -1
    if aa > bb:
        return 1
    return 0


def _compare(op: str, left: str, right: str) -> bool:
    diff = _cmp_version(left, right)
    if op == "==":
        return diff == 0
    if op == ">":
        return diff > 0
    if op == ">=":
        return diff >= 0
    if op == "<":
        return diff < 0
    if op == "<=":
        return diff <= 0
    raise RuntimeError(f"Invalid comparison operator in dependency: {op}")


def _depends_allows(depends: str | None, r_version: str) -> bool:
    if not depends:
        return True
    flat = re.sub(r"\s+", "", depends)
    constraints = [piece for piece in flat.split(",") if piece.startswith("R(")]
    if not constraints:
        return True
    results = []
    for piece in constraints:
        if len(piece) < 5 or not piece.endswith(")"):
            return True
        end = 3 + (piece[3:4] == "=")
        op = piece[2:end]
        version = piece[end:-1]
        if op not in _OPS:
            return True
        results.append(_compare(op, r_version, version))
    return all(results)


def _load_available(contrib_url: str) -> list[dict[str, str]]:
    cached = _available_cache.get(contrib_url)
    if cached is not None:
        return cached
    text = None
    for suffix in ("/PACKAGES.gz", "/PACKAGES"):
        try:
            payload = _get_bytes(contrib_url + suffix)
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        if suffix.endswith(".gz"):
            try:
                payload = gzip.decompress(payload)
            except (gzip.BadGzipFile, EOFError, OSError):
                continue
        text = payload.decode("utf-8", errors="replace")
        break
    if text is None:
        raise RuntimeError(f"Cannot download file from {contrib_url}/PACKAGES.gz")
    r_version = _installed_r_version()
    os_type = "windows" if sys.platform.startswith("win") else "unix"
    rows: list[dict[str, str]] = []
    for record in _dcf_records(text):
        package = record.get("Package")
        version = record.get("Version")
        if not package or not version:
            continue
        if not _depends_allows(record.get("Depends"), r_version):
            continue
        recorded_os = record.get("OS_type")
        if recorded_os not in (None, "", os_type):
            continue
        rows.append(
            {
                "Package": package,
                "Version": version,
                "Repository": contrib_url,
            }
        )
    _available_cache[contrib_url] = rows
    return rows


def _available_rows(repos: Any, kind: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for url in _contrib_urls(repos, kind):
        rows.extend(_load_available(url))
    return rows


def _parse_deps(string: str) -> list[dict[str, str | None]]:
    if re.match(r"^\s*$", string):
        return []
    pieces = re.split(r"\s*,\s*", string)
    rows: list[dict[str, str | None]] = []
    invalid: list[str] = []
    for piece in pieces:
        name = re.sub(r"\s*\(.*?\)", "", piece)
        name = re.sub(r"^\s+|\s+$", "", name)
        if not re.search(r"\(.*\)", piece):
            compare: str | None = None
            version: str | None = None
        else:
            compare_match = re.search(r"\(\s*(\S+)\s+.*\s*\)", piece)
            version_match = re.search(r"\(\s*\S+\s+(\S*)\s*\)", piece)
            compare = compare_match.group(1) if compare_match else piece
            version = version_match.group(1) if version_match else piece
        if compare is not None and compare not in _OPS:
            invalid.append(compare)
        if name != "R":
            rows.append({"compare": compare, "version": version})
    if invalid:
        raise RuntimeError(
            "Invalid comparison operator in dependency: " + ", ".join(invalid)
        )
    return rows


def _null_criteria(criteria: Any) -> bool:
    if criteria is None:
        return True
    if isinstance(criteria, (list, tuple)) and len(criteria) == 1 and criteria[0] is None:
        return True
    return False


def _criteria_parts(criteria: Any) -> list[Any]:
    if isinstance(criteria, str):
        return criteria.split(",")
    if isinstance(criteria, (list, tuple)):
        if len(criteria) == 1 and isinstance(criteria[0], str):
            return criteria[0].split(",")
        return list(criteria)
    raise TypeError("version must be a string, a list of strings, or NULL")


def version_criteria(criteria: Any) -> list[dict[str, str | None]]:
    """Split a version specification into compare and version columns.

    ``None`` matches every version. A single numeric version such as
    ``"2.5.0"`` is ``==``. A comma-separated string is several criteria.
    """

    if _null_criteria(criteria):
        return _parse_deps("p")
    spec = []
    for part in _criteria_parts(criteria):
        text = part if isinstance(part, str) else str(part)
        if _NUMERIC_VERSION.match(text):
            spec.append(f"p(== {text})")
        else:
            spec.append(f"p({text})")
    return _parse_deps(", ".join(spec))


def version_satisfies_criteria(to_check: Any, criteria: Any) -> bool:
    """Return whether a version meets every criterion.

    A missing compare, which is what ``version = NULL`` produces, is true.
    ``"2.5"`` and ``"2.5.0"`` compare equal.
    """

    if isinstance(to_check, (list, tuple)):
        if len(to_check) != 1:
            raise ValueError("to_check must be one version")
        to_check = to_check[0]
    if not isinstance(to_check, str):
        raise TypeError("to_check must be a version string")
    results = []
    for row in version_criteria(criteria):
        compare = row["compare"]
        if compare is None:
            results.append(True)
        else:
            version = row["version"]
            if not isinstance(version, str):
                raise TypeError("criterion version must be a string")
            results.append(_compare(compare, to_check, version))
    return all(results)


def version_from_tarball(tarball_name: str) -> str:
    """Return the version encoded in a ``package_version.tar.gz`` name."""

    match = _PACKAGE_VERSION.search(tarball_name)
    if match is None:
        raise RuntimeError("replacement has length zero")
    return match.group(1)


def _version_label(version: Any) -> str:
    if version is None:
        return "NULL"
    if isinstance(version, str):
        return version
    if isinstance(version, (list, tuple)):
        return ", ".join(str(part) for part in version)
    return str(version)


def _file_path(*parts: str) -> str:
    cleaned = []
    last = len(parts) - 1
    for index, part in enumerate(parts):
        if index != last:
            part = part.rstrip("/\\")
        cleaned.append(part)
    return "/".join(cleaned)


def package_find_archives(
    package: str, repo: str, verbose: bool = False
) -> list[str] | None:
    """Return archive tarball paths for ``package``, oldest first.

    The index is ``repo/src/contrib/Meta/archive.rds``. A failed download
    is an empty archive. The paths are the data frame's row names.
    """

    key = (repo, package)
    if key in _archive_cache:
        return _archive_cache[key]
    if verbose:
        print(f"Trying {repo}", file=sys.stderr)
    url = f"{repo}/src/contrib/Meta/archive.rds"
    try:
        payload = _get_bytes(url)
        data = gzip.decompress(payload)
    except (urllib.error.URLError, TimeoutError, OSError, gzip.BadGzipFile, EOFError):
        return None
    paths = _Reader(data).rownames(package)
    _archive_cache[key] = paths
    return paths


def download_version_url(
    package: str,
    version: Any,
    repos: Any,
    type: str,
    available: list[dict[str, str]] | None = None,
    verbose: bool | None = None,
) -> str:
    """Return the tarball URL for one package version.

    Current versions come from the contrib ``PACKAGES`` index. Older
    versions come from the archive, using the last row that satisfies
    ``version``.
    """

    repos_list = _repo_urls(repos)
    if verbose is None:
        verbose = len(repos_list) > 1
    rows = available if available is not None else _available_rows(repos, type)
    package_exists = False
    for row in rows:
        if row["Package"] != package:
            continue
        package_exists = True
        if version_satisfies_criteria(row["Version"], version):
            return (
                f"{row['Repository']}/{row['Package']}_{row['Version']}.tar.gz"
            )
    for repo in repos_list:
        info = package_find_archives(package, repo, verbose=verbose)
        if info is None:
            continue
        package_exists = True
        for package_path in reversed(info):
            if version_satisfies_criteria(version_from_tarball(package_path), version):
                return _file_path(repo, "src", "contrib", "Archive", package_path)
    if not package_exists:
        raise RuntimeError(f"couldn't find package '{package}'")
    label = _version_label(version)
    raise RuntimeError(f"version '{label}' is invalid for package '{package}'")


def download(
    path: str,
    url: str,
    auth_token: str | None = None,
    basic_auth: dict[str, str] | None = None,
    quiet: bool = True,
    headers: dict[str, str] | None = None,
) -> str:
    """Download ``url`` to ``path`` with urllib and return ``path``.

    ``auth_token`` sends ``Authorization: token ...``. ``basic_auth`` sends
    a Basic header. Those two cannot be combined, and either replaces an
    Authorization header already present in ``headers``. ``quiet`` is
    accepted because ``download.file`` prints a meter; urllib does not.
    """

    if basic_auth is not None and auth_token is not None:
        raise RuntimeError(
            "Cannot use both Basic and Token authentication at the same time"
        )
    if quiet is not True and quiet is not False:
        raise TypeError("quiet must be TRUE or FALSE")
    header_map: dict[str, str] = {}
    if headers:
        header_map.update({str(key): str(value) for key, value in headers.items()})
    if basic_auth is not None:
        userpass = f"{basic_auth['user']}:{basic_auth['password']}"
        token = base64.b64encode(userpass.encode("utf-8")).decode("ascii")
        header_map["Authorization"] = f"Basic {token}"
    if auth_token is not None:
        header_map["Authorization"] = f"token {auth_token}"
    request = urllib.request.Request(url, headers=header_map)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with open(path, "wb") as handle:
                shutil.copyfileobj(response, handle)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Cannot download file from {url}") from exc
    return path


def download_version(
    package: str,
    version: Any = None,
    repos: Any = "https://cloud.r-project.org",
    type: str = "source",
    **_extra: Any,
) -> str:
    """Download one CRAN package version and return the temporary path.

    ``version=None`` is the current contrib version. ``"2.5.0"`` means
    ``== 2.5.0``. Extra keyword arguments are ignored, as ``...`` is in R.
    """

    url = download_version_url(package, version, repos, type)
    descriptor, path = tempfile.mkstemp()
    os.close(descriptor)
    try:
        return download(path, url)
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
