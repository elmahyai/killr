#!/usr/bin/env python3
"""Run each R/Python proof pair, compare observable results, write docs/output.

Each proof prints one JSON line: {"value": [...], "median_ms": x}.
Numbers must agree within 1e-8 (max absolute difference is reported);
strings must agree exactly.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"
PY = ROOT.parents[1] / ".venv" / "bin" / "python"
TOL = 1e-8

NAMES = [
    "defer", "defer_parent", "deferred_clear", "deferred_run", "global_defer",
    "local_", "with_",
    "with_collate", "local_collate", "with_locale", "local_locale",
    "with_connection", "local_connection",
    "with_dir", "local_dir",
    "with_envvar", "local_envvar",
    "with_file", "local_file",
    "with_language", "local_language",
    "with_makevars", "local_makevars", "makevars_user", "set_makevars",
    "with_message_sink", "local_message_sink",
    "with_output_sink", "local_output_sink",
    "with_options", "local_options",
    "with_path", "local_path",
    "with_preserve_seed", "local_preserve_seed",
    "with_rng_version", "local_rng_version",
    "with_seed", "local_seed",
    "with_tempdir", "local_tempdir",
    "with_tempfile", "local_tempfile",
    "with_timezone", "local_timezone",
]

PY_NAMES = {
    "local_": "withr.factory.local_",
    "with_": "withr.factory.with_",
    "with_collate": "withr.collate.with_collate",
    "local_collate": "withr.collate.local_collate",
    "with_locale": "withr.locale_settings.with_locale",
    "local_locale": "withr.locale_settings.local_locale",
    "with_connection": "withr.connection.with_connection",
    "local_connection": "withr.connection.local_connection",
    "with_dir": "withr.directory.with_dir",
    "local_dir": "withr.directory.local_dir",
    "with_envvar": "withr.envvar.with_envvar",
    "local_envvar": "withr.envvar.local_envvar",
    "with_file": "withr.files.with_file",
    "local_file": "withr.files.local_file",
    "with_language": "withr.language.with_language",
    "local_language": "withr.language.local_language",
    "with_makevars": "withr.makevars.with_makevars",
    "local_makevars": "withr.makevars.local_makevars",
    "makevars_user": "withr.makevars.makevars_user",
    "set_makevars": "withr.makevars.set_makevars",
    "with_message_sink": "withr.sink.with_message_sink",
    "local_message_sink": "withr.sink.local_message_sink",
    "with_output_sink": "withr.sink.with_output_sink",
    "local_output_sink": "withr.sink.local_output_sink",
    "with_options": "withr.options.with_options",
    "local_options": "withr.options.local_options",
    "with_path": "withr.path.with_path",
    "local_path": "withr.path.local_path",
    "with_preserve_seed": "withr.seed.with_preserve_seed",
    "local_preserve_seed": "withr.seed.local_preserve_seed",
    "with_rng_version": "withr.rng.with_rng_version",
    "local_rng_version": "withr.rng.local_rng_version",
    "with_seed": "withr.seed.with_seed",
    "local_seed": "withr.seed.local_seed",
    "with_tempdir": "withr.tempfiles.with_tempdir",
    "local_tempdir": "withr.tempfiles.local_tempdir",
    "with_tempfile": "withr.tempfiles.with_tempfile",
    "local_tempfile": "withr.tempfiles.local_tempfile",
    "with_timezone": "withr.timezone.with_timezone",
    "local_timezone": "withr.timezone.local_timezone",
    "defer": "withr.deferred.defer",
    "defer_parent": "withr.deferred.defer_parent",
    "deferred_clear": "withr.deferred.deferred_clear",
    "deferred_run": "withr.deferred.deferred_run",
    "global_defer": "withr.deferred.global_defer",
}


def run_one(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=PROOF)
    lines = [line for line in proc.stdout.splitlines() if line.startswith("{")]
    if proc.returncode != 0 or not lines:
        raise RuntimeError(f"{cmd[-1]} failed:\n{proc.stdout}\n{proc.stderr}")
    return lines[-1]


def compare(r_value, p_value):
    if len(r_value) != len(p_value):
        return False, None
    max_diff = 0.0
    ok = True
    for a, b in zip(r_value, p_value):
        a_str, b_str = isinstance(a, str), isinstance(b, str)
        if a_str or b_str:
            if a != b:
                ok = False
            continue
        diff = abs(a - b)
        max_diff = max(max_diff, diff)
        if diff > TOL:
            ok = False
    return ok, max_diff


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = 0
    for name in NAMES:
        r_line = run_one(["Rscript", f"{name}-r.R"])
        p_line = run_one([str(PY), f"{name}-py.py"])
        (OUT / f"{name}-r.txt").write_text(r_line + "\n")
        (OUT / f"{name}-python.txt").write_text(p_line + "\n")

        r_json = json.loads(r_line)
        p_json = json.loads(p_line)
        matched, max_diff = compare(r_json["value"], p_json["value"])
        if not matched:
            failures += 1
        r_ms = r_json["median_ms"]
        p_ms = p_json["median_ms"]
        speedup = r_ms / p_ms if p_ms > 0 else float("inf")
        rows.append((name, PY_NAMES.get(name, name), matched, max_diff, r_ms, p_ms, speedup))

    header = f"{'R export':<22}{'matched':<9}{'max abs diff':<14}{'R ms':>10}{'Py ms':>10}{'speedup':>10}  Python name"
    lines = [header]
    for name, py_name, matched, max_diff, r_ms, p_ms, speedup in rows:
        diff_txt = "exact" if max_diff is None else f"{max_diff:.3g}"
        lines.append(
            f"{name:<22}{'yes' if matched else 'NO':<9}{diff_txt:<14}"
            f"{r_ms:>10.4f}{p_ms:>10.4f}{speedup:>10.2f}  {py_name}"
        )
    summary = "\n".join(lines) + "\n"
    (OUT / "summary.txt").write_text(summary)
    print(summary)
    print(f"{len(rows) - failures}/{len(rows)} matched")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
