"""Build registry.json and a self-contained dashboard from the translation records."""

from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
CRATES = ROOT / "crates"
NATIVE = ROOT / "ai-handbook" / "native.json"
PLOTTING = ROOT / "packages" / "killplot" / "library.json"
REGISTRY = ROOT / "registry.json"
PAGE = Path(__file__).resolve().parent / "index.html"
CRAN_CATALOG = ROOT / "rcran" / "catalog.json"
CRAN_IMPORTANCE = ROOT / "rcran" / "importance.json"
CRAN_REPLACED = ROOT / "rcran" / "replaced.json"
HUGE_EXPORTS = 200
RUST_STAND_INS = {"Rayon", "Polars and calamine", "cryptography"}
CRAN_NEXT = 20
R_DEPS_CACHE = Path(__file__).resolve().parent / "r-deps-cache.json"
LAUNCHES = Path(__file__).resolve().parent / "launches.json"
MODEL_WEIGHT = {
    "claude-haiku-5-5": 1,
    "claude-haiku-5-5-thinking-high": 2,
    "gpt-5.6-luna-medium": 1,
    "gpt-5.6-luna": 1,
    "composer-2.5-fast": 2,
    "grok-4.7-high-fast": 3,
    "gpt-5.6-sol-medium": 4,
    "gemini-4-argon-medium": 5,
    "claude-sonnet-5-5-high": 9,
    "claude-opus-5-5-medium": 17,
}
MODEL_LABEL = {
    "claude-haiku-5-5": "haiku",
    "claude-haiku-5-5-thinking-high": "haiku-th",
    "gpt-5.6-luna-medium": "luna",
    "gpt-5.6-luna": "luna",
    "composer-2.5-fast": "composer",
    "grok-4.7-high-fast": "grok",
    "gpt-5.6-sol-medium": "gpt",
    "gemini-4-argon-medium": "gemini",
    "claude-sonnet-5-5-high": "sonnet",
    "claude-opus-5-5-medium": "opus",
}
TASK_CANDIDATES = {
    "python-match": ["claude-haiku-5-5-thinking-high", "composer-2.5-fast"],
    "python-numerical": [
        "gpt-5.6-luna-medium",
        "composer-2.5-fast",
        "grok-4.7-high-fast",
    ],
    "python-other": [
        "gpt-5.6-luna-medium",
        "composer-2.5-fast",
        "grok-4.7-high-fast",
    ],
    "crate-new": ["grok-4.7-high-fast"],
    "crate-family": ["grok-4.7-high-fast"],
    "crate-retry": ["grok-4.7-high-fast"],
    "task-force": ["composer-2.5-fast", "grok-4.7-high-fast"],
    "hard-retry": ["grok-4.7-high-fast"],
}
TASK_DEFAULT = {
    "hard-retry": "grok-4.7-high-fast",
    "crate-new": "grok-4.7-high-fast",
    "crate-family": "grok-4.7-high-fast",
    "crate-retry": "grok-4.7-high-fast",
    "task-force": "composer-2.5-fast",
    "python-numerical": "gpt-5.6-luna-medium",
    "python-other": "gpt-5.6-luna-medium",
    "python-match": "claude-haiku-5-5-thinking-high",
}
R_LIBRARIES = (
    Path.home() / "R" / "x86_64-pc-linux-gnu-library" / "4.5",
    Path.home() / "R" / "library",
    Path("/usr/local/lib/R/site-library"),
    Path("/usr/lib/R/site-library"),
    Path("/usr/lib/R/library"),
)
# These ship with R. They are not opened as packages, and they do not block.
BASE_PACKAGES = frozenset({
    "base",
    "compiler",
    "datasets",
    "grDevices",
    "graphics",
    "grid",
    "methods",
    "parallel",
    "splines",
    "stats",
    "stats4",
    "tcltk",
    "tools",
    "utils",
})


def _cost_advice() -> dict:
    records = _load_launches()
    aside = _set_aside(records)
    tasks = {}
    for task, candidates in TASK_CANDIDATES.items():
        set_aside = [model for model in candidates if model in aside]
        recommended = next((model for model in candidates if model not in aside), None)
        tasks[task] = {
            "default": TASK_DEFAULT.get(task, candidates[0] if candidates else ""),
            "candidates": candidates,
            "set_aside": set_aside,
            "recommended": recommended or (candidates[0] if candidates else ""),
        }
    return {"tasks": tasks, "set_aside_models": sorted(aside)}


def main() -> None:
    if "--cost-advice" in sys.argv[1:]:
        print(json.dumps(_cost_advice(), indent=2))
        return
    if os.environ.get("KILLR_SITE_INNER") != "1":
        tools = ROOT / "orchestrator"
        sys.path.insert(0, str(tools))
        spec = importlib.util.spec_from_file_location("orch_site", tools / "site.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.site(home_only="--all-pages" not in sys.argv[1:])
        return
    home_only = "--home" in sys.argv[1:]
    native = json.loads(NATIVE.read_text())["native"]
    plotting = _plotting(PLOTTING)
    packages = [_package(path) for path in sorted(PACKAGES.glob("*/translation.json"))]
    r_dependencies = _load_r_dependencies(packages)
    for package in packages:
        package["r_dependencies"] = r_dependencies.get(package["name"])
    crates = _merge_crates(
        [_crate(path) for path in sorted(CRATES.glob("*/crate.json"))],
        packages,
    )
    registry = {
        "native": native,
        "plotting": plotting,
        "packages": [_index_package(item) for item in packages],
        "crates": crates,
    }
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n")
    PAGE.write_text(_page(native, plotting, packages, crates))
    written = [REGISTRY.relative_to(ROOT), PAGE.relative_to(ROOT)]
    by_name = {item["name"]: item for item in packages}
    if home_only:
        refresh = [
            package
            for package in packages
            if _package_band(package) == "translating"
            or not (ROOT / "dashboard" / "packages" / f"{package['name']}.html").is_file()
        ]
        for package in refresh:
            destination = ROOT / "dashboard" / "packages" / f"{package['name']}.html"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(_package_page(package, crates, by_name))
            written.append(destination.relative_to(ROOT))
        print("wrote " + ", ".join(str(path) for path in written))
        return
    for package in packages:
        destination = ROOT / "dashboard" / "packages" / f"{package['name']}.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(_package_page(package, crates, {item["name"]: item for item in packages}))
        written.append(destination.relative_to(ROOT))
    print("wrote " + ", ".join(str(path) for path in written))


def _package(path: Path) -> dict:
    record = json.loads(path.read_text())
    functions = record["functions"]
    docs_dir = path.parent / "docs"
    for item in functions:
        doc_path = docs_dir / f"{item['name']}.json"
        item["doc"] = json.loads(doc_path.read_text()) if doc_path.exists() else None
    translated = [item for item in functions if item.get("translated")]
    loads = sorted({name for item in functions for name in item.get("loads", [])})
    return {
        "name": record["name"],
        "cran_version": record.get("cran_version") or "",
        "status": record["status"],
        "inventory": record.get("inventory", "complete"),
        "blocked_by": record.get("blocked_by", []),
        "strategy": record.get("strategy") or "",
        "resume": record["resume"],
        "dependencies": record["dependencies"] if isinstance(record.get("dependencies"), dict) else None,
        "coverage": len(translated) / len(functions) if functions else 0.0,
        "translated_count": len(translated),
        "total": len(functions),
        "translated_functions": [item["name"] for item in translated],
        "loads": loads,
        "crate_claims": record.get("crate_claims") or [],
        "checks": [_check(item) for item in translated if item.get("check")],
        "functions": functions,
        "translation": str(path.relative_to(ROOT)),
    }


def _index_package(package: dict) -> dict:
    return {
        "name": package["name"],
        "cran_version": package.get("cran_version") or "",
        "status": package["status"],
        "inventory": package.get("inventory", "complete"),
        "coverage": package["coverage"],
        "translated_functions": package["translated_functions"],
        "loads": package["loads"],
        "dependencies": package.get("dependencies"),
        "crate_claims": package.get("crate_claims") or [],
        "checks": [
            {
                "name": check["name"],
                "r_ms": check["r_ms"],
                "translated_ms": check["translated_ms"],
                "speedup": check["speedup"],
                "matches": check["matches"],
                "max_abs_diff": check["max_abs_diff"],
            }
            for check in package["checks"]
        ],
        "translation": package["translation"],
    }


def _check(item: dict) -> dict:
    check = item["check"]
    return {
        "name": item["name"],
        "case": check.get("case"),
        "r_ms": check.get("r_ms"),
        "translated_ms": check.get("translated_ms"),
        "speedup": check.get("speedup"),
        "matches": check.get("matches"),
        "max_abs_diff": check.get("max_abs_diff"),
        "proof": check.get("proof") or {},
    }


def _plotting(path: Path) -> dict:
    record = json.loads(path.read_text())
    return {
        "library": record["name"],
        "backend": record["backend"],
        "rule": record["rule"],
        "functions": record.get("functions", []),
        "path": str(path.relative_to(ROOT)),
    }


def _crate(path: Path) -> dict:
    record = json.loads(path.read_text())
    return {
        "name": record["name"],
        "origin": record["origin"],
        "loaded_by": record.get("loaded_by", []),
        "assigned": record.get("assigned") or "",
        "path": str(path.relative_to(ROOT)),
    }


def _merge_crates(crates: list, packages: list) -> list:
    by_name = {item["name"]: item for item in crates}
    for package in packages:
        for claim in package.get("crate_claims") or []:
            if isinstance(claim, str):
                claim = {"name": claim}
            name = claim["name"]
            existing = by_name.get(name)
            if existing is None:
                by_name[name] = {
                    "name": name,
                    "origin": claim.get("origin") or "",
                    "loaded_by": claim.get("loaded_by") or [package["name"]],
                    "assigned": claim.get("assigned") or "",
                    "path": "",
                }
                continue
            if claim.get("assigned") and not existing.get("assigned"):
                existing["assigned"] = claim["assigned"]
            if claim.get("origin") and not existing.get("origin"):
                existing["origin"] = claim["origin"]
    return [by_name[name] for name in sorted(by_name)]


def _package_band(package: dict) -> str:
    # A one-item inventory can be entirely translated while the rest of the
    # package is still missing. That stays in progress. A complete inventory
    # is finished when its status says so, or when every recorded name is checked.
    if package.get("inventory") == "incomplete":
        return "huge" if package.get("strategy") == "huge" else "translating"
    finished = package["status"] == "complete" or (
        package["total"] and package["translated_count"] == package["total"]
    )
    if finished:
        return "finished"
    if package.get("strategy") == "huge":
        return "huge"
    return "translating"


def _band_label(band: str) -> str:
    return {"finished": "finished", "translating": "in progress", "huge": "huge"}[band]


def _crate_libraries(crates: list) -> list[str]:
    names = []
    seen = set()
    for crate in crates:
        for name in crate.get("loaded_by") or []:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return sorted(names, key=str.lower)


def _using_crate_packages(packages: list, crates: list) -> list:
    names = set(_crate_libraries(crates))
    return [package for package in packages if package["name"] in names]


def _replacement_groups() -> list:
    if not CRAN_REPLACED.is_file():
        return []
    record = json.loads(CRAN_REPLACED.read_text())
    groups = record.get("strategies")
    if not isinstance(groups, list):
        return []
    return [group for group in groups if isinstance(group, dict) and group.get("library")]


def _replaced_count() -> int:
    names = set()
    for group in _replacement_groups():
        for name in group.get("packages") or []:
            names.add(name)
    return len(names)


def _in_progress(packages: list) -> list:
    excluded = set(_cran_excluded())
    return [package for package in packages if package["name"] not in excluded]


def _band_cards(packages: list, crates: list, discovered_huge: list, ready: list, waiting: list) -> str:
    active = _in_progress(packages)
    counts = {"finished": 0, "translating": 0, "huge": 0}
    for package in active:
        counts[_package_band(package)] += 1
    opened = {package["name"] for package in active if _package_band(package) == "huge"}
    huge_count = counts["huge"] + sum(1 for item in discovered_huge if item["name"] not in opened)
    items = (
        ("queue", len(ready) + len(waiting), "Downloaded, not started"),
        ("finished", counts["finished"], "Finished"),
        ("translating", counts["translating"], "In progress"),
        ("crates", len(_using_crate_packages(active, crates)), "Using crates"),
        ("replaced", len(_cran_excluded()), "Replaced"),
        ("huge", huge_count, "Huge"),
    )
    buttons = []
    for key, count, label in items:
        active = " active" if key == "translating" else ""
        buttons.append(
            f'<button type="button" data-band="{key}" class="stat{active}">'
            f"<strong>{count}</strong><span>{label}</span></button>"
        )
    buttons.append(
        '<button type="button" data-band="cost" class="stat">'
        "<strong>Cost</strong></button>"
    )
    return '<div class="stats" id="bands">' + "".join(buttons) + "</div>"


def _queue_band(ready: list, waiting: list) -> str:
    return (
        "<h2>Next</h2>\n"
        '<p class="note">The first 20 that are ready. Order is last-month downloads on the '
        "RStudio CRAN mirror, saved in rcran/importance.json. A dependency is opened before "
        "the package that needs it. A package with more than 200 exports is huge.</p>\n"
        f"{_queue_list(ready, None)}\n"
        "<h2>Waiting</h2>\n"
        '<p class="note">Still waiting on a dependency. That dependency comes first.</p>\n'
        f"{_queue_list(waiting, _waiting_note)}"
    )


def _queue_list(items: list, note_for) -> str:
    if not items:
        return '<p class="note">None yet.</p>'
    rows = []
    for item in items:
        extra = ""
        if note_for is not None:
            extra = note_for(item)
        rows.append(
            "<li>"
            f"<strong>{_esc(item['name'])}</strong> "
            f'<span class="note">{_esc(item.get("version") or "")}{extra}</span>'
            "</li>"
        )
    return '<ul class="finished wave">\n' + "\n".join(rows) + "\n</ul>"


def _waiting_note(item: dict) -> str:
    names = ", ".join(f"{_esc(name)} {state}" for name, state in item["blockers"])
    return f" · {names}"


def _cran_priority(packages: list) -> tuple[list, list, list]:
    catalog = _cran_catalog()
    importance = _importance_names()
    if not catalog or not importance:
        return [], [], []
    excluded = _cran_excluded()
    by_name = {package["name"]: package for package in packages}
    catalog_by = {}
    for item in catalog:
        catalog_by.setdefault(item["name"], item)
    cache = _read_deps_cache()
    changed = False
    seen = set()
    ready = []
    waiting = []
    huge = []

    def consider(name: str) -> None:
        nonlocal changed
        if name in seen or name in BASE_PACKAGES or name in excluded or name in by_name:
            return
        seen.add(name)
        item = catalog_by.get(name)
        if item is None:
            return
        version = item.get("version") or ""
        deps, wrote = _cached_dependencies(cache, name, version)
        changed = changed or wrote
        if deps is None:
            return
        blockers = _dependency_blockers(deps, by_name, excluded)
        for dep_name, state in blockers:
            if state == "not started":
                consider(dep_name)
        exports, wrote = _cached_exports(cache, name, version)
        changed = changed or wrote
        if exports > HUGE_EXPORTS:
            huge.append(item)
            return
        if blockers:
            waiting.append({**item, "blockers": blockers})
        else:
            ready.append(item)

    for name in importance:
        consider(name)
    if changed:
        _write_deps_cache(cache)
    return ready[:CRAN_NEXT], waiting, huge


def _importance_names() -> list:
    if not CRAN_IMPORTANCE.is_file():
        return []
    record = json.loads(CRAN_IMPORTANCE.read_text())
    downloads = record.get("downloads")
    if not isinstance(downloads, list):
        return []
    names = []
    for item in downloads:
        if isinstance(item, dict) and item.get("package"):
            names.append(item["package"])
    return names


def _cached_dependencies(cache: dict, name: str, version: str):
    key = f"{name}@{version}"
    deps = cache.get(key)
    if isinstance(deps, dict):
        return deps, False
    deps = _tarball_dependencies(name, version)
    if deps is None:
        return None, False
    cache[key] = deps
    return deps, True


def _cached_exports(cache: dict, name: str, version: str):
    key = f"exports:{name}@{version}"
    count = cache.get(key)
    if isinstance(count, int):
        return count, False
    count = _namespace_exports(name, version)
    cache[key] = count
    return count, True


def _namespace_exports(name: str, version: str) -> int:
    text = _tarball_text(name, version, "NAMESPACE")
    if text is None:
        return 0
    return text.count("export(") + text.count("exportMethods(") + text.count("S3method(")


def _dependency_blockers(deps: dict, by_name: dict, excluded: dict) -> list:
    names = []
    for key in ("depends", "imports"):
        for entry in deps.get(key) or []:
            name = entry.get("name")
            if name and name not in names:
                names.append(name)
    blockers = []
    for name in names:
        state = _dep_state(name, by_name, excluded)
        if state in ("in progress", "not started", "huge"):
            blockers.append((name, state))
    return blockers


def _dep_state(name: str, by_name: dict, excluded: dict) -> str:
    # A routed package is not a block, even when a translation folder is still on disk.
    if name in BASE_PACKAGES:
        return "base"
    if name in excluded:
        return "replaced"
    other = by_name.get(name)
    if other is None:
        return "not started"
    return _band_label(_package_band(other))


def _cran_excluded() -> dict:
    if not CRAN_REPLACED.is_file():
        return {}
    record = json.loads(CRAN_REPLACED.read_text())
    packages = record.get("packages")
    if not isinstance(packages, list):
        return {}
    return {
        item["name"]: item.get("reason") or ""
        for item in packages
        if isinstance(item, dict) and item.get("name")
    }


def _cran_catalog() -> list:
    if not CRAN_CATALOG.is_file():
        return []
    record = json.loads(CRAN_CATALOG.read_text())
    packages = record.get("packages")
    return packages if isinstance(packages, list) else []


def _deps_summary(package: dict, href_for, by_name: dict, excluded: dict) -> str:
    r_line = _r_dependency_line(package, by_name, excluded)
    deps = package.get("dependencies")
    if not isinstance(deps, dict):
        return r_line or '<p class="note">Dependencies are not recorded yet.</p>'
    translated = deps.get("translated") or []
    native = deps.get("native") or []
    rust = deps.get("rust") or []
    if not translated and not native and not rust:
        python_line = '<p class="note">Dependencies: there are none.</p>'
    else:
        parts = []
        if translated:
            names = ", ".join(
                f'<a href="{href_for(name)}">{_esc(name)}</a>' for name in translated
            )
            parts.append(f"{names} translated")
        if native:
            parts.append(f"{_esc(', '.join(native))} native")
        if rust:
            parts.append(f"{_esc(', '.join(rust))} rust")
        python_line = f'<p class="note">Dependencies · {" · ".join(parts)}</p>'
    blockers = _dependency_blockers(package.get("r_dependencies") or {}, by_name, excluded)
    if isinstance(package.get("r_dependencies"), dict) and blockers:
        return python_line + _blocker_line(blockers)
    return python_line


def _r_dependency_line(package: dict, by_name: dict, excluded: dict) -> str:
    deps = package.get("r_dependencies")
    if not isinstance(deps, dict):
        return ""
    blockers = _dependency_blockers(deps, by_name, excluded)
    if not blockers:
        return '<p class="note">R dependencies are finished or replaced.</p>'
    return _blocker_line(blockers)


def _blocker_line(blockers: list) -> str:
    text = ", ".join(f"{_esc(name)} {state}" for name, state in blockers)
    return f'<p class="note">R dependencies · {text}</p>'


def _dep_line(entry: dict, href_for, by_name: dict, excluded: dict) -> str:
    name = entry["name"]
    state = _dep_state(name, by_name, excluded)
    other = by_name.get(name)
    if other is not None:
        shown = f'<a href="{href_for(name)}">{_esc(name)}</a>'
    else:
        shown = _esc(name)
    status = "" if state == "base" else state
    notes = [part for part in (entry.get("constraint") or "", status) if part]
    note = f' <span class="note">{" · ".join(notes)}</span>' if notes else ""
    return f"<p>{shown}{note}</p>"


def _r_sections(package: dict, href_for, by_name: dict, excluded: dict) -> str:
    deps = package.get("r_dependencies")
    if not isinstance(deps, dict):
        return '<p class="note">The R dependencies could not be loaded.</p>'
    sections = (
        ("depends", "Depends"),
        ("imports", "Imports"),
        ("linking_to", "LinkingTo"),
    )
    rows = []
    for key, title in sections:
        entries = deps.get(key) or []
        if not entries:
            continue
        body = "".join(_dep_line(entry, href_for, by_name, excluded) for entry in entries)
        rows.append(f"<h3>{title}</h3>{body}")
    if not rows:
        return '<p class="note">None.</p>'
    return "".join(rows)


def _python_sections(package: dict, href_for, by_name: dict, excluded: dict) -> str:
    deps = package.get("dependencies")
    if not isinstance(deps, dict):
        return '<p class="note">Dependencies are not recorded yet.</p>'
    translated = deps.get("translated") or []
    native = deps.get("native") or []
    rust = deps.get("rust") or []
    rows = []
    if translated:
        body = "".join(
            _dep_line({"name": name, "constraint": ""}, href_for, by_name, excluded)
            for name in translated
        )
        rows.append(f"<h3>Packages</h3>{body}")
    if native:
        rows.append(f"<h3>Native</h3><p>{_esc(', '.join(native))}</p>")
    if rust:
        rows.append(f"<h3>Crates</h3><p>{_esc(', '.join(rust))}</p>")
    if not rows:
        return '<p class="note">There are none.</p>'
    return "".join(rows)


def _deps_tab(package: dict, href_for, by_name: dict, excluded: dict) -> str:
    left = _r_sections(package, href_for, by_name, excluded)
    right = _python_sections(package, href_for, by_name, excluded)
    return (
        '<div class="pair">'
        f'<article class="pane"><p class="kicker">R</p>{left}</article>'
        f'<article class="pane"><p class="kicker">Python and Rust</p>{right}</article>'
        "</div>"
    )


def _read_deps_cache() -> dict:
    if not R_DEPS_CACHE.is_file():
        return {}
    return json.loads(R_DEPS_CACHE.read_text())


def _write_deps_cache(cache: dict) -> None:
    R_DEPS_CACHE.write_text(json.dumps(cache, indent=2) + "\n")


def _load_r_dependencies(packages: list) -> dict:
    cache = _read_deps_cache()
    found = {}
    pending = []
    changed = False
    for package in packages:
        version = package.get("cran_version") or ""
        key = f"{package['name']}@{version}"
        tarball = _tarball_dependencies(package["name"], version)
        if tarball is not None:
            if cache.get(key) != tarball:
                cache[key] = tarball
                changed = True
            found[package["name"]] = tarball
            continue
        if key in cache:
            found[package["name"]] = cache[key]
            continue
        local = _local_r_dependencies(package["name"], version)
        if local is not None:
            cache[key] = local
            found[package["name"]] = local
            changed = True
            continue
        pending.append(package)
    if pending:
        with ThreadPoolExecutor(max_workers=8) as pool:
            fetched = list(pool.map(_crandb_dependencies, pending))
        for package, deps in zip(pending, fetched):
            if deps is None:
                found[package["name"]] = None
                continue
            cache[f"{package['name']}@{package.get('cran_version') or ''}"] = deps
            found[package["name"]] = deps
            changed = True
    if changed:
        _write_deps_cache(cache)
    return found


def _tarball_dependencies(name: str, version: str):
    fields = _tarball_description(name, version)
    if fields is None:
        return None
    recorded = (fields.get("Version") or "").strip()
    if recorded and recorded != version:
        return None
    return _dependency_record(fields.get("Depends", ""), fields.get("Imports", ""), fields.get("LinkingTo", ""))


def _tarball_text(name: str, version: str, filename: str):
    if not name or not version:
        return None
    path = ROOT / "rcran" / "contrib" / f"{name}_{version}.tar.gz"
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        with tarfile.open(path, "r:gz") as archive:
            member = None
            for item in archive:
                if item.name.endswith("/" + filename) and item.name.count("/") == 1:
                    member = item
                    break
            if member is None:
                return None
            raw = archive.extractfile(member)
            if raw is None:
                return None
            return raw.read().decode("utf-8", "replace")
    except (tarfile.TarError, OSError):
        return None


def _tarball_description(name: str, version: str):
    if not name or not version:
        return None
    path = ROOT / "rcran" / "contrib" / f"{name}_{version}.tar.gz"
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        with tarfile.open(path, "r:gz") as archive:
            try:
                member = archive.getmember(f"{name}/DESCRIPTION")
            except KeyError:
                member = None
                for item in archive:
                    if item.name.endswith("/DESCRIPTION") and item.name.count("/") == 1:
                        member = item
                        break
            if member is None:
                return None
            raw = archive.extractfile(member)
            if raw is None:
                return None
            return _dcf_fields(raw.read().decode("utf-8", "replace"))
    except (tarfile.TarError, OSError):
        return None


def _local_r_dependencies(name: str, version: str):
    if not version:
        return None
    for library in R_LIBRARIES:
        path = library / name / "DESCRIPTION"
        if not path.is_file():
            continue
        fields = _dcf_fields(path.read_text(errors="replace"))
        if fields.get("Version") != version:
            continue
        return _dependency_record(fields.get("Depends", ""), fields.get("Imports", ""), fields.get("LinkingTo", ""))
    return None


def _crandb_dependencies(package: dict):
    version = package.get("cran_version") or ""
    if not version:
        return None
    url = f"https://crandb.r-pkg.org/{package['name']}/{version}"
    request = urllib.request.Request(url, headers={"User-Agent": "KillCRAN dashboard"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            record = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    if record.get("Version") != version:
        return None
    return _dependency_record(record.get("Depends"), record.get("Imports"), record.get("LinkingTo"))


def _dependency_record(depends, imports, linking_to) -> dict:
    return {
        "depends": _dependency_entries(depends),
        "imports": _dependency_entries(imports),
        "linking_to": _dependency_entries(linking_to),
    }


def _dependency_entries(field) -> list:
    if not field:
        return []
    if isinstance(field, dict):
        rows = []
        for name, constraint in field.items():
            if name == "R":
                continue
            text = "" if not constraint or constraint == "*" else str(constraint)
            rows.append({"name": name, "constraint": text})
        return rows
    return _parse_dependency_text(str(field))


def _parse_dependency_text(text: str) -> list:
    rows = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "(" in part and part.endswith(")"):
            name, constraint = part.split("(", 1)
            name = name.strip()
            constraint = constraint[:-1].strip()
        else:
            name, constraint = part, ""
        if not name or name == "R":
            continue
        rows.append({"name": name, "constraint": constraint})
    return rows


def _dcf_fields(text: str) -> dict:
    fields = {}
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


def _finished_list(packages: list) -> str:
    items = []
    for package in packages:
        href = f"packages/{package['name']}.html"
        version = _esc(package.get("cran_version") or "")
        version_note = f' <span class="note">{version}</span>' if version else ""
        key = _esc(package["name"].lower())
        items.append(
            f'<li data-name="{key}"><a href="{href}">{_esc(package["name"])}</a>{version_note}</li>'
        )
    if not items:
        return '<p class="note">None yet.</p>'
    return (
        '<input id="finished-search" type="search" placeholder="Find a package" aria-label="Find a finished package">\n'
        '<ul class="finished" id="finished-list">\n' + "\n".join(items) + "\n</ul>"
    )


def _stand_ins() -> dict:
    found = {}
    for group in _replacement_groups():
        library = group.get("library") or ""
        for name in group.get("packages") or []:
            found[name] = library
    return found


def _checked_line(name: str, by_name: dict) -> str:
    package = by_name.get(name)
    label = _esc(name)
    if package is None:
        return f"{label} · not opened"
    percent = package["coverage"] * 100.0
    done = f"{package['translated_count']} of {package['total']} · {percent:.1f}%"
    names = package.get("translated_functions") or []
    shown = ", ".join(names[:8])
    if len(names) > 8:
        shown += f", and {len(names) - 8} more"
    extra = f" · {_esc(shown)}" if shown else ""
    return f"{label} · {_esc(done)}{extra}"


def _replaced_table(by_name: dict) -> str:
    groups = _replacement_groups()
    covered = set()
    rows = []
    for group in groups:
        names = [name for name in group.get("packages") or []]
        covered.update(names)
        library = group.get("library") or ""
        if library in RUST_STAND_INS:
            library_cell = f'{_esc(library)} <span class="rust">Rust</span>'
        else:
            library_cell = _esc(library)
        where = "<br>".join(_checked_line(name, by_name) for name in names)
        rows.append(
            "<tr>"
            f"<td>{library_cell}</td>"
            f"<td>{where}</td>"
            f"<td>{_esc(group.get('strategy') or '')}</td>"
            "</tr>"
        )
    for name, reason in sorted(_cran_excluded().items(), key=lambda item: item[0].lower()):
        if name in covered:
            continue
        rows.append(
            "<tr>"
            "<td>—</td>"
            f"<td>{_checked_line(name, by_name)}</td>"
            f"<td>{_esc(reason)}</td>"
            "</tr>"
        )
    if not rows:
        return '<p class="note">None.</p>'
    body = "\n".join(rows)
    return f"""<div class="card">
<table>
<thead><tr><th>Library</th><th>Where</th><th>Reason</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
</div>"""


def _native_block(native: list, plotting: dict) -> str:
    native_rows = "\n".join(_native_row(item) for item in native) or "<tr><td colspan='3'>No agreed native libraries yet.</td></tr>"
    plotting_rows = "\n".join(
        f"<tr><td>{_esc(name)}</td></tr>" for name in plotting.get("functions") or []
    ) or "<tr><td>No extension functions yet.</td></tr>"
    return f"""<h2>Agreed native libraries</h2>
<div class="card">
<table>
<thead><tr><th>Library</th><th>Role</th><th>Why</th></tr></thead>
<tbody>
{native_rows}
</tbody>
</table>
</div>
<h2>Plotting</h2>
<div class="card">
<p>{_esc(plotting.get("rule") or "")}</p>
<p class="note">{_esc(plotting.get("library") or "")} extends {_esc(plotting.get("backend") or "")}. Charts Matplotlib can draw in a few lines call Matplotlib directly.</p>
<table>
<thead><tr><th>killplot functions</th></tr></thead>
<tbody>
{plotting_rows}
</tbody>
</table>
</div>"""


def _crate_pitch(crates: list, by_name: dict) -> str:
    grouped: dict[str, list] = {}
    orphans = []
    for crate in crates:
        loaded = [name for name in crate.get("loaded_by") or [] if name]
        if not loaded:
            orphans.append(crate)
            continue
        for name in loaded:
            grouped.setdefault(name, []).append(crate)
    stand_ins = _stand_ins()
    rows = []
    for name in sorted(grouped, key=str.lower):
        rows.append(_crate_pitch_row(name, grouped[name], by_name, stand_ins))
    if orphans:
        rows.append(_crate_pitch_row("", orphans, by_name, stand_ins))
    if not rows:
        return '<p class="note">No Rust units yet.</p>'
    body = "\n".join(rows)
    return f"""<p class="note">{len([n for n in _crate_libraries(crates) if n in by_name and n not in set(_cran_excluded())])} packages use {len(crates)} Rust crates. One row is the R package, the crates made from it, and the stand-in when that package was also replaced.</p>
<div class="card">
<table>
<thead><tr><th>R package</th><th>Crates</th><th>Replaced by</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
</div>"""


def _crate_pitch_row(name: str, crates: list, by_name: dict, stand_ins: dict) -> str:
    if name and name in by_name:
        package_cell = f'<a href="packages/{_esc(name)}.html">{_esc(name)}</a>'
    elif name:
        package_cell = _esc(name)
    else:
        package_cell = "—"
    chips = " ".join(
        f'<span class="chip">{_esc(crate["name"])}</span>'
        for crate in sorted(crates, key=lambda item: item["name"].lower())
    )
    library = stand_ins.get(name) or ""
    if not library:
        stand = "—"
    elif library in RUST_STAND_INS:
        stand = f'{_esc(library)} <span class="rust">Rust</span>'
    else:
        stand = _esc(library)
    return f"<tr><td>{package_cell}</td><td><div class=\"chips\">{chips}</div></td><td>{stand}</td></tr>"


def _package_groups(
    packages: list,
    crates: list,
    discovered_huge: list,
    ready: list,
    waiting: list,
    native: list,
    plotting: dict,
) -> str:
    active = _in_progress(packages)
    by_name = {package["name"]: package for package in packages}
    excluded = _cran_excluded()
    using_names = {package["name"] for package in _using_crate_packages(active, crates)}
    sections = [
        f'<section class="band" id="band-queue">{_queue_band(ready, waiting)}</section>'
    ]
    for key in ("finished", "translating"):
        chosen = [item for item in active if _package_band(item) == key]
        shown = " active" if key == "translating" else ""
        if key == "finished":
            rows = _finished_list(chosen)
        else:
            rows = "\n".join(
                _package_section(item, by_name, excluded, using_names) for item in chosen
            )
            if not rows:
                rows = '<p class="note">None yet.</p>'
        sections.append(f'<section class="band{shown}" id="band-{key}">{rows}</section>')
    sections.append(
        f'<section class="band" id="band-crates">{_crate_pitch(crates, by_name)}</section>'
    )
    sections.append(
        '<section class="band" id="band-replaced">'
        '<p class="note">A named library stands in. It is not a check against R. Rust is marked.</p>\n'
        + _replaced_table(by_name)
        + _native_block(native, plotting)
        + "</section>"
    )
    sections.append(
        '<section class="band" id="band-huge">'
        + _huge_band(packages, discovered_huge, by_name, excluded, using_names)
        + "</section>"
    )
    sections.append(f'<section class="band" id="band-cost">{_yield_panel()}</section>')
    return "\n".join(sections)


def _huge_band(packages: list, discovered_huge: list, by_name: dict, excluded: dict, using_names: set) -> str:
    opened = [package for package in packages if _package_band(package) == "huge"]
    opened_names = {package["name"] for package in opened}
    cards = "\n".join(
        _package_section(package, by_name, excluded, using_names) for package in opened
    )
    items = []
    for item in discovered_huge:
        if item["name"] in opened_names:
            continue
        version = item.get("version") or ""
        note = f' <span class="note">{_esc(version)}</span>' if version else ""
        items.append(f"<li>{_esc(item['name'])}{note}</li>")
    listing = '<ul class="finished">\n' + "\n".join(items) + "\n</ul>" if items else ""
    if not cards and not listing:
        return '<p class="note">None yet.</p>'
    return (
        '<p class="note">More than 200 exports. A stand-in has not been asked yet. A task force waits until that check says there is no stand-in.</p>\n'
        + cards
        + listing
    )


def _skip_r_string(text: str, index: int, quote: str) -> int:
    index += 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    return index


def _match_r_span(text: str, open_at: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    index = open_at
    while index < len(text):
        char = text[index]
        if char == "#":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if char in ("'", '"'):
            index = _skip_r_string(text, index, char)
            continue
        if char == open_ch:
            depth += 1
        elif char == close_ch:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def _r_function_lines(text: str, start: int, function_end: int) -> int:
    paren = text.find("(", function_end - len("function"))
    if paren < 0:
        return 1
    after_args = _match_r_span(text, paren, "(", ")")
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
        end = _match_r_span(text, after_args + index, "{", "}")
    else:
        newline = text.find("\n", after_args)
        end = len(text) if newline < 0 else newline
    body = text[start:end]
    return body.count("\n") + (0 if body.endswith("\n") else 1) if body else 0


def count_r_lines(name: str, version: str, function: str) -> int:
    """Line count of one function body in the package tarball. Zero when it is not found."""
    if not name or not version or not function:
        return 0
    path = ROOT / "rcran" / "contrib" / f"{name}_{version}.tar.gz"
    if not path.is_file() or path.stat().st_size == 0:
        return 0
    try:
        with tarfile.open(path, "r:gz") as archive:
            sources = []
            for item in archive:
                parts = item.name.split("/")
                if len(parts) != 3 or parts[1] != "R":
                    continue
                if not parts[2].lower().endswith((".r", ".s")):
                    continue
                raw = archive.extractfile(item)
                if raw is not None:
                    sources.append(raw.read().decode("utf-8", "replace"))
    except (tarfile.TarError, OSError):
        return 0
    text = "\n".join(sources)
    quoted = re.escape(function)
    name = rf"(?:`{quoted}`|\"{quoted}\"|'{quoted}'|{quoted})"
    direct = re.compile(rf"(?<![\w.]){name}\s*(?:<-|=)\s*function\b")
    found = direct.search(text)
    if found is not None:
        return _r_function_lines(text, found.start(), found.end())
    assign = re.compile(rf"(?m)^[ \t]*{name}\s*(?:<-|=)")
    found = assign.search(text)
    if found is None:
        return 0
    rest = text[found.end() :]
    if re.match(r"\s*[A-Za-z.][\w.]*\s*<-\s*function\b", rest):
        return 1
    stripped = rest.lstrip()
    if stripped.startswith(("list(", "c(", "structure(", "matrix(", "array(")):
        start = found.end() + (len(rest) - len(stripped)) + stripped.find("(")
        end = _match_r_span(text, start, "(", ")")
        body = text[found.start() : end]
        return body.count("\n") + (0 if body.endswith("\n") else 1) if body else 1
    newline = text.find("\n", found.end())
    end = len(text) if newline < 0 else newline
    body = text[found.start() : end]
    return max(body.count("\n") + (0 if body.endswith("\n") else 1), 1)


def _load_launches() -> list:
    if not LAUNCHES.is_file():
        return []
    try:
        payload = json.loads(LAUNCHES.read_text())
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _record_number(record: dict, key: str, default: float = 0) -> float:
    try:
        return float(record.get(key, default) or 0)
    except (TypeError, ValueError):
        return default


def _matched_lines(record: dict) -> float:
    if "matched_lines" in record:
        return _record_number(record, "matched_lines")
    matched = record.get("matched")
    if matched is True or matched == 1:
        return _record_number(record, "r_lines")
    return 0


def _matched_functions(record: dict) -> float:
    matched = record.get("matched")
    if isinstance(matched, bool):
        return 1 if matched else 0
    if matched is None:
        return 1 if _matched_lines(record) else 0
    return _record_number(record, "matched")


def _function_count(record: dict) -> float:
    if "functions" in record:
        return max(_record_number(record, "functions"), 0)
    return 1


def _yield_of(records: list) -> float:
    weighted_minutes = 0.0
    matched = 0.0
    for record in records:
        weight = MODEL_WEIGHT.get(record.get("model") or "", 1)
        weighted_minutes += weight * _record_number(record, "minutes")
        matched += _matched_lines(record)
    if weighted_minutes <= 0:
        return 0
    return matched / weighted_minutes


def _launch_task(task: str) -> str:
    if task == "hard-opus":
        return "hard-retry"
    return task


def _set_aside(records: list) -> set:
    by_task: dict[str, dict[str, list]] = {}
    for record in records:
        task = _launch_task(record.get("task") or "")
        model = record.get("model") or ""
        by_task.setdefault(task, {}).setdefault(model, []).append(record)
    aside = set()
    for task, models in by_task.items():
        candidates = TASK_CANDIDATES.get(task, [])
        for model, batches in models.items():
            if len(batches) < 5 or model not in candidates:
                continue
            own = _yield_of(batches)
            for cheaper in candidates:
                if MODEL_WEIGHT.get(cheaper, 99) >= MODEL_WEIGHT.get(model, 99):
                    continue
                other = models.get(cheaper) or []
                if other and _yield_of(other) > own:
                    aside.add(model)
    return aside


def _running_cost(records: list) -> list:
    ordered = sorted(records, key=lambda record: record.get("returned") or "")
    weighted_minutes = 0.0
    matched = 0.0
    points = []
    for record in ordered:
        weight = MODEL_WEIGHT.get(record.get("model") or "", 1)
        weighted_minutes += weight * _record_number(record, "minutes")
        matched += _matched_lines(record)
        if weighted_minutes > 0 and matched > 0:
            points.append((record.get("returned") or "", matched / weighted_minutes))
    return points


def _model_rows(records: list) -> list:
    aside = _set_aside(records)
    grouped: dict[str, list] = {}
    for record in records:
        model = record.get("model") or ""
        if model:
            grouped.setdefault(model, []).append(record)
    rows = []
    for model, batches in grouped.items():
        minutes = sum(_record_number(record, "minutes") for record in batches)
        lines = sum(_record_number(record, "r_lines") for record in batches)
        functions = sum(_function_count(record) for record in batches)
        matched = sum(_matched_functions(record) for record in batches)
        rows.append({
            "model": model,
            "speed": (lines / minutes) if minutes else 0,
            "success": (matched / functions) if functions else 0,
            "yield": _yield_of(batches),
            "aside": model in aside,
        })
    rows.sort(key=lambda row: row["yield"], reverse=True)
    return rows


def _axis_number(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"


def _clock_label(stamp: str) -> str:
    text = (stamp or "").replace("T", " ")
    return text[5:16] if len(text) >= 16 else text


def _model_label(model: str) -> str:
    return MODEL_LABEL.get(model, (model or "").split("-")[0] or model)


def _cost_curve(points: list, model: str = "") -> str:
    if not points:
        return '<p class="note">The curve starts when a batch returns.</p>'
    width, height = 480, 260
    left, right, top, bottom = 78, 28, 18, 52
    values = [point[1] for point in points]
    if max(values) - min(values) < 0.05:
        low = 0.0
        high = max(values[0] * 1.35, 1.0)
    else:
        pad = (max(values) - min(values)) * 0.15
        low = max(0.0, min(values) - pad)
        high = max(values) + pad
    span = high - low or 1
    plot_width = width - left - right
    plot_height = height - top - bottom

    def x_at(index: int) -> float:
        if len(points) == 1:
            return left + plot_width / 2
        return left + plot_width * index / (len(points) - 1)

    def y_at(value: float) -> float:
        return top + plot_height * (1 - (value - low) / span)

    marks = [f"{x_at(index):.1f},{y_at(point[1]):.1f}" for index, point in enumerate(points)]
    if len(points) == 1:
        x, y = marks[0].split(",")
        series = (
            f'<circle cx="{x}" cy="{y}" r="5" fill="#2f6f4e"/>'
            f'<text x="{float(x) + 8:.1f}" y="{float(y) - 8:.1f}" fill="#1c1915" font-size="12">'
            f"{_axis_number(values[0])}</text>"
        )
    else:
        series = f'<polyline fill="none" stroke="#2f6f4e" stroke-width="2" points="{" ".join(marks)}"/>'
    ticks = []
    for fraction, value in ((0, low), (0.5, low + span / 2), (1, high)):
        y = y_at(value)
        ticks.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#5c564e"/>'
            f'<text x="{left - 8}" y="{y + 4:.1f}" fill="#5c564e" font-size="11" text-anchor="end">'
            f"{_axis_number(value)}</text>"
        )
    start = _esc(_clock_label(points[0][0]))
    end = _esc(_clock_label(points[-1][0]))
    axis_y = height - bottom
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(_model_label(model))} R lines per minute over time">'
        f'<text fill="#5c564e" font-size="12" text-anchor="middle" '
        f'transform="translate(16, {top + plot_height / 2:.0f}) rotate(-90)">R lines per minute</text>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{axis_y}" stroke="#5c564e"/>'
        f'<line x1="{left}" y1="{axis_y}" x2="{width - right}" y2="{axis_y}" stroke="#5c564e"/>'
        f'{"".join(ticks)}'
        f"{series}"
        f'<text x="{left}" y="{axis_y + 16}" fill="#5c564e" font-size="11">{start}</text>'
        f'<text x="{width - right}" y="{axis_y + 16}" fill="#5c564e" font-size="11" text-anchor="end">{end}</text>'
        f'<text x="{left + plot_width / 2:.0f}" y="{height - 8}" fill="#5c564e" font-size="12" text-anchor="middle">Time</text>'
        "</svg>"
    )


def _yield_rows(rows: list) -> str:
    if not rows:
        return '<p class="note">No model has a finished batch yet.</p>'
    width = 440
    row_height = 28
    height = row_height * len(rows) + 28
    fastest = max(row["speed"] for row in rows) or 1
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="R lines per minute by model">',
        '<text x="88" y="14" fill="#5c564e" font-size="12">R lines per minute</text>',
    ]
    for index, row in enumerate(rows):
        y = 24 + index * row_height
        bar_x = 88
        bar_width = 220
        length = bar_width * row["speed"] / fastest
        filled = length * row["success"]
        label = _model_label(row["model"])
        mark = " set aside" if row["aside"] else ""
        parts.append(
            f'<text x="0" y="{y + 12}" fill="#1c1915" font-size="12">{_esc(label)}</text>'
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="14" rx="7" fill="#efe8dc"/>'
            f'<rect x="{bar_x}" y="{y}" width="{length:.1f}" height="14" rx="7" fill="#e4ddd2"/>'
            f'<rect x="{bar_x}" y="{y}" width="{filled:.1f}" height="14" rx="7" fill="#2f6f4e"/>'
            f'<text x="{bar_x + bar_width + 8}" y="{y + 12}" fill="#5c564e" font-size="11">'
            f'{row["yield"]:.1f}{_esc(mark)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _model_curves(records: list) -> str:
    grouped: dict[str, list] = {}
    for record in records:
        model = record.get("model") or ""
        if model:
            grouped.setdefault(model, []).append(record)
    if not grouped:
        return '<p class="note">The curve starts when a batch returns.</p>'
    parts = []
    for model in sorted(grouped, key=lambda name: min(record.get("returned") or "" for record in grouped[name])):
        points = _running_cost(grouped[model])
        if not points:
            continue
        parts.append(
            f"<h3>{_esc(_model_label(model))}</h3>{_cost_curve(points, model)}"
        )
    return "".join(parts) or '<p class="note">The curve starts when a batch returns.</p>'


def _model_totals(records: list) -> list:
    grouped: dict[str, list] = {}
    for record in records:
        model = record.get("model") or ""
        if model:
            grouped.setdefault(model, []).append(record)
    rows = []
    for model, batches in grouped.items():
        rows.append({
            "model": model,
            "batches": len(batches),
            "minutes": sum(_record_number(record, "minutes") for record in batches),
            "attempted": sum(_record_number(record, "r_lines") for record in batches),
            "matched": sum(_matched_lines(record) for record in batches),
            "functions": sum(_function_count(record) for record in batches),
            "matched_functions": sum(_matched_functions(record) for record in batches),
        })
    rows.sort(key=lambda row: row["matched"], reverse=True)
    return rows


def _totals_table(records: list) -> str:
    rows = _model_totals(records)
    if not rows:
        return ""

    def share(part: float, whole: float) -> str:
        return f"{100 * part / whole:.0f}%" if whole else "&ndash;"

    def speed(lines: float, minutes: float) -> str:
        return f"{lines / minutes:.1f}" if minutes else "&ndash;"

    body = []
    for row in rows:
        body.append(
            f"<tr><td>{_esc(_model_label(row['model']))}</td>"
            f"<td>{row['batches']}</td>"
            f"<td>{row['attempted']:.0f}</td>"
            f"<td>{row['matched']:.0f}</td>"
            f"<td>{share(row['matched'], row['attempted'])}</td>"
            f"<td>{share(row['matched_functions'], row['functions'])}</td>"
            f"<td>{speed(row['attempted'], row['minutes'])}</td></tr>"
        )
    total = {key: sum(row[key] for row in rows) for key in ("batches", "minutes", "attempted", "matched", "functions", "matched_functions")}
    body.append(
        f"<tr><td><strong>All models</strong></td>"
        f"<td><strong>{total['batches']}</strong></td>"
        f"<td><strong>{total['attempted']:.0f}</strong></td>"
        f"<td><strong>{total['matched']:.0f}</strong></td>"
        f"<td><strong>{share(total['matched'], total['attempted'])}</strong></td>"
        f"<td><strong>{share(total['matched_functions'], total['functions'])}</strong></td>"
        f"<td><strong>{speed(total['attempted'], total['minutes'])}</strong></td></tr>"
    )
    return (
        '<table class="model-totals">'
        "<thead><tr><th>Model</th><th>Batches</th><th>R lines attempted</th>"
        "<th>R lines translated</th><th>Line success</th><th>Function success</th>"
        "<th>R lines per minute</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _yield_panel() -> str:
    records = _load_launches()
    if not records:
        return (
            "<h2>Cost</h2>"
            '<p class="note">Each chart is one model, in R lines per minute. '
            "The curve starts when a batch returns.</p>"
        )
    return (
        "<h2>Cost</h2>"
        '<p class="note">Each chart is one model. Higher is better. '
        "A heavier model counts as more minutes, so the same lines sit lower, and a proof that fails pulls that model\'s line down. "
        "Green is the share that matched.</p>"
        f"{_totals_table(records)}"
        '<div class="yield-grid">'
        f"<div>{_model_curves(records)}</div>"
        f"<div>{_yield_rows(_model_rows(records))}</div>"
        "</div>"
    )


def _page(native: list, plotting: dict, packages: list, crates: list) -> str:
    ready, waiting, discovered_huge = _cran_priority(packages)
    package_groups = _package_groups(
        packages, crates, discovered_huge, ready, waiting, native, plotting
    ) if packages else "<p>No packages yet.</p>"
    stats = _band_cards(packages, crates, discovered_huge, ready, waiting) if packages else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KillCRAN</title>
<style>
:root {{
  color-scheme: light;
  --ink: #1c1915;
  --muted: #5c564e;
  --line: #e4ddd2;
  --paper: #f7f4ee;
  --card: #fffdf9;
  --done: #2f6f4e;
  --wait: #8a5a12;
  --bar: #2f6f4e;
  --r: #8d5a3c;
  --py: #2c5f8a;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font: 16px/1.5 "Iowan Old Style", "Palatino Linotype", Palatino, serif;
  color: var(--ink);
  background: var(--paper);
}}
main {{ max-width: 980px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
h1 {{ font-size: 2rem; font-weight: 600; margin: 0 0 0.25rem; }}
h2 {{ font-size: 1.25rem; margin: 2.25rem 0 0.75rem; }}
p.lead {{ color: var(--muted); margin-top: 0; }}
section.card {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem 1.1rem 1.2rem;
  margin-top: 1rem;
}}
.coverage {{
  display: flex; align-items: center; gap: 0.75rem; margin: 0.6rem 0;
}}
.track {{
  flex: 1; height: 10px; background: #efe8dc; border-radius: 99px; overflow: hidden;
}}
.fill {{ height: 100%; background: var(--bar); }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
th, td {{ text-align: left; padding: 0.45rem 0.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ color: var(--muted); font-weight: 600; font-size: 0.8rem; letter-spacing: 0.02em; }}
.yes {{ color: var(--done); font-weight: 600; }}
.no {{ color: var(--wait); font-weight: 600; }}
.note {{ color: var(--muted); }}
.rust {{ color: #9a3412; font-weight: 700; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
.chip {{
  color: #9a3412; font-weight: 700; font-size: 0.85rem;
  background: #f4ebe4; border-radius: 99px; padding: 0.05rem 0.5rem;
}}
.diff {{ white-space: nowrap; }}
.bars {{ display: grid; gap: 0.25rem; min-width: 8rem; }}
.bars span {{
  display: block; height: 8px; border-radius: 99px;
}}
.bars .r {{ background: var(--r); }}
.bars .py {{ background: var(--py); }}
.legend {{ color: var(--muted); font-size: 0.85rem; }}
.legend i {{
  display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 2px; margin-right: 0.2rem;
}}
.legend .r {{ background: var(--r); }}
.legend .py {{ background: var(--py); }}
a {{ color: inherit; }}
a:hover {{ color: var(--done); }}
ul.finished {{ list-style: none; padding: 0; margin: 0.25rem 0 0; }}
ul.finished li {{ padding: 0.35rem 0; border-bottom: 1px solid var(--line); }}
ul.finished li p {{ margin: 0.15rem 0 0; }}
ul.wave {{
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 0.2rem 0.9rem; margin-top: 0.6rem;
}}
.stats {{ display: flex; flex-wrap: nowrap; gap: 0.75rem; margin: 1.1rem 0 0.25rem; }}
.stats .stat, .stats button {{
  flex: 1 1 0; min-width: 0; background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 0.7rem 0.8rem 0.85rem; text-align: left;
}}
.stats button {{ font: inherit; cursor: pointer; }}
.stats button.active {{ background: var(--ink); border-color: var(--ink); }}
.stats strong {{ display: block; font-size: 1.6rem; line-height: 1.1; color: var(--done); }}
.stats span {{ color: var(--muted); font-size: 0.85rem; }}
.stats button.active strong, .stats button.active span {{ color: var(--paper); }}
.yield-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; align-items: start; }}
.yield-grid svg {{ width: 100%; height: auto; }}
.band {{ display: none; }}
.band.active {{ display: block; }}
#finished-search {{
  font: inherit; width: 100%; margin: 0.9rem 0 0.2rem; padding: 0.4rem 0.65rem;
  border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--ink);
}}
</style>
</head>
<body>
<main>
<h1>KillCRAN</h1>
<p class="lead">CRAN functions are translated to Python. Fortran and numerical C are translated to Rust, and that is the part to notice. A package that is not translated is replaced by a named library, and that library is not a check against R.</p>
{stats}
{package_groups}
</main>
<script>
const bands = ["queue", "finished", "translating", "crates", "replaced", "huge", "cost"];
function fromHash() {{
  const name = decodeURIComponent(location.hash.replace(/^#/, ""));
  selectBand(bands.includes(name) ? name : "translating");
}}
function selectBand(band) {{
  for (const button of document.querySelectorAll("#bands button")) {{
    button.classList.toggle("active", button.dataset.band === band);
  }}
  for (const section of document.querySelectorAll(".band")) {{
    section.classList.toggle("active", section.id === "band-" + band);
  }}
}}
for (const button of document.querySelectorAll("#bands button")) {{
  button.addEventListener("click", () => {{
    const band = button.dataset.band;
    if (location.hash === "#" + band) selectBand(band);
    else location.hash = band;
  }});
}}
function bindListSearch(inputId, listId) {{
  const input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener("input", () => {{
    const query = input.value.trim().toLowerCase();
    for (const item of document.querySelectorAll("#" + listId + " li")) {{
      item.hidden = Boolean(query) && !item.dataset.name.includes(query);
    }}
  }});
}}
bindListSearch("finished-search", "finished-list");
window.addEventListener("hashchange", fromHash);
fromHash();
</script>
</body>
</html>
"""


def _coverage_note(package: dict) -> str:
    blocked = ", ".join(package["blocked_by"]) or "none"
    status = _esc(package["status"])
    percent = package["coverage"] * 100.0
    return (
        f"{package['translated_count']} of {package['total']} functions · {percent:.1f}%"
        f" · {status} · blocked by {_esc(blocked)}"
    )


def _coverage_bar(package: dict) -> str:
    if not package["total"]:
        return ""
    percent = package["coverage"] * 100.0
    return (
        f'<div class="coverage"><div class="track"><div class="fill" style="width:{percent:.1f}%"></div></div>'
        f"<strong>{percent:.1f}%</strong></div>"
    )


def _package_section(package: dict, by_name: dict, excluded: dict, rust_names: set) -> str:
    href = f"packages/{package['name']}.html"
    version = _esc(package.get("cran_version") or "")
    version_note = f' <span class="note">{version}</span>' if version else ""
    strategy = package.get("strategy") or ""
    strategy_note = f' <span class="note">{_esc(strategy)}</span>' if strategy else ""
    rust = (
        ' <span class="rust">Rust</span>'
        if package["name"] in rust_names or package.get("crate_claims")
        else ""
    )
    return f"""
<section class="card">
<h2 style="margin-top:0"><a href="{href}">{_esc(package["name"])}</a>{version_note}{strategy_note}{rust}</h2>
<p>{_esc(package["resume"])}</p>
<p class="note">{_coverage_note(package)}</p>
{_coverage_bar(package)}
{_deps_summary(package, lambda name: f"packages/{name}.html", by_name, excluded)}
</section>
"""


def _index_table(package: dict, crates: list, by_name: dict) -> str:
    excluded = _cran_excluded()
    rows = "\n".join(_function_row(item, by_name, excluded) for item in package["functions"])
    return f"""<table>
<thead><tr><th>Function</th><th>Status</th><th>Working</th><th>Depends</th><th>Notes</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
<h2 style="margin-top:1.4rem">Crates</h2>
{_crate_table(package, crates)}"""


def _crate_table(package: dict, crates: list) -> str:
    by_name = {item["name"]: item for item in crates}
    names = list(package["loads"])
    for claim in package.get("crate_claims") or []:
        claim_name = claim if isinstance(claim, str) else claim["name"]
        if claim_name not in names:
            names.append(claim_name)
    shown = [by_name[name] for name in names if name in by_name]
    if not shown:
        return '<p class="note">This package loads no Rust crates.</p>'
    rows = "\n".join(
        f"<tr><td>{_esc(item['name'])}</td><td>{_esc(item['origin'])}</td>"
        f"<td>{_agent_cell(item.get('assigned') or '')}</td></tr>"
        for item in shown
    )
    return f"""<table>
<thead><tr><th>Crate</th><th>Fortran origin</th><th>Blocked</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>"""


def _comparison_table(package: dict) -> str:
    rows = "\n".join(_check_row(check) for check in package["checks"])
    if not rows:
        rows = "<tr><td colspan='8'>None have been compared yet.</td></tr>"
    proofs = [
        {
            "name": check["name"],
            "r": (check.get("proof") or {}).get("r") or "",
            "python": (check.get("proof") or {}).get("python") or "",
        }
        for check in package["checks"]
        if (check.get("proof") or {}).get("r")
    ]
    payload = json.dumps(proofs, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<p class="legend"><i class="r"></i> R &nbsp; <i class="py"></i> translated</p>
<table>
<thead><tr><th>Function</th><th>Case</th><th>R ms</th><th>Translated ms</th><th>Speedup</th><th>Result</th><th>Max abs diff</th><th></th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
<div id="proof" class="proof" hidden>
<p class="note">One untimed call, then the median of 20 timings, in milliseconds. R uses Sys.time(). Python uses time.perf_counter().</p>
<div class="pair">
<article class="pane"><p class="kicker">R</p><pre id="proof-r"></pre></article>
<article class="pane"><p class="kicker">Python</p><pre id="proof-py"></pre></article>
</div>
</div>
<script type="application/json" id="proof-data">{payload}</script>"""


def _function_row(item: dict, by_name: dict, excluded: dict) -> str:
    depends, unsolved = _function_depends(item, by_name, excluded)
    if item.get("translated"):
        status = "<span class='yes'>translated</span>"
        uses = ", ".join(item.get("uses") or [])
        note = item.get("done") or ""
        if uses:
            note = f"{note} Uses {uses}."
    else:
        note = item.get("not_done") or ""
        if note.startswith("Left"):
            status = "<span class='note'>left</span>"
        elif note.startswith("Dataset"):
            status = "<span class='note'>not copied</span>"
        elif unsolved:
            status = "<span class='no'>waiting</span>"
        else:
            status = "<span class='yes'>ready</span>"
    working = "<span class='no'>working</span>" if item.get("assigned") else "—"
    href = f"#{item['name']}"
    return (
        f"<tr><td><a href=\"{href}\">{_esc(item['name'])}</a></td>"
        f"<td>{status}</td><td>{working}</td><td>{_esc(depends)}</td><td>{_esc(note)}</td></tr>"
    )


def _function_depends(item: dict, by_name: dict, excluded: dict) -> tuple[str, bool]:
    names = list(item.get("loads") or [])
    for name in item.get("blocked_by") or []:
        if name not in names:
            names.append(name)
    if not names:
        return "none", False
    parts = []
    unsolved = False
    for name in names:
        state = _dep_state(name, by_name, excluded)
        if state in ("finished", "replaced", "base"):
            parts.append(f"{name} solved")
        else:
            unsolved = True
            parts.append(f"{name} not yet")
    return ", ".join(parts), unsolved


def _check_row(check: dict) -> str:
    slower = max(
        [value for value in (check["r_ms"], check["translated_ms"]) if value is not None],
        default=None,
    )
    bars = []
    if check["r_ms"] is not None and slower:
        bars.append(f"<span class='r' style='width:{100.0 * check['r_ms'] / slower:.1f}%'></span>")
    if check["translated_ms"] is not None and slower:
        bars.append(
            f"<span class='py' style='width:{100.0 * check['translated_ms'] / slower:.1f}%'></span>"
        )
    if check["matches"] is True:
        result = "<span class='yes'>matches</span>"
    elif check["matches"] is False:
        result = "<span class='no'>differs</span>"
    else:
        result = "<span class='note'>not compared</span>"
    diff = "—" if check["max_abs_diff"] is None else f"{check['max_abs_diff']:.3g}"
    pace = _pace(check)
    proof = check.get("proof") or {}
    if proof.get("r") and proof.get("python"):
        pace = (
            f'<button type="button" class="proof-toggle" data-name="{_esc(check["name"])}">'
            f"{pace}</button>"
        )
    return (
        "<tr>"
        f"<td>{_esc(check['name'])}</td>"
        f"<td>{_esc(check['case'] or '')}</td>"
        f"<td>{_num(check['r_ms'])}</td>"
        f"<td>{_num(check['translated_ms'])}</td>"
        f"<td>{pace}</td>"
        f"<td>{result}</td>"
        f"<td class='diff'>{diff}</td>"
        f"<td><div class='bars'>{''.join(bars)}</div></td>"
        "</tr>"
    )


def _agent_cell(assigned: str) -> str:
    if not assigned:
        return "—"
    return f"<span class='no'>{_esc(assigned)}</span>"


def _native_row(item: dict) -> str:
    return f"<tr><td>{_esc(item['name'])}</td><td>{_esc(item['role'])}</td><td>{_esc(item['why'])}</td></tr>"


def _pace(check: dict) -> str:
    r_ms = check.get("r_ms")
    translated_ms = check.get("translated_ms")
    if not r_ms or not translated_ms:
        return "—"
    percent = (r_ms / translated_ms - 1.0) * 100.0
    if percent > 0:
        return f"<span class='yes'>+{percent:.0f}%</span>"
    if percent < 0:
        return f"<span class='slower'>{percent:.0f}%</span>"
    return "<span class='note'>0%</span>"


def _num(value) -> str:
    if value is None:
        return "—"
    return f"{value:.3g}"


def _side_with_output(side, docs_dir: Path):
    if not isinstance(side, dict):
        return side
    side = dict(side)
    relative = side.get("output")
    paths = relative if isinstance(relative, list) else ([relative] if relative else [])
    blocks = []
    for item in paths:
        path = docs_dir / item
        if not path.exists():
            continue
        text = path.read_text()
        if path.suffix == ".svg":
            start = text.find("<svg")
            blocks.append({"svg": text[start:] if start >= 0 else text})
        else:
            blocks.append({"text": text.rstrip("\n")})
    side["output_blocks"] = blocks
    return side


def _esc(value: str) -> str:
    return html.escape(str(value))


def _recorded_side(item: dict, key: str, docs_dir: Path, description: str, usage: str):
    recorded = item.get(key)
    if not isinstance(recorded, dict):
        recorded = {}
    side = {}
    if description:
        side["description"] = description
    if usage:
        side["usage"] = usage
    if recorded.get("output"):
        side["output"] = recorded["output"]
    if not side:
        return None
    return _side_with_output(side, docs_dir)


def _package_page(package: dict, crates: list, by_name: dict) -> str:
    docs_dir = (ROOT / package["translation"]).parent / "docs"
    entries = []
    for item in package["functions"]:
        doc = item.get("doc") or {}
        origin = _side_with_output(doc.get("origin"), docs_dir)
        translation = _side_with_output(doc.get("translation"), docs_dir)
        if item.get("translated"):
            if not translation:
                translation = _recorded_side(
                    item, "translation", docs_dir, item.get("done") or "Checked.", item.get("python") or ""
                )
            if not origin:
                origin = _recorded_side(item, "origin", docs_dir, "", "")
        entries.append(
            {
                "name": item["name"],
                "translated": bool(item.get("translated")),
                "not_done": item.get("not_done") or "",
                "title": doc.get("title") or item["name"],
                "origin": origin,
                "translation": translation,
            }
        )
    data = json.dumps(entries, ensure_ascii=False).replace("<", "\\u003c")
    page = _PACKAGE_PAGE
    replacements = {
        "__NAME__": html.escape(package["name"]),
        "__VERSION__": html.escape(package.get("cran_version") or ""),
        "__RESUME__": html.escape(package["resume"]),
        "__COVERAGE__": f'<p class="note">{_coverage_note(package)}</p>\n{_coverage_bar(package)}',
        "__DEPS__": _deps_tab(package, lambda name: f"{name}.html", by_name, _cran_excluded()),
        "__INDEX__": _index_table(package, crates, by_name),
        "__COMPARISON__": _comparison_table(package),
        "__DATA__": data,
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


_PACKAGE_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ · KillCRAN</title>
<style>
:root {
  color-scheme: light;
  --ink: #1c1915;
  --muted: #5c564e;
  --line: #e4ddd2;
  --paper: #f7f4ee;
  --card: #fffdf9;
  --done: #2f6f4e;
  --wait: #8a5a12;
  --r: #8d5a3c;
  --py: #2c5f8a;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font: 16px/1.5 "Iowan Old Style", "Palatino Linotype", Palatino, serif;
  color: var(--ink);
  background: var(--paper);
}
main { max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
h1 { font-size: 2rem; font-weight: 600; margin: 0.2rem 0; }
h2 { font-size: 1.35rem; margin: 0 0 0.6rem; }
h3 { font-size: 0.95rem; margin: 1.1rem 0 0.3rem; }
a { color: inherit; }
.crumb { margin: 0; color: var(--muted); }
.crumb a:hover { color: var(--done); }
.note { color: var(--muted); }
.yes { color: var(--done); font-weight: 600; }
.no { color: var(--wait); font-weight: 600; }
.slower { color: #9b2c2c; font-weight: 600; }
.coverage { display: flex; align-items: center; gap: 0.75rem; margin: 0.6rem 0 1rem; }
.track { flex: 1; height: 10px; background: #efe8dc; border-radius: 99px; overflow: hidden; }
.fill { height: 100%; background: var(--done); }
.views { display: flex; gap: 0.5rem; margin: 0.2rem 0 1rem; }
.views button {
  font: inherit; cursor: pointer; border: 1px solid var(--line);
  background: var(--card); border-radius: 8px; padding: 0.25rem 0.7rem;
}
.views button.active { background: var(--ink); color: var(--paper); }
.view { display: none; }
.view.active { display: block; }
table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
th, td { text-align: left; padding: 0.45rem 0.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 0.8rem; letter-spacing: 0.02em; }
.diff { white-space: nowrap; }
.bars { display: grid; gap: 0.25rem; min-width: 8rem; }
.bars span { display: block; height: 8px; border-radius: 99px; }
.bars .r { background: var(--r); }
.bars .py { background: var(--py); }
.legend { color: var(--muted); font-size: 0.85rem; }
.legend i { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 2px; margin-right: 0.2rem; }
.legend .r { background: var(--r); }
.legend .py { background: var(--py); }
#function-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 0.8rem; }
#function-list button {
  font: inherit; cursor: pointer; border: 1px solid var(--line);
  background: var(--card); border-radius: 999px; padding: 0.15rem 0.7rem;
}
#function-list button.yes { color: var(--done); }
#function-list button.no { color: var(--wait); }
#function-list button.active { background: var(--ink); color: var(--paper); }
.controls { display: flex; gap: 0.5rem; margin-bottom: 0.8rem; }
.controls button {
  font: inherit; cursor: pointer; border: 1px solid var(--line);
  background: var(--card); border-radius: 8px; padding: 0.25rem 0.7rem;
}
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: start; }
.pair.hide-origin, .pair.hide-translation { grid-template-columns: 1fr; }
.pair.hide-origin .origin, .pair.hide-translation .translation { display: none; }
.pane { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 0.9rem 1rem 1.2rem; }
.kicker { margin: 0; letter-spacing: 0.06em; text-transform: uppercase; font-size: 0.75rem; color: var(--muted); }
pre {
  white-space: pre-wrap; background: #f3eee6; padding: 0.7rem 0.8rem;
  border-radius: 8px; margin: 0.2rem 0 0;
}
.output { margin-top: 0.4rem; border: 1px solid var(--line); border-radius: 8px; overflow: auto; background: #fffdf9; }
.output + .output { margin-top: 0.75rem; }
.output svg { width: 100%; height: auto; display: block; }
.output pre { margin: 0; background: transparent; }
dt { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; margin-top: 0.55rem; }
dd { margin: 0.1rem 0 0; }
#both-hidden { display: none; }
#both-hidden.visible { display: block; }
button.proof-toggle {
  font: inherit; background: none; border: 0; padding: 0; cursor: pointer;
}
button.proof-toggle.active { text-decoration: underline; text-underline-offset: 0.15em; }
.proof { margin-top: 1rem; }
.proof[hidden] { display: none; }
</style>
</head>
<body>
<main>
<p class="crumb"><a href="../index.html">KillCRAN</a></p>
<h1>__NAME__</h1>
<p class="note">CRAN __VERSION__</p>
<p>__RESUME__</p>
__COVERAGE__
<div class="views" id="views">
  <button type="button" data-view="index">Index</button>
  <button type="button" data-view="comparison">Comparison</button>
  <button type="button" data-view="functions">Functions</button>
  <button type="button" data-view="dependencies">Dependencies</button>
</div>
<section class="view" id="view-index"><div class="pane">__INDEX__</div></section>
<section class="view" id="view-comparison"><div class="pane">__COMPARISON__</div></section>
<section class="view" id="view-dependencies">__DEPS__</section>
<section class="view" id="view-functions">
<div id="function-list"></div>
<div class="controls">
  <button type="button" id="hide-r">Hide R</button>
  <button type="button" id="hide-py">Hide translation</button>
</div>
<p id="both-hidden" class="note">Both sides are hidden.</p>
<div class="pair" id="pair">
  <article class="pane origin" id="origin"></article>
  <article class="pane translation" id="translation"></article>
</div>
</section>
</main>
<script>
const functions = __DATA__;
const index = document.getElementById("function-list");
const pair = document.getElementById("pair");

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"
  }[ch]));
}

function block(title, text) {
  if (!text) return "";
  return `<h3>${title}</h3><p>${esc(text)}</p>`;
}

function renderSide(side) {
  const args = (side.arguments || []).map((item) =>
    `<dt>${esc(item.name)}</dt><dd>${esc(item.text)}</dd>`
  ).join("");
  return [
    block("Description", side.description),
    `<h3>Usage</h3><pre>${esc(side.usage || "")}</pre>`,
    `<h3>Arguments</h3><dl>${args}</dl>`,
    block("Details", side.details),
    block("Value", side.value),
    `<h3>Example</h3><pre>${esc(side.example || "")}</pre>`,
    outputBlock(side),
  ].join("");
}

function outputBlock(side) {
  const blocks = side.output_blocks || [];
  if (!blocks.length) {
    return `<h3>Output</h3><p class="note">Output has not been captured.</p>`;
  }
  const html = blocks.map((block) => {
    if (block.svg) return `<div class="output">${block.svg}</div>`;
    return `<div class="output"><pre>${esc(block.text)}</pre></div>`;
  }).join("");
  return `<h3>Output</h3>${html}`;
}

function show(name) {
  const fn = functions.find((item) => item.name === name) || functions[0];
  if (!fn) return;
  for (const button of index.querySelectorAll("button")) {
    button.classList.toggle("active", button.dataset.name === fn.name);
  }
  document.getElementById("origin").innerHTML =
    `<p class="kicker">R</p><h2>${esc(fn.title)}</h2>` +
    (fn.origin ? renderSide(fn.origin) : "<p>No original help recorded.</p>");
  const right = document.getElementById("translation");
  if (fn.translation) {
    right.innerHTML = `<p class="kicker">Python</p><h2>${esc(fn.title)}</h2>` + renderSide(fn.translation);
  } else {
    right.innerHTML = `<p class="kicker">Python</p><h2>${esc(fn.title)}</h2>` +
      `<p class="no">Not translated yet.</p><p>${esc(fn.not_done)}</p>`;
  }
}

for (const fn of functions) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.name = fn.name;
  button.textContent = fn.name;
  button.className = fn.translated ? "yes" : "no";
  button.addEventListener("click", () => {
    const current = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (current === fn.name) show(fn.name);
    else location.hash = encodeURIComponent(fn.name);
  });
  index.appendChild(button);
}

function toggle(className, button, hiddenLabel, shownLabel) {
  pair.classList.toggle(className);
  const hidden = pair.classList.contains(className);
  button.textContent = hidden ? shownLabel : hiddenLabel;
  const both = pair.classList.contains("hide-origin") && pair.classList.contains("hide-translation");
  document.getElementById("both-hidden").classList.toggle("visible", both);
}

document.getElementById("hide-r").addEventListener("click", (event) => {
  toggle("hide-origin", event.currentTarget, "Hide R", "Show R");
});
document.getElementById("hide-py").addEventListener("click", (event) => {
  toggle("hide-translation", event.currentTarget, "Hide translation", "Show translation");
});

function selectView(view) {
  for (const button of document.querySelectorAll("#views button")) {
    button.classList.toggle("active", button.dataset.view === view);
  }
  document.getElementById("view-index").classList.toggle("active", view === "index");
  document.getElementById("view-comparison").classList.toggle("active", view === "comparison");
  document.getElementById("view-functions").classList.toggle("active", view === "functions");
  document.getElementById("view-dependencies").classList.toggle("active", view === "dependencies");
}

for (const button of document.querySelectorAll("#views button")) {
  button.addEventListener("click", () => {
    const view = button.dataset.view;
    if (view === "functions") {
      const current = decodeURIComponent(location.hash.replace(/^#/, ""));
      const known = functions.some((item) => item.name === current);
      const next = known ? current : (functions[0] ? functions[0].name : "");
      if (current === next) selectView("functions");
      else location.hash = encodeURIComponent(next);
      return;
    }
    if (location.hash === "#" + view) selectView(view);
    else location.hash = view;
  });
}

const proofNode = document.getElementById("proof");
const proofData = JSON.parse(document.getElementById("proof-data")?.textContent || "[]");
let openProof = "";

function markProof(name) {
  for (const button of document.querySelectorAll(".proof-toggle")) {
    button.classList.toggle("active", button.dataset.name === name);
  }
}

function showProof(name) {
  if (!proofNode) return;
  if (openProof === name) {
    proofNode.hidden = true;
    openProof = "";
    markProof("");
    return;
  }
  const item = proofData.find((entry) => entry.name === name);
  if (!item) return;
  document.getElementById("proof-r").textContent = item.r;
  document.getElementById("proof-py").textContent = item.python;
  proofNode.hidden = false;
  openProof = name;
  markProof(name);
}

document.getElementById("view-comparison").addEventListener("click", (event) => {
  const button = event.target.closest(".proof-toggle");
  if (!button) return;
  showProof(button.dataset.name);
});

function fromHash() {
  const name = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (!name || name === "index") {
    selectView("index");
    return;
  }
  if (name === "comparison") {
    selectView("comparison");
    return;
  }
  if (name === "dependencies") {
    selectView("dependencies");
    return;
  }
  selectView("functions");
  show(name);
}
window.addEventListener("hashchange", fromHash);
fromHash();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
