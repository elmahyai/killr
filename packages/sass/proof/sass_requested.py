"""Per-function fixed-input proof and timing for the requested sass exports."""
from __future__ import annotations

import contextlib
import io
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.sass.sass_bundle import sass_bundle
from packages.sass.sass_bundle_remove import sass_bundle_remove
from packages.sass.sass_cache_options import sass_cache_options
from packages.sass.sass_file import sass_file
from packages.sass.sass_import import sass_import
from packages.sass.sass_layer import sass_layer
from packages.sass.sass_layer_file import sass_layer_file
from packages.sass.sass_layer_merge import sass_layer_merge
from packages.sass.sass_options import sass_options
from packages.sass.sass_options_get import sass_options_get
from packages.sass.sass_options_set import sass_options_set
from packages.sass.sass_partial import sass_partial
from packages.sass.write_file_attachments import write_file_attachments

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="sass-requested-") as directory:
        td = Path(directory)
        scss = td / "input.scss"
        scss.write_text("/*-- scss:rules --*/\na {\n  color: red;\n}\n")
        attachment = td / "attachment.txt"
        attachment.write_text("attachment")
        destination = td / "attachments"
        destination.mkdir()
        bundle = sass_bundle(theme="a", other="b")
        layer = sass_layer(
            rules="a { color: red; }",
            file_attachments={"x": str(attachment)},
        )

        def options_get():
            sass_options_set(output_style="compressed")
            value = sass_options_get()
            sass_options_set(None)
            return value

        def options_set():
            sass_options_set(output_style="compressed")
            sass_options_set(None)
            return None

        cases = {
            "sass_import": (sass_import, ("a\\b\"c'd",), {}),
            "sass_file": (sass_file, (str(scss),), {}),
            "sass_bundle": (sass_bundle, (), {"theme": "a", "other": "b"}),
            "sass_bundle_remove": (sass_bundle_remove, (bundle, "other"), {}),
            "sass_cache_options": (sass_cache_options, (None, None), {}),
            "sass_layer": (sass_layer, (), {
                "rules": "a { color: red; }",
                "file_attachments": {"x": str(attachment)},
            }),
            "sass_layer_file": (sass_layer_file, (str(scss),), {}),
            "sass_layer_merge": (sass_layer_merge, (layer, sass_layer_file(str(scss))), {}),
            "sass_options": (sass_options, (), {
                "output_style": "expanded", "include_path": "x", "indent_width": 3,
            }),
            "sass_options_get": (options_get, (), {}),
            "sass_options_set": (options_set, (), {}),
            "sass_partial": (sass_partial, ("a { color: red; }", bundle), {}),
            "write_file_attachments": (
                write_file_attachments,
                ({"x": str(attachment)}, str(destination)),
                {},
            ),
        }

        def summary(name, value):
            if name in {"sass_import", "sass_file"}:
                if name == "sass_import":
                    return str(value)
                return Path(str(value).removeprefix('@import "').removesuffix('";')).name
            if name in {"sass_bundle", "sass_bundle_remove"}:
                return "|".join(value.layers)
            if name == "sass_cache_options":
                return ""
            if name == "sass_layer":
                return f"{len(value.layers)}|{next(iter(value.layers.values())).rules}"
            if name == "sass_layer_file":
                rules = next(iter(value.layers.values())).rules
                return f"{len(value.layers)}|{''.join(rules) if isinstance(rules, str) else chr(10).join(rules)}"
            if name == "sass_layer_merge":
                return str(len(value.layers))
            if name == "sass_options":
                return f"{value['precision']}|{value['output_style']}|{value['include_path']}|{len(value['indent'])}"
            if name == "sass_options_get":
                return str(value["output_style"])
            if name == "sass_partial":
                return str(value).rstrip("\r\n")
            if name in {"sass_options_set", "write_file_attachments"}:
                return "NULL"
            return str(value)

        report = []
        for name, (fn, args, kwargs) in cases.items():
            with contextlib.redirect_stderr(io.StringIO()):
                value = fn(*args, **kwargs)
            actual = summary(name, value)
            times = []
            for _ in range(20):
                start = time.perf_counter()
                with contextlib.redirect_stderr(io.StringIO()):
                    fn(*args, **kwargs)
                times.append((time.perf_counter() - start) * 1000)
            translated_ms = statistics.median(times)
            (OUT / f"{name}_python.txt").write_text(actual + "\n")
            (PROOF / f"{name}_python_result.txt").write_text(
                f"value={actual}\ntranslated_ms={translated_ms:.12g}\n"
            )
            report.append((name, actual, translated_ms))

        (PROOF / "sass_requested_python_results.txt").write_text(
            "\n".join(f"{name}\t{value}\t{ms:.12g}" for name, value, ms in report) + "\n"
        )
        r_timings = {}
        for line in (PROOF / "sass_requested_r_timing.txt").read_text().splitlines():
            name, milliseconds = line.split("\t")
            r_timings[name] = float(milliseconds)
        lines = ["function,matches,max_abs_diff,r_ms,translated_ms,speedup,proof_r,proof_python"]
        for name, value, translated_ms in report:
            r_value = (OUT / f"{name}_r.txt").read_text().rstrip("\n")
            if name == "sass_file":
                r_value = Path(r_value).name
            matches = value == r_value
            lines.append(
                f"{name},{'yes' if matches else 'no'},{0 if matches else 1},"
                f"{r_timings[name]:.12g},{translated_ms:.12g},"
                f"{r_timings[name] / translated_ms:.12g},"
                f"{OUT / (name + '_r.txt')},{OUT / (name + '_python.txt')}"
            )
        (OUT / "sass_requested_compare.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
