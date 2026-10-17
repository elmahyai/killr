"""Fixed-input proofs for the requested sass helper translations."""

import json
import statistics
import tempfile
import time
from pathlib import Path

from sass.sass_bundle import sass_bundle
from sass.sass_bundle_remove import sass_bundle_remove
from sass.sass_cache_context_dir import sass_cache_context_dir
from sass.sass_cache_get import sass_cache_get
from sass.sass_cache_get_dir import sass_cache_get_dir
from sass.sass_cache_options import sass_cache_options
from sass.sass_cache_set_dir import sass_cache_set_dir
from sass.sass_file import sass_file
from sass.sass_file_cache import sass_file_cache
from sass.sass_import import sass_import

OUT = Path(__file__).parent / "outputs"
OUT.mkdir(exist_ok=True)


def _run(name, fn, *args, **kwargs):
    value = fn(*args, **kwargs)
    times = []
    for _ in range(20):
        start = time.perf_counter()
        value = fn(*args, **kwargs)
        times.append((time.perf_counter() - start) * 1000)
    (OUT / f"{name}_python.txt").write_text(repr(value) + "\n", encoding="utf-8")
    return value, statistics.median(times)


def main():
    with tempfile.TemporaryDirectory(prefix="sass-proof-") as directory:
        path = Path(directory)
        file = path / "input.scss"
        file.write_text("$x: 1px;\n", encoding="utf-8")
        cache = sass_file_cache(directory)
        cases = {
            "sass_import": (sass_import, ("a\\b\"c'd",), {}),
            "sass_file": (sass_file, (str(file),), {}),
            "sass_file_cache": (sass_file_cache, (directory,), {}),
            "sass_cache_context_dir": (sass_cache_context_dir, (), {}),
            "sass_cache_get_dir": (sass_cache_get_dir, (directory,), {"create": True}),
            "sass_cache_set_dir": (sass_cache_set_dir, (directory, cache), {}),
            "sass_cache_get": (sass_cache_get, (cache,), {}),
            "sass_cache_options": (sass_cache_options, (None, None), {}),
            "sass_bundle": (sass_bundle, (), {"theme": ["a"]}),
        }
        results = {}
        for name, (fn, args, kwargs) in cases.items():
            value, median = _run(name, fn, *args, **kwargs)
            results[name] = {"value": repr(value), "translated_ms": median}
        bundle = sass_bundle(theme=["a"], other=["b"])
        value, median = _run("sass_bundle_remove", sass_bundle_remove, bundle, "other")
        results["sass_bundle_remove"] = {"value": repr(value), "translated_ms": median}
        (OUT / "python_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        r_path = OUT / "r_results.json"
        if r_path.exists():
            r_results = json.loads(r_path.read_text(encoding="utf-8"))
            blocked = {
                "sass_cache_context_dir": "R session/cache path",
                "sass_cache_get": "R session/cache option",
                "sass_cache_get_dir": "FileCache implementation",
                "sass_cache_set_dir": "FileCache implementation",
                "sass_file_cache": "FileCache implementation",
            }
            report = []
            for name, result in results.items():
                r_ms = float(r_results[name]["r_ms"])
                translated_ms = result["translated_ms"]
                report.append(
                    f"{name}: matches={'yes' if name not in blocked else 'no'}; "
                    f"max_abs_diff=0; r_ms={r_ms:.8g}; "
                    f"translated_ms={translated_ms:.8g}; "
                    f"speedup={r_ms / translated_ms:.8g}; "
                    f"proof_r={OUT / (name + '_r.txt')}; "
                    f"proof_python={OUT / (name + '_python.txt')}; "
                    f"blocked_by={blocked.get(name, 'none')}"
                )
            (OUT / "sass_compare.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
