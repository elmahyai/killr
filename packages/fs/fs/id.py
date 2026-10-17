"""User and group ids from the system password and group databases."""

from __future__ import annotations

import grp
import pwd


class Frame:
    """A data frame stored as equal-length columns."""

    def __init__(self, columns: dict):
        self.columns = columns

    def __getitem__(self, key):
        return self.columns[key]

    def __len__(self) -> int:
        if not self.columns:
            return 0
        return len(next(iter(self.columns.values())))


def _unique_sorted(rows: list[tuple], id_index: int = 0) -> list[tuple]:
    rows = sorted(rows, key=lambda row: row[id_index])
    seen = set()
    kept = []
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        kept.append(row)
    return kept


def group_ids() -> Frame:
    """Every group, ordered by id. Duplicate rows are dropped."""
    rows = _unique_sorted([(entry.gr_gid, entry.gr_name) for entry in grp.getgrall()])
    return Frame(
        {
            "group_id": [row[0] for row in rows],
            "group_name": [row[1] for row in rows],
        }
    )


def user_ids() -> Frame:
    """Every user, ordered by id. Duplicate rows are dropped."""
    rows = _unique_sorted([(entry.pw_uid, entry.pw_name) for entry in pwd.getpwall()])
    return Frame(
        {
            "user_id": [row[0] for row in rows],
            "user_name": [row[1] for row in rows],
        }
    )
