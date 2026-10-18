#!/usr/bin/env python3
"""Prepare one CRAN tarball for translation. Writes the orchestrator database with --store-low or --fill-high."""

from __future__ import annotations

import json
import os
import re
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRIB = ROOT / "rcran" / "contrib"
INDEX = ROOT / "orchestrator" / "index"
EXPERIENCE = ROOT / "ai-handbook" / "experience"
CRATE_MODEL = "claude-haiku-5-5-thinking-high"
PYTHON_MODEL = "gpt-5.6-luna-medium"
BASE_PACKAGES = {
    "base",
    "compiler",
    "datasets",
    "graphics",
    "grDevices",
    "grid",
    "methods",
    "parallel",
    "splines",
    "stats",
    "stats4",
    "tcltk",
    "tools",
    "utils",
}
REGISTER_SRC = re.compile(
    r"(?i)register|r_init|(^|_)init\.(c|cpp|cc|cxx)$|rcppexports"
)
FALSE_WAIT = {
    "FUN",
    "FUN.VALUE",
    "pkg",
    "error",
    "object",
    "value",
    "data",
    "x",
    "n",
    "i",
    "j",
}

SKIP_SRC = {"makevars", "makevars.win", "makevars.ucrt", "makefile"}
C_EXT = {".c"}
FORTRAN_EXT = {".f", ".for", ".f90", ".f95", ".f03"}
CPP_EXT = {".cpp", ".cc", ".cxx"}
OTHER_SKIP_EXT = {".o", ".so", ".a", ".dll", ".dylib", ".obj", ".lib", ".exe"}
OTHER_LANG = {
    ".h": "header",
    ".hpp": "header",
    ".hh": "header",
    ".hxx": "header",
    ".cuh": "CUDA header",
    ".cu": "CUDA",
    ".s": "assembly",
    ".asm": "assembly",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".rs": "Rust",
    ".inc": "include",
    ".fpp": "Fortran preprocess",
    ".i": "SWIG",
    ".r": "R",
}
R_EXT = {".r", ".s"}
RD_EXT = {".rd"}
DIRS = ("R", "src", "man", "data", "tests", "vignettes")

C_DEF = re.compile(
    r"^(?:static\s+)?(?:[\w\s\*]+?)\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{",
    re.M,
)
C_DEF_LINE = re.compile(
    r"^(?:static\s+)?(?:void|int|double|float|char|long|unsigned|SEXP|Rboolean|"
    r"Rcomplex|size_t|R_len_t|R_xlen_t)\b.*\(",
    re.M,
)
FORTRAN_UNIT = re.compile(
    r"(?im)^(?:[\s\d]*|     )(?:SUBROUTINE|FUNCTION|ENTRY)\s+([A-Za-z][A-Za-z0-9_]*)"
)
R_DEF = re.compile(
    r"(?m)^[ \t]*(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|([A-Za-z.][A-Za-z0-9._]*))"
    r"\s*(?:<-|=)\s*function\b"
)
NATIVE_CALL = re.compile(
    r"""\.(C|Fortran|Call|External)\s*\(\s*(?:(?:PACKAGE\s*=\s*[^,]+,\s*)?"""
    r"""["']([^"']+)["']|([A-Za-z.][A-Za-z0-9._]*))"""
)
NS_EXPORT = re.compile(r"export\(([^)]*)\)", re.S)
NS_PATTERN = re.compile(r"exportPattern\(\s*[\"']([^\"']+)[\"']\s*\)")
NS_S3 = re.compile(r"S3method\(\s*([^,\s]+)\s*,\s*([^)\s]+)\s*\)")
NS_METHODS = re.compile(r"exportMethods\(([^)]*)\)", re.S)
R_TOKEN = re.compile(r"[A-Za-z.][A-Za-z0-9._]*|`[^`]+`")
NS_DYNLIB = re.compile(r"useDynLib\(\s*([^)\s,]+)")
RD_NAME = re.compile(r"\\name\{([^}]+)\}")
LOAD_NS = re.compile(r"\b([A-Za-z.][A-Za-z0-9.]*):::")
LOAD_EXPORT = re.compile(r"\b([A-Za-z.][A-Za-z0-9.]*)::")
LOAD_CALL = re.compile(
    r"\b([A-Za-z.][A-Za-z0-9.]*):::{0,1}(`[^`]+`|[A-Za-z.][A-Za-z0-9._]*)"
)
LOAD_LIB = re.compile(
    r"""\b(?:library|require|requireNamespace)\s*\(\s*["']?([A-Za-z.][A-Za-z0-9.]*)"""
)
DEP_SECTIONS = (
    ("depends", "Depends"),
    ("imports", "Imports"),
    ("suggests", "Suggests"),
    ("linking_to", "LinkingTo"),
)


def prepare(package: str, contrib: Path = CONTRIB) -> dict:
    record = package_record(package)
    routed = replaced_entry(package)
    status = record.get("status") or ""
    if status == "replaced" or routed:
        return thin_report(package, record, routed, contrib, "replaced")
    if status == "complete":
        return thin_report(package, record, {}, contrib, "complete")
    report = analyze(package, contrib)
    report["packets"] = build_packets(report["functions"])
    report["launch"] = build_launch(report)
    return report


def analyze(package: str, contrib: Path = CONTRIB) -> dict:
    tarball, version = find_tarball(package, contrib)
    members = read_tarball(tarball, package)
    fields = dcf_fields(members.get("DESCRIPTION") or "")
    version = (fields.get("Version") or "").strip() or version
    exports = namespace_exports(members.get("NAMESPACE") or "")
    functions = r_function_defs(members)
    mark_exports(functions, exports)
    reindex_functions(functions)
    native = native_inventory(members)
    native_used = native_calls(functions)
    batches = build_file_batches(members, functions)
    return {
        "package": fields.get("Package") or package,
        "version": version,
        "tarball": str(tarball),
        "description": {
            "title": fields.get("Title") or "",
            "license": fields.get("License") or "",
            "needs_compilation": fields.get("NeedsCompilation") or "",
            "depends": split_deps(fields.get("Depends")),
            "imports": split_deps(fields.get("Imports")),
            "suggests": split_deps(fields.get("Suggests")),
            "linking_to": split_deps(fields.get("LinkingTo")),
        },
        "files": file_inventory(members),
        "namespace": exports,
        "functions": [function_record(item) for item in functions],
        "native": {
            "n_c": native["n_c"],
            "n_fortran": native["n_fortran"],
            "n_cpp": native["n_cpp"],
            "n_c_files": native["n_c_files"],
            "n_fortran_files": native["n_fortran_files"],
            "n_cpp_files": native["n_cpp_files"],
            "src_symbols": sorted(native["symbols"]),
            "used_in_r": native_used,
        },
        "help_topics": help_topics(members),
        "data": sorted(
            rel for rel in members if rel.split("/")[0] == "data" and "/" in rel
        ),
        "counts": counts_card(functions, native, members),
        "kernel": kernel_stats(members),
        "batches": batches,
    }


def find_tarball(name: str, contrib: Path) -> tuple[Path, str]:
    found = []
    for path in contrib.glob(f"{name}_*.tar.gz"):
        stem = path.name[: -len(".tar.gz")]
        prefix = name + "_"
        if stem.startswith(prefix) and stem[len(prefix) :]:
            found.append((path, stem[len(prefix) :]))
    if not found:
        raise FileNotFoundError(f"no tarball for {name} in {contrib}")
    found.sort(key=lambda item: item[1])
    return found[-1]


def read_tarball(path: Path, name: str) -> dict[str, str]:
    members: dict[str, str] = {}
    with tarfile.open(path, "r:gz") as archive:
        for item in archive:
            if not item.isfile():
                continue
            parts = item.name.split("/")
            if len(parts) < 2 or parts[0] != name:
                continue
            raw = archive.extractfile(item)
            if raw is None:
                continue
            members["/".join(parts[1:])] = raw.read().decode("utf-8", "replace")
    return members


def dcf_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    name = None
    values: list[str] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")):
            if name:
                values.append(line.strip())
            continue
        if ":" not in line:
            continue
        if name:
            fields[name] = " ".join(values).strip()
        name, value = line.split(":", 1)
        values = [value.strip()]
    if name:
        fields[name] = " ".join(values).strip()
    return fields


def split_deps(text: str | None) -> list[dict[str, str]]:
    rows = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "(" in part and part.endswith(")"):
            dep, constraint = part.split("(", 1)
            dep, constraint = dep.strip(), constraint[:-1].strip()
        else:
            dep, constraint = part, ""
        if not dep or dep == "R":
            continue
        rows.append({"dep": dep, "constraint": constraint})
    return rows


def namespace_exports(text: str) -> dict:
    names: list[str] = []
    for block in NS_EXPORT.findall(text):
        names.extend(_ns_items(block))
    for block in NS_METHODS.findall(text):
        names.extend(_ns_items(block))
    for generic, klass in NS_S3.findall(text):
        names.append(f"{generic.strip()}.{klass.strip()}")
    dynlib = [item.strip().strip("`\"'") for item in NS_DYNLIB.findall(text)]
    return {
        "names": names,
        "patterns": NS_PATTERN.findall(text),
        "use_dynlib": [item for item in dynlib if item],
    }


def r_name_tokens(code: str) -> set[str]:
    found: set[str] = set()
    for match in R_TOKEN.finditer(code):
        token = match.group(0)
        if token.startswith("`") and token.endswith("`"):
            token = token[1:-1]
        if token:
            found.add(token)
    return found


def _export_regex(pattern: str) -> re.Pattern:
    text = (pattern or "").strip()
    if text in {"*", ".", "^.*", "^.", ".*"}:
        return re.compile(r".")
    try:
        return re.compile(text)
    except re.error:
        globbed = re.escape(text).replace(r"\*", ".*").replace(r"\?", ".")
        try:
            return re.compile(globbed)
        except re.error:
            return re.compile(r".")


def replaced_entry(package: str) -> dict:
    reason = replaced_reasons().get(package)
    if reason is None:
        return {}
    return {"name": package, "reason": reason}


def replaced_reasons() -> dict[str, str]:
    path = ROOT / "rcran" / "replaced.json"
    if not path.is_file():
        return {}
    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["name"]: item.get("reason") or ""
        for item in record.get("packages") or []
        if item.get("name")
    }


_SKIP_NATIVE = {
    "json",
    "csv",
    "gzip",
    "pickle",
    "regex",
    "signal",
    "fcntl",
    "base64",
    "hashlib",
    "getpass",
    "termios",
    "subprocess",
    "urllib",
    "ctypes",
    "zoneinfo",
}
_NATIVE_LABEL = {
    "numpy": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "polars": "Polars",
    "geopandas": "GeoPandas",
    "sqlalchemy": "SQLAlchemy",
}
_ROUTING_STAND_INS = (
    ("scipy sparse", "SciPy sparse"),
    ("scipy.sparse", "SciPy sparse"),
    ("calamine", "calamine"),
    ("geopandas", "GeoPandas"),
    ("sqlalchemy", "SQLAlchemy"),
    ("matplotlib", "Matplotlib"),
    ("libxml2", "libxml2"),
    ("rasterio", "rasterio"),
    ("requests", "requests"),
    ("cmdstanpy", "cmdstanpy"),
    ("polars", "Polars"),
    ("numpy", "NumPy"),
    ("scipy", "SciPy"),
    ("plotly", "Plotly"),
    ("rayon", "Rayon"),
    ("quarto", "Quarto"),
    ("igraph", "igraph"),
    ("dash", "Dash"),
)


def _stand_in_needles() -> list[tuple[str, str]]:
    needles = list(_ROUTING_STAND_INS)
    seen = {label.lower() for _, label in needles}
    path = ROOT / "ai-handbook" / "native.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("native") or []:
            name = (item.get("name") or "").strip()
            if not name or name.lower() in _SKIP_NATIVE or len(name) < 3:
                continue
            label = _NATIVE_LABEL.get(name.lower(), name)
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            needles.append((name.lower(), label))
    needles.sort(key=lambda pair: -len(pair[0]))
    return needles


def replacement_notes(package: str, reason: str = "") -> str:
    reason = reason or replaced_reasons().get(package) or ""
    blob = reason.lower()
    found: list[str] = []
    for needle, label in _stand_in_needles():
        if re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", blob):
            if label not in found:
                found.append(label)
    if found:
        compact = [
            label
            for label in found
            if not any(
                label != other and label.lower() in other.lower() for other in found
            )
        ]
        return "replaced by " + ", ".join(compact)
    if reason:
        return _clip(reason, 120)
    return ""


def thin_report(
    package: str,
    record: dict,
    routed: dict,
    contrib: Path,
    status: str,
) -> dict:
    tarball, version = find_tarball(package, contrib)
    try:
        tarball_rel = str(tarball.relative_to(ROOT))
    except ValueError:
        tarball_rel = str(tarball)
    reason = (
        (record.get("resume") or "")
        or (routed.get("reason") or "")
        or (
            f"already in packages/{package}; status={status}"
            if status == "complete"
            else "listed in rcran/replaced.json"
        )
    )
    stored = record.get("strategy") or ""
    if status == "replaced":
        strategy = "replaced"
        strategy_file = ""
    else:
        strategy_file = _strategy_file(stored)
        strategy = stored if strategy_file else status
    launch = {
        "package": package,
        "version": version,
        "tarball": tarball_rel,
        "strategy": strategy,
        "strategy_file": strategy_file,
        "crate": _crate_line(package, record, crate_ready(package, record)),
        "low_status": low_unit_status(package, record),
        "python": f"packages/{package}" if record else "",
        "status": status,
        "resume": _clip(reason, 180),
        "gaps": [
            row["name"]
            for row in record.get("functions") or []
            if (row.get("not_done") or "").startswith("Left:")
        ][:5],
        "send": [],
        "skip": [
            {
                "path": package,
                "lane": "skip",
                "job": "skip",
                "note": _clip(reason, 220),
            }
        ],
        "later": [],
    }
    return {
        "package": package,
        "version": version,
        "tarball": str(tarball),
        "thin": True,
        "functions": [],
        "packets": [],
        "batches": [],
        "counts": {
            "n_r": 0,
            "exported": 0,
            "internal": 0,
            "n_c": 0,
            "n_fortran": 0,
            "n_cpp": 0,
            "n_c_files": 0,
            "n_fortran_files": 0,
            "n_cpp_files": 0,
            "rd_topics": 0,
            "data_files": 0,
        },
        "launch": launch,
        "description": {},
        "files": {},
        "namespace": {},
    }


def _ns_items(block: str) -> list[str]:
    names = []
    for item in block.split(","):
        item = item.strip().strip("`\"'")
        if item:
            names.append(item)
    return names


def r_function_defs(members: dict[str, str]) -> list[dict]:
    found = []
    for rel, text in members.items():
        parts = rel.split("/")
        if len(parts) != 2 or parts[0] != "R":
            continue
        if Path(parts[1]).suffix.lower() not in R_EXT:
            continue
        for match in R_DEF.finditer(text):
            name = next(group for group in match.groups() if group)
            start, end = function_span(text, match.start(), match.end())
            start_line = text.count("\n", 0, start) + 1
            end_line = text.count("\n", 0, end) + 1
            body = text[start:end]
            n_lines = body.count("\n") + (0 if body.endswith("\n") else 1)
            found.append(
                {
                    "name": name,
                    "r_file": rel,
                    "start_line": start_line,
                    "end_line": end_line,
                    "n_lines": n_lines,
                    "exported": False,
                    "body": body,
                }
            )
    found.sort(key=lambda item: item["name"])
    return found


def function_span(text: str, start: int, function_end: int) -> tuple[int, int]:
    paren = text.find("(", function_end - len("function"))
    if paren < 0:
        return start, function_end
    after_args = match_span(text, paren, "(", ")")
    rest = text[after_args:]
    index = 0
    while index < len(rest):
        if rest[index] in " \t\r\n":
            index += 1
            continue
        if rest[index] == "#":
            newline = rest.find("\n", index)
            index = len(rest) if newline < 0 else newline + 1
            continue
        break
    stripped = rest[index:]
    if stripped.startswith("{"):
        end = match_span(text, after_args + index, "{", "}")
    else:
        newline = text.find("\n", after_args)
        end = len(text) if newline < 0 else newline
    return start, end


def match_span(text: str, open_at: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    index = open_at
    while index < len(text):
        char = text[index]
        if char == "#":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if char in ("'", '"'):
            index = skip_string(text, index, char)
            continue
        if char == open_ch:
            depth += 1
        elif char == close_ch:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def skip_string(text: str, index: int, quote: str) -> int:
    index += 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    return index


def mark_exports(functions: list[dict], exports: dict) -> None:
    patterns = [_export_regex(pattern) for pattern in exports["patterns"]]
    wanted = set(exports["names"])
    for item in functions:
        name = item["name"]
        item["exported"] = name in wanted or any(
            pattern.search(name) for pattern in patterns
        )


def reindex_functions(functions: list[dict]) -> None:
    names = [item["name"] for item in functions]
    by_name = {item["name"]: item for item in functions}
    uses_of: dict[str, list[str]] = {}
    for item in functions:
        source = item["body"]
        code = blank_r_strings(strip_r_comments(source))
        tokens = r_name_tokens(code)
        uses = [other for other in names if other != item["name"] and other in tokens]
        native = []
        for match in NATIVE_CALL.finditer(source):
            symbol = match.group(2) or match.group(3)
            if symbol and symbol not in native:
                native.append(symbol)
        loads = []
        for regex in (LOAD_LIB, LOAD_NS, LOAD_EXPORT):
            for match in regex.finditer(code):
                pkg = match.group(1)
                if pkg and pkg not in loads:
                    loads.append(pkg)
        item["source"] = source
        item["uses"] = uses
        item["same_file"] = [
            name for name in uses if by_name[name]["r_file"] == item["r_file"]
        ]
        item["native"] = native
        item["loads"] = loads
        uses_of[item["name"]] = uses
    for item in functions:
        item["needed"] = transitive_uses(item["name"], uses_of)
    used_by: dict[str, list[str]] = {name: [] for name in names}
    for item in functions:
        for other in item["uses"]:
            used_by[other].append(item["name"])
    for item in functions:
        item["used_by"] = sorted(used_by[item["name"]])


def transitive_uses(start: str, uses_of: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    stack = list(uses_of.get(start, []))
    while stack:
        name = stack.pop()
        if name == start or name in seen:
            continue
        seen.add(name)
        stack.extend(uses_of.get(name, []))
    return sorted(seen)


def build_file_batches(members: dict[str, str], functions: list[dict]) -> list[dict]:
    defined = {item["name"]: item["r_file"] for item in functions}
    src = []
    for rel in sorted(members):
        parts = rel.split("/")
        if not parts or parts[0] != "src":
            continue
        if parts[-1].lower() in SKIP_SRC:
            continue
        suffix = Path(parts[-1]).suffix.lower()
        if suffix not in C_EXT | FORTRAN_EXT | CPP_EXT:
            continue
        src.append(
            {
                "path": rel,
                "kind": "src",
                "wait_for": [],
                "libraries": [],
                "native": [],
            }
        )
    r_batches = []
    for rel in sorted(members):
        parts = rel.split("/")
        if len(parts) != 2 or parts[0] != "R":
            continue
        if Path(parts[1]).suffix.lower() not in R_EXT:
            continue
        text = members[rel]
        code = blank_r_strings(strip_r_comments(text))
        tokens = r_name_tokens(code)
        wait_for = [
            name for name, home in defined.items() if home != rel and name in tokens
        ]
        libraries = []
        outside = []
        for match in LOAD_CALL.finditer(code):
            pkg, fun = match.group(1), match.group(2)
            if not pkg:
                continue
            if pkg not in libraries:
                libraries.append(pkg)
            fun = fun.strip("`") if fun else ""
            key = f"{pkg}::{fun}" if fun else pkg
            if key not in {item["key"] for item in outside}:
                outside.append({"key": key, "package": pkg, "function": fun})
        for match in LOAD_LIB.finditer(code):
            pkg = match.group(1)
            if pkg and pkg not in libraries:
                libraries.append(pkg)
                if pkg not in {item["package"] for item in outside}:
                    outside.append({"key": pkg, "package": pkg, "function": ""})
        native = []
        for match in NATIVE_CALL.finditer(text):
            symbol = match.group(2) or match.group(3)
            if symbol and symbol not in native:
                native.append(symbol)
        r_batches.append(
            {
                "path": rel,
                "kind": "R",
                "wait_for": wait_for,
                "libraries": libraries,
                "outside": outside,
                "native": native,
            }
        )
    r_batches.sort(key=lambda item: (len(item["wait_for"]), item["path"]))
    return src + r_batches


def build_launch(report: dict) -> dict:
    package = report["package"]
    record = package_record(package)
    crate_ok = crate_ready(package, record)
    homes = {item["name"]: item["r_file"] for item in report.get("functions") or []}
    send: list[dict] = []
    skip: list[dict] = []
    later: list[dict] = []
    states = {
        item["r_file"]: _file_state(
            item["r_file"], report.get("functions") or [], record
        )
        for item in report.get("functions") or []
    }
    for batch in report.get("batches") or []:
        card = classify_batch(
            package, batch, crate_ok, homes, record, states.get(batch["path"]), states
        )
        if card["lane"] == "send":
            send.append(card)
        elif card["lane"] == "skip":
            skip.append(card)
        else:
            later.append(card)
    send, skip = _fold_crate_jobs(package, send, skip, crate_ok)
    send = _prefer_package_file(package, send)
    crate_line = _crate_line(package, record, crate_ok)
    skip = _fold_crate_skips(package, skip, crate_line)
    skip = _fold_same_skips(skip)
    skip.sort(key=lambda card: (0 if card.get("low") else 1, card.get("path") or ""))
    counts = report["counts"]
    kernel = counts["n_c"] + counts["n_fortran"] + counts["n_cpp"] > 0
    n_r = counts["n_r"]
    if n_r > 200:
        band = "huge"
    elif n_r <= 20:
        band = "small"
    elif n_r <= 80:
        band = "medium"
    else:
        band = "large"
    strategy = record.get("strategy") or (f"{band}-low" if kernel else band)
    tarball = report["tarball"]
    try:
        tarball = str(Path(tarball).relative_to(ROOT))
    except ValueError:
        pass
    return {
        "package": package,
        "version": report["version"],
        "tarball": tarball,
        "strategy": strategy,
        "strategy_file": _strategy_file(strategy),
        "crate": _crate_line(package, record, crate_ok),
        "low_status": low_unit_status(package, record),
        "python": f"packages/{package}" if record else "",
        "status": record.get("status") or "",
        "resume": _clip(record.get("resume") or "", 180),
        "gaps": [
            row["name"]
            for row in record.get("functions") or []
            if (row.get("not_done") or "").startswith("Left:")
        ][:5],
        "package_high": [
            row for row in _package_high(report) if row.get("status") != "replaced"
        ],
        "package_low": _package_low(report, package, record, crate_ok),
        "package_skip": _package_skip(report),
        "kernel": report.get("kernel") or {},
        "send": send,
        "skip": skip,
        "later": later,
    }


def classify_batch(
    package: str,
    batch: dict,
    crate_ok: bool = False,
    homes: dict[str, str] | None = None,
    record: dict | None = None,
    file_state: str | None = None,
    states: dict[str, str] | None = None,
) -> dict:
    path = batch["path"]
    base = Path(path).name
    if batch["kind"] == "src":
        crate = _crate_line(package, record or {}, crate_ok) or f"crates/{package}"
        kstatus = "ready" if crate_ok else "to Rust"
        if "rcppexports" in base.lower() or REGISTER_SRC.search(base):
            return {
                "path": path,
                "lane": "skip",
                "note": "not a kernel (R registration)",
            }
        if crate_ok:
            return {
                "path": path,
                "lane": "skip",
                "note": f"already in {crate}; do not port again",
                "low": [{"name": path, "via": crate, "status": "ready"}],
            }
        claims = claimed_crates(record or {})
        if claims:
            return {
                "path": path,
                "lane": "skip",
                "note": (
                    f"claimed as {', '.join(f'crates/{name}' for name in claims)}; "
                    f"do not start crates/{package}"
                ),
                "low": [{"name": path, "via": ", ".join(f"crates/{n}" for n in claims), "status": "claimed"}],
            }
        suffix = Path(base).suffix.lower()
        if suffix in FORTRAN_EXT:
            lang = "Fortran"
        elif suffix in CPP_EXT:
            lang = "C++"
        else:
            lang = "C"
        return {
            "path": path,
            "lane": "send",
            "low": [{"name": f"{lang} {path}", "via": crate, "status": kstatus}],
            "high": [],
            "same": [],
        }
    homes = homes or {}
    record = record or {}
    replaced = replaced_names()
    blocked = []
    for name in batch["wait_for"]:
        if name in FALSE_WAIT or name == package or len(name) <= 1:
            continue
        home = homes.get(name)
        blocked.append(f"{home}:{name}" if home else name)
    for name in batch["native"]:
        if name in FALSE_WAIT or name == package:
            continue
        blocked.append(name)
    for lib in batch["libraries"]:
        if lib in BASE_PACKAGES or lib in replaced or lib == package or lib in FALSE_WAIT:
            continue
        other = package_record(lib)
        if (other.get("status") or "") in {"complete", "replaced"}:
            continue
        blocked.append(lib)
    blocked = [item for item in _unique(blocked) if _still_blocked(item, states or {})]
    low, high, same = file_deps(package, batch, homes, record, crate_ok, states or {})
    already = (record.get("status") or "") == "complete"
    if already:
        return {
            "path": path,
            "lane": "skip",
            "job": "skip",
            "note": f"already in packages/{package}; status=complete",
        }
    hook = Path(path).name.lower()
    if (
        hook in {"zzz.r", "onload.r"}
        or hook.endswith("-pkg.r")
        or hook.endswith("-package.r")
        or hook.startswith("import-standalone")
        or hook.startswith("compat-")
        or hook.startswith("rcppexports")
    ):
        return {
            "path": path,
            "lane": "skip",
            "job": "skip",
            "note": "package hook or vendored standalone; not a function batch",
        }
    inventoried = {
        row["name"] for row in (record.get("functions") or []) if row.get("name")
    }
    if (record.get("inventory") or "") == "partial" and inventoried:
        file_names = {name for name, home in homes.items() if home == path}
        if not (file_names & inventoried):
            return {
                "path": path,
                "lane": "skip",
                "job": "skip",
                "note": "outside partial inventory; do not open",
            }
    if file_state == "left":
        return {
            "path": path,
            "lane": "skip",
            "note": "Left / routed; do not translate",
            "low": low,
            "high": high,
            "same": same,
        }
    if file_state == "done":
        return {
            "path": path,
            "lane": "skip",
            "note": f"already in packages/{package}; translated",
            "low": low,
            "high": high,
            "same": same,
        }
    if file_state == "written":
        return {
            "path": path,
            "lane": "skip",
            "note": f"already written in packages/{package}",
            "low": low,
            "high": high,
            "same": same,
        }
    data_only = Path(path).name.lower().startswith("data-") or Path(path).name.lower().startswith("data.")
    if data_only and not blocked:
        return {
            "path": path,
            "lane": "skip",
            "note": "data file, not a function batch",
        }
    waiting = _waiting_deps(low, high, same, crate_ok)
    card = {
        "path": path,
        "low": low,
        "high": high,
        "same": same,
    }
    if waiting:
        card["lane"] = "later"
        card["blocked_on"] = waiting
        return card
    card["lane"] = "send"
    return card


def _file_state(path: str, functions: list[dict], record: dict) -> str | None:
    names = [item["name"] for item in functions if item.get("r_file") == path]
    by_name = {row["name"]: row for row in record.get("functions") or [] if row.get("name")}
    rows = [by_name[name] for name in names if name in by_name]
    if not rows:
        return None
    notes = [(row.get("not_done") or "") for row in rows]
    if all(note.startswith("Left:") for note in notes):
        return "left"
    if all(row.get("translated") and not (row.get("not_done") or "") for row in rows):
        return "done"
    if all(row.get("python") for row in rows) and all(
        note.startswith("Waiting:") or note.startswith("Left:") or note == ""
        for note in notes
    ):
        return "written"
    return "open"


def package_record(package: str) -> dict:
    path = ROOT / "packages" / package / "translation.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def package_status(name: str) -> str:
    if name in BASE_PACKAGES:
        return "base"
    if name in replaced_names():
        return "replaced"
    record = package_record(name)
    if not record:
        return "not translated"
    return record.get("status") or "not translated"


def file_deps(
    package: str,
    batch: dict,
    homes: dict[str, str],
    record: dict,
    crate_ok: bool,
    states: dict[str, str],
) -> tuple[list[dict], list[dict], list[dict]]:
    crate = _crate_line(package, record, crate_ok) or f"crates/{package}"
    kstatus = "ready" if crate_ok else "to Rust"
    low = [
        {"name": name, "via": crate, "status": kstatus}
        for name in batch.get("native") or []
        if name not in FALSE_WAIT and name != package
    ]
    high = []
    for item in batch.get("outside") or []:
        lib = item.get("package") or ""
        if lib in BASE_PACKAGES or lib == package or lib in FALSE_WAIT:
            continue
        fun = item.get("function") or ""
        high.append(
            {
                "name": f"{lib}::{fun}" if fun else lib,
                "package": lib,
                "function": fun,
                "status": package_status(lib),
            }
        )
    if not high:
        for lib in batch.get("libraries") or []:
            if lib in BASE_PACKAGES or lib == package or lib in FALSE_WAIT:
                continue
            high.append({"name": lib, "package": lib, "function": "", "status": package_status(lib)})
    seen_files: set[str] = set()
    same = []
    for name in batch.get("wait_for") or []:
        if name in FALSE_WAIT or name == package or len(name) <= 1:
            continue
        home = homes.get(name)
        if not home or home == batch.get("path") or _is_hook_path(home):
            continue
        if Path(home).name.lower().startswith("rcppexports"):
            if not crate_ok:
                low.append({"name": "low-level", "via": crate, "status": "to Rust"})
            continue
        if home in seen_files:
            continue
        seen_files.add(home)
        same.append({"name": home, "status": (states.get(home) or "open")})
    return low, high, same


def _waiting_deps(
    low: list[dict], high: list[dict], same: list[dict], crate_ok: bool
) -> list[str]:
    waiting = []
    if low and not crate_ok:
        waiting.extend(
            f"{item['name']} ({item.get('via') or 'crate'} {item['status']})"
            for item in low
        )
    for item in high:
        if item["status"] in {"not translated", "in_progress", "to Rust"}:
            waiting.append(f"{item['name']} {item['status']}")
    for item in same:
        if _is_hook_path(item["name"]):
            continue
        if item["status"] in {"open", None}:
            waiting.append(item["name"])
    return _unique(waiting)


def _package_high(report: dict) -> list[dict]:
    desc = report.get("description") or {}
    rows = []
    for item in list(desc.get("depends") or []) + list(desc.get("imports") or []):
        name = item.get("dep") if isinstance(item, dict) else item
        if not name or name in BASE_PACKAGES:
            continue
        rows.append({"name": name, "status": package_status(name)})
    return _unique_dep_rows(rows)


def _package_low(
    report: dict, package: str, record: dict, crate_ok: bool
) -> list[dict]:
    rows = []
    crate = _crate_line(package, record, crate_ok)
    if crate:
        rows.append({"name": crate, "status": "ready" if crate_ok else "claimed"})
        return rows
    counts = report.get("counts") or {}
    bits = []
    if counts.get("n_fortran") or counts.get("n_fortran_files"):
        bits.append("Fortran")
    if counts.get("n_c") or counts.get("n_c_files"):
        bits.append("C")
    if counts.get("n_cpp") or counts.get("n_cpp_files"):
        bits.append("C++")
    if bits:
        rows.append({"name": "+".join(bits), "status": "to Rust"})
    return rows


def _package_skip(report: dict) -> list[str]:
    names = []
    for row in _package_high(report):
        if row.get("status") == "replaced":
            names.append(row["name"])
    desc = report.get("description") or {}
    for item in desc.get("linking_to") or []:
        name = item.get("dep") if isinstance(item, dict) else item
        if name and package_status(name) == "replaced":
            names.append(name)
    return _unique(names)


def _is_hook_path(item: str) -> bool:
    path = item.split(":", 1)[0]
    name = Path(path).name.lower()
    return (
        name.startswith("import-standalone")
        or name.startswith("compat-")
        or name in {"zzz.r", "onload.r"}
        or name.endswith("-pkg.r")
        or name.endswith("-package.r")
    )


def _unique_dep_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for row in rows:
        name = row.get("name") or ""
        if name in seen:
            continue
        seen.add(name)
        out.append(row)
    return out


def claimed_crates(record: dict) -> list[str]:
    names = []
    for item in record.get("crate_claims") or []:
        if isinstance(item, dict):
            name = item.get("name") or ""
        else:
            name = str(item)
        if name:
            names.append(name)
    rust = (record.get("dependencies") or {}).get("rust") or []
    for item in rust:
        if isinstance(item, dict):
            name = item.get("name") or ""
        else:
            name = str(item)
        if name:
            names.append(name)
    return _unique(names)


def crate_ready(package: str, record: dict | None = None) -> bool:
    path = ROOT / "crates" / package / "crate.json"
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not (loaded.get("assigned") or ""):
            return True
    names = claimed_crates(record or {})
    if not names:
        return False
    return all((ROOT / "crates" / name / "crate.json").is_file() for name in names)


def low_unit_status(package: str, record: dict | None = None) -> str:
    record = record or {}
    names = _unique([package] + claimed_crates(record))
    found = []
    underway = False
    for name in names:
        path = ROOT / "crates" / name / "crate.json"
        if not path.is_file():
            continue
        found.append(name)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if loaded.get("assigned"):
            underway = True
    claims = claimed_crates(record)
    if underway:
        return "underway"
    if crate_ready(package, record):
        return "done"
    if found and claims and len(found) < len(claims):
        return "underway"
    if claims and not found:
        return "underway"
    if found:
        return "done"
    return "pending"


def _crate_line(package: str, record: dict, crate_ok: bool) -> str:
    if (ROOT / "crates" / package / "crate.json").is_file():
        return f"crates/{package}"
    names = claimed_crates(record)
    if crate_ok and names:
        return ", ".join(f"crates/{name}" for name in names)
    return ""


def _fold_crate_jobs(
    package: str, send: list[dict], skip: list[dict], crate_ok: bool
) -> tuple[list[dict], list[dict]]:
    if crate_ok:
        return send, skip
    crates = [
        card
        for card in send
        if str(card.get("path") or "").startswith("src/")
        and "rcppexports" not in Path(card["path"]).name.lower()
    ]
    rest = [card for card in send if not str(card.get("path") or "").startswith("src/")]
    if len(crates) <= 1:
        return send, skip
    langs = _unique(
        [
            "Fortran" if Path(card["path"]).suffix.lower() in FORTRAN_EXT else "C"
            for card in crates
        ]
    )
    crate = f"crates/{package}"
    folded = {
        "path": crates[0]["path"],
        "files": [card["path"] for card in crates],
        "lane": "send",
        "low": [
            {
                "name": ", ".join(card["path"] for card in crates),
                "via": crate,
                "status": "to Rust",
            }
        ],
        "high": [],
        "same": [],
    }
    return [folded] + rest, skip


def _prefer_package_file(package: str, send: list[dict]) -> list[dict]:
    want = f"{package}.r"

    def key(card: dict) -> tuple:
        name = Path(card["path"]).name.lower()
        if str(card.get("path") or "").startswith("src/"):
            return (0, card["path"])
        if name == want:
            return (1, card["path"])
        if name.endswith("-pkg.r") or name in {"zzz.r", "onload.r"}:
            return (3, card["path"])
        return (2, card["path"])

    return sorted(send, key=key)


def _fold_same_skips(skip: list[dict]) -> list[dict]:
    order: list[str] = []
    groups: dict[str, list[dict]] = {}
    for card in skip:
        note = card.get("note") or ""
        if note not in groups:
            groups[note] = []
            order.append(note)
        groups[note].append(card)
    out = []
    for note in order:
        cards = groups[note]
        rich = [
            card
            for card in cards
            if card.get("low") or card.get("high") or card.get("same")
        ]
        plain = [
            card
            for card in cards
            if not (card.get("low") or card.get("high") or card.get("same"))
        ]
        out.extend(rich)
        if not plain:
            continue
        if len(plain) == 1:
            out.append(plain[0])
            continue
        out.append(
            {
                "path": f"{plain[0]['path']} + {len(plain) - 1} more",
                "lane": "skip",
                "note": note,
            }
        )
    return out


def _fold_crate_skips(
    package: str, skip: list[dict], crate_line: str = ""
) -> list[dict]:
    covered = []
    claimed = []
    rest = []
    claim_note = ""
    for card in skip:
        note = card.get("note") or ""
        if note.startswith("already in crates/"):
            covered.append(card["path"])
        elif note.startswith("claimed as "):
            claimed.append(card["path"])
            claim_note = note.split(";", 1)[0]
        else:
            rest.append(card)
    out = []
    if covered:
        out.append(
            {
                "path": crate_line or f"crates/{package}",
                "lane": "skip",
                "job": "skip",
                "note": f"covers {', '.join(covered)}; do not port again",
            }
        )
    if claimed:
        out.append(
            {
                "path": claim_note or f"crates/{package}",
                "lane": "skip",
                "job": "skip",
                "note": f"covers {', '.join(claimed)}; do not start crates/{package}",
            }
        )
    return out + rest if out else skip


def match_experience(query: str) -> list[str]:
    words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) >= 4}
    scored = []
    if not EXPERIENCE.is_dir():
        return []
    for path in EXPERIENCE.glob("*.md"):
        stem_words = {
            w for w in re.findall(r"[a-z0-9]+", path.stem.lower()) if len(w) >= 4
        }
        hit = stem_words & words
        if not hit:
            continue
        scored.append((len(hit), path.name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    generic = {
        "round",
        "data",
        "table",
        "file",
        "name",
        "names",
        "default",
        "start",
        "html",
        "list",
        "type",
        "text",
        "code",
        "path",
        "from",
        "with",
        "this",
    }
    names = []
    for score, name in scored:
        stem_words = {
            w for w in re.findall(r"[a-z0-9]+", Path(name).stem.lower()) if len(w) >= 4
        }
        hit = stem_words & words
        if score == 1 and hit <= generic:
            continue
        names.append(name)
        if len(names) == 3:
            break
    return names


def replaced_names() -> set[str]:
    path = ROOT / "rcran" / "replaced.json"
    if not path.is_file():
        return set()
    record = json.loads(path.read_text(encoding="utf-8"))
    return {item["name"] for item in record.get("packages") or [] if item.get("name")}


def _still_blocked(item: str, states: dict[str, str]) -> bool:
    if ":" not in item:
        return True
    home = item.split(":", 1)[0]
    name = Path(home).name.lower()
    if (
        name.startswith("import-standalone")
        or name.startswith("compat-")
        or name in {"zzz.r", "onload.r"}
        or name.endswith("-pkg.r")
        or name.endswith("-package.r")
    ):
        return False
    if home.startswith("R/") and states.get(home) in {"done", "written", "left"}:
        return False
    return True


def _strategy_file(strategy: str) -> str:
    if not strategy:
        return ""
    path = ROOT / "ai-handbook" / "strategies" / f"{strategy}.md"
    if path.is_file():
        return f"ai-handbook/strategies/{strategy}.md"
    alt = strategy.removesuffix("-low")
    if alt != strategy and (ROOT / "ai-handbook" / "strategies" / f"{alt}.md").is_file():
        return f"ai-handbook/strategies/{alt}.md"
    return ""


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_packets(functions: list[dict]) -> list[dict]:
    by_name = {item["name"]: item for item in functions}
    packets = []
    for item in functions:
        helpers = [
            {
                "name": name,
                "r_file": by_name[name]["r_file"],
                "source": by_name[name]["source"],
            }
            for name in item["needed"]
        ]
        packets.append(
            {
                "name": item["name"],
                "r_file": item["r_file"],
                "start_line": item["start_line"],
                "end_line": item["end_line"],
                "n_lines": item["n_lines"],
                "exported": item["exported"],
                "source": item["source"],
                "helpers": helpers,
                "native": item["native"],
                "loads": item["loads"],
                "standalone": not item["needed"]
                and not item["native"]
                and not item["loads"],
            }
        )
    return packets


def function_record(item: dict) -> dict:
    return {
        "name": item["name"],
        "r_file": item["r_file"],
        "start_line": item["start_line"],
        "end_line": item["end_line"],
        "n_lines": item["n_lines"],
        "exported": item["exported"],
        "source": item["source"],
        "uses": item["uses"],
        "same_file": item["same_file"],
        "native": item["native"],
        "loads": item["loads"],
        "needed": item["needed"],
        "used_by": item["used_by"],
    }


def strip_r_comments(text: str) -> str:
    out = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            end = skip_string(text, index, char)
            out.append(text[index:end])
            index = end
            continue
        if char == "#":
            newline = text.find("\n", index)
            if newline < 0:
                break
            out.append("\n")
            index = newline + 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def blank_r_strings(text: str) -> str:
    out = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            end = skip_string(text, index, char)
            out.append(" " * (end - index))
            index = end
            continue
        out.append(char)
        index += 1
    return "".join(out)


def native_inventory(members: dict[str, str]) -> dict:
    n_c = n_f = n_cpp = 0
    n_c_files = n_f_files = n_cpp_files = 0
    symbols: set[str] = set()
    for rel, text in members.items():
        parts = rel.split("/")
        if not parts or parts[0] != "src":
            continue
        base = parts[-1]
        if base.lower() in SKIP_SRC:
            continue
        suffix = Path(base).suffix.lower()
        if suffix in C_EXT:
            n_c_files += 1
            names = c_definitions(text)
            n_c += len(names)
            symbols.update(name.lower() for name in names)
        elif suffix in FORTRAN_EXT:
            n_f_files += 1
            names = fortran_definitions(text)
            n_f += len(names)
            symbols.update(name.lower() for name in names)
        elif suffix in CPP_EXT:
            n_cpp_files += 1
            names = c_definitions(text)
            n_cpp += len(names)
            symbols.update(name.lower() for name in names)
    return {
        "n_c": n_c,
        "n_fortran": n_f,
        "n_cpp": n_cpp,
        "n_c_files": n_c_files,
        "n_fortran_files": n_f_files,
        "n_cpp_files": n_cpp_files,
        "symbols": symbols,
    }


def kernel_stats(members: dict[str, str]) -> dict:
    langs = {
        "C": {"files": 0, "lines": 0},
        "Fortran": {"files": 0, "lines": 0},
        "C++": {"files": 0, "lines": 0},
    }
    other_items: list[dict] = []
    for rel, text in members.items():
        parts = rel.split("/")
        if not parts or parts[0] != "src":
            continue
        base = parts[-1]
        if base.lower() in SKIP_SRC or base.lower().startswith("makevars"):
            continue
        if "rcppexports" in base.lower() or REGISTER_SRC.search(base):
            continue
        suffix = Path(base).suffix.lower()
        if suffix in OTHER_SKIP_EXT:
            continue
        if suffix in FORTRAN_EXT:
            lang = "Fortran"
        elif suffix in CPP_EXT:
            lang = "C++"
        elif suffix in C_EXT:
            lang = "C"
        else:
            n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
            other_items.append(
                {
                    "lang": OTHER_LANG.get(suffix, suffix.lstrip(".") or "other"),
                    "file": base,
                    "lines": n_lines,
                }
            )
            continue
        n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        langs[lang]["files"] += 1
        langs[lang]["lines"] += n_lines
    total_files = sum(item["files"] for item in langs.values()) + len(other_items)
    total_lines = sum(item["lines"] for item in langs.values()) + sum(
        item["lines"] for item in other_items
    )
    n_langs = sum(1 for item in langs.values() if item["files"])
    if total_lines == 0:
        size = ""
        together = False
        assign = ""
    elif total_lines <= 1000:
        size = "small"
        together = True
        assign = "one agent"
    elif total_lines <= 4000:
        size = "medium"
        together = True
        assign = "one agent" if n_langs == 1 or total_files <= 5 else "split by language"
    elif total_lines <= 12000:
        size = "large"
        together = n_langs == 1 and total_files <= 4
        assign = "one agent" if together else "split"
    else:
        size = "huge"
        together = False
        assign = "split; not one agent"
    return {
        "languages": langs,
        "files": total_files,
        "lines": total_lines,
        "size": size,
        "together": together,
        "assign": assign,
        "other": {
            "files": len(other_items),
            "lines": sum(item["lines"] for item in other_items),
            "items": other_items,
        },
    }


def _other_note(items: list[dict]) -> str:
    if not items:
        return ""
    bits = [f"{item['lang']} {item['file']}" for item in items]
    return _clip("other: " + ", ".join(bits), 180)


def c_definitions(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    stripped = strip_c_comments(text)

    def add(name: str) -> None:
        if name in {"if", "for", "while", "switch", "return", "sizeof"}:
            return
        if name not in seen:
            seen.add(name)
            names.append(name)

    for match in C_DEF.finditer(stripped):
        add(match.group(1))
    for match in C_DEF_LINE.finditer(stripped):
        line = match.group(0).rstrip()
        if line.endswith(";"):
            continue
        ident = re.findall(r"([A-Za-z_]\w*)\s*\(", line)
        if ident:
            add(ident[-1])
    return names


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//.*?$", "", text, flags=re.M)


def fortran_definitions(text: str) -> list[str]:
    names = []
    for raw in text.splitlines():
        if not raw:
            continue
        if raw[0] in "Cc*!":
            continue
        body = raw[6:] if len(raw) >= 7 else raw
        match = re.match(
            r"\s*(?:SUBROUTINE|FUNCTION|ENTRY)\s+([A-Za-z][A-Za-z0-9_]*)",
            body,
            re.I,
        )
        if match:
            names.append(match.group(1))
    if names:
        return names
    return [match.group(1) for match in FORTRAN_UNIT.finditer(text)]


def native_calls(functions: list[dict]) -> list[dict[str, str]]:
    rows = []
    seen: set[tuple[str, str, str]] = set()
    for item in functions:
        for match in NATIVE_CALL.finditer(item["body"]):
            symbol = match.group(2) or match.group(3)
            if not symbol:
                continue
            key = (item["name"], match.group(1), symbol)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {"function": item["name"], "kind": match.group(1), "symbol": symbol}
            )
    rows.sort(key=lambda row: (row["function"], row["kind"], row["symbol"]))
    return rows


def file_inventory(members: dict[str, str]) -> dict:
    by_dir = {name: 0 for name in DIRS}
    lines = {"r": 0, "c": 0, "fortran": 0, "cpp": 0, "rd": 0}
    for rel, text in members.items():
        top = rel.split("/", 1)[0]
        if top in by_dir:
            by_dir[top] += 1
        suffix = Path(rel).suffix.lower()
        n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        if suffix in R_EXT and top == "R":
            lines["r"] += n_lines
        elif suffix in C_EXT and top == "src":
            lines["c"] += n_lines
        elif suffix in FORTRAN_EXT and top == "src":
            lines["fortran"] += n_lines
        elif suffix in CPP_EXT and top == "src":
            lines["cpp"] += n_lines
        elif suffix in RD_EXT and top == "man":
            lines["rd"] += n_lines
    return {"by_dir": by_dir, "lines": lines, "n_files": len(members)}


def help_topics(members: dict[str, str]) -> list[dict[str, str]]:
    topics = []
    for rel, text in members.items():
        parts = rel.split("/")
        if len(parts) != 2 or parts[0] != "man":
            continue
        if Path(parts[1]).suffix.lower() not in RD_EXT:
            continue
        match = RD_NAME.search(text)
        topics.append({"file": rel, "name": match.group(1) if match else parts[1]})
    topics.sort(key=lambda item: item["name"])
    return topics


def counts_card(functions: list[dict], native: dict, members: dict[str, str]) -> dict:
    exported = sum(1 for item in functions if item["exported"])
    help_n = sum(
        1
        for rel in members
        if rel.startswith("man/") and Path(rel).suffix.lower() in RD_EXT
    )
    data_n = sum(1 for rel in members if rel.split("/")[0] == "data" and "/" in rel)
    return {
        "n_r": len(functions),
        "exported": exported,
        "internal": len(functions) - exported,
        "n_c": native["n_c"],
        "n_fortran": native["n_fortran"],
        "n_cpp": native["n_cpp"],
        "n_c_files": native["n_c_files"],
        "n_fortran_files": native["n_fortran_files"],
        "n_cpp_files": native["n_cpp_files"],
        "rd_topics": help_n,
        "data_files": data_n,
    }


def format_report(report: dict) -> str:
    launch = report.get("launch") or build_launch(report)
    lines = []
    low = _format_low_analysis(report, launch)
    if low:
        lines.append("low-level")
        lines.extend(low)
    high = []
    for card in _sort_high_batches(_print_batches(launch)):
        high.extend(_format_card(card))
    if high:
        if lines:
            lines.append("")
        lines.append("high-level")
        lines.extend(high)
    return ("\n".join(lines) + "\n") if lines else ""


def _format_low_analysis(report: dict, launch: dict) -> list[str]:
    stats = report.get("kernel") or launch.get("kernel") or {}
    status = launch.get("low_status") or ""
    crate = launch.get("crate") or ""
    has_kernel = bool(stats.get("lines")) or bool(crate) or bool(status)
    if not has_kernel:
        return []
    lines = [f"  status: {status or 'pending'}"]
    for lang in ("Fortran", "C", "C++"):
        item = (stats.get("languages") or {}).get(lang) or {}
        if not item.get("files"):
            continue
        noun = "file" if item["files"] == 1 else "files"
        lines.append(f"  {lang}: {item['files']} {noun}, {item['lines']} lines")
    if stats.get("lines"):
        bits = [f"{stats['lines']} lines", stats.get("size") or ""]
        lines.append(f"  {'  '.join(bit for bit in bits if bit)}")
    if crate:
        lines.append(f"  crate: {crate}")
    return lines


def _print_batches(launch: dict) -> list[dict]:
    cards = []
    for card in (
        list(launch.get("send") or [])
        + list(launch.get("later") or [])
        + list(launch.get("skip") or [])
    ):
        path = card.get("path") or ""
        if not path.startswith("R/"):
            continue
        note = card.get("note") or ""
        base = Path(path).name.lower()
        if base in {"rcppexports.r"}:
            continue
        if (
            "registration" in note
            or "data file" in note
            or "vendored" in note
            or "hook" in note
            or note.startswith("Left")
        ):
            continue
        cards.append(card)
    return cards


def _internal_names(card: dict) -> list[str]:
    names = []
    for row in card.get("same") or []:
        raw = row.get("name") or ""
        if not raw or _is_hook_path(raw):
            continue
        name = _r_name(raw)
        if name:
            names.append(name)
    return _unique(names)


def _needs_low(card: dict) -> bool:
    return bool(card.get("low")) and any(
        row.get("status") != "ready" for row in card["low"]
    )


def _outside_names(card: dict) -> list[str]:
    return _unique(
        [
            row.get("name") or ""
            for row in card.get("high") or []
            if row.get("name") and row.get("status") != "replaced"
        ]
    )


def _sort_high_batches(cards: list[dict]) -> list[dict]:
    by_name = {_r_name(card.get("path") or ""): card for card in cards}
    depth: dict[str, int] = {}

    def walk(name: str, stack: set[str]) -> int:
        if name in depth:
            return depth[name]
        if name in stack:
            return 0
        card = by_name.get(name)
        if not card:
            depth[name] = 0
            return 0
        stack.add(name)
        kids = _internal_names(card)
        value = 0 if not kids else 1 + max(walk(kid, stack) for kid in kids)
        if _needs_low(card):
            value += 1
        stack.discard(name)
        depth[name] = value
        return value

    for name in by_name:
        walk(name, set())

    def key(card: dict) -> tuple:
        name = _r_name(card.get("path") or "")
        internals = _internal_names(card)
        outside = _outside_names(card)
        n_deps = len(internals) + len(outside) + (1 if _needs_low(card) else 0)
        return (n_deps, depth.get(name, 0), name)

    return sorted(cards, key=key)


def _format_card(card: dict) -> list[str]:
    lines = [_r_name(card.get("path") or "")]
    lines.extend(_format_card_deps(card, indent="  "))
    return lines


def _r_name(path: str) -> str:
    name = path[2:] if path.startswith("R/") else path
    if name.lower().endswith(".r"):
        return name[:-2]
    return name


def _format_card_deps(card: dict, indent: str = "    ") -> list[str]:
    lines = []
    other = _internal_names(card)
    outside = _outside_names(card)
    if other:
        lines.append(f"{indent}internal files: {_join(other)}")
    if outside:
        lines.append(f"{indent}packages: {_join(outside)}")
    if _needs_low(card):
        lines.append(f"{indent}+ low-level")
    return lines


def _format_low(rows: list[dict]) -> str:
    if not rows:
        return "(none)"
    parts = []
    via = ""
    status = ""
    names = []
    for row in rows:
        names.append(row.get("name") or "")
        via = row.get("via") or via
        status = row.get("status") or status
    text = ", ".join(name for name in names if name)
    if via:
        text += f" → {via} {status}".rstrip()
    elif status:
        text += f" {status}"
    return text or "(none)"


def _format_dep_list(rows: list[dict]) -> str:
    if not rows:
        return "(none)"
    return ", ".join(
        f"{row.get('name')} {row.get('status')}".strip() for row in rows if row.get("name")
    )


def _join(values: list[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _write_package_file(dest: Path, report: dict) -> None:
    launch = report.get("launch") or {}
    record = {
        "package": launch.get("package") or report.get("package"),
        "version": launch.get("version") or report.get("version"),
        "tarball": launch.get("tarball") or report.get("tarball"),
        "strategy": launch.get("strategy") or "",
        "strategy_file": launch.get("strategy_file") or "",
        "status": launch.get("status") or "",
        "python": launch.get("python") or "",
        "crate": launch.get("crate") or "",
        "low_status": launch.get("low_status") or "",
        "resume": launch.get("resume") or "",
        "high": launch.get("package_high") or [],
        "low": launch.get("package_low") or [],
        "skip_packages": launch.get("package_skip") or [],
        "skip": [
            {"path": card.get("path"), "note": card.get("note") or ""}
            for card in launch.get("skip") or []
        ],
        "left": launch.get("gaps") or [],
        "kernel": report.get("kernel") or launch.get("kernel") or {},
    }
    (dest / "package.json").write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )


def write_index(report: dict, root: Path = INDEX) -> Path:
    dest = root / report["package"]
    dest.mkdir(parents=True, exist_ok=True)
    _write_package_file(dest, report)
    if report.get("thin"):
        (dest / "launch.json").write_text(
            json.dumps(report.get("launch") or {}, indent=2) + "\n",
            encoding="utf-8",
        )
        return dest
    functions_dir = dest / "functions"
    functions_dir.mkdir(parents=True, exist_ok=True)
    keep = set()
    for item in report["functions"]:
        name = _index_name(item["name"])
        keep.add(f"{name}.R")
        (functions_dir / f"{name}.R").write_text(item["source"], encoding="utf-8")
    for path in functions_dir.glob("*.R"):
        if path.name not in keep:
            path.unlink()
    tables = [
        {
            "name": item["name"],
            "r_file": item["r_file"],
            "start_line": item["start_line"],
            "end_line": item["end_line"],
            "n_lines": item["n_lines"],
            "exported": item["exported"],
            "uses": item["uses"],
            "same_file": item["same_file"],
            "native": item["native"],
            "loads": item["loads"],
            "needed": item["needed"],
            "used_by": item["used_by"],
        }
        for item in report["functions"]
    ]
    (dest / "deps.json").write_text(
        json.dumps(
            {
                "package": report["package"],
                "version": report["version"],
                "functions": tables,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    packets = report.get("packets") or []
    packets_dir = dest / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    keep_packets = set()
    table = []
    for item in packets:
        name = _index_name(item["name"])
        keep_packets.add(f"{name}.json")
        (packets_dir / f"{name}.json").write_text(
            json.dumps(item, indent=2) + "\n", encoding="utf-8"
        )
        table.append(
            {
                "name": item["name"],
                "n_lines": item["n_lines"],
                "n_helpers": len(item["helpers"]),
                "helpers": [helper["name"] for helper in item["helpers"]],
                "native": item["native"],
                "loads": item["loads"],
                "standalone": item["standalone"],
            }
        )
    for path in packets_dir.glob("*.json"):
        if path.name not in keep_packets:
            path.unlink()
    (dest / "packets.json").write_text(
        json.dumps(
            {
                "package": report["package"],
                "version": report["version"],
                "packets": table,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (dest / "batches.json").write_text(
        json.dumps(
            {
                "package": report["package"],
                "version": report["version"],
                "batches": report.get("batches") or [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    desc = report["description"]
    (dest / "description.json").write_text(
        json.dumps(
            {
                "package": report["package"],
                "version": report["version"],
                "title": desc["title"],
                "license": desc["license"],
                "needs_compilation": desc["needs_compilation"],
                "depends": desc["depends"],
                "imports": desc["imports"],
                "suggests": desc["suggests"],
                "linking_to": desc["linking_to"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (dest / "launch.json").write_text(
        json.dumps(report.get("launch") or {}, indent=2) + "\n",
        encoding="utf-8",
    )
    (dest / "functions.json").write_text(
        json.dumps(
            {
                "package": report["package"],
                "version": report["version"],
                "functions": tables,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def _index_name(name: str) -> str:
    return re.sub(r"[^\w.-]", "_", name)


def low_level_row(report: dict) -> dict:
    launch = report.get("launch") or {}
    stats = report.get("kernel") or launch.get("kernel") or {}
    langs = stats.get("languages") or {}
    fortran = langs.get("Fortran") or {}
    c_lang = langs.get("C") or {}
    cpp = langs.get("C++") or {}
    known_lines = (
        int(fortran.get("lines") or 0)
        + int(c_lang.get("lines") or 0)
        + int(cpp.get("lines") or 0)
    )
    known_files = (
        int(fortran.get("files") or 0)
        + int(c_lang.get("files") or 0)
        + int(cpp.get("files") or 0)
    )
    other = stats.get("other") or {}
    total_lines = int(stats.get("lines") or 0)
    total_files = int(stats.get("files") or 0)
    notes = launch.get("notes") or ""
    extra = _other_note(other.get("items") or [])
    if extra and extra not in notes:
        notes = f"{notes}; {extra}" if notes else extra
    return {
        "package": launch.get("package") or report.get("package") or "",
        "version": launch.get("version") or report.get("version") or "",
        "status": launch.get("low_status") or "",
        "fortran_files": int(fortran.get("files") or 0),
        "fortran_lines": int(fortran.get("lines") or 0),
        "c_files": int(c_lang.get("files") or 0),
        "c_lines": int(c_lang.get("lines") or 0),
        "cpp_files": int(cpp.get("files") or 0),
        "cpp_lines": int(cpp.get("lines") or 0),
        "other_files": int(other.get("files") or max(0, total_files - known_files)),
        "other_lines": int(other.get("lines") or max(0, total_lines - known_lines)),
        "lines": total_lines,
        "size": stats.get("size") or "",
        "crate": launch.get("crate") or "",
        "notes": notes,
    }


def store_low_level(report: dict) -> None:
    from screenlib import upsert_low_level

    upsert_low_level(low_level_row(report))


def _r_file_lines(members: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for rel, text in members.items():
        parts = rel.split("/")
        if len(parts) != 2 or parts[0] != "R":
            continue
        if Path(parts[1]).suffix.lower() not in R_EXT:
            continue
        out[rel] = text.count("\n") + (0 if text.endswith("\n") else 1)
    return out


def _low_status_for(package: str, record: dict) -> str:
    from screenlib import connect

    db = connect()
    try:
        row = db.execute(
            """SELECT status, fortran_lines + c_lines + cpp_lines
               FROM low_level WHERE package = ?""",
            (package,),
        ).fetchone()
    finally:
        db.close()
    if row:
        status, compiled = row[0] or "", int(row[1] or 0)
        if compiled <= 0:
            return "none"
        return status or "pending"
    if crate_ready(package, record) or claimed_crates(record):
        return low_unit_status(package, record)
    return "none"


def high_level_bundle(package: str) -> tuple[dict, list[dict]]:
    tarball, version = find_tarball(package, CONTRIB)
    members = read_tarball(tarball, package)
    fields = dcf_fields(members.get("DESCRIPTION") or "")
    version = (fields.get("Version") or "").strip() or version
    functions = r_function_defs(members)
    reindex_functions(functions)
    batches = build_file_batches(members, functions)
    native = native_inventory(members)
    report = {
        "package": fields.get("Package") or package,
        "version": version,
        "tarball": str(tarball),
        "functions": [function_record(item) for item in functions],
        "batches": batches,
        "counts": counts_card(functions, native, members),
        "kernel": kernel_stats(members),
    }
    report["launch"] = build_launch(report)
    lines_by = _r_file_lines(members)
    record = package_record(package)
    low_status = _low_status_for(package, record)
    names_by_file: dict[str, list[str]] = {}
    for item in report["functions"]:
        home = _r_name(item.get("r_file") or "")
        if home:
            names_by_file.setdefault(home, []).append(item["name"])
    cards = _sort_high_batches(_print_batches(report["launch"]))
    card_by_stem: dict[str, dict] = {}
    depends: list[str] = []
    for card in cards:
        path = card.get("path") or ""
        if " + " in path:
            continue
        card_by_stem[_r_name(path)] = card
        for item in _outside_names(card):
            name = (item.split("::", 1)[0] if item else "").strip()
            if name and name not in BASE_PACKAGES:
                depends.append(name)
    files = []
    seen: set[str] = set()
    for card in cards:
        path = card.get("path") or ""
        if " + " in path:
            continue
        stem = _r_name(path)
        if not stem or stem in seen:
            continue
        seen.add(stem)
        real = next((item for item in lines_by if _r_name(item) == stem), path)
        files.append(
            {
                "file": stem,
                "lines": int(lines_by.get(real) or 0),
                "internal": _internal_names(card),
                "packages": _outside_names(card),
                "needs_low": _needs_low(card),
                "functions": names_by_file.get(stem) or [],
            }
        )
    for path, lines in sorted(lines_by.items()):
        stem = _r_name(path)
        if not stem or stem in seen:
            continue
        seen.add(stem)
        files.append(
            {
                "file": stem,
                "lines": int(lines),
                "internal": [],
                "packages": [],
                "needs_low": False,
                "functions": names_by_file.get(stem) or [],
            }
        )
    depends = _unique(depends)
    blockers = [
        name
        for name in depends
        if package_status(name) not in {"complete", "replaced", "base"}
    ]
    row = {
        "package": package,
        "version": version,
        "files": len(lines_by),
        "lines": sum(lines_by.values()),
        "low_status": low_status,
        "free": not blockers,
        "depends": blockers,
    }
    return row, files


def store_high_level(package: str) -> tuple[dict, list[dict]]:
    from screenlib import upsert_high_level

    row, files = high_level_bundle(package)
    upsert_high_level(row, files)
    return row, files


def stored_high_level() -> set[str]:
    from screenlib import connect

    db = connect()
    try:
        return {row[0] for row in db.execute("SELECT package FROM high_level")}
    finally:
        db.close()


def _high_level_job(name: str) -> tuple[str, dict | None, list | None, str]:
    try:
        row, files = high_level_bundle(name)
        return name, row, files, ""
    except Exception as exc:
        return name, None, None, f"{type(exc).__name__}: {exc}"


def fill_high_level(
    limit: int | None = None, skip_stored: bool = True, workers: int | None = None
) -> list[dict]:
    from screenlib import upsert_high_level

    stored = stored_high_level() if skip_stored else set()
    names: list[str] = []
    seen: set[str] = set()
    for name in catalog_names():
        if name in seen or (skip_stored and name in stored):
            continue
        names.append(name)
        seen.add(name)
        if limit is not None and len(names) >= limit:
            break
    rows = []
    total = len(names)
    n_workers = workers if workers is not None else min(8, os.cpu_count() or 4)
    n_workers = max(1, n_workers)
    if n_workers == 1 or total <= 1:
        for i, name in enumerate(names, 1):
            _fill_progress(i, total, name)
            try:
                row, _files = store_high_level(name)
                rows.append(row)
            except Exception as exc:
                print(f"\nskip {name}: {exc}", file=sys.stderr)
        if total:
            print(file=sys.stderr)
        return rows
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        pending = {pool.submit(_high_level_job, name): name for name in names}
        for fut in as_completed(pending):
            name, row, files, err = fut.result()
            done += 1
            _fill_progress(done, total, name)
            if err:
                print(f"\nskip {name}: {err}", file=sys.stderr)
                continue
            upsert_high_level(row, files)
            rows.append(row)
    if total:
        print(file=sys.stderr)
    return rows


def _kernel_from_tarball(package: str) -> tuple[str, dict]:
    tarball, version = find_tarball(package, CONTRIB)
    return version, kernel_stats(read_tarball(tarball, package))


def low_level_from_disk(package: str) -> dict:
    record = package_record(package)
    version = record.get("cran_version") or ""
    kernel: dict = {}
    broken = ""
    try:
        version, kernel = _kernel_from_tarball(package)
    except FileNotFoundError:
        broken = "tarball not on disk"
    except (OSError, EOFError, ValueError) as exc:
        broken = f"tarball unreadable: {exc}"
    routed = replaced_entry(package)
    if routed or (record.get("status") or "") == "replaced":
        status = "replaced"
        notes = replacement_notes(package, routed.get("reason") or "")
    else:
        status = low_unit_status(package, record)
        notes = broken
    return {
        "package": package,
        "version": version,
        "kernel": kernel,
        "launch": {
            "package": package,
            "version": version,
            "low_status": status,
            "crate": _crate_line(package, record, crate_ready(package, record)),
            "notes": notes,
        },
    }


def catalog_names() -> list[str]:
    path = ROOT / "rcran" / "catalog.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [item["name"] for item in data.get("packages") or [] if item.get("name")]


def stored_low_level() -> set[str]:
    from screenlib import connect

    db = connect()
    try:
        return {row[0] for row in db.execute("SELECT package FROM low_level")}
    finally:
        db.close()


def _fill_progress(done: int, total: int, name: str) -> None:
    width = 32
    frac = done / total if total else 1
    filled = int(width * frac)
    bar = "#" * filled + "." * (width - filled)
    label = (name or "")[:36]
    print(f"\r[{bar}] {done}/{total} {label:<36}", end="", file=sys.stderr, flush=True)


def replaced_missing_names() -> list[str]:
    from screenlib import connect

    db = connect()
    try:
        return [
            row[0]
            for row in db.execute(
                """SELECT package FROM low_level
                   WHERE status = 'replaced'
                     AND fortran_lines + c_lines + cpp_lines = 0
                   ORDER BY package"""
            )
        ]
    finally:
        db.close()


def fill_low_level(
    statuses: tuple[str, ...] = ("complete", "in_progress", "replaced"),
    limit: int | None = None,
    skip_stored: bool = True,
    names: list[str] | None = None,
) -> list[dict]:
    stored = stored_low_level() if skip_stored else set()
    given = names is not None
    names = list(names or [])
    seen: set[str] = set(names)
    if given:
        names = names[:limit] if limit is not None else names
    else:
        for name in catalog_names():
            if name in seen or (skip_stored and name in stored):
                continue
            names.append(name)
            seen.add(name)
            if limit is not None and len(names) >= limit:
                break
        if limit is None or len(names) < (limit or 0):
            for path in sorted((ROOT / "packages").glob("*/translation.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                name = record.get("name") or ""
                if not name or name in seen or (skip_stored and name in stored):
                    continue
                if (record.get("status") or "") not in statuses and name not in replaced_reasons():
                    continue
                names.append(name)
                seen.add(name)
                if limit is not None and len(names) >= limit:
                    break
    rows = []
    total = len(names)
    for i, name in enumerate(names, 1):
        _fill_progress(i, total, name)
        try:
            report = low_level_from_disk(name)
            store_low_level(report)
            rows.append(low_level_row(report))
        except Exception as exc:
            print(f"\nskip {name}: {exc}", file=sys.stderr)
    if total:
        print(file=sys.stderr)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    store = "--store-low" in args
    store_high = "--store-high" in args
    fill = "--fill-low" in args
    fill_high = "--fill-high" in args
    rescan_replaced = "--rescan-replaced" in args
    rest = [
        item
        for item in args
        if item
        not in {
            "--json",
            "--store-low",
            "--store-high",
            "--fill-low",
            "--fill-high",
            "--rescan-replaced",
        }
    ]
    if fill_high:
        limit = int(rest[0]) if rest and rest[0].isdigit() else None
        rows = fill_high_level(limit=limit)
        print(f"stored {len(rows)} new high-level rows")
        return 0
    if fill:
        if rescan_replaced:
            rows = fill_low_level(
                names=replaced_missing_names(),
                skip_stored=False,
            )
            print(f"rescanned {len(rows)} replaced rows missing compiled counts")
            return 0
        limit = int(rest[0]) if rest and rest[0].isdigit() else None
        rows = fill_low_level(limit=limit)
        print(f"stored {len(rows)} new low-level rows")
        return 0
    names = rest
    if len(names) != 1:
        print(
            "usage: python3 orchestrator/prepare.py <package> [--json] [--store-low]",
            file=sys.stderr,
        )
        print(
            "       python3 orchestrator/prepare.py --fill-low [count]",
            file=sys.stderr,
        )
        print(
            "       python3 orchestrator/prepare.py --fill-low --rescan-replaced",
            file=sys.stderr,
        )
        print(
            "       python3 orchestrator/prepare.py --fill-high [count]",
            file=sys.stderr,
        )
        return 2
    report = prepare(names[0])
    write_index(report)
    if store:
        store_low_level(report)
    if store_high:
        store_high_level(names[0])
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
