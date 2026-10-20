"""Rebuild the one GitHub Pages dashboard from the orchestrator database."""

from __future__ import annotations

import html
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from screenlib import ROOT, connect

DASH = ROOT / "dashboard"
DOCS = ROOT / "docs"
PAGES_URL = "https://elmahyai.github.io/killr/"
README = ROOT / "README.md"
REGISTRY = ROOT / "registry.json"
PLOTTING = ROOT / "packages" / "killplot" / "library.json"
START = "<!-- progress:start -->"
END = "<!-- progress:end -->"
NOT_DONE_LIMIT = 220
OUTPUT_LIMIT = 6000
SVG_LIMIT = 400_000
SITE_INNER = "KILLR_SITE_INNER"


def site(home_only: bool = True) -> dict:
    from batch import batch
    from ingest import ingest

    ingest()
    db = connect()
    db.row_factory = sqlite3.Row
    try:
        screened = [row["name"] for row in db.execute("SELECT DISTINCT name FROM packages")]
    finally:
        db.close()
    for name in screened:
        batch(name)
    _write_registry()
    _run_existing_builders(home_only)
    _enhance_screened_pages()
    payload = _payload()
    _write_progress_js(payload)
    _update_front(payload)
    _update_readme(payload)
    _copy_dashboard()
    return payload["totals"]


def _run_existing_builders(home_only: bool) -> None:
    env = os.environ.copy()
    env[SITE_INNER] = "1"
    args = [sys.executable, str(DASH / "build.py")]
    if home_only:
        args.append("--home")
    subprocess.run(args, cwd=str(ROOT), check=True, env=env)


def _write_registry() -> None:
    db = connect()
    db.row_factory = sqlite3.Row
    try:
        native = [
            {"name": row["name"], "role": row["role"], "why": row["why"]}
            for row in db.execute("SELECT name, role, why FROM native ORDER BY name")
        ]
        plotting = {}
        if PLOTTING.is_file():
            record = json.loads(PLOTTING.read_text(encoding="utf-8"))
            plotting = {
                "library": record.get("name"),
                "backend": record.get("backend"),
                "rule": record.get("rule"),
                "functions": record.get("functions", []),
                "path": str(PLOTTING.relative_to(ROOT)),
            }
        packages = []
        for row in db.execute("SELECT * FROM translation_packages ORDER BY name"):
            fns = db.execute(
                "SELECT * FROM translation_functions WHERE package = ? ORDER BY name",
                (row["name"],),
            ).fetchall()
            translated = [fn["name"] for fn in fns if fn["translated"]]
            checks = []
            for fn in fns:
                check = json.loads(fn["check_json"] or "{}")
                if fn["translated"] and check:
                    checks.append({"name": fn["name"], **check})
            loads = []
            for fn in fns:
                loads.extend(json.loads(fn["loads"] or "[]"))
            deps = json.loads(row["dependencies"] or "{}")
            packages.append(
                {
                    "name": row["name"],
                    "cran_version": row["cran_version"],
                    "status": row["status"],
                    "inventory": row["inventory"],
                    "coverage": (len(translated) / len(fns)) if fns else 0.0,
                    "translated_functions": translated,
                    "loads": sorted(set(loads)),
                    "dependencies": deps,
                    "crate_claims": json.loads(row["crate_claims"] or "[]"),
                    "checks": checks,
                    "translation": row["translation"],
                }
            )
        crates = []
        for row in db.execute("SELECT * FROM crates ORDER BY name"):
            crates.append(
                {
                    "name": row["name"],
                    "origin": row["origin"],
                    "loaded_by": json.loads(row["loaded_by"] or "[]"),
                    "assigned": row["assigned"],
                    "path": row["path"],
                }
            )
    finally:
        db.close()
    REGISTRY.write_text(
        json.dumps({"native": native, "plotting": plotting, "packages": packages, "crates": crates}, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _slim_doc(side: dict | None, package: str) -> dict | None:
    if not side:
        return None
    slim = {
        "description": side.get("description") or "",
        "usage": side.get("usage") or "",
        "arguments": side.get("arguments") or [],
        "details": side.get("details") or "",
        "value": side.get("value") or "",
        "example": side.get("example") or "",
    }
    blocks = _output_blocks(_doc_refs(side, package))
    if blocks:
        slim["out"] = blocks
    return slim


def _doc_refs(side: dict, package: str) -> list[tuple[str, Path]]:
    relative = side.get("output")
    paths = relative if isinstance(relative, list) else ([relative] if relative else [])
    docs = ROOT / "packages" / package / "docs"
    refs = []
    for item in paths:
        if not isinstance(item, str) or not item:
            continue
        refs.append(("", _with_fallback(_output_path(item, docs))))
    return refs


_PROOF_LABELS = {"r": "R", "python": "Python", "py": "Python", "compare": "Comparison"}


def _output_path(reference: str, docs: Path) -> Path:
    path = Path(reference)
    if path.is_absolute():
        return path
    if reference.startswith("packages/"):
        return ROOT / reference
    if reference.startswith("docs/"):
        under_package = docs.parent / reference
        if under_package.exists():
            return under_package
        return docs / reference[len("docs/"):]
    return docs / reference


def _with_fallback(path: Path) -> Path:
    if path.exists():
        return path
    for short, long in (("-py.", "-python."), ("-python.", "-py.")):
        if short in path.name:
            other = path.with_name(path.name.replace(short, long, 1))
            if other.is_file():
                return other
    return path


def _dir_refs(reference: str, docs: Path, name: str) -> list[tuple[str, Path]]:
    base = _output_path(reference, docs)
    if not base.is_dir():
        return []
    refs = []
    for suffix, label in (("-r", "R"), ("-python", "Python"), ("-py", "Python")):
        path = _with_fallback(base / f"{name}{suffix}.txt")
        if path.is_file():
            refs.append((label, path))
    for path in sorted(base.glob(f"{name}-*.svg")):
        refs.append(("", path))
    return refs


def _proof_refs(value, docs: Path, name: str) -> list[tuple[str, Path]]:
    refs: list[tuple[str, Path]] = []

    def walk(node, label: str = ""):
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "dir" and isinstance(child, str):
                    refs.extend(_dir_refs(child, docs, name))
                else:
                    walk(child, _PROOF_LABELS.get(key, key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, label or ("R" if index == 0 else "Python"))
        elif isinstance(node, str) and node:
            refs.append((label, _with_fallback(_output_path(node, docs))))

    walk(value)
    return refs


def _output_blocks(refs: list[tuple[str, Path]]) -> list[dict]:
    blocks = []
    seen = set()
    for label, path in refs:
        if str(path) in seen:
            continue
        seen.add(str(path))
        try:
            if not path.is_file():
                continue
            if path.suffix == ".svg":
                text = path.read_text(errors="replace")
                if len(text) > SVG_LIMIT:
                    blocks.append({"label": label, "text": "(plot omitted: larger than 400 KB)"})
                    continue
                start = text.find("<svg")
                blocks.append({"label": label, "svg": text[start:] if start >= 0 else text})
                continue
            text = path.read_text(errors="replace").rstrip("\n")
            if len(text) > OUTPUT_LIMIT:
                text = text[:OUTPUT_LIMIT].rstrip() + "\n… (truncated)"
            blocks.append({"label": label, "text": text})
        except OSError:
            continue
    return blocks


def _fn_progress(fn: sqlite3.Row) -> dict:
    not_done = (fn["not_done"] or "").strip()
    if len(not_done) > NOT_DONE_LIMIT:
        not_done = not_done[: NOT_DONE_LIMIT - 1] + "…"
    check = json.loads(fn["check_json"] or "{}")
    doc = json.loads(fn["doc_json"] or "{}")
    proof = check.get("proof") or {}
    spd = check.get("speedup")
    proof_out = _output_blocks(
        _proof_refs(check.get("output"), ROOT / "packages" / fn["package"] / "docs", fn["name"])
    )
    origin = _slim_doc(doc.get("origin"), fn["package"])
    translation = _slim_doc(doc.get("translation"), fn["package"])
    return {
        "n": fn["name"],
        "t": bool(fn["translated"]),
        "nd": not_done,
        "ok": _exact(check) if check else None,
        # Close but not exact, with the difference recorded: counted apart from "ok".
        "appr": _approximate(check) if check else False,
        "s": round(spd, 2) if spd else None,
        "title": doc.get("title") or fn["name"],
        "origin": origin,
        "translation": translation,
        "proof": (
            {"r": proof.get("r") or "", "python": proof.get("python") or ""}
            if proof.get("r") or proof.get("python")
            else None
        ),
        "pout": proof_out or None,
    }


# The constitution's proof law: a function is finished when its proof matches R within 1e-8.
LAW_TOLERANCE = 1e-8


def _exact(check: dict) -> bool:
    """A proof counted as a pass: it matched R, and within the law's tolerance."""
    if not check.get("matches"):
        return False
    diff = check.get("max_abs_diff")
    return diff is None or diff <= LAW_TOLERANCE


def _approximate(check: dict) -> bool:
    """A recorded proof that is close but not exact, so it is never counted as a pass.

    A check that was never compared (``matches`` is null) is not approximate: it is
    simply unproven, and is reported as such.
    """
    if _exact(check):
        return False
    if check.get("matches") is True:
        return True
    if check.get("matches") is False:
        return bool(check.get("approximate"))
    return False


def _checks_of(fns: list[dict]) -> dict:
    checks = [fn for fn in fns if fn.get("ok") is not None]
    speeds = [fn["s"] for fn in fns if fn.get("s") is not None]
    return {
        "passed": sum(1 for fn in checks if fn["ok"]),
        "approximate": sum(1 for fn in checks if fn.get("appr") and not fn["ok"]),
        "not_exact": sum(1 for fn in checks if not fn["ok"]),
        "total": len(checks),
        "speed": round(statistics.median(speeds), 2) if speeds else None,
    }


def _thin_row(row: sqlite3.Row) -> bool:
    files = (
        int(row["fortran_files"] or 0)
        + int(row["c_files"] or 0)
        + int(row["cpp_files"] or 0)
        + int(row["other_files"] or 0)
    )
    return files == 0 and bool((row["crate"] or "").strip())


def _payload() -> dict:
    db = connect()
    db.row_factory = sqlite3.Row
    try:
        packages = []
        fn_by_pkg: dict[str, dict[str, dict]] = {}
        for row in db.execute("SELECT * FROM translation_packages ORDER BY name"):
            fns = db.execute(
                "SELECT * FROM translation_functions WHERE package = ? ORDER BY name",
                (row["name"],),
            ).fetchall()
            functions = []
            checks_detail = []
            speedups = []
            packed: dict[str, dict] = {}
            for fn in fns:
                item = _fn_progress(fn)
                packed[item["n"]] = item
                functions.append(
                    {
                        "n": item["n"],
                        "t": item["t"],
                        "nd": item["nd"],
                        "b": bool(json.loads(fn["blocked_by"] or "[]")),
                    }
                )
                # Only a translated function has a proof to count. An untranslated
                # function keeps its recorded check for display, never as a pass.
                if item["ok"] is not None and item["t"]:
                    if item["s"]:
                        speedups.append(item["s"])
                    checks_detail.append(
                        {
                            "n": item["n"],
                            "ok": item["ok"],
                            "appr": item.get("appr", False),
                            "s": item["s"],
                        }
                    )
            fn_by_pkg[row["name"]] = packed
            screen = db.execute(
                "SELECT * FROM packages WHERE name = ? ORDER BY version DESC",
                (row["name"],),
            ).fetchone()
            deps = json.loads(row["dependencies"] or "{}")
            packages.append(
                {
                    "name": row["name"],
                    "version": row["cran_version"],
                    "status": row["status"],
                    "coverage": round((sum(1 for f in functions if f["t"]) / len(functions)) if functions else 0, 4),
                    "total": len(functions),
                    "translated": sum(1 for f in functions if f["t"]),
                    "checks": {
                        "passed": sum(1 for c in checks_detail if c["ok"]),
                        "approximate": sum(
                            1 for c in checks_detail if c.get("appr") and not c["ok"]
                        ),
                        "total": len(checks_detail),
                        "median_speedup": round(statistics.median(speedups), 2) if speedups else None,
                    },
                    "resume": row["resume"],
                    "blocked_by": json.loads(row["blocked_by"] or "[]"),
                    "rust": bool(deps.get("rust") or json.loads(row["crate_claims"] or "[]")),
                    "functions": functions,
                    "checks_detail": checks_detail,
                    "screen": dict(screen) if screen else None,
                    "strategy": row["strategy"],
                }
            )
        crates = []
        for row in db.execute("SELECT * FROM crates ORDER BY name"):
            assigned = (row["assigned"] or "").strip()
            crates.append(
                {
                    "name": row["name"],
                    "origin": row["origin"],
                    "loaded_by": json.loads(row["loaded_by"] or "[]"),
                    "state": "assigned" if assigned else "done",
                    "assigned": assigned,
                }
            )
        batches = []
        for row in db.execute("SELECT * FROM batches ORDER BY package, r_file"):
            names = [
                item["function"]
                for item in db.execute(
                    "SELECT function FROM batch_functions WHERE batch_id = ? ORDER BY function",
                    (row["id"],),
                )
            ]
            batches.append(
                {
                    "id": row["id"],
                    "package": row["package"],
                    "version": row["version"],
                    "r_file": row["r_file"],
                    "task": row["task"],
                    "model": row["model"],
                    "functions": names,
                    "n_functions": row["n_functions"],
                }
            )
        cost = []
        for row in db.execute(
            "SELECT task, model, COUNT(*) AS n FROM launches GROUP BY task, model ORDER BY task, model"
        ):
            cost.append({"task": row["task"], "model": row["model"], "n": row["n"]})
        low_level = []
        for row in db.execute("SELECT * FROM low_level ORDER BY package"):
            thin = _thin_row(row)
            low_level.append(
                {
                    "package": row["package"],
                    "version": row["version"],
                    "status": row["status"],
                    "thin": thin,
                    "fortran_files": row["fortran_files"],
                    "fortran_lines": row["fortran_lines"],
                    "c_files": row["c_files"],
                    "c_lines": row["c_lines"],
                    "cpp_files": row["cpp_files"],
                    "cpp_lines": row["cpp_lines"],
                    "other_files": row["other_files"],
                    "other_lines": row["other_lines"],
                    "lines": row["lines"],
                    "size": row["size"],
                    "crate": row["crate"],
                    "notes": row["notes"] if "notes" in row.keys() else "",
                }
            )
        high_files: dict[str, list[dict]] = {}
        for row in db.execute("SELECT * FROM high_level_files ORDER BY package, file"):
            names = json.loads(row["functions"] or "[]") if "functions" in row.keys() else []
            packed = fn_by_pkg.get(row["package"]) or {}
            fns = [packed[name] for name in names if name in packed]
            stats = _checks_of(fns)
            high_files.setdefault(row["package"], []).append(
                {
                    "file": row["file"],
                    "lines": row["lines"],
                    "internal": json.loads(row["internal"] or "[]"),
                    "packages": json.loads(row["packages"] or "[]"),
                    "needs_low": bool(row["needs_low"]),
                    "fns": fns,
                    "checks": {
                        "passed": stats["passed"],
                        "approximate": stats.get("approximate", 0),
                        "total": stats["total"],
                    },
                    "speed": stats["speed"],
                }
            )
        high_level = []
        for row in db.execute("SELECT * FROM high_level ORDER BY package"):
            rfiles = high_files.get(row["package"], [])
            assigned = {fn["n"] for item in rfiles for fn in item.get("fns") or []}
            leftover = [
                fn
                for name, fn in (fn_by_pkg.get(row["package"]) or {}).items()
                if name not in assigned
            ]
            file_fns = [fn for item in rfiles for fn in item.get("fns") or []]
            extra = (
                _checks_of(leftover)
                if leftover
                else {"passed": 0, "approximate": 0, "total": 0, "speed": None}
            )
            if leftover and not file_fns:
                stats = extra
            elif leftover:
                extra = _checks_of(leftover)
                rfiles.append(
                    {
                        "file": "(other)",
                        "lines": 0,
                        "internal": [],
                        "packages": [],
                        "needs_low": False,
                        "fns": leftover,
                        "checks": {
                            "passed": extra["passed"],
                            "approximate": extra.get("approximate", 0),
                            "total": extra["total"],
                        },
                        "speed": extra["speed"],
                    }
                )
                stats = _checks_of(file_fns + leftover)
            else:
                stats = _checks_of(file_fns)
            high_level.append(
                {
                    "package": row["package"],
                    "version": row["version"],
                    "files": row["files"],
                    "lines": row["lines"],
                    "low_status": row["low_status"],
                    "free": bool(row["free"]),
                    "depends": json.loads(row["depends"] or "[]"),
                    # Per-file detail is only ever opened from a package that is in the
                    # catalog of opened packages. Keeping it for the 25k screened-only
                    # rows costs ~70 MB and pushes progress.js past GitHub's 100 MB limit.
                    "rfiles": rfiles if row["package"] in fn_by_pkg else [],
                    "fns": leftover if leftover and not file_fns else [],
                    "checks": {
                        "passed": stats["passed"],
                        "approximate": stats.get("approximate", 0),
                        "total": stats["total"],
                    },
                    "speed": stats["speed"],
                }
            )
    finally:
        db.close()
    totals = _totals(packages, crates, low_level, high_level)
    totals["batches"] = len(batches)
    totals["screened"] = sum(1 for p in packages if p.get("screen"))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "generated": generated,
        "url": PAGES_URL,
        "totals": totals,
        "packages": packages,
        "crates": crates,
        "batches": batches,
        "cost": cost,
        "low_level": low_level,
        "high_level": high_level,
    }


def _totals(
    packages: list[dict],
    crates: list[dict],
    low_level: list[dict] | None = None,
    high_level: list[dict] | None = None,
) -> dict:
    by_status: dict[str, int] = {}
    for package in packages:
        by_status[package["status"]] = by_status.get(package["status"], 0) + 1
    graded = [p for p in packages if p["status"] != "replaced"]
    speeds = [
        c["s"]
        for p in packages
        for c in p["checks_detail"]
        if c["s"] is not None and c["ok"]
    ]
    rows = low_level or []
    return {
        "packages": len(packages),
        "graded": len(graded),
        "complete": by_status.get("complete", 0),
        "in_progress": by_status.get("in_progress", 0),
        "replaced": by_status.get("replaced", 0),
        "functions_total": sum(p["total"] for p in graded),
        "functions_done": sum(p["translated"] for p in graded),
        "checks_total": sum(p["checks"]["total"] for p in packages),
        "checks_passed": sum(p["checks"]["passed"] for p in packages),
        # Proofs that are close but not exact, kept out of checks_passed on purpose.
        "checks_approximate": sum(p["checks"].get("approximate", 0) for p in packages),
        "median_speedup": round(statistics.median(speeds), 2) if speeds else None,
        "crates": len(crates),
        "crates_assigned": sum(1 for c in crates if c["state"] == "assigned"),
        "low_done": sum(1 for r in rows if r["status"] == "done"),
        "low_underway": sum(1 for r in rows if r["status"] == "underway"),
        "low_pending": sum(1 for r in rows if r["status"] == "pending"),
        "low_replaced": sum(1 for r in rows if r["status"] == "replaced"),
        "low_thin": sum(1 for r in rows if r.get("thin")),
        "low_compiled": sum(
            1
            for r in rows
            if (r.get("fortran_lines") or 0)
            + (r.get("c_lines") or 0)
            + (r.get("cpp_lines") or 0)
            > 0
        ),
        "high_packages": len(high_level or []),
        "high_free": sum(1 for r in (high_level or []) if r.get("free")),
    }


def _write_progress_js(payload: dict) -> None:
    dest = DOCS / "data"
    dest.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    (dest / "progress.js").write_text(
        "// Generated by the orchestrator from orchestrator/orchestrator.sqlite. Do not edit by hand.\n"
        f"window.KILLR_DATA = {body};\n",
        encoding="utf-8",
    )


def _update_front(_payload: dict) -> None:
    """The front-page How it works copy is edited by hand."""
    return


def _update_readme(payload: dict) -> None:
    totals = payload["totals"]
    packages = payload["packages"]
    generated = payload["generated"]

    def badge(label: str, value: str, color: str) -> str:
        def esc(text: str) -> str:
            return text.replace("-", "--").replace("_", "__").replace(" ", "%20")

        return f"![{label}](https://img.shields.io/badge/{esc(label)}-{esc(value)}-{color})"

    lines = [
        START,
        "",
        "## Progress",
        "",
        f"Snapshot from the orchestrator, {generated}. The interactive version is at "
        f"[{PAGES_URL}]({PAGES_URL}).",
        "",
        " ".join(
            [
                badge("complete", f"{totals['complete']}", "brightgreen"),
                badge("in progress", f"{totals['in_progress']}", "yellow"),
                badge("replaced", f"{totals['replaced']}", "lightgrey"),
                badge(
                    "functions",
                    f"{totals['functions_done']} of {totals['functions_total']}",
                    "blue",
                ),
                badge(
                    "proof checks",
                    f"{totals['checks_passed']} of {totals['checks_total']}",
                    "blue",
                ),
                # Only appears when some proof is close but not exact.
                *(
                    [
                        badge(
                            "close, not exact",
                            f"{totals['checks_approximate']}",
                            "orange",
                        )
                    ]
                    if totals.get("checks_approximate")
                    else []
                ),
                badge("rust crates", f"{totals['crates']}", "orange"),
            ]
        ),
        "",
        "| Status | Packages |",
        "| --- | ---: |",
        f"| Complete | {totals['complete']} |",
        f"| In progress | {totals['in_progress']} |",
        f"| Replaced by a stand-in | {totals['replaced']} |",
        "",
        "<details>",
        f"<summary>All {len(packages)} packages</summary>",
        "",
        "| Package | Status | Functions | Proof checks | Median speedup |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for package in packages:
        speed = (
            f"{package['checks']['median_speedup']}x"
            if package["checks"]["median_speedup"]
            else "-"
        )
        appr = package["checks"].get("approximate", 0)
        # Name the accepted differences in the same cell, so they never read as passes.
        check_cell = f"{package['checks']['passed']} / {package['checks']['total']}"
        if appr:
            check_cell += f" (+{appr} close)"
        lines.append(
            f"| {package['name']} | {package['status'].replace('_', ' ')} | "
            f"{package['translated']} / {package['total']} | "
            f"{check_cell} | {speed} |"
        )
    lines += ["", "</details>", "", END]
    block = "\n".join(lines)
    text = README.read_text(encoding="utf-8") if README.is_file() else ""
    if START in text and END in text:
        head, rest = text.split(START, 1)
        _, tail = rest.split(END, 1)
        text = head + block + tail
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    README.write_text(text, encoding="utf-8")


def _copy_dashboard() -> None:
    dest = DOCS / "dashboard"
    dest.mkdir(parents=True, exist_ok=True)
    src_index = DASH / "index.html"
    if src_index.is_file():
        shutil.copyfile(src_index, dest / "index.html")
    src_pkgs = DASH / "packages"
    dst_pkgs = dest / "packages"
    if src_pkgs.is_dir():
        dst_pkgs.mkdir(parents=True, exist_ok=True)
        for path in src_pkgs.glob("*.html"):
            shutil.copyfile(path, dst_pkgs / path.name)


def _enhance_screened_pages() -> None:
    db = connect()
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("SELECT * FROM packages").fetchall()
        batches = list(db.execute("SELECT * FROM batches"))
        batch_fns = {
            row["id"]: [
                item["function"]
                for item in db.execute(
                    "SELECT function FROM batch_functions WHERE batch_id = ? ORDER BY function",
                    (row["id"],),
                )
            ]
            for row in batches
        }
        deps = list(db.execute("SELECT * FROM package_deps"))
    finally:
        db.close()
    by_pkg = {row["name"]: row for row in rows}
    for name, screen in by_pkg.items():
        path = DASH / "packages" / f"{name}.html"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace('id="desk-screen"', 'id="orch-screen"')
        text = text.replace("Desk screen", "Screen")
        if 'id="orch-screen"' in text:
            path.write_text(text, encoding="utf-8")
            continue
        pkg_batches = [row for row in batches if row["package"] == name]
        pkg_deps = [row for row in deps if row["package"] == name]
        card = _screen_card(screen, pkg_deps, pkg_batches, batch_fns)
        if "<main>" in text:
            text = text.replace("<main>", "<main>\n" + card, 1)
        else:
            text = card + text
        path.write_text(text, encoding="utf-8")


def _screen_card(screen, deps, batches, batch_fns) -> str:
    dep_rows = "".join(
        f"<tr><td>{html.escape(row['section'])}</td><td>{html.escape(row['dep'])}</td>"
        f"<td>{html.escape(row['constraint_text'] or '')}</td></tr>"
        for row in deps
    ) or "<tr><td colspan='3'>None</td></tr>"
    batch_rows = "".join(
        f"<tr><td>{html.escape(row['r_file'])}</td><td>{html.escape(row['task'])}</td>"
        f"<td>{html.escape(row['model'])}</td>"
        f"<td>{html.escape(', '.join(batch_fns.get(row['id'], [])))}</td></tr>"
        for row in batches
    ) or "<tr><td colspan='4'>No batches yet.</td></tr>"
    return f"""<section class="card" id="orch-screen">
<p class="kicker">Screen</p>
<p>R {screen['n_r']} · C {screen['n_c']} ({screen['n_c_files']} files) · Fortran {screen['n_fortran']} ({screen['n_fortran_files']} files) · C++ {screen['n_cpp']} ({screen['n_cpp_files']} files) · {html.escape(screen['strategy_hint'])}</p>
<h3>Package dependencies</h3>
<table><thead><tr><th>Section</th><th>Package</th><th></th></tr></thead><tbody>{dep_rows}</tbody></table>
<h3>Next batches</h3>
<table><thead><tr><th>File</th><th>Task</th><th>Model</th><th>Functions</th></tr></thead><tbody>{batch_rows}</tbody></table>
</section>
"""
