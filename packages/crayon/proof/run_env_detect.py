"""Compare terminal and environment detection between R crayon and Python crayon.

Each scenario sets the same environment variables for both sides. A
scenario marked ``pty`` runs both processes inside a pseudo-terminal
(``script``), so stdout and stderr are terminals, as in an interactive
shell. Without a pseudo-terminal both streams are pipes.

Outputs go to docs/output/env-<scenario>-<case>-{r,python}.txt and the
summary to docs/env_detect.json.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PROOF = PACKAGE / "proof"
OUTPUT = PACKAGE / "docs" / "output"
R_LIBS = "/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5"

# name -> (environment overrides, use a pseudo-terminal)
SCENARIOS: dict[str, tuple[dict[str, str], bool]] = {
    "pipe-plain": ({}, False),
    "pipe-r-cli-256": ({"R_CLI_NUM_COLORS": "256"}, False),
    "pipe-term-vars": ({"TERM": "xterm-256color", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.4.1"}, False),
    "pty-xterm-256color": ({"TERM": "xterm-256color"}, True),
    "pty-truecolor": ({"TERM": "xterm-256color", "COLORTERM": "truecolor"}, True),
    "pty-24bit": ({"TERM": "xterm-256color", "COLORTERM": "24bit"}, True),
    "pty-colorterm-other": ({"TERM": "xterm-256color", "COLORTERM": "yes"}, True),
    "pty-xterm": ({"TERM": "xterm"}, True),
    "pty-linux": ({"TERM": "linux"}, True),
    "pty-dumb": ({"TERM": "dumb"}, True),
    "pty-no-term": ({}, True),
    "pty-emacs": ({"TERM": "xterm-256color", "INSIDE_EMACS": "27.1,comint"}, True),
    "pty-emacs-old": ({"TERM": "xterm-256color", "INSIDE_EMACS": "22.3,comint"}, True),
    "pty-no-color": ({"TERM": "xterm-256color", "NO_COLOR": "1"}, True),
    "pty-r-cli-wins": ({"TERM": "xterm-256color", "NO_COLOR": "1", "R_CLI_NUM_COLORS": "4"}, True),
    "pty-iterm": ({"TERM": "xterm-256color", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.4.1"}, True),
    "pty-iterm-old": ({"TERM": "xterm-256color", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.0.9"}, True),
    "pty-vte": ({"TERM": "xterm-256color", "VTE_VERSION": "0.60.0"}, True),
    "pty-vte-old": ({"TERM": "xterm-256color", "VTE_VERSION": "0.40.0"}, True),
    "pty-ci": ({"TERM": "xterm-256color", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.4.1", "CI": "true"}, True),
}

# name -> (R expression, Python expression)
CASES: dict[str, tuple[str, str]] = {
    "detect": (
        "c(num_ansi_colors(), has_color(), num_colors(), has_hyperlink())",
        "[num_ansi_colors(), has_color(), num_colors(), has_hyperlink()]",
    ),
    "hyperlink": (
        'hyperlink("R", "https://r-project.org")',
        'hyperlink("R", "https://r-project.org")',
    ),
}


def base_env(extra: dict[str, str]) -> dict[str, str]:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/ahmed",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "R_LIBS_USER": R_LIBS,
        "PYTHONPATH": str(PACKAGE),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(extra)
    return env


def run(argv: list[str], env: dict[str, str], pty: bool) -> None:
    command = ["script", "-qec", shlex.join(argv), "/dev/null"] if pty else argv
    completed = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{shlex.join(argv)}\n{completed.stdout}\n{completed.stderr}")


def read_values(path: Path) -> tuple[float, list[tuple[str, object]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    ms = float(lines[0].split()[1])
    values: list[tuple[str, object]] = []
    for line in lines[1:]:
        kind, _, payload = line.partition(" ")
        if kind == "chr":
            values.append(("chr", bytes.fromhex(payload).decode("utf-8")))
        elif kind == "num":
            values.append(("num", float(payload)))
    return ms, values


def compare(left: list[tuple[str, object]], right: list[tuple[str, object]]) -> float | None:
    if len(left) != len(right):
        return None
    worst = 0.0
    for (lk, lv), (rk, rv) in zip(left, right):
        if lk != rk:
            return None
        if lk == "chr":
            if lv != rv:
                return None
        else:
            worst = max(worst, abs(float(lv) - float(rv)))
    return worst


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for case, (r_expr, py_expr) in CASES.items():
        for scenario, (extra, pty) in SCENARIOS.items():
            env = base_env(extra)
            stem = f"env-{scenario}-{case}"
            r_out = OUTPUT / f"{stem}-r.txt"
            py_out = OUTPUT / f"{stem}-python.txt"
            run(
                ["Rscript", "--vanilla", str(PROOF / "env_detect-r.R"), str(r_out), "", r_expr],
                env,
                pty,
            )
            run(
                [sys.executable, str(PROOF / "env_detect-py.py"), str(py_out), "", py_expr],
                env,
                pty,
            )
            r_ms, r_values = read_values(r_out)
            py_ms, py_values = read_values(py_out)
            diff = compare(r_values, py_values)
            summary.append({
                "case": case,
                "scenario": scenario,
                "pty": pty,
                "env": extra,
                "r_value": [v for _, v in r_values],
                "python_value": [v for _, v in py_values],
                "matched": diff is not None and diff <= 1e-8,
                "max_abs_diff": diff,
                "r_ms": r_ms,
                "python_ms": py_ms,
                "speedup": r_ms / py_ms if py_ms else None,
            })
            print(
                f"{case:10s} {scenario:22s} matched={diff is not None and diff <= 1e-8} "
                f"R={[v for _, v in r_values]} PY={[v for _, v in py_values]} "
                f"R_ms={r_ms:.3f} PY_ms={py_ms:.4f}",
                flush=True,
            )
    (PACKAGE / "docs" / "env_detect.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    failed = [row for row in summary if not row["matched"]]
    print(f"{len(summary) - len(failed)}/{len(summary)} matched")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
