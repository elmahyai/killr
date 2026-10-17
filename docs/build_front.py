"""Build the data for the front page and the progress section of the README.

Reads registry.json, every packages/<Name>/translation.json, and crates/<name>/crate.json.
Writes:
  docs/data/progress.js   loaded by docs/index.html (works from file:// and GitHub Pages)
  README.md               the block between the progress markers is regenerated
  docs/dashboard/         a copy of dashboard/ so the per-package pages resolve

Run after dashboard/build.py --home:
  python3 docs/build_front.py
"""

from __future__ import annotations

import json
import shutil
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry.json"
PACKAGES = ROOT / "packages"
CRATES = ROOT / "crates"
DATA_DIR = ROOT / "docs" / "data"
README = ROOT / "README.md"
DASH_SRC = ROOT / "dashboard"
DASH_DST = ROOT / "docs" / "dashboard"
PAGES_URL = "https://elmahyai.github.io/killr/"
START = "<!-- progress:start -->"
END = "<!-- progress:end -->"
NOT_DONE_LIMIT = 220


def _grade(status: str, coverage: float, checks: list) -> str:
    """Exam grade. Replaced packages are exempt and get no grade."""
    if status == "replaced":
        return "EX"
    if coverage <= 0:
        return "F"
    failing = any(not c.get("matches") for c in checks)
    if coverage >= 1 and checks and not failing:
        return "A"
    if coverage >= 0.75:
        return "B"
    if coverage >= 0.5:
        return "C"
    return "D"


def _load_translation(name: str) -> dict:
    path = PACKAGES / name / "translation.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _package_rows(registry: dict) -> list[dict]:
    rows = []
    for record in registry.get("packages", []):
        name = record["name"]
        status = record.get("status") or "unknown"
        coverage = float(record.get("coverage") or 0.0)
        checks = record.get("checks") or []
        translation = _load_translation(name)
        functions = []
        for fn in translation.get("functions") or []:
            not_done = (fn.get("not_done") or "").strip()
            if len(not_done) > NOT_DONE_LIMIT:
                not_done = not_done[: NOT_DONE_LIMIT - 1] + "…"
            functions.append(
                {
                    "n": fn.get("name", ""),
                    "t": bool(fn.get("translated")),
                    "nd": not_done,
                    "b": bool(fn.get("blocked_by")),
                }
            )
        total = len(functions)
        translated = sum(1 for f in functions if f["t"])
        if total == 0:
            total = len(record.get("translated_functions") or [])
            translated = total
        passed = sum(1 for c in checks if c.get("matches"))
        speedups = [c["speedup"] for c in checks if c.get("speedup")]
        rows.append(
            {
                "name": name,
                "version": record.get("cran_version") or "",
                "status": status,
                "coverage": round(coverage, 4),
                "grade": _grade(status, coverage, checks),
                "total": total,
                "translated": translated,
                "checks": {
                    "passed": passed,
                    "total": len(checks),
                    "median_speedup": round(statistics.median(speedups), 2) if speedups else None,
                },
                "resume": (translation.get("resume") or "").strip(),
                "blocked_by": translation.get("blocked_by") or [],
                "rust": bool((record.get("dependencies") or {}).get("rust")),
                "functions": functions,
                "checks_detail": [
                    {
                        "n": c.get("name", ""),
                        "ok": bool(c.get("matches")),
                        "s": round(c["speedup"], 2) if c.get("speedup") else None,
                    }
                    for c in checks
                ],
            }
        )
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def _crate_rows(registry: dict) -> list[dict]:
    rows = []
    for crate in registry.get("crates", []):
        assigned = (crate.get("assigned") or "").strip()
        rows.append(
            {
                "name": crate["name"],
                "origin": crate.get("origin") or "",
                "loaded_by": crate.get("loaded_by") or [],
                "state": "assigned" if assigned else "done",
                "assigned": assigned,
            }
        )
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def _totals(packages: list[dict], crates: list[dict]) -> dict:
    by_status = {}
    for p in packages:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    graded = [p for p in packages if p["status"] != "replaced"]
    functions_total = sum(p["total"] for p in graded)
    functions_done = sum(p["translated"] for p in graded)
    checks_total = sum(p["checks"]["total"] for p in packages)
    checks_passed = sum(p["checks"]["passed"] for p in packages)
    speeds = [
        c["s"]
        for p in packages
        for c in p["checks_detail"]
        if c["s"] is not None and c["ok"]
    ]
    grades = {}
    for p in graded:
        grades[p["grade"]] = grades.get(p["grade"], 0) + 1
    return {
        "packages": len(packages),
        "graded": len(graded),
        "complete": by_status.get("complete", 0),
        "in_progress": by_status.get("in_progress", 0),
        "replaced": by_status.get("replaced", 0),
        "functions_total": functions_total,
        "functions_done": functions_done,
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "median_speedup": round(statistics.median(speeds), 2) if speeds else None,
        "crates": len(crates),
        "crates_assigned": sum(1 for c in crates if c["state"] == "assigned"),
        "grades": grades,
    }


def _write_js(payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (DATA_DIR / "progress.js").write_text(
        "// Generated by docs/build_front.py. Do not edit by hand.\n"
        f"window.KILLR_DATA = {body};\n",
        encoding="utf-8",
    )


def _badge(label: str, value: str, color: str) -> str:
    def esc(text: str) -> str:
        return text.replace("-", "--").replace("_", "__").replace(" ", "%20")

    return f"![{label}](https://img.shields.io/badge/{esc(label)}-{esc(value)}-{color})"


def _readme_block(totals: dict, packages: list[dict], generated: str) -> str:
    graded = totals["graded"]
    lines = [
        START,
        "",
        "## Progress",
        "",
        f"Snapshot from the registry, {generated}. The interactive version is at "
        f"[{PAGES_URL}]({PAGES_URL}).",
        "",
        " ".join(
            [
                _badge("complete", f"{totals['complete']}", "brightgreen"),
                _badge("in progress", f"{totals['in_progress']}", "yellow"),
                _badge("replaced", f"{totals['replaced']}", "lightgrey"),
                _badge(
                    "functions",
                    f"{totals['functions_done']} of {totals['functions_total']}",
                    "blue",
                ),
                _badge(
                    "proof checks",
                    f"{totals['checks_passed']} of {totals['checks_total']}",
                    "blue",
                ),
                _badge("rust crates", f"{totals['crates']}", "orange"),
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
        f"<summary>All {len(packages)} packages (grade A to F; EX is exempt)</summary>",
        "",
        "| Package | Status | Grade | Functions | Proof checks | Median speedup |",
        "| --- | --- | :---: | ---: | ---: | ---: |",
    ]
    for p in packages:
        speed = f"{p['checks']['median_speedup']}x" if p["checks"]["median_speedup"] else "-"
        lines.append(
            f"| {p['name']} | {p['status'].replace('_', ' ')} | {p['grade']} | "
            f"{p['translated']} / {p['total']} | "
            f"{p['checks']['passed']} / {p['checks']['total']} | {speed} |"
        )
    lines += ["", "</details>", "", END]
    return "\n".join(lines)


def _update_readme(block: str) -> None:
    text = README.read_text(encoding="utf-8") if README.is_file() else ""
    if START in text and END in text:
        head, rest = text.split(START, 1)
        _, tail = rest.split(END, 1)
        text = head + block + tail
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    README.write_text(text, encoding="utf-8")


def _copy_dashboard() -> None:
    if not DASH_SRC.is_dir():
        return
    DASH_DST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DASH_SRC / "index.html", DASH_DST / "index.html")
    src_pkgs = DASH_SRC / "packages"
    dst_pkgs = DASH_DST / "packages"
    if src_pkgs.is_dir():
        if dst_pkgs.exists():
            shutil.rmtree(dst_pkgs)
        shutil.copytree(src_pkgs, dst_pkgs)


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    packages = _package_rows(registry)
    crates = _crate_rows(registry)
    totals = _totals(packages, crates)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "generated": generated,
        "url": PAGES_URL,
        "totals": totals,
        "packages": packages,
        "crates": crates,
    }
    _write_js(payload)
    _update_readme(_readme_block(totals, packages, generated))
    _copy_dashboard()
    print(
        f"packages {len(packages)} (complete {totals['complete']}, in progress "
        f"{totals['in_progress']}, replaced {totals['replaced']}); crates {len(crates)}; "
        f"functions {totals['functions_done']}/{totals['functions_total']}"
    )


if __name__ == "__main__":
    main()
