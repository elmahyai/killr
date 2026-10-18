"""Screen one CRAN tarball already in rcran/contrib into the orchestrator database."""

from __future__ import annotations

import json
import re
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRIB = ROOT / "rcran" / "contrib"
DB_PATH = ROOT / "orchestrator" / "orchestrator.sqlite"

SKIP_SRC = {"makevars", "makevars.win", "makevars.ucrt", "makefile"}
C_EXT = {".c"}
FORTRAN_EXT = {".f", ".for", ".f90", ".f95", ".f03"}
CPP_EXT = {".cpp", ".cc", ".cxx"}
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
LOAD_NS = re.compile(r"\b([A-Za-z.][A-Za-z0-9.]*):::")
LOAD_EXPORT = re.compile(r"\b([A-Za-z.][A-Za-z0-9.]*)::")
LOAD_LIB = re.compile(
    r"""\b(?:library|require|requireNamespace)\s*\(\s*["']?([A-Za-z.][A-Za-z0-9.]*)"""
)
NS_EXPORT = re.compile(r"export\(([^)]*)\)", re.S)
NS_PATTERN = re.compile(r"exportPattern\(\s*[\"']([^\"']+)[\"']\s*\)")
NS_S3 = re.compile(r"S3method\(\s*([^,\s]+)\s*,\s*([^)\s]+)\s*\)")
NS_METHODS = re.compile(r"exportMethods\(([^)]*)\)", re.S)


SCHEMA = """
CREATE TABLE IF NOT EXISTS packages (
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    n_r INTEGER NOT NULL,
    n_c INTEGER NOT NULL,
    n_fortran INTEGER NOT NULL,
    n_cpp INTEGER NOT NULL,
    n_c_files INTEGER NOT NULL,
    n_fortran_files INTEGER NOT NULL,
    n_cpp_files INTEGER NOT NULL,
    strategy_hint TEXT NOT NULL,
    screened_at TEXT NOT NULL,
    PRIMARY KEY (name, version)
);
CREATE TABLE IF NOT EXISTS package_deps (
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    dep TEXT NOT NULL,
    section TEXT NOT NULL,
    constraint_text TEXT NOT NULL,
    PRIMARY KEY (package, version, dep, section)
);
CREATE TABLE IF NOT EXISTS functions (
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    r_file TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    n_lines INTEGER NOT NULL,
    PRIMARY KEY (package, version, name)
);
CREATE TABLE IF NOT EXISTS function_deps (
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    function TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    PRIMARY KEY (package, version, function, kind, target)
);
CREATE TABLE IF NOT EXISTS translation_packages (
    name TEXT NOT NULL PRIMARY KEY,
    cran_version TEXT NOT NULL,
    inventory TEXT NOT NULL,
    status TEXT NOT NULL,
    blocked_by TEXT NOT NULL,
    crate_claims TEXT NOT NULL,
    resume TEXT NOT NULL,
    strategy TEXT NOT NULL,
    dependencies TEXT NOT NULL,
    translation TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS translation_functions (
    package TEXT NOT NULL,
    name TEXT NOT NULL,
    translated INTEGER NOT NULL,
    python TEXT NOT NULL,
    loads TEXT NOT NULL,
    uses TEXT NOT NULL,
    done TEXT NOT NULL,
    not_done TEXT NOT NULL,
    blocked_by TEXT NOT NULL,
    assigned TEXT NOT NULL,
    check_json TEXT NOT NULL,
    doc_json TEXT NOT NULL,
    PRIMARY KEY (package, name)
);
CREATE TABLE IF NOT EXISTS crates (
    name TEXT NOT NULL PRIMARY KEY,
    origin TEXT NOT NULL,
    loaded_by TEXT NOT NULL,
    assigned TEXT NOT NULL,
    path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS launches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    task TEXT NOT NULL,
    minutes REAL,
    r_lines INTEGER,
    matched_lines INTEGER,
    functions INTEGER,
    matched INTEGER,
    returned TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS native (
    name TEXT NOT NULL PRIMARY KEY,
    role TEXT NOT NULL,
    why TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS replaced (
    name TEXT NOT NULL PRIMARY KEY,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches (
    id TEXT NOT NULL PRIMARY KEY,
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    r_file TEXT NOT NULL,
    task TEXT NOT NULL,
    model TEXT NOT NULL,
    n_functions INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS batch_functions (
    batch_id TEXT NOT NULL,
    function TEXT NOT NULL,
    PRIMARY KEY (batch_id, function)
);
CREATE TABLE IF NOT EXISTS low_level (
    package TEXT NOT NULL PRIMARY KEY,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    fortran_files INTEGER NOT NULL,
    fortran_lines INTEGER NOT NULL,
    c_files INTEGER NOT NULL,
    c_lines INTEGER NOT NULL,
    cpp_files INTEGER NOT NULL,
    cpp_lines INTEGER NOT NULL,
    other_files INTEGER NOT NULL,
    other_lines INTEGER NOT NULL,
    lines INTEGER NOT NULL,
    size TEXT NOT NULL,
    crate TEXT NOT NULL,
    notes TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS high_level (
    package TEXT NOT NULL PRIMARY KEY,
    version TEXT NOT NULL,
    files INTEGER NOT NULL,
    lines INTEGER NOT NULL,
    low_status TEXT NOT NULL,
    free INTEGER NOT NULL,
    depends TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS high_level_files (
    package TEXT NOT NULL,
    file TEXT NOT NULL,
    lines INTEGER NOT NULL,
    internal TEXT NOT NULL,
    packages TEXT NOT NULL,
    needs_low INTEGER NOT NULL,
    functions TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (package, file)
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=60)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    _ensure_column(db, "low_level", "notes", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(db, "high_level_files", "functions", "TEXT NOT NULL DEFAULT '[]'")
    return db


def _ensure_column(db: sqlite3.Connection, table: str, column: str, spec: str) -> None:
    cols = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    if cols and column not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")
        db.commit()


def upsert_low_level(row: dict, path: Path = DB_PATH) -> None:
    db = connect(path)
    db.execute(
        """INSERT INTO low_level (
            package, version, status,
            fortran_files, fortran_lines,
            c_files, c_lines,
            cpp_files, cpp_lines,
            other_files, other_lines,
            lines, size, crate, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(package) DO UPDATE SET
            version=excluded.version,
            status=excluded.status,
            fortran_files=excluded.fortran_files,
            fortran_lines=excluded.fortran_lines,
            c_files=excluded.c_files,
            c_lines=excluded.c_lines,
            cpp_files=excluded.cpp_files,
            cpp_lines=excluded.cpp_lines,
            other_files=excluded.other_files,
            other_lines=excluded.other_lines,
            lines=excluded.lines,
            size=excluded.size,
            crate=excluded.crate,
            notes=excluded.notes,
            updated_at=excluded.updated_at""",
        (
            row["package"],
            row.get("version") or "",
            row.get("status") or "",
            int(row.get("fortran_files") or 0),
            int(row.get("fortran_lines") or 0),
            int(row.get("c_files") or 0),
            int(row.get("c_lines") or 0),
            int(row.get("cpp_files") or 0),
            int(row.get("cpp_lines") or 0),
            int(row.get("other_files") or 0),
            int(row.get("other_lines") or 0),
            int(row.get("lines") or 0),
            row.get("size") or "",
            row.get("crate") or "",
            row.get("notes") or "",
            row.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        ),
    )
    db.commit()
    db.close()


def upsert_high_level(row: dict, files: list[dict], path: Path = DB_PATH) -> None:
    db = connect(path)
    package = row["package"]
    db.execute(
        """INSERT INTO high_level (
            package, version, files, lines, low_status, free, depends, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(package) DO UPDATE SET
            version=excluded.version,
            files=excluded.files,
            lines=excluded.lines,
            low_status=excluded.low_status,
            free=excluded.free,
            depends=excluded.depends,
            updated_at=excluded.updated_at""",
        (
            package,
            row.get("version") or "",
            int(row.get("files") or 0),
            int(row.get("lines") or 0),
            row.get("low_status") or "none",
            1 if row.get("free") else 0,
            json.dumps(row.get("depends") or [], ensure_ascii=False),
            row.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        ),
    )
    db.execute("DELETE FROM high_level_files WHERE package = ?", (package,))
    db.executemany(
        """INSERT INTO high_level_files (
            package, file, lines, internal, packages, needs_low, functions
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                package,
                item.get("file") or "",
                int(item.get("lines") or 0),
                json.dumps(item.get("internal") or [], ensure_ascii=False),
                json.dumps(item.get("packages") or [], ensure_ascii=False),
                1 if item.get("needs_low") else 0,
                json.dumps(item.get("functions") or [], ensure_ascii=False),
            )
            for item in files
        ],
    )
    db.commit()
    db.close()


def find_tarball(name: str, contrib: Path = CONTRIB) -> tuple[Path, str]:
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


def screen(name: str, db_path: Path = DB_PATH, contrib: Path = CONTRIB) -> dict:
    tarball, version = find_tarball(name, contrib)
    members = read_tarball(tarball, name)
    description = dcf_fields(members.get("DESCRIPTION") or "")
    recorded = (description.get("Version") or "").strip()
    if recorded:
        version = recorded
    package_deps = dependency_entries(description)
    exports = namespace_exports(members.get("NAMESPACE") or "")
    r_functions = r_function_defs(members)
    chosen = select_exports(exports, r_functions)
    native = native_inventory(members)
    function_deps = collect_function_deps(chosen, native["symbols"])
    n_r = len(chosen)
    hint = strategy_hint(n_r, native["n_c"], native["n_fortran"], native["n_cpp"])
    row = {
        "name": name,
        "version": version,
        "n_r": n_r,
        "n_c": native["n_c"],
        "n_fortran": native["n_fortran"],
        "n_cpp": native["n_cpp"],
        "n_c_files": native["n_c_files"],
        "n_fortran_files": native["n_fortran_files"],
        "n_cpp_files": native["n_cpp_files"],
        "strategy_hint": hint,
        "screened_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_deps": package_deps,
        "functions": chosen,
        "function_deps": function_deps,
        "tarball": str(tarball),
    }
    write_screen(db_path, row)
    return row


def write_screen(db_path: Path, row: dict) -> None:
    db = connect(db_path)
    name, version = row["name"], row["version"]
    try:
        for table in ("function_deps", "functions", "package_deps", "packages"):
            key = "name" if table == "packages" else "package"
            db.execute(f"DELETE FROM {table} WHERE {key} = ? AND version = ?", (name, version))
        db.execute(
            """INSERT INTO packages (
                name, version, n_r, n_c, n_fortran, n_cpp,
                n_c_files, n_fortran_files, n_cpp_files, strategy_hint, screened_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                version,
                row["n_r"],
                row["n_c"],
                row["n_fortran"],
                row["n_cpp"],
                row["n_c_files"],
                row["n_fortran_files"],
                row["n_cpp_files"],
                row["strategy_hint"],
                row["screened_at"],
            ),
        )
        db.executemany(
            """INSERT INTO package_deps (package, version, dep, section, constraint_text)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (name, version, item["dep"], item["section"], item["constraint"])
                for item in row["package_deps"]
            ],
        )
        db.executemany(
            """INSERT INTO functions (
                package, version, name, r_file, start_line, end_line, n_lines
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    name,
                    version,
                    item["name"],
                    item["r_file"],
                    item["start_line"],
                    item["end_line"],
                    item["n_lines"],
                )
                for item in row["functions"]
            ],
        )
        db.executemany(
            """INSERT INTO function_deps (package, version, function, kind, target)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (name, version, item["function"], item["kind"], item["target"])
                for item in row["function_deps"]
            ],
        )
        db.commit()
    finally:
        db.close()


def status(name: str, db_path: Path = DB_PATH) -> str:
    db = connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        pkg = db.execute(
            "SELECT * FROM packages WHERE name = ? ORDER BY version DESC", (name,)
        ).fetchone()
        if pkg is None:
            return f"{name}: not screened\n"
        deps = db.execute(
            """SELECT section, dep, constraint_text FROM package_deps
               WHERE package = ? AND version = ? ORDER BY section, dep""",
            (name, pkg["version"]),
        ).fetchall()
        fns = db.execute(
            """SELECT name, r_file, start_line, end_line, n_lines FROM functions
               WHERE package = ? AND version = ? ORDER BY name""",
            (name, pkg["version"]),
        ).fetchall()
        fdeps = db.execute(
            """SELECT function, kind, target FROM function_deps
               WHERE package = ? AND version = ? ORDER BY function, kind, target""",
            (name, pkg["version"]),
        ).fetchall()
        batches = db.execute(
            """SELECT id, r_file, task, model, n_functions FROM batches
               WHERE package = ? AND version = ? ORDER BY r_file, id""",
            (name, pkg["version"]),
        ).fetchall()
        batch_fns = {}
        for batch in batches:
            batch_fns[batch["id"]] = [
                row[0]
                for row in db.execute(
                    "SELECT function FROM batch_functions WHERE batch_id = ? ORDER BY function",
                    (batch["id"],),
                )
            ]
    finally:
        db.close()
    lines = [
        f"{pkg['name']} {pkg['version']}",
        f"  n_r={pkg['n_r']}  n_c={pkg['n_c']}  n_fortran={pkg['n_fortran']}  n_cpp={pkg['n_cpp']}",
        f"  files: c={pkg['n_c_files']}  fortran={pkg['n_fortran_files']}  cpp={pkg['n_cpp_files']}",
        f"  strategy_hint={pkg['strategy_hint']}",
        f"  screened_at={pkg['screened_at']}",
        "  package_deps:",
    ]
    if deps:
        for item in deps:
            extra = f" ({item['constraint_text']})" if item["constraint_text"] else ""
            lines.append(f"    {item['section']}  {item['dep']}{extra}")
    else:
        lines.append("    (none)")
    lines.append(f"  functions: {len(fns)}")
    for item in fns:
        lines.append(
            f"    {item['name']}  {item['r_file']}:{item['start_line']}-{item['end_line']}"
            f"  ({item['n_lines']} lines)"
        )
    lines.append(f"  function_deps: {len(fdeps)}")
    for item in fdeps:
        lines.append(f"    {item['function']}  {item['kind']}  {item['target']}")
    lines.append(f"  batches: {len(batches)}")
    for item in batches:
        names = ", ".join(batch_fns.get(item["id"], []))
        lines.append(
            f"    {item['r_file']}  {item['task']}  {item['model']}"
            f"  ({item['n_functions']})  {names}"
        )
    return "\n".join(lines) + "\n"


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
            text = raw.read().decode("utf-8", "replace")
            rel = "/".join(parts[1:])
            members[rel] = text
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


def dependency_entries(fields: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    for section, key in (
        ("depends", "Depends"),
        ("imports", "Imports"),
        ("linking_to", "LinkingTo"),
    ):
        for part in (fields.get(key) or "").split(","):
            part = part.strip()
            if not part:
                continue
            if "(" in part and part.endswith(")"):
                dep, constraint = part.split("(", 1)
                dep = dep.strip()
                constraint = constraint[:-1].strip()
            else:
                dep, constraint = part, ""
            if not dep or dep == "R":
                continue
            rows.append({"dep": dep, "section": section, "constraint": constraint})
    return rows


def namespace_exports(text: str) -> dict:
    names: list[str] = []
    for block in NS_EXPORT.findall(text):
        for item in block.split(","):
            item = item.strip().strip("`\"'")
            if item:
                names.append(item)
    for block in NS_METHODS.findall(text):
        for item in block.split(","):
            item = item.strip().strip("`\"'")
            if item:
                names.append(item)
    for generic, klass in NS_S3.findall(text):
        names.append(f"{generic.strip()}.{klass.strip()}")
    patterns = NS_PATTERN.findall(text)
    return {"names": names, "patterns": patterns}


def r_function_defs(members: dict[str, str]) -> list[dict]:
    found = []
    for rel, text in members.items():
        parts = rel.split("/")
        if len(parts) != 2 or parts[0] != "R":
            continue
        if not parts[1].lower().endswith((".r", ".s")):
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
                    "start": start,
                    "end": end,
                    "start_line": start_line,
                    "end_line": end_line,
                    "n_lines": n_lines,
                    "body": body,
                }
            )
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


def select_exports(exports: dict, r_functions: list[dict]) -> list[dict]:
    patterns = [re.compile(pattern) for pattern in exports["patterns"]]
    wanted = set(exports["names"])
    chosen = []
    seen = set()
    for item in r_functions:
        name = item["name"]
        if name in seen:
            continue
        if name in wanted or any(pattern.search(name) for pattern in patterns):
            seen.add(name)
            chosen.append({k: item[k] for k in item if k != "body"})
            chosen[-1]["body"] = item["body"]
    chosen.sort(key=lambda item: item["name"])
    return chosen


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


def collect_function_deps(
    functions: list[dict], native_symbols: set[str]
) -> list[dict[str, str]]:
    export_names = [item["name"] for item in functions]
    rows = []
    seen: set[tuple[str, str, str]] = set()
    for item in functions:
        body = strip_r_comments(item["body"])
        code = blank_r_strings(body)
        for other in export_names:
            if other == item["name"]:
                continue
            if re.search(rf"(?<![A-Za-z0-9._]){re.escape(other)}(?![A-Za-z0-9._])", code):
                add_dep(rows, seen, item["name"], "uses", other)
        for match in LOAD_LIB.finditer(code):
            add_dep(rows, seen, item["name"], "loads", match.group(1))
        for match in LOAD_NS.finditer(code):
            add_dep(rows, seen, item["name"], "loads", match.group(1))
        for match in LOAD_EXPORT.finditer(code):
            add_dep(rows, seen, item["name"], "loads", match.group(1))
        for match in NATIVE_CALL.finditer(body):
            symbol = match.group(2) or match.group(3)
            if symbol and symbol.lower() in native_symbols:
                add_dep(rows, seen, item["name"], "native", symbol)
    rows.sort(key=lambda row: (row["function"], row["kind"], row["target"]))
    return rows


def add_dep(
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str]],
    function: str,
    kind: str,
    target: str,
) -> None:
    key = (function, kind, target)
    if key in seen:
        return
    seen.add(key)
    rows.append({"function": function, "kind": kind, "target": target})


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


def strategy_hint(n_r: int, n_c: int, n_fortran: int, n_cpp: int) -> str:
    kernel = (n_c + n_fortran + n_cpp) > 0
    if n_r > 200:
        return "huge"
    if n_r <= 20:
        band = "small"
    elif n_r <= 80:
        band = "medium"
    else:
        band = "large"
    return f"{band}-low" if kernel else band
