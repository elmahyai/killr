#!/usr/bin/env python3
"""The orchestrator: ingest records, screen tarballs, cut batches, write the one dashboard."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from batch import batch  # noqa: E402
from ingest import ingest  # noqa: E402
from screenlib import screen, status  # noqa: E402


def _load_site():
    spec = importlib.util.spec_from_file_location("orch_site", HERE / "site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.site


site = _load_site()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _usage()
    command = args[0]
    if command == "ingest":
        counts = ingest()
        print(
            "ingested "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        return 0
    if command == "screen":
        if len(args) < 2:
            return _usage()
        row = screen(args[1])
        batch(args[1])
        print(f"screened {row['name']} {row['version']}", file=sys.stderr)
        print(status(args[1]), end="")
        return 0
    if command == "batch":
        if len(args) < 2:
            return _usage()
        made = batch(args[1])
        print(f"batches {len(made)}")
        print(status(args[1]), end="")
        return 0
    if command == "status":
        if len(args) < 2:
            return _usage()
        print(status(args[1]), end="")
        return 0
    if command == "site":
        totals = site(home_only="--all-pages" not in args)
        print(
            f"packages {totals['packages']} (complete {totals['complete']}, "
            f"in progress {totals['in_progress']}, replaced {totals['replaced']}); "
            f"batches {totals.get('batches', 0)}; screened {totals.get('screened', 0)}"
        )
        return 0
    return _usage()


def _usage() -> int:
    print("usage: python3 orchestrator/killr.py ingest", file=sys.stderr)
    print("       python3 orchestrator/killr.py screen <package>", file=sys.stderr)
    print("       python3 orchestrator/killr.py batch <package>", file=sys.stderr)
    print("       python3 orchestrator/killr.py status <package>", file=sys.stderr)
    print("       python3 orchestrator/killr.py site", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
