import json
import os
import statistics
import subprocess
import tempfile
import time

from remotes.add_metadata import add_metadata

pkg = tempfile.mkdtemp()
os.makedirs(os.path.join(pkg, "Meta"))
rds = os.path.join(pkg, "Meta", "package.rds")
subprocess.check_call(
    [
        "Rscript",
        "--vanilla",
        "-e",
        "saveRDS(structure(list(DESCRIPTION = c(Package = 'foo', Version = '1.0.0')), class = 'packageDescription2'), commandArgs(TRUE)[[1]])",
        rds,
    ]
)
meta = {"RemoteType": "github", "RemoteRepo": "foo"}
add_metadata(pkg, meta)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    add_metadata(pkg, meta)
    elapsed.append((time.perf_counter() - started) * 1000)
text = subprocess.check_output(
    [
        "Rscript",
        "--vanilla",
        "-e",
        "d <- readRDS(commandArgs(TRUE)[[1]])$DESCRIPTION; cat(paste(sprintf('%s=%s', names(d), d), collapse = '\\n'))",
        rds,
    ],
    text=True,
)
print(json.dumps({"value": text, "median_ms": statistics.median(elapsed)}))
