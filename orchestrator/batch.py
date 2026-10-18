"""Cut batches for a screened package and pick skilled vs fast models."""

from __future__ import annotations

import sqlite3
import uuid
from collections import defaultdict

from screenlib import ROOT, connect

BATCH_SIZE = 14
EXPERIENCE = ROOT / "ai-handbook" / "experience"
NUMERICAL = (
    "fit",
    "dist",
    "dens",
    "spline",
    "optim",
    "likeli",
    "quantil",
    "random",
    "cdf",
    "pdf",
    "censor",
    "mle",
)
TASK_DEFAULT = {
    "hard-retry": "claude-haiku-5-5-thinking-high",
    "crate-new": "claude-haiku-5-5-thinking-high",
    "crate-family": "claude-haiku-5-5-thinking-high",
    "crate-retry": "claude-haiku-5-5-thinking-high",
    "task-force": "gpt-5.6-luna-medium",
    "python-numerical": "gpt-5.6-luna-medium",
    "python-other": "gpt-5.6-luna-medium",
    "python-match": "claude-haiku-5-5-thinking-high",
}
TASK_CANDIDATES = {
    "python-match": ["claude-haiku-5-5-thinking-high", "gpt-5.6-luna-medium"],
    "python-numerical": ["gpt-5.6-luna-medium", "claude-haiku-5-5-thinking-high"],
    "python-other": ["gpt-5.6-luna-medium", "claude-haiku-5-5-thinking-high"],
    "crate-new": ["claude-haiku-5-5-thinking-high"],
}


def batch(name: str, db_path=None) -> list[dict]:
    db = connect(db_path) if db_path else connect()
    db.row_factory = sqlite3.Row
    try:
        pkg = db.execute(
            "SELECT * FROM packages WHERE name = ? ORDER BY version DESC", (name,)
        ).fetchone()
        if pkg is None:
            return []
        version = pkg["version"]
        functions = db.execute(
            """SELECT name, r_file FROM functions
               WHERE package = ? AND version = ? ORDER BY r_file, name""",
            (name, version),
        ).fetchall()
        native = {
            row["function"]
            for row in db.execute(
                """SELECT DISTINCT function FROM function_deps
                   WHERE package = ? AND version = ? AND kind = 'native'""",
                (name, version),
            )
        }
        crate_assigned = db.execute(
            "SELECT assigned FROM crates WHERE name = ?", (name,)
        ).fetchone()
        experience = _experience_stems()
        groups: dict[str, list[str]] = defaultdict(list)
        for item in functions:
            groups[item["r_file"]].append(item["name"])
        made = []
        db.execute("DELETE FROM batch_functions WHERE batch_id IN (SELECT id FROM batches WHERE package = ?)", (name,))
        db.execute("DELETE FROM batches WHERE package = ?", (name,))
        for r_file, names in groups.items():
            for chunk in _chunks(names, BATCH_SIZE):
                task = _task(chunk, native, experience, crate_assigned)
                model = _model(task, db)
                batch_id = str(uuid.uuid4())
                db.execute(
                    """INSERT INTO batches (id, package, version, r_file, task, model, n_functions)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (batch_id, name, version, r_file, task, model, len(chunk)),
                )
                db.executemany(
                    "INSERT INTO batch_functions (batch_id, function) VALUES (?, ?)",
                    [(batch_id, fn) for fn in chunk],
                )
                made.append(
                    {
                        "id": batch_id,
                        "package": name,
                        "version": version,
                        "r_file": r_file,
                        "task": task,
                        "model": model,
                        "functions": chunk,
                    }
                )
        db.commit()
    finally:
        db.close()
    return made


def _chunks(names: list[str], size: int) -> list[list[str]]:
    return [names[i : i + size] for i in range(0, len(names), size)]


def _experience_stems() -> list[str]:
    stems = []
    if EXPERIENCE.is_dir():
        stems.extend(path.stem.lower().replace("-", " ") for path in EXPERIENCE.glob("*.md"))
    pkg_exp = ROOT / "packages"
    if pkg_exp.is_dir():
        for path in pkg_exp.glob("*/experience/*.md"):
            stems.append(path.stem.lower().replace("-", " "))
    return stems


def _task(
    names: list[str],
    native: set[str],
    experience: list[str],
    crate_assigned,
) -> str:
    blob = " ".join(names).lower()
    if crate_assigned is not None and (crate_assigned["assigned"] or "").strip():
        if any(name in native for name in names):
            return "crate-new"
    if any(word in blob for word in NUMERICAL):
        return "python-numerical"
    for stem in experience:
        words = [w for w in stem.split() if len(w) > 3]
        if any(word in blob for word in words):
            return "python-match"
    return "python-other"


def _model(task: str, db: sqlite3.Connection) -> str:
    default = TASK_DEFAULT.get(task, "gpt-5.6-luna-medium")
    candidates = TASK_CANDIDATES.get(task, [default])
    launches = db.execute(
        "SELECT model, task, matched_lines, minutes FROM launches WHERE task = ?",
        (task,),
    ).fetchall()
    aside = _set_aside(launches)
    return next((model for model in candidates if model not in aside), default)


def _set_aside(launches) -> set[str]:
    by_model: dict[str, list] = defaultdict(list)
    for row in launches:
        by_model[row["model"]].append(row)
    aside = set()
    for model, rows in by_model.items():
        if len(rows) < 5:
            continue
        yield_m = _yield(rows)
        cheaper = [
            other
            for other, other_rows in by_model.items()
            if other != model and len(other_rows) >= 5 and _weight(other) < _weight(model)
        ]
        if cheaper and any(_yield(by_model[other]) > yield_m for other in cheaper):
            aside.add(model)
    return aside


def _yield(rows) -> float:
    matched = sum(row["matched_lines"] or 0 for row in rows)
    minutes = sum((row["minutes"] or 0) * _weight(row["model"]) for row in rows)
    return matched / minutes if minutes else 0.0


def _weight(model: str) -> float:
    return {
        "gpt-5.6-luna-medium": 1,
        "gpt-5.6-luna": 1,
        "claude-haiku-5-5": 1,
        "claude-haiku-5-5-thinking-high": 2,
        "composer-2.5-fast": 2,
        "grok-4.7-high-fast": 3,
    }.get(model, 1)
