from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from mathjaxr.preview import preview_rd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix="mathjaxr-preview-"))
(fixture / "man").mkdir()
(fixture / "DESCRIPTION").write_text("Package: demo\nVersion: 1.0\n", encoding="utf-8")
(fixture / "man" / "demo.Rd").write_text(
    "\\name{demo}\n\\title{Demo}\n\\description{Hello world.}\n", encoding="utf-8"
)

preview_rd(fixture / "demo.Rd", view=False, type="txt")
generated = Path(tempfile.gettempdir()) / "demo.Rd.txt"
shutil.copyfile(generated, OUT / "preview_rd-py.txt")

times = []
for _ in range(20):
    started = time.perf_counter()
    preview_rd(fixture / "demo.Rd", view=False, type="txt")
    times.append((time.perf_counter() - started) * 1000)
print(f"translated_ms={sorted(times)[9]:.6f}")
print(f"output={OUT / 'preview_rd-py.txt'}")
