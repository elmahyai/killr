"""Copy existing dashboard records into the orchestrator database. Source files stay."""

from __future__ import annotations

import json

from screenlib import ROOT, connect

PACKAGES = ROOT / "packages"
CRATES = ROOT / "crates"
LAUNCHES = ROOT / "dashboard" / "launches.json"
NATIVE = ROOT / "ai-handbook" / "native.json"
REPLACED = ROOT / "rcran" / "replaced.json"


def ingest(db_path=None) -> dict[str, int]:
    db = connect(db_path) if db_path else connect()
    counts = {
        "translation_packages": 0,
        "translation_functions": 0,
        "crates": 0,
        "launches": 0,
        "native": 0,
        "replaced": 0,
    }
    try:
        for path in sorted(PACKAGES.glob("*/translation.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            name = record["name"]
            db.execute(
                """INSERT INTO translation_packages (
                    name, cran_version, inventory, status, blocked_by, crate_claims,
                    resume, strategy, dependencies, translation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    cran_version=excluded.cran_version,
                    inventory=excluded.inventory,
                    status=excluded.status,
                    blocked_by=excluded.blocked_by,
                    crate_claims=excluded.crate_claims,
                    resume=excluded.resume,
                    strategy=excluded.strategy,
                    dependencies=excluded.dependencies,
                    translation=excluded.translation""",
                (
                    name,
                    record.get("cran_version") or "",
                    record.get("inventory") or "complete",
                    record.get("status") or "",
                    json.dumps(record.get("blocked_by") or [], ensure_ascii=False),
                    json.dumps(record.get("crate_claims") or [], ensure_ascii=False),
                    record.get("resume") or "",
                    record.get("strategy") or "",
                    json.dumps(record.get("dependencies") or {}, ensure_ascii=False),
                    str(path.relative_to(ROOT)),
                ),
            )
            counts["translation_packages"] += 1
            db.execute("DELETE FROM translation_functions WHERE package = ?", (name,))
            docs_dir = path.parent / "docs"
            rows = []
            for item in record.get("functions") or []:
                doc_path = docs_dir / f"{item.get('name', '')}.json"
                doc = {}
                if doc_path.is_file():
                    try:
                        doc = json.loads(doc_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        doc = {}
                rows.append(
                    (
                        name,
                        item.get("name") or "",
                        1 if item.get("translated") else 0,
                        # Exact on proven cases, one mode covered: done, counted as done.
                        1 if item.get("covered") else 0,
                        item.get("python") or "",
                        json.dumps(item.get("loads") or [], ensure_ascii=False),
                        json.dumps(item.get("uses") or [], ensure_ascii=False),
                        item.get("done") or "",
                        item.get("not_done") or "",
                        json.dumps(item.get("blocked_by") or [], ensure_ascii=False),
                        item.get("assigned") or "",
                        json.dumps(item.get("check") or {}, ensure_ascii=False),
                        json.dumps(doc, ensure_ascii=False),
                    )
                )
            db.executemany(
                """INSERT INTO translation_functions (
                    package, name, translated, covered, python, loads, uses, done, not_done,
                    blocked_by, assigned, check_json, doc_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            counts["translation_functions"] += len(rows)

        for path in sorted(CRATES.glob("*/crate.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            db.execute(
                """INSERT INTO crates (name, origin, loaded_by, assigned, path)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                    origin=excluded.origin,
                    loaded_by=excluded.loaded_by,
                    assigned=excluded.assigned,
                    path=excluded.path""",
                (
                    record["name"],
                    record.get("origin") or "",
                    json.dumps(record.get("loaded_by") or [], ensure_ascii=False),
                    record.get("assigned") or "",
                    str(path.relative_to(ROOT)),
                ),
            )
            counts["crates"] += 1

        if LAUNCHES.is_file():
            records = json.loads(LAUNCHES.read_text(encoding="utf-8"))
            if isinstance(records, list):
                db.execute("DELETE FROM launches")
                db.executemany(
                    """INSERT INTO launches (
                        model, task, minutes, r_lines, matched_lines, functions, matched, returned
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            item.get("model") or "",
                            item.get("task") or "",
                            item.get("minutes"),
                            item.get("r_lines"),
                            item.get("matched_lines"),
                            item.get("functions"),
                            item.get("matched"),
                            item.get("returned") or "",
                        )
                        for item in records
                        if isinstance(item, dict)
                    ],
                )
                counts["launches"] = len(records)

        if NATIVE.is_file():
            record = json.loads(NATIVE.read_text(encoding="utf-8"))
            items = record.get("native") if isinstance(record, dict) else record
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict) or not item.get("name"):
                        continue
                    db.execute(
                        """INSERT INTO native (name, role, why) VALUES (?, ?, ?)
                           ON CONFLICT(name) DO UPDATE SET role=excluded.role, why=excluded.why""",
                        (item["name"], item.get("role") or "", item.get("why") or ""),
                    )
                    counts["native"] += 1

        if REPLACED.is_file():
            record = json.loads(REPLACED.read_text(encoding="utf-8"))
            items = record.get("packages") if isinstance(record, dict) else record
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict) or not item.get("name"):
                        continue
                    db.execute(
                        """INSERT INTO replaced (name, reason) VALUES (?, ?)
                           ON CONFLICT(name) DO UPDATE SET reason=excluded.reason""",
                        (item["name"], item.get("reason") or ""),
                    )
                    counts["replaced"] += 1

        db.commit()
    finally:
        db.close()
    return counts
