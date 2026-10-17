"""Shared harness for the sass proofs.

Each <name>_proof.py runs <name>_r.R with Rscript, reads the canonical R
values from outputs/<name>_r.json, computes the same cases in Python, and
compares them. The primary timed call runs once untimed, then 20 times with
time.perf_counter(). Results go to outputs/<name>_result.json and
docs/output/<name>.txt.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

PROOF = Path(__file__).resolve().parent
PACKAGE = PROOF.parent
OUTPUTS = PROOF / "outputs"
DOCS = PACKAGE / "docs" / "output"

# Make packages/ importable so `sass.<module>` resolves to packages/sass/<module>.py.
sys.path.insert(0, str(PACKAGE.parent))

from sass._common import FontCollection, SassLayer  # noqa: E402
from sass._sass_values import HtmlDep  # noqa: E402


def canon_dep(d: HtmlDep) -> dict:
    return {
        "name": d.name,
        "version": d.version,
        "kind": d.kind,
        "href": d.href,
        "head": d.head,
        "stylesheet": d.stylesheet,
    }


def canon_collection(fc: FontCollection) -> dict:
    return {
        "families": list(fc.families),
        "default_flag": fc.default_flag is True,
        "html_deps": [canon_dep(d) for d in fc.html_deps],
    }


def canon_layer(layer: SassLayer) -> dict:
    fa = layer.file_attachments
    if fa is None:
        fa_c = None
    elif isinstance(fa, dict) and fa:
        fa_c = canon(fa)
    else:
        fa_c = []
    return {
        "functions": canon(layer.functions),
        "defaults": canon(layer.defaults),
        "mixins": canon(layer.mixins),
        "rules": canon(layer.rules),
        "declarations": canon(layer.declarations),
        "html_deps": canon(layer.html_deps),
        "file_attachments": fa_c,
    }


def canon(x):
    if x is None or isinstance(x, (bool, str, int, float)):
        return x
    if isinstance(x, FontCollection):
        return canon_collection(x)
    if isinstance(x, SassLayer):
        return canon_layer(x)
    if isinstance(x, HtmlDep):
        return canon_dep(x)
    if isinstance(x, dict):
        return {str(k): canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x]
    return repr(x)


def _json_round_trip(value):
    return json.loads(json.dumps(value))


def _median_ms(fn, n: int = 20) -> float:
    fn()  # one untimed call
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times) * 1000.0


def _run_r(name: str) -> dict:
    script = PROOF / f"{name}_r.R"
    subprocess.run(["Rscript", str(script)], check=True, capture_output=True, text=True)
    return json.loads((OUTPUTS / f"{name}_r.json").read_text(encoding="utf-8"))


def run(name: str, cases: dict, timed, primary: str, text_extra: dict | None = None) -> dict:
    """Compare every case with R, time the primary call, and write the outputs.

    cases maps a case name to a zero-argument function returning a value that
    canon() can convert. timed is the zero-argument call timed for the speedup.
    """
    r_payload = _run_r(name)
    r_cases = r_payload["cases"]

    py_cases = {}
    per_case = []
    for case, fn in cases.items():
        try:
            py_val = _json_round_trip(canon(fn()))
        except Exception as exc:  # error cases compare as the canonical error marker
            py_val = {"error": "error"}
            py_detail = f"{type(exc).__name__}: {exc}"
        else:
            py_detail = ""
        py_cases[case] = py_val
        r_val = r_cases.get(case)
        match = r_val == py_val
        per_case.append({"case": case, "match": match, "r": r_val, "py": py_val, "py_detail": py_detail})

    all_match = all(item["match"] for item in per_case)
    py_ms = _median_ms(timed)
    r_ms = float(r_payload["r_ms"])
    speedup = r_ms / py_ms if py_ms else float("inf")
    max_abs_diff = 0.0 if all_match else float("inf")

    summary = {
        "function": name,
        "matches": "yes" if all_match else "no",
        "max_abs_diff": max_abs_diff,
        "r_ms": r_ms,
        "translated_ms": py_ms,
        "speedup": speedup,
        "primary_case": primary,
        "cases_matched": sum(item["match"] for item in per_case),
        "cases_total": len(per_case),
        "r_version": r_payload["r_version"],
        "sass_version": r_payload["sass_version"],
        "proof_script": f"packages/sass/proof/{name}_proof.py",
        "r_script": f"packages/sass/proof/{name}_r.R",
        "output_file": f"packages/sass/docs/output/{name}.txt",
        "blocked_by": [],
    }
    (OUTPUTS / f"{name}_result.json").write_text(
        json.dumps({"summary": summary, "cases": per_case}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"function: {name}",
        f"sass_version: {summary['sass_version']}",
        f"r_version: {summary['r_version']}",
        f"matches: {summary['matches']}",
        f"cases_matched: {summary['cases_matched']}/{summary['cases_total']}",
        f"max_abs_diff: {max_abs_diff}",
        f"primary_case: {primary}",
        f"r_ms: {r_ms:.6f}",
        f"translated_ms: {py_ms:.6f}",
        f"speedup: {speedup:.4f}",
        "",
    ]
    for item in per_case:
        lines.append(f"[{item['case']}] match={'yes' if item['match'] else 'no'}")
        lines.append(f"  R : {json.dumps(item['r'], ensure_ascii=False)}")
        lines.append(f"  Py: {json.dumps(item['py'], ensure_ascii=False)}")
        if item["py_detail"]:
            lines.append(f"  Py error: {item['py_detail']}")
    if text_extra:
        for key, value in text_extra.items():
            lines.append("")
            lines.append(f"--- {key} ---")
            lines.append(value)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return summary
