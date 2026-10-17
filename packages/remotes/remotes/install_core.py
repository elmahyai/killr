"""Shared download, metadata, and R CMD INSTALL path for remotes install_*."""

from __future__ import annotations

import base64
import gzip
import os
import re
import shutil
import subprocess
import sys
import tarfile
import warnings
import tempfile
import urllib.error
import urllib.request
import zipfile
from typing import Any, Callable

from remotes.add_metadata import _read_dcf, add_metadata
from remotes.standardise_dep import NA, standardise_dep

# Character NA. R's NA == x is not TRUE, so two missing SHAs still differ.
class NACharacter:
    def __repr__(self) -> str:
        return "NA"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NACharacter)

    def __hash__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        raise ValueError("missing value where TRUE/FALSE needed")


NA_CHARACTER = NACharacter()

_MISSING = object()
_INSTALLING: list[str] = []
_LIB_PATHS: list[str] | None = None
_AVAILABLE: dict[tuple, dict[str, dict[str, str]]] = {}
_BASE_PACKAGES: set[str] | None = None

_VERSION_RE = re.compile(r"^(?:[0-9]+[.-])*[0-9]+$")
_TARBALL_VER = re.compile(r".+_((?:[0-9]+[.-])*[0-9]+)\.tar\.gz$")
_BUILDING = re.compile(r"^[*] building[^A-Za-z0-9]+([-A-Za-z0-9_.]+)[^A-Za-z0-9]+$")

DownloadFn = Callable[..., str]
MetaFn = Callable[..., dict[str, Any]]
NameFn = Callable[..., Any]
ShaFn = Callable[..., Any]
FormatFn = Callable[..., str]

DOWNLOAD: dict[str, DownloadFn] = {}
METADATA: dict[str, MetaFn] = {}
PACKAGE_NAME: dict[str, NameFn] = {}
SHA: dict[str, ShaFn] = {}
FORMAT: dict[str, FormatFn] = {}


class InstallError(RuntimeError):
    """R's install_error condition, message only."""


class Remote:
    """A remote object. classes starts with ``<kind>_remote`` then ``remote``."""

    def __init__(self, kind: str, **fields: Any):
        self.kind = kind
        self.classes = (f"{kind}_remote", "remote")
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"Remote({self.kind!r}, {self._fields!r})"


def register_remote(
    kind: str,
    *,
    download: DownloadFn,
    metadata: MetaFn,
    package_name: NameFn,
    sha: ShaFn,
    fmt: FormatFn,
) -> None:
    DOWNLOAD[kind] = download
    METADATA[kind] = metadata
    PACKAGE_NAME[kind] = package_name
    SHA[kind] = sha
    FORMAT[kind] = fmt


def is_remote(value: Any) -> bool:
    classes = getattr(value, "classes", ())
    return isinstance(classes, tuple) and "remote" in classes


def remote_kind(remote: Any) -> str:
    kind = getattr(remote, "kind", None)
    if isinstance(kind, str) and kind:
        return kind
    for name in getattr(remote, "classes", ()):
        if name.endswith("_remote"):
            return name[: -len("_remote")]
    raise RuntimeError("is.remote(remote) is not TRUE")


def is_na(value: Any) -> bool:
    return value is None or isinstance(value, NACharacter)


def message(text: str) -> None:
    """R message(): stderr, with a trailing newline."""
    print(text, file=__import__("sys").stderr)


def match_arg(arg: Any, choices: list[str]) -> str:
    """match.arg. A unique prefix matches. R 4.5 quotes choices with U+201C."""
    if isinstance(arg, (list, tuple)):
        if len(arg) == 0:
            arg = ""
        else:
            arg = arg[0]
    if not isinstance(arg, str):
        arg = "" if arg is None else str(arg)
    exact = [choice for choice in choices if choice == arg]
    if exact:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(arg) and arg != ""]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise RuntimeError(f"'arg' should be one of {quoted}")


def is_interactive() -> bool:
    """Rscript is non-interactive. A Python script has no ps1 either."""
    import sys

    return hasattr(sys, "ps1") and bool(getattr(sys, "ps1", None)) and sys.stdin.isatty()


def resolve_upgrade(upgrade: Any, interactive: bool | None = None) -> str:
    if upgrade is True:
        upgrade = "always"
    elif upgrade is False:
        upgrade = "never"
    upgrade = match_arg(upgrade, ["default", "ask", "always", "never"])
    if upgrade == "default":
        upgrade = os.environ.get("R_REMOTES_UPGRADE", "ask")
        upgrade = match_arg(upgrade, ["default", "ask", "always", "never"])
        if upgrade == "default":
            upgrade = "ask"
    if interactive is None:
        interactive = is_interactive()
    if not interactive and upgrade == "ask":
        upgrade = "always"
    return upgrade


def file_ext(path: str) -> str:
    base = os.path.basename(path)
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1]


def is_binary_pkg(path: str) -> bool:
    return file_ext(path) in ("tgz", "zip")


def as_paths(value: Any) -> list[str]:
    """One string is one path. A list is several paths, the way a character vector is."""
    if isinstance(value, (list, tuple)):
        return [os.fspath(item) for item in value]
    if value is None:
        return []
    return [os.fspath(value)]


def one_lib(lib: Any) -> str | None:
    if lib is None:
        return None
    if isinstance(lib, (list, tuple)):
        if not lib:
            return None
        return os.fspath(lib[0])
    return os.fspath(lib)


def build_url(host: str, *parts: Any) -> str:
    """file.path of the host and the parts, then a scheme when the host has none."""
    pieces = [str(host).rstrip("/")]
    for part in parts:
        if part is None:
            continue
        text = str(part).strip("/")
        if text == "":
            continue
        pieces.append(text)
    url = "/".join(pieces)
    if re.match(r"^[A-Za-z]+://", url):
        return url
    return "https://" + url


def download(
    path: str,
    url: str,
    auth_token: str | None = None,
    basic_auth: dict[str, str] | None = None,
    quiet: bool = True,
    headers: dict[str, str] | None = None,
) -> str:
    """Download url to path. Token and basic auth both set is an error."""
    if basic_auth is not None and auth_token is not None:
        raise RuntimeError("Cannot use both Basic and Token authentication at the same time")
    hdrs: dict[str, str] = {"User-Agent": "R (3.6.0)"}
    if headers:
        for key, value in headers.items():
            if value is not None and not isinstance(value, NACharacter):
                hdrs[key] = value
    if basic_auth is not None:
        userpass = f"{basic_auth['user']}:{basic_auth['password']}".encode()
        hdrs["Authorization"] = "Basic " + base64.b64encode(userpass).decode("ascii")
    if auth_token is not None and not isinstance(auth_token, NACharacter):
        hdrs["Authorization"] = f"token {auth_token}"
    request = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = RuntimeError(f"HTTP error {exc.code} from {url}: {detail[:500]}")
        error.status = exc.code  # type: ignore[attr-defined]
        raise error from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to download `{url}`: {exc}") from exc
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


def _temp_file(suffix: str) -> str:
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    name = handle.name
    handle.close()
    return name


def git_extract_sha1_tar(bundle: str) -> str | None:
    """SHA1 from the pax comment of a git archive, or None."""
    try:
        with open(bundle, "rb") as handle:
            raw = handle.read(2)
        if raw == b"\x1f\x8b":
            with gzip.open(bundle, "rb") as handle:
                data = handle.read(0x200 + 0x33)
        else:
            with open(bundle, "rb") as handle:
                data = handle.read(0x200 + 0x33)
    except OSError:
        return None
    if len(data) < 0x200 + 0x33:
        return None
    res = data[0x200 : 0x200 + 0x33].decode("latin1", errors="replace")
    if res.startswith("52 comment="):
        return res[len("52 comment=") :]
    return None


def _slash_count(path: str) -> int:
    return path.count("/")


def getrootdir(file_list: list[str]) -> str:
    if not file_list:
        raise RuntimeError("length(file_list) > 0 is not TRUE")
    counts = [_slash_count(name) for name in file_list]
    least = min(counts)
    if least == 0:
        return "."
    chosen = file_list[counts.index(least)]
    return re.sub(r"/[^/]*$", "", chosen)


def _listed_names(names: list[tuple[str, bool]]) -> list[str]:
    """R's untar and unzip list directories with a trailing slash."""
    listed = []
    for name, is_dir in names:
        if is_dir and not name.endswith("/"):
            name = name + "/"
        listed.append(name)
    return listed


def _decompress(src: str, target: str) -> str:
    if not os.path.exists(src):
        raise RuntimeError(f"file.exists({src}) is not TRUE")
    if re.search(r"\.zip$", src):
        with zipfile.ZipFile(src) as archive:
            pairs = [(info.filename, info.is_dir()) for info in archive.infolist()]
            archive.extractall(target)
        outdir = getrootdir(_listed_names(pairs))
    elif re.search(r"\.(tar|tar\.gz|tar\.bz2|tgz|tbz)$", src):
        with tarfile.open(src, "r:*") as archive:
            pairs = [(member.name, member.isdir()) for member in archive.getmembers()]
            if "filter" in tarfile.TarFile.extractall.__code__.co_varnames:
                archive.extractall(target, filter="data")
            else:
                archive.extractall(target)
        outdir = getrootdir(_listed_names(pairs))
    else:
        ext = re.sub(r"^[^.]*\.", "", os.path.basename(src))
        raise RuntimeError(f"Don't know how to decompress files with extension {ext}")
    return os.path.join(target, outdir)


def source_pkg(path: str, subdir: str | None = None) -> str:
    """Directory that holds DESCRIPTION. Archives are unpacked into a temp directory."""
    if not os.path.isdir(path):
        outdir = tempfile.mkdtemp(prefix="remotes")
        path = _decompress(path, outdir)
    pkg_path = path if subdir is None else os.path.join(path, subdir)
    if not os.path.exists(os.path.join(pkg_path, "DESCRIPTION")):
        raise RuntimeError("Does not appear to be an R package (no DESCRIPTION)")
    configure = os.path.join(pkg_path, "configure")
    if os.path.exists(configure):
        os.chmod(configure, 0o777)
    return pkg_path


def clear_description_md5(pkg_path: str) -> None:
    path = os.path.join(pkg_path, "MD5")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="surrogateescape") as handle:
        lines = handle.read().splitlines()
    kept = [line for line in lines if not re.search(r".*\*DESCRIPTION$", line)]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(kept))
        if kept:
            handle.write("\n")


def read_desc(path: str) -> dict[str, str]:
    return _read_dcf(path)


def description_field(directory: str, field: str) -> str | None:
    path = os.path.join(directory, "DESCRIPTION")
    if not os.path.exists(path):
        return None
    record = read_desc(path)
    if field in record:
        return record[field]
    for key, value in record.items():
        if key.lower() == field.lower():
            return value
    return None


def session_lib_paths() -> list[str]:
    """Proof order: ~/R/library, then R's .libPaths(). Read-only."""
    global _LIB_PATHS
    if _LIB_PATHS is not None:
        return _LIB_PATHS
    home = os.path.realpath(os.path.expanduser("~/R/library"))
    completed = subprocess.run(
        ["Rscript", "-e", "cat(paste(.libPaths(), collapse='\n'))"],
        check=False,
        capture_output=True,
        text=True,
    )
    found = []
    if completed.returncode == 0:
        found = [os.path.realpath(line) for line in completed.stdout.splitlines() if line]
    if home not in found:
        found.insert(0, home)
    elif found[0] != home:
        found = [home] + [path for path in found if path != home]
    _LIB_PATHS = found
    return found


def _base_packages() -> set[str]:
    global _BASE_PACKAGES
    if _BASE_PACKAGES is not None:
        return _BASE_PACKAGES
    names: set[str] = set()
    for lib in session_lib_paths():
        if not os.path.isdir(lib):
            continue
        try:
            entries = os.listdir(lib)
        except OSError:
            continue
        for entry in entries:
            desc = os.path.join(lib, entry, "DESCRIPTION")
            if not os.path.isfile(desc):
                continue
            try:
                record = read_desc(desc)
            except (OSError, ValueError):
                continue
            priority = record.get("Priority", "")
            package = record.get("Package", entry)
            if priority in ("base", "recommended"):
                names.add(package)
    _BASE_PACKAGES = names
    return names


def find_installed_description(name: str, lib: list[str] | None = None) -> dict[str, str] | None:
    """packageDescription. The first library that has the package wins."""
    libraries = lib if lib is not None else session_lib_paths()
    for directory in libraries:
        path = os.path.join(directory, name, "DESCRIPTION")
        if os.path.isfile(path):
            try:
                return read_desc(path)
            except (OSError, ValueError):
                return None
    return None


def installed_version(lib: str, name: str) -> str | None:
    return description_field(os.path.join(lib, name), "Version")


def package_name_of(remote: Any, **kwargs: Any) -> Any:
    kind = remote_kind(remote)
    handler = PACKAGE_NAME.get(kind)
    if handler is None:
        return getattr(remote, "repo", NA_CHARACTER)
    return handler(remote, **kwargs)


def remote_sha_of(remote: Any, **kwargs: Any) -> Any:
    kind = remote_kind(remote)
    handler = SHA.get(kind)
    if handler is None:
        return NA_CHARACTER
    return handler(remote, **kwargs)


def metadata_of(remote: Any, bundle: str | None, source: str | None, sha: Any) -> dict[str, Any]:
    kind = remote_kind(remote)
    handler = METADATA.get(kind)
    if handler is None:
        return {}
    return handler(remote, bundle=bundle, source=source, sha=sha)


def format_remote(remote: Any) -> str:
    kind = remote_kind(remote)
    handler = FORMAT.get(kind)
    if handler is None:
        return kind
    return handler(remote)


def different_sha(remote_sha: Any, local_sha: Any) -> bool:
    """True unless the two SHAs are the same non-missing string."""
    if is_na(remote_sha) or is_na(local_sha):
        return True
    return remote_sha != local_sha


def _or_null(left: Any, right: Any) -> Any:
    if left is None:
        return right
    return left


def package2remote(name: str, lib: list[str] | None = None, repos: Any = None, type: str | None = None) -> Remote:
    """Installed DESCRIPTION as a remote. A missing package is a cran remote with SHA NA."""
    record = find_installed_description(name, lib)
    if record is None:
        return Remote(
            "cran",
            name=name,
            repos=repos,
            pkg_type=type,
            sha=NA_CHARACTER,
        )
    remote_type = record.get("RemoteType")
    version = record.get("Version")
    if remote_type is None or remote_type in ("cran", "standard", "any"):
        return Remote(
            "cran",
            name=record.get("Package", name),
            repos=repos,
            pkg_type=type,
            sha=version if version is not None else NA_CHARACTER,
        )
    if remote_type == "local":
        path = (record.get("RemoteUrl") or "").strip()
        if path == "":
            path = record.get("RemotePkgRef")
        return Remote(
            "local",
            path=path,
            subdir=record.get("RemoteSubdir"),
            sha=_or_null(record.get("RemoteSha"), version),
        )
    if remote_type == "github":
        return Remote(
            "github",
            host=record.get("RemoteHost"),
            package=record.get("RemotePackage"),
            repo=record.get("RemoteRepo"),
            subdir=record.get("RemoteSubdir"),
            username=record.get("RemoteUsername"),
            ref=record.get("RemoteRef"),
            sha=record.get("RemoteSha"),
            auth_token=None,
        )
    # Other remote types keep the recorded SHA. The install skip uses that field.
    return Remote(remote_type, repo=record.get("RemoteRepo") or name, sha=record.get("RemoteSha", NA_CHARACTER), name=name)


def local_sha(name: str) -> Any:
    if is_na(name):
        return NA_CHARACTER
    sha = getattr(package2remote(str(name)), "sha", None)
    if sha is None:
        return NA_CHARACTER
    return sha


def _r_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _r_character(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return _r_string(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return "character()"
        return "c(" + ", ".join(_r_string(str(item)) for item in value) + ")"
    return _r_string(str(value))


def _r_dependencies(value: Any) -> str:
    if value is False:
        return "FALSE"
    if value is True:
        return "TRUE"
    if value is NA or value is None or isinstance(value, NACharacter):
        return "NA"
    if isinstance(value, (list, tuple)):
        return "c(" + ", ".join(_r_string(str(item)) for item in value) + ")"
    if isinstance(value, str):
        return _r_string(value)
    return "NA"


def _errors_from_warnings() -> bool:
    """R_REMOTES_NO_ERRORS_FROM_WARNINGS defaults to true, so a failed install warns."""
    raw = os.environ.get("R_REMOTES_NO_ERRORS_FROM_WARNINGS", "true").strip().lower()
    return raw not in ("true", "1", "yes", "t")


def r_cmd_install(pkgdir: str, lib: str | None, quiet: bool, install_opts: Any = None) -> None:
    """R CMD INSTALL into lib. lib is the destination, the way install.packages uses it.

    A non-zero status warns and the caller still returns the package name.
    Set R_REMOTES_NO_ERRORS_FROM_WARNINGS to false to raise instead.
    """
    # R CMD INSTALL has no --quiet. quiet only hides the captured output.
    command = ["R", "CMD", "INSTALL"]
    if lib is not None:
        command.extend(["-l", lib])
    if install_opts:
        opts = [install_opts] if isinstance(install_opts, str) else list(install_opts)
        command.extend(str(opt) for opt in opts)
    command.append(pkgdir)
    env = os.environ.copy()
    if lib is not None:
        libs = lib + os.pathsep + os.pathsep.join(session_lib_paths())
        env["R_LIBS"] = libs
        env["R_LIBS_USER"] = libs
        env["R_LIBS_SITE"] = libs
    env["RGL_USE_NULL"] = "TRUE"
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    if completed.returncode != 0:
        detail = ((completed.stderr or "") + (completed.stdout or "")).strip()
        if _errors_from_warnings():
            raise RuntimeError(detail or f"R CMD INSTALL failed with status {completed.returncode}")
        if not quiet and detail:
            sys.stderr.write(detail + "\n")
        warnings.warn(
            f"installation of package '{pkgdir}' had non-zero exit status",
            stacklevel=2,
        )
        return
    if not quiet and completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")


def r_install_packages(
    packages: list[str],
    repos: Any,
    type: str,
    dependencies: Any,
    quiet: bool,
    lib: str | None,
    install_opts: Any = None,
) -> None:
    """utils::install.packages for a cran_remote. The destination is lib."""
    if lib is None:
        raise RuntimeError("lib is required so install.packages does not use the user library")
    repos_value = repos
    if isinstance(repos, dict):
        names = ", ".join(_r_string(str(key)) for key in repos)
        urls = ", ".join(_r_string(str(value)) for value in repos.values())
        repos_code = f"stats::setNames(c({urls}), c({names}))"
    else:
        repos_code = _r_character(repos_value)
    opts = "NULL"
    if install_opts:
        opts = _r_character(install_opts)
    script = "\n".join(
        [
            f"pkgs <- {_r_character(packages)}",
            f"lib <- {_r_character([lib])}",
            f"repos <- {repos_code}",
            "utils::install.packages(",
            "  pkgs,",
            "  lib = lib,",
            "  repos = repos,",
            f"  type = {_r_string(type)},",
            f"  dependencies = {_r_dependencies(dependencies)},",
            f"  quiet = {'TRUE' if quiet else 'FALSE'},",
            f"  INSTALL_opts = {opts}",
            ")",
        ]
    )
    path = _temp_file(".R")
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        completed = subprocess.run(["Rscript", path], capture_output=True, text=True)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or "") + (completed.stdout or "")
        raise RuntimeError(detail.strip() or "install.packages failed")
    if not quiet and completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")


def normalize_build_opts(build_opts: list[str] | None, build_manual: bool, build_vignettes: bool) -> list[str]:
    opts = list(build_opts or [])
    if build_manual is not True:
        if "--no-manual" not in opts:
            opts.append("--no-manual")
    else:
        opts = [opt for opt in opts if opt != "--no-manual"]
    if build_vignettes is not True:
        if "--no-build-vignettes" not in opts:
            opts.append("--no-build-vignettes")
    else:
        opts = [opt for opt in opts if opt != "--no-build-vignettes"]
    return opts


def safe_build_package(
    pkgdir: str,
    build_opts: list[str] | None,
    build_manual: bool,
    build_vignettes: bool,
    dest_path: str,
    quiet: bool,
) -> str:
    opts = normalize_build_opts(build_opts, build_manual, build_vignettes)
    if not quiet:
        message("Running `R CMD build`...")
    command = ["R", "CMD", "build", *opts, os.path.realpath(pkgdir)]
    completed = subprocess.run(command, cwd=dest_path, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError("Failed to `R CMD build` package, try `build = FALSE`.")
    lines = [line for line in completed.stdout.splitlines() if line]
    if lines:
        match = _BUILDING.match(lines[-1])
        if match:
            return os.path.join(dest_path, match.group(1))
    archives = [
        os.path.join(dest_path, name)
        for name in os.listdir(dest_path)
        if name.endswith(".tar.gz")
    ]
    if not archives:
        raise RuntimeError("Failed to `R CMD build` package, try `build = FALSE`.")
    return archives[0]


def _check_circular(pkgdir: str, quiet: bool) -> bool:
    name = description_field(pkgdir, "Package")
    if name is None:
        return False
    if name in _INSTALLING:
        if not quiet:
            message(f"Skipping {name}, it is already being installed")
        return True
    _INSTALLING.append(name)
    return False


def install_source(
    pkgdir: str,
    dependencies: Any,
    quiet: bool,
    build: Any,
    build_opts: list[str] | None,
    build_manual: bool,
    build_vignettes: bool,
    upgrade: Any,
    repos: Any,
    type: str | None,
    **kwargs: Any,
) -> str:
    """install(): dependencies, optional R CMD build, then R CMD INSTALL."""
    root = len(_INSTALLING) == 0
    try:
        record = read_desc(os.path.join(pkgdir, "DESCRIPTION"))
        pkg_name = record.get("Package")
        if pkg_name is None:
            lowered = {key.lower(): value for key, value in record.items()}
            pkg_name = lowered.get("package")
        if pkg_name is None:
            raise RuntimeError("Does not appear to be an R package (no DESCRIPTION)")
        if _check_circular(pkgdir, quiet):
            return str(pkg_name)
        # Lazy import: install_deps imports the update path, which imports this module.
        from remotes.install_deps import install_deps

        install_deps(
            pkgdir,
            dependencies=dependencies,
            quiet=quiet,
            build=build,
            build_opts=build_opts,
            build_manual=build_manual,
            build_vignettes=build_vignettes,
            upgrade=upgrade,
            repos=repos,
            type=type,
            **kwargs,
        )
        built = pkgdir
        if build is True:
            dest = tempfile.mkdtemp()
            built = safe_build_package(pkgdir, build_opts, build_manual, build_vignettes, dest, quiet)
        r_cmd_install(built, one_lib(kwargs.get("lib")), bool(quiet), kwargs.get("INSTALL_opts"))
        return str(pkg_name)
    finally:
        if root:
            _INSTALLING.clear()


def _meta_for_write(meta: dict[str, Any]) -> dict[str, Any]:
    """None and character NA are dropped. Strings are written."""
    cleaned: dict[str, Any] = {}
    for key, value in meta.items():
        if value is None or isinstance(value, NACharacter):
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned


def install_one(
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
    if not is_remote(remote):
        raise RuntimeError("is.remote(remote) is not TRUE")
    kind = remote_kind(remote)
    package_name = package_name_of(remote)
    local = local_sha(package_name)
    sha = remote_sha_of(remote, local_sha=local)
    if force is not True and not different_sha(sha, local):
        if not quiet:
            shown = "" if is_na(sha) else str(sha)[:8]
            message(
                f"Skipping install of '{package_name}' from a {kind} remote,"
                f" the SHA1 ({shown}) has not changed since last install.\n"
                "  Use `force = TRUE` to force installation"
            )
        return None if is_na(package_name) else package_name
    if kind == "cran":
        from remotes.install_cran import install_packages

        name = None if is_na(package_name) else str(package_name)
        install_packages(
            [name] if name else [],
            repos=getattr(remote, "repos", repos),
            type=getattr(remote, "pkg_type", type) or "source",
            dependencies=dependencies,
            quiet=quiet,
            **kwargs,
        )
        return name
    bundle = None
    source = None
    try:
        try:
            bundle = DOWNLOAD[kind](remote, quiet=quiet)
        except Exception as exc:
            # try() always catches a download error and returns NA. quiet only hides it.
            if not quiet:
                message(str(exc))
            return None
        source = source_pkg(bundle, subdir=getattr(remote, "subdir", None))
        update_submodules(source, getattr(remote, "subdir", None), quiet)
        meta = metadata_of(remote, bundle, source, sha)
        add_metadata(source, _meta_for_write(meta))
        clear_description_md5(source)
        return install_source(
            source,
            dependencies=dependencies,
            quiet=quiet,
            build=build,
            build_opts=build_opts if build_opts is not None else ["--no-resave-data", "--no-manual", "--no-build-vignettes"],
            build_manual=build_manual,
            build_vignettes=build_vignettes,
            upgrade=upgrade,
            repos=repos,
            type=type,
            **kwargs,
        )
    finally:
        if source and os.path.isdir(source):
            shutil.rmtree(source, ignore_errors=True)
        if bundle and bundle != source and os.path.exists(bundle):
            if os.path.isdir(bundle):
                shutil.rmtree(bundle, ignore_errors=True)
            else:
                try:
                    os.unlink(bundle)
                except OSError:
                    pass


def _install_error(remote: Any, error: BaseException) -> str:
    try:
        name = package_name_of(remote)
        if is_na(name):
            name = "unknown package"
    except Exception:
        name = "unknown package"
    try:
        where = format_remote(remote)
    except Exception:
        where = "remote"
    return f"Failed to install '{name}' from {where}:\n  {error}"


def install_remotes(remotes: list[Any], **kwargs: Any) -> list[Any]:
    result: list[Any] = []
    for remote in remotes:
        try:
            result.append(install_one(remote, **kwargs))
        except InstallError:
            raise
        except Exception as exc:
            raise InstallError(_install_error(remote, exc)) from exc
    return result


def fix_repositories(repos: Any) -> list[str]:
    if repos is None:
        repos = ["https://cloud.r-project.org"]
    if isinstance(repos, str):
        repos = [repos]
    if isinstance(repos, dict):
        repos = list(repos.values())
    if len(repos) == 0:
        return []
    return ["https://cloud.r-project.org" if item == "@CRAN@" else str(item) for item in repos]


def contrib_url(repos: Any, type: str | None = "source") -> list[str]:
    suffix = "src/contrib" if type in (None, "source", "both") else "src/contrib"
    urls = []
    for repo in fix_repositories(repos):
        urls.append(repo.rstrip("/") + "/" + suffix)
    return urls


def _parse_packages(text: str, repository: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    current: dict[str, str] = {}
    last_key: str | None = None
    for line in text.splitlines():
        if line.strip() == "":
            if current.get("Package") and current["Package"] not in records:
                current["Repository"] = repository
                records[current["Package"]] = current
            current = {}
            last_key = None
            continue
        if line[:1] in " \t" and last_key is not None:
            current[last_key] = current.get(last_key, "") + " " + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        last_key = key.strip()
        current[last_key] = value.strip()
    if current.get("Package") and current["Package"] not in records:
        current["Repository"] = repository
        records[current["Package"]] = current
    return records


def available_packages(repos: Any = None, type: str | None = "source") -> dict[str, dict[str, str]]:
    """Cached PACKAGES index. The first row for a package name is kept."""
    fixed = tuple(fix_repositories(repos))
    key = (fixed, type or "source")
    cached = _AVAILABLE.get(key)
    if cached is not None:
        return cached
    combined: dict[str, dict[str, str]] = {}
    for url in contrib_url(fixed, type):
        text = None
        for name in ("PACKAGES", "PACKAGES.gz"):
            dest = _temp_file(".packages")
            try:
                download(dest, url.rstrip("/") + "/" + name)
                raw = open(dest, "rb").read()
                if name.endswith(".gz") or raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                text = raw.decode("utf-8", errors="replace")
                break
            except Exception:
                text = None
            finally:
                try:
                    os.unlink(dest)
                except OSError:
                    pass
        if text is None:
            continue
        for package, record in _parse_packages(text, url).items():
            if package not in combined:
                combined[package] = record
    _AVAILABLE[key] = combined
    return combined


def trim_ws(value: Any) -> Any:
    if is_na(value) or not isinstance(value, str):
        return value
    return re.sub(r"^[\s\f\n\r\t\v]+|[\s\f\n\r\t\v]+$", "", value)


def dep_names(field: str | None) -> list[str]:
    if not field or not field.strip():
        return []
    names = []
    for piece in re.split(r"\s*,\s*", field.strip()):
        name = re.sub(r"\s*\(.*?\)", "", piece).strip()
        if name and name != "R":
            names.append(name)
    return names


def find_deps(packages: list[str], available: dict[str, dict[str, str]], top_dep: Any = True) -> list[str]:
    if len(packages) == 0 or top_dep is False:
        return []
    fields = [name.lower() for name in standardise_dep(top_dep)]
    rec_fields = [name.lower() for name in standardise_dep(NA)]
    top: list[str] = []
    for package in packages:
        record = available.get(package, {})
        for field, value in record.items():
            if field.lower() in fields:
                top.extend(dep_names(value))
    rec: list[str] = []
    if rec_fields and top:
        seen = set(top)
        stack = list(top)
        while stack:
            name = stack.pop()
            record = available.get(name, {})
            for field, value in record.items():
                if field.lower() not in rec_fields:
                    continue
                for dep in dep_names(value):
                    if dep not in seen:
                        seen.add(dep)
                        rec.append(dep)
                        stack.append(dep)
    ordered = list(packages) + top + rec
    # unique(rev(...)) keeps the last occurrence, then that order is reversed back.
    # unique(rev(c(packages, deps))) keeps the last copy, in reverse order.
    reversed_unique: list[str] = []
    seen_rev: set[str] = set()
    for name in reversed(ordered):
        if name not in seen_rev:
            seen_rev.add(name)
            reversed_unique.append(name)
    return reversed_unique


def run_git(args: list[str], quiet: bool = True, path: str | None = None) -> list[str]:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git does not seem to be installed on your system.")
    if not quiet:
        message(git + " " + " ".join(args))
    completed = subprocess.run(
        [git, *args],
        cwd=path or None,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode})")
    return [line for line in completed.stdout.splitlines() if line != ""]


def svn_binary() -> str:
    found = shutil.which("svn")
    if found:
        return found
    raise RuntimeError("SVN does not seem to be installed on your system.")


def update_submodules(source: str, subdir: str | None, quiet: bool) -> None:
    path = os.path.join(source, ".gitmodules")
    if not os.path.exists(path) and subdir:
        up = source
        for _ in subdir.split("/"):
            up = os.path.dirname(up)
        path = os.path.join(up, ".gitmodules")
    if not os.path.exists(path):
        return
    # A missing or empty .gitmodules is the usual package. Parsing is the R loop
    # only when path and url are both present.
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return
    section = None
    rows: dict[str, dict[str, str]] = {}
    name_re = re.compile(r'^\s*\[submodule "(?P<sub>.*)"\]\s*$')
    map_re = re.compile(r"^\s*(?P<name>[A-Za-z][A-Za-z0-9-]*)\s*=\s*(?P<value>.*)\s*$")
    for line in lines:
        header = name_re.match(line)
        if header:
            section = header.group("sub")
            rows.setdefault(section, {})
            continue
        mapped = map_re.match(line)
        if mapped and section is not None:
            rows[section][mapped.group("name").lower()] = mapped.group("value")
    for info in rows.values():
        url = info.get("url")
        dest = info.get("path")
        if not url or not dest:
            continue
        branch = info.get("branch")
        args = ["clone", "--depth", "1", "--no-hardlinks", "--recurse-submodules"]
        if branch and branch != "HEAD":
            args.extend(["--branch", branch])
        args.extend([url, os.path.join(source, dest)])
        try:
            run_git(args, quiet=quiet)
        except RuntimeError:
            if not quiet:
                raise


def default_build_opts() -> list[str]:
    return ["--no-resave-data", "--no-manual", "--no-build-vignettes"]


def call_install_remotes(remotes: list[Any], **kwargs: Any) -> list[Any]:
    if "build_opts" not in kwargs or kwargs["build_opts"] is None:
        kwargs["build_opts"] = default_build_opts()
    return install_remotes(remotes, **kwargs)
