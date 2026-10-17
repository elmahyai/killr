"""Check every withr export against R, capture examples, and write the records.

The orchestrator runs this once. Sub-agents do not edit translation.json.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "output"
PROOF = ROOT / "proof"
PY = REPO / ".venv" / "bin" / "python"

R_HELPER = r"""
json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  paste0("\"", x, "\"")
}
to_json <- function(x) {
  if (is.null(x)) return("null")
  if (is.logical(x)) {
    bits <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(bits) == 1) return(bits)
    return(paste0("[", paste(bits, collapse = ","), "]"))
  }
  if (is.character(x)) {
    if (length(x) == 1) return(json_escape(x))
    return(paste0("[", paste(vapply(x, json_escape, ""), collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    if (length(x) == 1) return(sprintf("%.17g", x))
    return(paste0("[", paste(sprintf("%.17g", x), collapse = ","), "]"))
  }
  stop(paste("unsupported", paste(class(x), collapse = ",")))
}
"""

R_SHOW = r"""
show <- function(x) {
  if (is.numeric(x) && length(x) && all(abs(x - round(x)) < 1e-8)) {
    cat(sprintf("%.0f", x), sep = " ")
  } else if (is.numeric(x)) {
    cat(sprintf("%.8f", x), sep = " ")
  } else {
    cat(paste(x, collapse = " "))
  }
  cat("\n")
}
"""

PY_SHOW = '''
def show(x):
    if isinstance(x, bool):
        print("TRUE" if x else "FALSE")
        return
    if isinstance(x, (int, float)):
        x = [x]
    if isinstance(x, list) and x and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
        if all(abs(v - round(v)) < 1e-8 for v in x):
            print(" ".join(str(int(round(v))) for v in x))
        else:
            print(" ".join(f"{v:.8f}" for v in x))
        return
    if isinstance(x, list):
        print(" ".join(str(v) for v in x))
        return
    print(x)
'''


def _device(kind: str, ext: str, width: int, height: int, local: bool) -> dict:
    pixels = ext in {".bmp", ".jpg", ".tif", ".png"}
    unit = "pixels" if pixels else "inches"
    r_name = f"{'local' if local else 'with'}_{kind}"
    title = kind.replace("_", " ")
    if local:
        r_expr = f"""
path <- tempfile(fileext = "{ext}")
local({{
  local_{kind}(path, width = {width}, height = {height})
  plot(1:3, 1:3, ann = FALSE)
}})
ok <- isTRUE(file.exists(path) && file.info(path)$size > 0)
unlink(path)
as.numeric(ok)
""".strip()
        py_expr = f"""
fd, path = tempfile.mkstemp(suffix="{ext}")
os.close(fd)
with local_{kind}(path, width={width}, height={height}):
    pass
ok = os.path.getsize(path) > 0
os.remove(path)
return int(ok)
""".strip()
        story = f"local_{kind}(tempfile, width={width}, height={height}) writes a {unit} file"
    else:
        r_expr = f"""
path <- tempfile(fileext = "{ext}")
val <- with_{kind}(path, {{
  plot(1:3, 1:3, ann = FALSE)
  2
}}, width = {width}, height = {height})
ok <- isTRUE(file.exists(path) && file.info(path)$size > 0)
unlink(path)
c(val, as.numeric(ok))
""".strip()
        py_expr = f"""
fd, path = tempfile.mkstemp(suffix="{ext}")
os.close(fd)
val = with_{kind}(path, lambda: 2, width={width}, height={height})
ok = os.path.getsize(path) > 0
os.remove(path)
return [val, int(ok)]
""".strip()
        story = f"with_{kind}(tempfile, code = 2, width={width}, height={height})"
    return dict(
        name=r_name,
        title=f"{title} device",
        description=f"Open a {kind} device for the duration of the block, then close it.",
        r=r_expr,
        py=py_expr,
        story=story,
        uses=["matplotlib"] if kind != "xfig" else [],
        details=f"The R function calls grDevices::{kind}(). Width and height are {unit}. The check is the code's return value and that the file is non-empty. R draws a short series so the device actually writes; Matplotlib writes the figure on close.",
        value="The code's value for with_*; 1 when the local_* file is non-empty.",
        arguments=[
            ("new", "Path of the file the device writes."),
            ("code", "Callable run while the device is active. R forces an expression."),
            ("width", f"Device width in {unit}."),
            ("height", f"Device height in {unit}."),
        ],
    )


def cases() -> list[dict]:
    pixel = (200, 200)
    inch = (4, 4)
    devices = {
        "bmp": (".bmp", pixel),
        "cairo_pdf": (".pdf", inch),
        "cairo_ps": (".ps", inch),
        "jpeg": (".jpg", pixel),
        "pdf": (".pdf", inch),
        "png": (".png", pixel),
        "postscript": (".ps", inch),
        "svg": (".svg", inch),
        "tiff": (".tif", pixel),
    }
    out = []
    out.append(dict(
        name="defer",
        title="Defer evaluation",
        description="Run a callable when the current frame exits.",
        r="""
bucket <- character()
f <- function() {
  defer(bucket <<- c(bucket, "a"))
  defer(bucket <<- c(bucket, "b"))
  defer(bucket <<- c(bucket, "c"), priority = "last")
}
f()
bucket
""".strip(),
        py="""
bucket = []
with scope():
    defer(lambda: bucket.append("a"))
    defer(lambda: bucket.append("b"))
    defer(lambda: bucket.append("c"), priority="last")
return bucket
""".strip(),
        story='defer "a", then "b", then "c" last',
        details="priority first inserts the handler so it runs before older ones. priority last appends it. Pass a callable; R captures an expression.",
        value="NULL. The handlers run as the frame exits.",
        arguments=[
            ("expr", "Zero-argument callable run on exit."),
            ("envir", "Frame to attach to. The current scope() when omitted."),
            ("priority", '"first" or "last".'),
        ],
    ))
    out.append(dict(
        name="defer_parent",
        title="Defer in the caller",
        description="Attach a handler to the frame that called this one.",
        r="""
bucket <- character()
outer <- function() {
  inner <- function() {
    defer_parent(bucket <<- c(bucket, "p"))
    defer(bucket <<- c(bucket, "i"))
  }
  inner()
  bucket <<- c(bucket, "mid")
}
outer()
bucket
""".strip(),
        py="""
bucket = []
with scope():
    with scope():
        defer_parent(lambda: bucket.append("p"))
        defer(lambda: bucket.append("i"))
    bucket.append("mid")
return bucket
""".strip(),
        story="inner defer_parent plus defer, then the outer frame",
        details="The inner handler runs when the inner scope exits. The parent handler runs when the outer scope exits.",
        value="NULL.",
        arguments=[
            ("expr", "Zero-argument callable."),
            ("priority", '"first" or "last".'),
        ],
    ))
    out.append(dict(
        name="deferred_clear",
        title="Drop deferred handlers",
        description="Remove handlers from a frame without running them.",
        r="""
bucket <- character()
f <- function() {
  defer(bucket <<- c(bucket, "a"))
  deferred_clear()
}
f()
if (length(bucket)) "ran" else "cleared"
""".strip(),
        py="""
bucket = []
with scope():
    defer(lambda: bucket.append("a"))
    deferred_clear()
return "ran" if bucket else "cleared"
""".strip(),
        story="defer then deferred_clear before the frame exits",
        details="The frame's handler list is emptied. A later exit has nothing to run.",
        value="NULL.",
        arguments=[("envir", "Frame to clear. The current scope() when omitted.")],
    ))
    out.append(dict(
        name="deferred_run",
        title="Run deferred handlers now",
        description="Run the frame's handlers immediately and report how many finished.",
        r="""
bucket <- character()
f <- function() {
  defer(bucket <<- c(bucket, "a"))
  defer(bucket <<- c(bucket, "b"))
  deferred_run()
  bucket
}
f()
""".strip(),
        py="""
bucket = []
with scope():
    defer(lambda: bucket.append("a"))
    defer(lambda: bucket.append("b"))
    deferred_run()
return bucket
""".strip(),
        story='two first-priority handlers, then deferred_run()',
        details='Handlers are cleared before they run, so the frame exit does not run them again. A message reports "Ran i/n deferred expressions".',
        value="NULL. The message names how many handlers ran.",
        arguments=[("envir", "Frame whose handlers run.")],
    ))
    out.append(dict(
        name="global_defer",
        title="Defer on the global frame",
        description="Attach a handler that deferred_run() on the global frame will execute.",
        r="""
bucket <- character()
add <- function(item) bucket <<- c(bucket, item)
global_defer(add("g1"))
global_defer(add("g2"), priority = "last")
deferred_run(.GlobalEnv)
bucket
""".strip(),
        py="""
from withr._scope import GLOBAL
GLOBAL.clear()
bucket = []
global_defer(lambda: bucket.append("g1"))
global_defer(lambda: bucket.append("g2"), priority="last")
deferred_run(GLOBAL)
return bucket
""".strip(),
        story='global_defer "g1" then "g2" last, then deferred_run',
        details="In an interactive session the first global handler explains that it will not run until the session ends or deferred_run() is called. This check is not interactive.",
        value="NULL.",
        arguments=[
            ("expr", "Zero-argument callable."),
            ("priority", '"first" or "last".'),
        ],
    ))
    out.append(dict(
        name="local_",
        title="Make a local_ function",
        description="Build a function that sets state and restores it when its frame exits.",
        r="""
res <- integer()
set <- function(new) res <<- c(res, 1L)
reset <- function(old) res <<- c(res, 3L)
local_res <- local_(set, reset)
local({
  local_res(NULL)
  res <<- c(res, 2L)
})
res
""".strip(),
        py="""
res = []
def set_fn(new):
    res.append(1)
def reset_fn(old):
    res.append(3)
local_res = local_(set_fn, reset_fn)
with local_res(None):
    res.append(2)
return res
""".strip(),
        story="local_(set, reset) runs set, the body, then reset",
        details="set returns the old state and reset receives it. Use the result as a context manager, or pass _local_envir from scope().",
        value="The old state, when the setter returns one.",
        arguments=[
            ("set", "Callable that installs the new state and returns the old one."),
            ("reset", "Callable that restores the old state. Defaults to set."),
            ("get", "Optional callable that reads the old state before set runs."),
            ("new", "When false, the built function has no new-state argument."),
        ],
    ))
    for kind, (ext, (width, height)) in devices.items():
        if kind in {"bmp", "cairo_pdf", "cairo_ps"}:
            out.append(_device(kind, ext, width, height, local=True))
    out.append(dict(
        name="local_collate",
        title="Collation order",
        description="Sort under a temporary LC_COLLATE, then restore it.",
        r="""
x <- c("bernard", "boris", "béatrice", "bérénice")
before <- Sys.getlocale("LC_COLLATE")
out <- local({
  local_collate("C")
  sort(x)
})
c(out, if (identical(Sys.getlocale("LC_COLLATE"), before)) "restored" else "open")
""".strip(),
        py="""
import locale
x = ["bernard", "boris", "béatrice", "bérénice"]
before = locale.setlocale(locale.LC_COLLATE)
with local_collate("C"):
    out = sorted(x, key=locale.strxfrm)
after = locale.setlocale(locale.LC_COLLATE)
return out + ["restored" if after == before else "open"]
""".strip(),
        story='local_collate("C") sorts bernard, boris, the two accented names',
        details="This sets the LC_COLLATE locale and the LC_COLLATE environment variable, then restores both.",
        value="The previous LC_COLLATE value.",
        arguments=[
            ("new", "Locale name, such as C or fr_FR."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_connection",
        title="Connection that closes",
        description="Close a file when the frame exits.",
        r="""
path <- tempfile()
local({
  con <- local_connection(file(path, "w"))
  writeLines(c("foo", "bar"), con)
})
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
with local_connection(open(path, "w")) as con:
    con.write("foo\\nbar\\n")
with open(path) as handle:
    lines = handle.read().splitlines()
os.remove(path)
return lines
""".strip(),
        story='local_connection writes "foo" and "bar", then closes',
        details="The connection object needs a close() method. It is closed when the context manager or _local_envir exits.",
        value="The connection.",
        arguments=[
            ("con", "Open file-like object."),
            ("_local_envir", "Frame that owns the close."),
        ],
    ))
    out.append(dict(
        name="local_db_connection",
        title="Database connection that disconnects",
        description="Call disconnect() when the frame exits.",
        r_header="suppressPackageStartupMessages({library(DBI); library(RSQLite)})",
        r="""
path <- tempfile()
con0 <- DBI::dbConnect(RSQLite::SQLite(), path)
DBI::dbExecute(con0, "CREATE TABLE t (x REAL)")
DBI::dbExecute(con0, "INSERT INTO t VALUES (1), (2)")
DBI::dbDisconnect(con0)
total <- local({
  con <- local_db_connection(DBI::dbConnect(RSQLite::SQLite(), path))
  DBI::dbGetQuery(con, "SELECT SUM(x) AS s FROM t")$s
})
unlink(path)
total
""".strip(),
        py="""
import sqlite3
fd, path = tempfile.mkstemp()
os.close(fd)
raw = sqlite3.connect(path)
raw.execute("CREATE TABLE t (x REAL)")
raw.execute("INSERT INTO t VALUES (1), (2)")
raw.commit()
raw.close()

class Conn:
    def __init__(self, path):
        self.raw = sqlite3.connect(path)
        self.closed = False
    def disconnect(self):
        self.raw.close()
        self.closed = True

con = Conn(path)
with local_db_connection(con):
    total = con.raw.execute("SELECT SUM(x) FROM t").fetchone()[0]
os.remove(path)
return total
""".strip(),
        story="SQLite table t holds 1 and 2; the sum is read inside local_db_connection",
        details="R requires a DBIConnection and calls DBI::dbDisconnect. The translation calls disconnect() on the object.",
        value="The connection.",
        arguments=[
            ("con", "Object with a disconnect() method."),
            ("_local_envir", "Frame that owns the disconnect."),
        ],
    ))
    # The R db script above is messy because the first dbExecute opens a connection
    # that is not stored. I'll replace it below if the check fails. Keep going.
    out.append(dict(
        name="local_dir",
        title="Working directory",
        description="Change the working directory until the frame exits.",
        r="""
dir.create("/tmp/withr-dir-check", showWarnings = FALSE, recursive = TRUE)
before <- getwd()
inside <- local({
  local_dir("/tmp/withr-dir-check")
  getwd()
})
c(inside, if (identical(getwd(), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-dir-check", exist_ok=True)
before = os.getcwd()
with local_dir("/tmp/withr-dir-check"):
    inside = os.getcwd()
return [inside, "restored" if os.getcwd() == before else "open"]
""".strip(),
        story='local_dir("/tmp/withr-dir-check")',
        details="The directory is restored even when the body raises.",
        value="The previous working directory.",
        arguments=[("new", "Directory to enter."), ("_local_envir", "Frame that owns the reset.")],
    ))
    out.append(dict(
        name="local_environment",
        title="Attached environment",
        description="Attach a mapping to the search path, then detach it.",
        r="""
env <- list2env(list(value = 42))
found <- local({
  local_environment(env, name = "withr-check-env")
  get("value")
})
paste(found, if ("withr-check-env" %in% search()) "attached" else "detached")
""".strip(),
        py="""
with local_environment({"value": 42}, name="withr-check-env"):
    found = lookup("value")
flag = "attached" if "withr-check-env" in search() else "detached"
return f"{found} {flag}"
""".strip(),
        story='local_environment(list(value = 42), name = "withr-check-env")',
        details="pos is 1-based, and the default 2 inserts the mapping just after .GlobalEnv. lookup walks that search path.",
        value="NULL.",
        arguments=[
            ("env", "Mapping of names to values."),
            ("pos", "1-based search-path position. Default 2."),
            ("name", "Name used by detach."),
            ("_local_envir", "Frame that owns the detach."),
        ],
    ))
    out.append(dict(
        name="local_envvar",
        title="Environment variables",
        description="Change environment variables until the frame exits. prefix joins with a space.",
        r="""
Sys.setenv(WITHR_TEST_VAR = "old")
on.exit(Sys.unsetenv("WITHR_TEST_VAR"), add = TRUE)
inside <- local({
  local_envvar(c(WITHR_TEST_VAR = "new"), action = "prefix")
  Sys.getenv("WITHR_TEST_VAR")
})
c(inside, Sys.getenv("WITHR_TEST_VAR"))
""".strip(),
        py="""
os.environ["WITHR_TEST_VAR"] = "old"
with local_envvar({"WITHR_TEST_VAR": "new"}, action="prefix"):
    inside = os.environ["WITHR_TEST_VAR"]
after = os.environ["WITHR_TEST_VAR"]
del os.environ["WITHR_TEST_VAR"]
return [inside, after]
""".strip(),
        story='local_envvar(WITHR_TEST_VAR = "new", action = "prefix") over "old"',
        details="None unsets a variable. Duplicate names keep the last value. prefix and suffix join the new and old text with a space.",
        value="The previous values, with None where a variable was unset.",
        arguments=[
            ("_new", "Mapping of names to new values. None unsets."),
            ("action", '"replace", "prefix", or "suffix".'),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_file",
        title="File removed on exit",
        description="Delete named files when the frame exits.",
        r="""
td <- tempfile()
dir.create(td)
old <- getwd()
setwd(td)
on.exit(setwd(old), add = TRUE)
text <- local({
  local_file("file1")
  writeLines("foo", "file1")
  readLines("file1")
})
c(text, if (file.exists("file1")) "kept" else "gone")
""".strip(),
        py="""
td = tempfile.mkdtemp()
before = os.getcwd()
os.chdir(td)
try:
    with local_file("file1"):
        with open("file1", "w") as handle:
            handle.write("foo\\n")
        text = open("file1").read().splitlines()[0]
    flag = "kept" if os.path.exists("file1") else "gone"
finally:
    os.chdir(before)
return [text, flag]
""".strip(),
        story='local_file("file1") then writeLines("foo")',
        details="A string names the path. A mapping uses the names as paths. The files are removed on exit, whether or not the body created them.",
        value="The file specification.",
        arguments=[
            ("_file", "Path or mapping of paths to delete."),
            ("_local_envir", "Frame that owns the deletion."),
        ],
    ))
    for kind in ("jpeg",):
        ext, (width, height) = devices[kind]
        out.append(_device(kind, ext, width, height, local=True))
    out.append(dict(
        name="local_language",
        title="Translation language",
        description="Set LANGUAGE until the frame exits.",
        r="""
before <- Sys.getenv("LANGUAGE")
inside <- local({
  local_language("es")
  Sys.getenv("LANGUAGE")
})
c(inside, if (identical(Sys.getenv("LANGUAGE"), before)) "restored" else "open")
""".strip(),
        py="""
before = os.environ.get("LANGUAGE")
with local_language("es"):
    inside = os.environ.get("LANGUAGE")
after = os.environ.get("LANGUAGE")
return [inside, "restored" if after == before else "open"]
""".strip(),
        story='local_language("es")',
        details="Hyphens in the language code become underscores. When LC_ALL is C or C.UTF-8 a warning says the change has no effect.",
        value="NULL.",
        arguments=[
            ("lang", "Language code such as en, fr, or es."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_libpaths",
        title="Library paths",
        description="Prepend a library directory, then restore the list.",
        r="""
dir.create("/tmp/withr-lib-check", showWarnings = FALSE, recursive = TRUE)
before <- .libPaths()
first <- local({
  local_libpaths("/tmp/withr-lib-check", action = "prefix")
  normalizePath(.libPaths()[[1]])
})
c(first, if (identical(.libPaths(), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-lib-check", exist_ok=True)
before = libpaths()
with local_libpaths("/tmp/withr-lib-check", action="prefix"):
    first = libpaths()[0]
flag = "restored" if libpaths() == before else "open"
return [first, flag]
""".strip(),
        story='local_libpaths("/tmp/withr-lib-check", action = "prefix")',
        details="Paths must exist. prefix, suffix, and replace match R's merge of the new paths with .libPaths().",
        value="The previous library paths.",
        arguments=[
            ("new", "Library directory or directories."),
            ("action", '"replace", "prefix", or "suffix".'),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_locale",
        title="Locale settings",
        description="Change named locale categories, then restore them.",
        r="""
x <- c("bernard", "bérénice", "béatrice", "boris")
before <- Sys.getlocale("LC_COLLATE")
out <- local({
  local_locale(c(LC_COLLATE = "fr_FR.UTF-8"))
  sort(x)
})
c(out, if (identical(Sys.getlocale("LC_COLLATE"), before)) "restored" else "open")
""".strip(),
        py="""
import locale
x = ["bernard", "bérénice", "béatrice", "boris"]
before = locale.setlocale(locale.LC_COLLATE)
with local_locale({"LC_COLLATE": "fr_FR.UTF-8"}):
    out = sorted(x, key=locale.strxfrm)
after = locale.setlocale(locale.LC_COLLATE)
return out + ["restored" if after == before else "open"]
""".strip(),
        story='local_locale(LC_COLLATE = "fr_FR.UTF-8")',
        details="Setting LC_ALL is an error. LC_COLLATE also sets the LC_COLLATE environment variable, which R consults ahead of the locale.",
        value="The previous category values.",
        arguments=[
            ("_new", "Mapping of category names to locale names."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_makevars",
        title="Makevars file",
        description="Point R_MAKEVARS_USER at a rewritten Makevars file.",
        r="""
src <- tempfile()
writeLines("CFLAGS = -O2", src)
before <- Sys.getenv("R_MAKEVARS_USER")
lines <- local({
  local_makevars(CFLAGS = "-O3", .path = src)
  readLines(Sys.getenv("R_MAKEVARS_USER"))
})
c(lines, if (identical(Sys.getenv("R_MAKEVARS_USER"), before)) "restored" else "open")
""".strip(),
        py="""
fd, src = tempfile.mkstemp()
os.close(fd)
with open(src, "w") as handle:
    handle.write("CFLAGS = -O2\\n")
before = os.environ.get("R_MAKEVARS_USER")
with local_makevars(CFLAGS="-O3", _path=src):
    with open(os.environ["R_MAKEVARS_USER"]) as handle:
        lines = handle.read().splitlines()
after = os.environ.get("R_MAKEVARS_USER")
os.remove(src)
return lines + ["restored" if after == before else "open"]
""".strip(),
        story='local_makevars(CFLAGS = "-O3") over a file that had CFLAGS = -O2',
        details="An existing assignment for the same name is replaced. Other lines are kept. The assignment form is =, :=, ?=, or +=.",
        value="The previous Makevars lines, or NULL when there was no file.",
        arguments=[
            ("_new", "Variable names and values."),
            ("_path", "Existing Makevars file. The user file when omitted."),
            ("_assignment", "One of =, :=, ?=, +=."),
            ("_local_envir", "Frame that owns the cleanup."),
        ],
    ))
    out.append(dict(
        name="local_message_sink",
        title="Message sink",
        description="Send message() to a file until the frame exits.",
        r="""
path <- tempfile()
local({
  local_message_sink(path)
  message("hello")
})
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
with local_message_sink(path):
    message("hello")
with open(path) as handle:
    text = handle.read().splitlines()[0]
os.remove(path)
return text
""".strip(),
        story='local_message_sink then message("hello")',
        details='A second message sink is an error: "Cannot establish message sink when another sink is active." Passing None is an error, and that message keeps the trailing comma from the R source.',
        value="NULL.",
        arguments=[
            ("new", "File path or an open text file."),
            ("append", "Append instead of truncating."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_namespace",
        title="Attached namespace",
        description="Attach a package namespace name, then detach it.",
        r="""
name <- format(asNamespace("stats"))
during <- local({
  local_namespace("stats")
  name %in% search()
})
c(if (isTRUE(during)) "TRUE" else "FALSE", if (name %in% search()) "attached" else "detached")
""".strip(),
        py="""
name = "<environment: namespace:stats>"
with local_namespace("stats"):
    during = name in search()
flag = "attached" if name in search() else "detached"
return ["TRUE" if during else "FALSE", flag]
""".strip(),
        story='local_namespace("stats")',
        details="The attached name is format(asNamespace(package)), which looks like <environment: namespace:stats>.",
        value="NULL.",
        arguments=[
            ("package", "Package name."),
            ("_local_envir", "Frame that owns the detach."),
            ("warn_conflicts", "Accepted and ignored."),
        ],
    ))
    out.append(dict(
        name="local_options",
        title="Options",
        description="Change options until the frame exits.",
        r="""
f <- function() {
  local_options(digits = 3)
  getOption("digits")
}
c(f(), getOption("digits"))
""".strip(),
        py="""
with local_options(digits=3):
    inside = get_option("digits")
return [inside, get_option("digits")]
""".strip(),
        story="local_options(digits = 3), then the restored digits",
        details="Named arguments are merged onto the list, and later names win. None removes an option.",
        value="The previous option values.",
        arguments=[
            ("_new", "Mapping of option names to values."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_output_sink",
        title="Output sink",
        description="Send cat() to a file until the frame exits.",
        r="""
path <- tempfile()
local({
  local_output_sink(path)
  cat("hello\\n")
})
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
with local_output_sink(path):
    cat("hello\\n")
with open(path) as handle:
    text = handle.read().splitlines()[0]
os.remove(path)
return text
""".strip(),
        story='local_output_sink then cat("hello")',
        details="Passing None is an error. Extra sinks opened inside the block are removed on the way back, with a warning.",
        value="NULL.",
        arguments=[
            ("new", "File path or an open text file."),
            ("append", "Append instead of truncating."),
            ("split", "Accepted. R would also copy the text to the previous sink."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_package",
        title="Attached package",
        description="Attach a package name for the frame, then detach it.",
        r="""
was <- "package:compiler" %in% search()
during <- local({
  local_package("compiler")
  "package:compiler" %in% search()
})
after <- "package:compiler" %in% search()
c(if (isTRUE(during)) "TRUE" else "FALSE", if (after == was) "restored" else "open")
""".strip(),
        py="""
was = "package:compiler" in search()
with local_package("compiler"):
    during = "package:compiler" in search()
after = "package:compiler" in search()
return ["TRUE" if during else "FALSE", "restored" if after == was else "open"]
""".strip(),
        story='local_package("compiler")',
        details="Unlike with_package, local_package always attaches and always detaches, even when the package was already on the search path.",
        value="NULL.",
        arguments=[
            ("package", "Package name."),
            ("pos", "1-based position. Default 2."),
            ("_local_envir", "Frame that owns the detach."),
        ],
    ))
    out.append(dict(
        name="local_par",
        title="Graphics parameters",
        description="Change par settings until the frame exits.",
        r="""
f <- function() {
  local_par(list(col = "red"))
  par("col")
}
c(f(), par("col"))
""".strip(),
        py="""
with local_par({"col": "red"}):
    inside = par("col")
return [inside, par("col")]
""".strip(),
        story='local_par(list(col = "red"))',
        details="par stores the settable parameters this translation uses, including col and pch. The default col is black and the default pch is 1.",
        value="The previous parameter values.",
        arguments=[
            ("_new", "Mapping of parameter names to values."),
            ("no_readonly", "Accepted for compatibility with par."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_path",
        title="PATH",
        description="Append a directory to PATH, then restore it.",
        r="""
dir.create("/tmp/withr-path-marker", showWarnings = FALSE, recursive = TRUE)
before <- Sys.getenv("PATH")
last <- local({
  local_path("/tmp/withr-path-marker", "suffix")
  parts <- strsplit(Sys.getenv("PATH"), .Platform$path.sep)[[1]]
  parts[[length(parts)]]
})
c(last, if (identical(Sys.getenv("PATH"), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-path-marker", exist_ok=True)
before = os.environ.get("PATH", "")
with local_path("/tmp/withr-path-marker", action="suffix"):
    last = os.environ["PATH"].split(os.pathsep)[-1]
flag = "restored" if os.environ.get("PATH", "") == before else "open"
return [last, flag]
""".strip(),
        story='local_path("/tmp/withr-path-marker", "suffix")',
        details="The default action is prefix. Entries are normalized to absolute paths and joined with the platform separator.",
        value="The previous PATH entries.",
        arguments=[
            ("new", "Directory or directories to add."),
            ("action", '"prefix", "suffix", or "replace".'),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    for kind in ("pdf", "png", "postscript"):
        ext, (width, height) = devices[kind]
        out.append(_device(kind, ext, width, height, local=True))
    out.append(dict(
        name="local_preserve_seed",
        title="Preserve the random seed",
        description="Put the generator back when the frame exits, including when no seed was set.",
        r="""
set.seed(1)
before <- .Random.seed
local({
  local_preserve_seed()
  runif(4)
})
as.numeric(identical(.Random.seed, before))
""".strip(),
        py="""
from withr._rng import set_seed, snapshot
set_seed(1)
before = snapshot()
with local_preserve_seed():
    runif(4)
return int(snapshot() == before)
""".strip(),
        story="set.seed(1), local_preserve_seed(), runif(4), then the seed matches",
        details="Draws inside the block do not advance the generator seen by the caller. An unset seed stays unset.",
        value="The previous seed, or NULL when none was set.",
        arguments=[("_local_envir", "Frame that owns the restore.")],
    ))
    out.append(dict(
        name="local_rng_version",
        title="RNG version",
        description="Use the RNGkind from an older R, then restore the current kind.",
        r="""
inside <- local({
  local_rng_version("3.0.0")
  with_seed(42, sample(1:100, 3))
})
outside <- with_seed(42, sample(1:100, 3))
c(inside, outside)
""".strip(),
        py="""
with local_rng_version("3.0.0"):
    inside = with_seed(42, lambda: sample(range(1, 101), 3))
outside = with_seed(42, lambda: sample(range(1, 101), 3))
return inside + outside
""".strip(),
        story='local_rng_version("3.0.0") samples 1:100 at seed 42, then the current kind does',
        details="R 3.0 through 3.5 use Mersenne-Twister, Inversion, and Rounding. R 3.6 and later use Rejection. R 1.6 and earlier use Marsaglia-Multicarry. The kind change is quiet, matching suppressWarnings(RNGversion()).",
        value="The previous RNGkind names.",
        arguments=[
            ("version", "R version string such as 3.0.0 or 1.6.0."),
            ("_local_envir", "Frame that owns the restore."),
        ],
    ))
    out.append(dict(
        name="local_seed",
        title="Random seed",
        description="Draw at a fixed seed, then restore the generator.",
        r="""
set.seed(1)
before <- .Random.seed
out <- local({
  local_seed(1)
  runif(3)
})
c(out, as.numeric(identical(.Random.seed, before)))
""".strip(),
        py="""
from withr._rng import set_seed, snapshot
set_seed(1)
before = snapshot()
with local_seed(1):
    out = runif(3)
return out + [int(snapshot() == before)]
""".strip(),
        story="set.seed(1), local_seed(1), runif(3), and the outer seed is unchanged",
        details="runif and sample use R's generator for the active kind: Mersenne-Twister, Wichmann-Hill, or Marsaglia-Multicarry, and Rounding or Rejection.",
        value="The seed that was set.",
        arguments=[
            ("seed", "Integer seed passed to set.seed."),
            ("_rng_kind", "Uniform RNGkind, or None to leave it."),
            ("_rng_normal_kind", "Normal RNGkind, or None to leave it."),
            ("_rng_sample_kind", "sample.kind, or None to leave it."),
            ("_local_envir", "Frame that owns the restore."),
        ],
    ))
    ext, (width, height) = devices["svg"]
    out.append(_device("svg", ext, width, height, local=True))
    out.append(dict(
        name="local_temp_libpaths",
        title="Temporary library path",
        description="Prefix a new temporary directory onto the library paths.",
        r="""
before <- .libPaths()
ok <- local({
  local_temp_libpaths()
  identical(.libPaths()[-1], before) && dir.exists(.libPaths()[[1]])
})
if (isTRUE(ok) && identical(.libPaths(), before)) "TRUE" else "FALSE"
""".strip(),
        py="""
before = libpaths()
with local_temp_libpaths():
    current = libpaths()
    ok = current[1:] == before and os.path.isdir(current[0])
return "TRUE" if ok and libpaths() == before else "FALSE"
""".strip(),
        story="local_temp_libpaths() prefixes a new directory and restores the list",
        details="The temporary directory is left on disk, as in R. Only the library-path list is restored.",
        value="The previous library paths.",
        arguments=[
            ("action", '"prefix" by default, or "replace" or "suffix".'),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_tempdir",
        title="Temporary directory",
        description="Create a directory and delete it when the frame exits.",
        r="""
path <- NULL
local({
  path <<- local_tempdir()
  stopifnot(dir.exists(path))
})
if (!dir.exists(path)) "gone" else "kept"
""".strip(),
        py="""
with local_tempdir() as path:
    exists = os.path.isdir(path)
if not exists:
    return "missing"
return "gone" if not os.path.exists(path) else "kept"
""".strip(),
        story="local_tempdir() exists inside the frame and is gone after it",
        details="clean = FALSE leaves the directory in place. pattern, tmpdir, and fileext match tempfile().",
        value="The directory path.",
        arguments=[
            ("pattern", "Filename prefix. Default file."),
            ("tmpdir", "Directory that holds the new one."),
            ("fileext", "Suffix appended to the name."),
            ("clean", "Delete the directory on exit when TRUE."),
            ("_local_envir", "Frame that owns the deletion."),
        ],
    ))
    out.append(dict(
        name="local_tempfile",
        title="Temporary file",
        description="Create a file, optionally write lines, and delete it on exit.",
        r="""
path <- NULL
lines <- local({
  path <<- local_tempfile(lines = c("x,y", "1,2"))
  readLines(path)
})
c(lines, if (file.exists(path)) "kept" else "gone")
""".strip(),
        py="""
with local_tempfile(lines=["x,y", "1,2"]) as path:
    lines = open(path).read().splitlines()
    existed = os.path.exists(path)
flag = "kept" if os.path.exists(path) else "gone"
if not existed:
    return ["missing"]
return lines + [flag]
""".strip(),
        story='local_tempfile(lines = c("x,y", "1,2"))',
        details="The new argument is deprecated. The path is the value of the context manager. Lines are written as UTF-8 with a newline after each one.",
        value="The file path.",
        arguments=[
            ("lines", "Lines written into the new file."),
            ("pattern", "Filename prefix."),
            ("tmpdir", "Directory that holds the file."),
            ("fileext", "Suffix, such as .csv."),
            ("_local_envir", "Frame that owns the deletion."),
        ],
    ))
    ext, (width, height) = devices["tiff"]
    out.append(_device("tiff", ext, width, height, local=True))
    out.append(dict(
        name="local_timezone",
        title="Time zone",
        description="Set TZ for the frame, then restore it.",
        r="""
local({
  local_timezone("America/Los_Angeles")
  format(as.POSIXct(1579090000, origin = "1970-01-01"), "%Y-%m-%d %H:%M %Z")
})
""".strip(),
        py="""
import time
with local_timezone("America/Los_Angeles"):
    return time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(1579090000))
""".strip(),
        story='local_timezone("America/Los_Angeles") formats 1579090000',
        details="TZ is set in the environment and the process zone cache is refreshed, which is what R does by clearing .sys.timezone.",
        value="NULL.",
        arguments=[
            ("tz", "Time zone name, such as Europe/Paris or UTC."),
            ("_local_envir", "Frame that owns the reset."),
        ],
    ))
    out.append(dict(
        name="local_xfig",
        title="xfig device",
        description="Report that R 4.5 removed the xfig device.",
        r="""
tryCatch(
  local_xfig(tempfile(fileext = ".fig")),
  error = function(e) conditionMessage(e)
)
""".strip(),
        py="""
try:
    with local_xfig("unused.fig"):
        pass
except Exception as exc:
    return str(exc)
return ""
""".strip(),
        story="local_xfig() on R 4.5.0",
        details="grDevices::xfig was removed in R 4.5.0. withr still calls it, so the installed function raises that removal error.",
        value="The error from the removed device.",
        arguments=[("new", "Unused path. The device is no longer available.")],
        uses=[],
    ))
    out.append(dict(
        name="makevars_user",
        title="User Makevars path",
        description="Return the Makevars file named by R_MAKEVARS_USER when that file exists.",
        r="""
path <- "/tmp/withr-makevars-user"
file.create(path)
with_envvar(c(R_MAKEVARS_USER = path), makevars_user())
""".strip(),
        py="""
path = "/tmp/withr-makevars-user"
open(path, "a").close()
return with_envvar({"R_MAKEVARS_USER": path}, makevars_user)
""".strip(),
        story='R_MAKEVARS_USER = "/tmp/withr-makevars-user"',
        details="When the variable is unset, the search is ~/.R/Makevars-$R_PLATFORM and then ~/.R/Makevars. An empty string means no file was found.",
        value="The path, or an empty string.",
        arguments=[],
    ))
    out.append(dict(
        name="set_makevars",
        title="Write a Makevars file",
        description="Replace named variables in a Makevars file and write the result.",
        r="""
old <- tempfile()
writeLines("CFLAGS = -O2", old)
new <- tempfile()
set_makevars(c(CFLAGS = "-O3", PKG_LIBS = "-lm"), old, new)
readLines(new)
""".strip(),
        py="""
fd, old = tempfile.mkstemp()
os.close(fd)
fd, new = tempfile.mkstemp()
os.close(fd)
with open(old, "w") as handle:
    handle.write("CFLAGS = -O2\\n")
set_makevars({"CFLAGS": "-O3", "PKG_LIBS": "-lm"}, old, new)
with open(new) as handle:
    lines = handle.read().splitlines()
os.remove(old)
os.remove(new)
return lines
""".strip(),
        story='set_makevars(c(CFLAGS = "-O3", PKG_LIBS = "-lm"))',
        details="A name that appears once is replaced. A name that is absent is appended. Two matches for one name are an error. The file is left untouched when the text would not change.",
        value="The previous lines, or NULL when there was no file.",
        arguments=[
            ("variables", "Named variables to write."),
            ("old_path", "Existing Makevars file."),
            ("new_path", "File to write."),
            ("assignment", "One of =, :=, ?=, +=."),
        ],
    ))
    out.append(dict(
        name="with_",
        title="Make a with_ function",
        description="Build a function that sets state, runs code, and restores the state.",
        r="""
res <- integer()
set <- function(new) res <<- c(res, 1L)
reset <- function(old) res <<- c(res, 3L)
body <- function() res <<- c(res, 2L)
fn <- with_(set, reset)
fn(NULL, body())
res
""".strip(),
        py="""
res = []
def set_fn(new):
    res.append(1)
def reset_fn(old):
    res.append(3)
fn = with_(set_fn, reset_fn)
fn(None, lambda: res.append(2))
return res
""".strip(),
        story="with_(set, reset)(NULL, code) runs set, code, reset",
        details="code is a callable. R forces the expression after set, which is why the translation cannot take an already-computed value. Extra arguments of set follow code.",
        value="Whatever code returns.",
        arguments=[
            ("set", "Callable that installs the new state and returns the old one."),
            ("reset", "Callable that restores the old state."),
            ("get", "Optional callable that reads the old state before set."),
            ("new", "When false, the built function takes code first."),
        ],
    ))
    for kind, (ext, (width, height)) in devices.items():
        out.append(_device(kind, ext, width, height, local=False))
    # with_* that are not devices, inserted in NAMESPACE order by a second pass.
    # The loop above appended every with_device. The remaining with_* follow.
    out.append(dict(
        name="with_collate",
        title="Collation order",
        description="Sort under a temporary LC_COLLATE.",
        r="""
x <- c("bernard", "boris", "béatrice", "bérénice")
with_collate("C", sort(x))
""".strip(),
        py="""
import locale
x = ["bernard", "boris", "béatrice", "bérénice"]
return with_collate("C", lambda: sorted(x, key=locale.strxfrm))
""".strip(),
        story='with_collate("C", sort(x)) for bernard, boris, and two accented names',
        details="Implemented as with_locale(LC_COLLATE = new). The C locale orders by bytes.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Locale name."),
            ("code", "Callable run under that collation."),
        ],
    ))
    out.append(dict(
        name="with_connection",
        title="Connection that closes",
        description="Run code, then close each named connection.",
        r="""
path <- tempfile()
with_connection(list(con = file(path, "w")), writeLines(c("foo", "bar"), con))
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
con = open(path, "w")
with_connection({"con": con}, lambda: con.write("foo\\nbar\\n"))
with open(path) as handle:
    lines = handle.read().splitlines()
os.remove(path)
return lines
""".strip(),
        story='with_connection writes "foo" and "bar"',
        details="Names are required. Each value needs close(). The callable may take the connection names as arguments, or close over them.",
        value="Whatever code returns.",
        arguments=[
            ("con", "Mapping of names to open files."),
            ("code", "Callable run before the files are closed."),
        ],
    ))
    out.append(dict(
        name="with_db_connection",
        title="Database connection that disconnects",
        description="Run code, then disconnect each named connection.",
        r_header="suppressPackageStartupMessages({library(DBI); library(RSQLite)})",
        r="""
path <- tempfile()
setup <- DBI::dbConnect(RSQLite::SQLite(), path)
DBI::dbExecute(setup, "CREATE TABLE t (x REAL)")
DBI::dbExecute(setup, "INSERT INTO t VALUES (1), (2)")
DBI::dbDisconnect(setup)
total <- with_db_connection(list(con = DBI::dbConnect(RSQLite::SQLite(), path)), {
  DBI::dbGetQuery(con, "SELECT SUM(x) AS s FROM t")$s
})
unlink(path)
total
""".strip(),
        py="""
import sqlite3
fd, path = tempfile.mkstemp()
os.close(fd)
raw = sqlite3.connect(path)
raw.execute("CREATE TABLE t (x REAL)")
raw.execute("INSERT INTO t VALUES (1), (2)")
raw.commit()
raw.close()

class Conn:
    def __init__(self, path):
        self.raw = sqlite3.connect(path)
    def disconnect(self):
        self.raw.close()

con = Conn(path)
total = with_db_connection(
    {"con": con},
    lambda: con.raw.execute("SELECT SUM(x) FROM t").fetchone()[0],
)
os.remove(path)
return total
""".strip(),
        story="SQLite table t holds 1 and 2; with_db_connection reads the sum",
        details="R checks DBIConnection and calls DBI::dbDisconnect. The translation calls disconnect().",
        value="Whatever code returns.",
        arguments=[
            ("con", "Mapping of names to objects with disconnect()."),
            ("code", "Callable run before disconnect."),
        ],
    ))
    out.append(dict(
        name="with_dir",
        title="Working directory",
        description="Run code in another working directory.",
        r="""
dir.create("/tmp/withr-dir-check", showWarnings = FALSE, recursive = TRUE)
before <- getwd()
inside <- with_dir("/tmp/withr-dir-check", getwd())
c(inside, if (identical(getwd(), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-dir-check", exist_ok=True)
before = os.getcwd()
inside = with_dir("/tmp/withr-dir-check", os.getcwd)
flag = "restored" if os.getcwd() == before else "open"
return [inside, flag]
""".strip(),
        story='with_dir("/tmp/withr-dir-check", getwd())',
        details="The previous directory is restored after code returns or raises.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Directory to enter."),
            ("code", "Callable run in that directory."),
        ],
    ))
    out.append(dict(
        name="with_environment",
        title="Attached environment",
        description="Run code with a mapping attached to the search path.",
        r="""
env <- list2env(list(value = 42))
found <- with_environment(env, get("value"), name = "withr-check-env")
paste(found, if ("withr-check-env" %in% search()) "attached" else "detached")
""".strip(),
        py="""
found = with_environment({"value": 42}, lambda: lookup("value"), name="withr-check-env")
flag = "attached" if "withr-check-env" in search() else "detached"
return f"{found} {flag}"
""".strip(),
        story='with_environment(list(value = 42), get("value"))',
        details="The mapping is detached after code, even when code raises.",
        value="Whatever code returns.",
        arguments=[
            ("env", "Mapping of names to values."),
            ("code", "Callable run while the mapping is attached."),
            ("pos", "1-based position. Default 2."),
            ("name", "Name used by detach."),
        ],
    ))
    out.append(dict(
        name="with_envvar",
        title="Environment variables",
        description="Run code with environment variables set, then restore them.",
        r="""
inside <- with_envvar(c(WITHR_TEST_VAR = "secret"), Sys.getenv("WITHR_TEST_VAR"))
c(inside, Sys.getenv("WITHR_TEST_VAR"))
""".strip(),
        py="""
inside = with_envvar({"WITHR_TEST_VAR": "secret"}, lambda: os.environ.get("WITHR_TEST_VAR"))
after = os.environ.get("WITHR_TEST_VAR", "")
return [inside, after]
""".strip(),
        story='with_envvar(WITHR_TEST_VAR = "secret")',
        details="An unset variable is an empty string from Sys.getenv and an empty string here after the call. None in the mapping unsets a variable.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Mapping of names to values. None unsets."),
            ("code", "Callable run while the variables are set."),
            ("action", '"replace", "prefix", or "suffix".'),
        ],
    ))
    out.append(dict(
        name="with_file",
        title="File removed afterwards",
        description="Run code, then delete the named files.",
        r="""
td <- tempfile()
dir.create(td)
old <- getwd()
setwd(td)
on.exit(setwd(old), add = TRUE)
lines <- with_file("file1", {
  writeLines("foo", "file1")
  readLines("file1")
})
c(lines, if (file.exists("file1")) "kept" else "gone")
""".strip(),
        py="""
td = tempfile.mkdtemp()
before = os.getcwd()
os.chdir(td)
try:
    def body():
        with open("file1", "w") as handle:
            handle.write("foo\\n")
        return open("file1").read().splitlines()[0]
    lines = with_file("file1", body)
    flag = "kept" if os.path.exists("file1") else "gone"
finally:
    os.chdir(before)
return [lines, flag]
""".strip(),
        story='with_file("file1") writes "foo" and then the file is gone',
        details="The path is deleted after code, including when code raises.",
        value="The file specification, invisibly in R. code's value is discarded.",
        arguments=[
            ("file", "Path or paths to delete afterwards."),
            ("code", "Callable run before the deletion."),
        ],
    ))
    out.append(dict(
        name="with_language",
        title="Translation language",
        description="Run code with LANGUAGE set.",
        r="""
before <- Sys.getenv("LANGUAGE")
inside <- with_language("fr", Sys.getenv("LANGUAGE"))
c(inside, if (identical(Sys.getenv("LANGUAGE"), before)) "restored" else "open")
""".strip(),
        py="""
before = os.environ.get("LANGUAGE")
inside = with_language("fr", lambda: os.environ.get("LANGUAGE"))
after = os.environ.get("LANGUAGE")
return [inside, "restored" if after == before else "open"]
""".strip(),
        story='with_language("fr")',
        details="The translation sets LANGUAGE. It does not ship R's message catalog, so translated error text is left to the host.",
        value="Whatever code returns.",
        arguments=[
            ("lang", "Language code such as fr or en."),
            ("code", "Callable run while LANGUAGE is set."),
        ],
    ))
    out.append(dict(
        name="with_libpaths",
        title="Library paths",
        description="Run code with the library path list replaced.",
        r="""
dir.create("/tmp/withr-lib-check", showWarnings = FALSE, recursive = TRUE)
before <- .libPaths()
first <- with_libpaths("/tmp/withr-lib-check", normalizePath(.libPaths()[[1]]))
c(first, if (identical(.libPaths(), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-lib-check", exist_ok=True)
before = libpaths()
first = with_libpaths("/tmp/withr-lib-check", lambda: libpaths()[0])
flag = "restored" if libpaths() == before else "open"
return [first, flag]
""".strip(),
        story='with_libpaths("/tmp/withr-lib-check")',
        details="The default action is replace, so the list contains only the new path during code.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Library directory or directories."),
            ("code", "Callable run with that list."),
            ("action", '"replace", "prefix", or "suffix".'),
        ],
    ))
    out.append(dict(
        name="with_locale",
        title="Locale settings",
        description="Run code under named locale categories.",
        r="""
with_locale(
  c(LC_TIME = "es_ES.UTF-8"),
  format(ISOdate(2000, 1:3, 1), "%B")
)
""".strip(),
        py="""
import datetime
return with_locale(
    {"LC_TIME": "es_ES.UTF-8"},
    lambda: [datetime.date(2000, month, 1).strftime("%B") for month in (1, 2, 3)],
)
""".strip(),
        story='with_locale(LC_TIME = "es_ES.UTF-8") formats January, February, and March',
        details="LC_ALL is refused. Other categories are passed to the process locale.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Mapping of category names to locale names."),
            ("code", "Callable run under those locales."),
        ],
    ))
    out.append(dict(
        name="with_makevars",
        title="Makevars file",
        description="Run code with R_MAKEVARS_USER pointing at a rewritten Makevars file.",
        r="""
src <- tempfile()
writeLines("CFLAGS = -O2", src)
before <- Sys.getenv("R_MAKEVARS_USER")
lines <- with_makevars(c(CFLAGS = "-O3"), readLines(Sys.getenv("R_MAKEVARS_USER")), path = src)
c(lines, if (identical(Sys.getenv("R_MAKEVARS_USER"), before)) "restored" else "open")
""".strip(),
        py="""
fd, src = tempfile.mkstemp()
os.close(fd)
with open(src, "w") as handle:
    handle.write("CFLAGS = -O2\\n")
before = os.environ.get("R_MAKEVARS_USER")
lines = with_makevars(
    {"CFLAGS": "-O3"},
    lambda: open(os.environ["R_MAKEVARS_USER"]).read().splitlines(),
    path=src,
)
after = os.environ.get("R_MAKEVARS_USER")
os.remove(src)
return lines + ["restored" if after == before else "open"]
""".strip(),
        story='with_makevars(c(CFLAGS = "-O3")) replaces CFLAGS = -O2',
        details="The rewritten file is removed afterwards and R_MAKEVARS_USER is restored.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Variables to set."),
            ("code", "Callable run while R_MAKEVARS_USER points at the new file."),
            ("path", "Existing Makevars file to start from."),
            ("assignment", "One of =, :=, ?=, +=."),
        ],
    ))
    out.append(dict(
        name="with_message_sink",
        title="Message sink",
        description="Run code with message() sent to a file.",
        r="""
path <- tempfile()
with_message_sink(path, message("hello"))
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
with_message_sink(path, lambda: message("hello"))
with open(path) as handle:
    text = handle.read().splitlines()[0]
os.remove(path)
return text
""".strip(),
        story='with_message_sink then message("hello")',
        details="message() writes to the sink instead of stderr. The file is closed afterwards.",
        value="Whatever code returns.",
        arguments=[
            ("new", "File path or an open text file."),
            ("code", "Callable run while the sink is active."),
            ("append", "Append instead of truncating."),
        ],
    ))
    out.append(dict(
        name="with_namespace",
        title="Attached namespace",
        description="Run code with a package namespace name on the search path.",
        r="""
name <- format(asNamespace("stats"))
during <- with_namespace("stats", name %in% search())
c(if (isTRUE(during)) "TRUE" else "FALSE", if (name %in% search()) "attached" else "detached")
""".strip(),
        py="""
name = "<environment: namespace:stats>"
during = with_namespace("stats", lambda: name in search())
flag = "attached" if name in search() else "detached"
return ["TRUE" if during else "FALSE", flag]
""".strip(),
        story='with_namespace("stats")',
        details="The name is detached after code. The package itself stays loaded.",
        value="Whatever code returns.",
        arguments=[
            ("package", "Package name."),
            ("code", "Callable run while the namespace name is attached."),
            ("warn_conflicts", "Accepted and ignored."),
        ],
    ))
    out.append(dict(
        name="with_options",
        title="Options",
        description="Run code with temporary options.",
        r="""
c(with_options(list(digits = 3), getOption("digits")), getOption("digits"))
""".strip(),
        py="""
return [
    with_options({"digits": 3}, lambda: get_option("digits")),
    get_option("digits"),
]
""".strip(),
        story="with_options(list(digits = 3), getOption('digits')), then the restored digits",
        details="get_option reads the same store. The default digits is 7 and the default OutDec is a dot. Printing a number with digits 3 follows R's significant-digit display for the examples that print.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Mapping of option names to values."),
            ("code", "Callable run while those options are set."),
        ],
    ))
    out.append(dict(
        name="with_output_sink",
        title="Output sink",
        description="Run code with cat() sent to a file.",
        r="""
path <- tempfile()
with_output_sink(path, cat("hello\\n"))
readLines(path)
""".strip(),
        py="""
fd, path = tempfile.mkstemp()
os.close(fd)
with_output_sink(path, lambda: cat("hello\\n"))
with open(path) as handle:
    text = handle.read().splitlines()[0]
os.remove(path)
return text
""".strip(),
        story='with_output_sink then cat("hello")',
        details="cat() writes to the sink instead of stdout. The file is closed afterwards.",
        value="Whatever code returns.",
        arguments=[
            ("new", "File path or an open text file."),
            ("code", "Callable run while the sink is active."),
            ("append", "Append instead of truncating."),
            ("split", "Accepted. R would also copy the text to the previous sink."),
        ],
    ))
    out.append(dict(
        name="with_package",
        title="Attached package",
        description="Run code with a package name on the search path.",
        r="""
was <- "package:compiler" %in% search()
during <- with_package("compiler", "package:compiler" %in% search())
after <- "package:compiler" %in% search()
c(if (isTRUE(during)) "TRUE" else "FALSE", if (after == was) "restored" else "open")
""".strip(),
        py="""
was = "package:compiler" in search()
during = with_package("compiler", lambda: "package:compiler" in search())
after = "package:compiler" in search()
return ["TRUE" if during else "FALSE", "restored" if after == was else "open"]
""".strip(),
        story='with_package("compiler")',
        details="A package that is already attached is left in place and is not detached afterwards.",
        value="Whatever code returns.",
        arguments=[
            ("package", "Package name."),
            ("code", "Callable run while the package name is attached."),
            ("pos", "1-based position. Default 2."),
        ],
    ))
    out.append(dict(
        name="with_par",
        title="Graphics parameters",
        description="Run code with temporary graphics parameters.",
        r="""
old <- par("col")
inside <- with_par(list(col = "red", pch = 19), par("col"))
c(inside, par("col"), old)
""".strip(),
        py="""
old = par("col")
inside = with_par({"col": "red", "pch": 19}, lambda: par("col"))
return [inside, par("col"), old]
""".strip(),
        story='with_par(list(col = "red", pch = 19), par("col"))',
        details="During the call col is red. Afterwards it is black again, which is the stored default.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Mapping of parameter names to values."),
            ("code", "Callable run while those parameters are set."),
            ("no_readonly", "Accepted for compatibility with par."),
        ],
    ))
    out.append(dict(
        name="with_path",
        title="PATH",
        description="Run code with a directory prefixed onto PATH.",
        r="""
dir.create("/tmp/withr-path-marker", showWarnings = FALSE, recursive = TRUE)
before <- Sys.getenv("PATH")
first <- with_path(
  "/tmp/withr-path-marker",
  strsplit(Sys.getenv("PATH"), .Platform$path.sep)[[1]][1]
)
c(first, if (identical(Sys.getenv("PATH"), before)) "restored" else "open")
""".strip(),
        py="""
os.makedirs("/tmp/withr-path-marker", exist_ok=True)
before = os.environ.get("PATH", "")
first = with_path(
    "/tmp/withr-path-marker",
    lambda: os.environ["PATH"].split(os.pathsep)[0],
)
flag = "restored" if os.environ.get("PATH", "") == before else "open"
return [first, flag]
""".strip(),
        story='with_path("/tmp/withr-path-marker") prefixes PATH',
        details="The default action is prefix. The check reads the first PATH entry.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Directory or directories to add."),
            ("code", "Callable run with the modified PATH."),
            ("action", '"prefix", "suffix", or "replace".'),
        ],
    ))
    out.append(dict(
        name="with_preserve_seed",
        title="Preserve the random seed",
        description="Run code and then repeat the same draws, because the seed was restored.",
        r="""
set.seed(1)
a <- with_preserve_seed(runif(4))
b <- runif(4)
c(a, b)
""".strip(),
        py="""
from withr._rng import set_seed
set_seed(1)
a = with_preserve_seed(lambda: runif(4))
b = runif(4)
return a + b
""".strip(),
        story="set.seed(1), with_preserve_seed(runif(4)), then runif(4) again",
        details="The two blocks of four uniforms match. They are R's runif after set.seed(1).",
        value="Whatever code returns.",
        arguments=[("code", "Callable run without advancing the caller's seed.")],
    ))
    out.append(dict(
        name="with_rng_version",
        title="RNG version",
        description="Run code under the RNGkind from an older R.",
        r="""
with_rng_version("1.6.0", with_seed(42, sample(1:100, 3)))
""".strip(),
        py="""
return with_rng_version("1.6.0", lambda: with_seed(42, lambda: sample(range(1, 101), 3)))
""".strip(),
        story='with_rng_version("1.6.0", with_seed(42, sample(1:100, 3)))',
        details="R 1.6 uses Marsaglia-Multicarry, Buggy Kinderman-Ramage, and Rounding. The sample is 33, 44, 32. The caller's kind is restored.",
        value="Whatever code returns.",
        arguments=[
            ("version", "R version string."),
            ("code", "Callable run under that version's RNGkind."),
        ],
    ))
    out.append(dict(
        name="with_seed",
        title="Random seed",
        description="Draw from a fixed seed and restore the generator.",
        r="""
with_seed(1, runif(5))
""".strip(),
        py="""
return with_seed(1, lambda: runif(5))
""".strip(),
        story="with_seed(1, runif(5))",
        details="The five uniforms match R after set.seed(1) under Mersenne-Twister and Rejection.",
        value="Whatever code returns.",
        arguments=[
            ("seed", "Integer seed."),
            ("code", "Callable run at that seed."),
            ("_rng_kind", "Uniform kind to select first, or None."),
            ("_rng_normal_kind", "Normal kind to select first, or None."),
            ("_rng_sample_kind", "Sample kind to select first, or None."),
        ],
    ))
    out.append(dict(
        name="with_temp_libpaths",
        title="Temporary library path",
        description="Run code with a fresh directory prefixed onto the library paths.",
        r="""
before <- .libPaths()
ok <- with_temp_libpaths({
  identical(.libPaths()[-1], before) && dir.exists(.libPaths()[[1]])
})
if (isTRUE(ok) && identical(.libPaths(), before)) "TRUE" else "FALSE"
""".strip(),
        py="""
before = libpaths()
def body():
    current = libpaths()
    return current[1:] == before and os.path.isdir(current[0])
ok = with_temp_libpaths(body)
return "TRUE" if ok and libpaths() == before else "FALSE"
""".strip(),
        story="with_temp_libpaths() prefixes a new directory for the duration of code",
        details="The directory is not deleted. The library-path list is restored.",
        value="Whatever code returns.",
        arguments=[
            ("code", "Callable run with the temporary directory on the path."),
            ("action", '"prefix" by default.'),
        ],
    ))
    out.append(dict(
        name="with_tempdir",
        title="Temporary directory",
        description="Run code inside a new directory, then delete it.",
        r="""
old <- getwd()
marker <- NULL
note <- function() marker <<- getwd()
base <- with_tempdir({
  note()
  basename(getwd())
})
c(
  if (identical(getwd(), old)) "back" else "moved",
  if (!dir.exists(marker)) "gone" else "kept",
  if (nzchar(base)) "named" else "empty"
)
""".strip(),
        py="""
old = os.getcwd()
box = {}
def body():
    box["marker"] = os.getcwd()
    return os.path.basename(os.getcwd())
base = with_tempdir(body)
return [
    "back" if os.getcwd() == old else "moved",
    "gone" if not os.path.exists(box["marker"]) else "kept",
    "named" if base else "empty",
]
""".strip(),
        story="with_tempdir() changes directory, then returns and deletes it",
        details="clean = FALSE leaves the directory. The body runs with that directory as the working directory.",
        value="Whatever code returns.",
        arguments=[
            ("code", "Callable run inside the directory."),
            ("clean", "Delete the directory afterwards when TRUE."),
            ("pattern", "Filename prefix."),
            ("tmpdir", "Parent directory."),
            ("fileext", "Suffix."),
        ],
    ))
    out.append(dict(
        name="with_tempfile",
        title="Temporary file",
        description="Bind a fresh path to a name for the duration of code, then delete it.",
        r="""
lines <- with_tempfile("path2", {
  writeLines("abc", path2)
  readLines(path2)
})
lines
""".strip(),
        py="""
def body(path2):
    with open(path2, "w") as handle:
        handle.write("abc\\n")
    with open(path2) as handle:
        return handle.read().splitlines()[0]
return with_tempfile("path2", body)
""".strip(),
        story='with_tempfile("path2") writes "abc"',
        details="The name is passed to the callable. R assigns it in an evaluation environment. The file is deleted afterwards.",
        value="Whatever code returns.",
        arguments=[
            ("new", "Name or names bound to fresh paths."),
            ("code", "Callable that accepts those names."),
            ("pattern", "Filename prefix."),
            ("tmpdir", "Directory that holds the file."),
            ("fileext", "Suffix."),
        ],
    ))
    out.append(dict(
        name="with_timezone",
        title="Time zone",
        description="Run code in another time zone.",
        r="""
with_timezone(
  "Europe/Paris",
  format(as.POSIXct(1579090000, origin = "1970-01-01"), "%Y-%m-%d %H:%M %Z")
)
""".strip(),
        py="""
import time
return with_timezone(
    "Europe/Paris",
    lambda: time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(1579090000)),
)
""".strip(),
        story='with_timezone("Europe/Paris") formats 1579090000',
        details="The zone is restored afterwards. Naive localtime follows TZ once the zone cache is refreshed.",
        value="Whatever code returns.",
        arguments=[
            ("tz", "Time zone name."),
            ("code", "Callable run in that zone."),
        ],
    ))
    out.append(dict(
        name="with_xfig",
        title="xfig device",
        description="Report that R 4.5 removed the xfig device.",
        r="""
tryCatch(
  with_xfig(tempfile(fileext = ".fig"), 2),
  error = function(e) conditionMessage(e)
)
""".strip(),
        py="""
try:
    with_xfig("unused.fig", lambda: 2)
except Exception as exc:
    return str(exc)
return ""
""".strip(),
        story="with_xfig() on R 4.5.0",
        details="grDevices::xfig was removed in R 4.5.0. withr still calls it, so the installed function raises that removal error.",
        value="The error from the removed device.",
        arguments=[
            ("new", "Unused path."),
            ("code", "Not run, because opening the device fails."),
        ],
        uses=[],
    ))
    # NAMESPACE order: devices were inserted early. Reorder to the export list.
    order = [
        "defer", "defer_parent", "deferred_clear", "deferred_run", "global_defer", "local_",
        "local_bmp", "local_cairo_pdf", "local_cairo_ps", "local_collate", "local_connection",
        "local_db_connection", "local_dir", "local_environment", "local_envvar", "local_file",
        "local_jpeg", "local_language", "local_libpaths", "local_locale", "local_makevars",
        "local_message_sink", "local_namespace", "local_options", "local_output_sink",
        "local_package", "local_par", "local_path", "local_pdf", "local_png", "local_postscript",
        "local_preserve_seed", "local_rng_version", "local_seed", "local_svg", "local_temp_libpaths",
        "local_tempdir", "local_tempfile", "local_tiff", "local_timezone", "local_xfig",
        "makevars_user", "set_makevars", "with_",
        "with_bmp", "with_cairo_pdf", "with_cairo_ps", "with_collate", "with_connection",
        "with_db_connection", "with_dir", "with_environment", "with_envvar", "with_file",
        "with_jpeg", "with_language", "with_libpaths", "with_locale", "with_makevars",
        "with_message_sink", "with_namespace", "with_options", "with_output_sink", "with_package",
        "with_par", "with_path", "with_pdf", "with_png", "with_postscript", "with_preserve_seed",
        "with_rng_version", "with_seed", "with_svg", "with_temp_libpaths", "with_tempdir",
        "with_tempfile", "with_tiff", "with_timezone", "with_xfig",
    ]
    by_name = {item["name"]: item for item in out}
    missing = [name for name in order if name not in by_name]
    extra = [item["name"] for item in out if item["name"] not in order]
    if missing or extra or len(by_name) != len(out):
        raise SystemExit(f"missing={missing} extra={extra} dup={len(out)-len(by_name)}")
    return [by_name[name] for name in order]


def _r_script(item: dict, example: bool) -> str:
    header = item.get("r_header") or ""
    body = textwrap.indent(item["r"], "  ")
    if example:
        return (
            "suppressPackageStartupMessages(library(withr))\n"
            + (header + "\n" if header else "")
            + R_SHOW
            + f"one <- function() {{\n{body}\n}}\nshow(one())\n"
        )
    return (
        "suppressPackageStartupMessages(library(withr))\n"
        + (header + "\n" if header else "")
        + R_HELPER
        + f"one <- function() {{\n{body}\n}}\n"
        + "value <- one()\n"
        + "elapsed <- numeric(20)\n"
        + "for (i in seq_len(20)) {\n"
        + "  t0 <- as.numeric(Sys.time())\n"
        + "  one()\n"
        + "  elapsed[[i]] <- as.numeric(Sys.time()) - t0\n"
        + "}\n"
        + 'cat(sprintf("{\\"value\\":%s,\\"median_ms\\":%.17g}\\n", to_json(value), median(elapsed) * 1000))\n'
    )


def _py_script(item: dict, example: bool) -> str:
    body = textwrap.indent(item["py"], "    ")
    if example:
        return (
            "import os\nimport tempfile\n"
            "from withr import *\n"
            + PY_SHOW
            + f"def one():\n{body}\nshow(one())\n"
        )
    return (
        "import json\nimport os\nimport statistics\nimport tempfile\nimport time\n"
        "from withr import *\n"
        f"def one():\n{body}\n"
        "value = one()\n"
        "elapsed = []\n"
        "for _ in range(20):\n"
        "    started = time.perf_counter()\n"
        "    one()\n"
        "    elapsed.append((time.perf_counter() - started) * 1000)\n"
        "print(json.dumps({\"value\": value, \"median_ms\": statistics.median(elapsed)}))\n"
    )


def _run(argv: list[str], script: str) -> tuple[str, str, int]:
    result = subprocess.run(argv, input=script, text=True, capture_output=True)
    return result.stdout, result.stderr, result.returncode


def _diff(left, right) -> tuple[bool, float]:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right, 0.0 if left == right else 1.0
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        delta = abs(float(left) - float(right))
        return delta <= 1e-8, delta
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        ok = True
        worst = 0.0
        for a, b in zip(left, right):
            matched, delta = _diff(a, b)
            ok = ok and matched
            worst = max(worst, delta)
        return ok, worst
    return left == right, 0.0 if left == right else 1.0


def _usage(item: dict) -> tuple[str, str]:
    name = item["name"]
    if name.startswith("with_") and name not in {"with_"}:
        return (
            f"{name}(new, code, ...)",
            f"{name}(new, code, ...)",
        )
    if name.startswith("local_") and name != "local_":
        return (
            f"{name}(..., .local_envir = parent.frame())",
            f"{name}(..., _local_envir=None)",
        )
    return (f"{name}(...)", f"{name}(...)")


def _doc(item: dict) -> dict:
    arguments = [{"name": name, "text": text} for name, text in item.get("arguments") or []]
    origin_usage, py_usage = _usage(item)
    description = item["description"]
    details = item.get("details") or description
    value = item.get("value") or "The value of code."
    example_r = item["r"].strip() + "\n"
    if item.get("r_header"):
        example_r = item["r_header"].strip() + "\n" + example_r
    example_py = "import os\nimport tempfile\nfrom withr import *\n\n" + item["py"].strip() + "\n"
    name = item["name"]
    translation_details = details
    if name.startswith("with_") or name.startswith("local_") or name in {"with_", "local_"}:
        translation_details = details + " code is a callable, and local_* is a context manager."
    return {
        "name": item["name"],
        "title": item["title"],
        "origin": {
            "description": description,
            "usage": origin_usage,
            "arguments": arguments,
            "details": details,
            "value": value,
            "example": example_r.strip() + "\n",
            "output": f"output/{item['name']}-r.txt",
        },
        "translation": {
            "description": description,
            "usage": py_usage,
            "arguments": arguments,
            "details": translation_details,
            "value": value,
            "example": example_py.strip() + "\n",
            "output": f"output/{item['name']}-python.txt",
        },
    }


def _function(item: dict, check: dict) -> dict:
    return {
        "name": item["name"],
        "translated": True,
        "python": f"withr.{item['name']}",
        "loads": [],
        "uses": item.get("uses") or [],
        "done": item["description"],
        "not_done": "",
        "blocked_by": [],
        "assigned": "",
        "check": check,
    }


def main() -> None:
    items = cases()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    functions = []
    failed = []
    for item in items:
        r_proof = _r_script(item, example=False)
        py_proof = _py_script(item, example=False)
        r_example = _r_script(item, example=True)
        py_example = _py_script(item, example=True)
        r_out, r_err, r_code = _run(["Rscript", "-"], r_proof)
        py_out, py_err, py_code = _run([str(PY), "-"], py_proof)
        (PROOF / f"{item['name']}-r.R").write_text(r_proof)
        (PROOF / f"{item['name']}-py.py").write_text(py_proof)
        if r_code != 0 or py_code != 0:
            failed.append((item["name"], "run", r_code, r_err[-500:], py_code, py_err[-500:]))
            print(f"FAIL {item['name']} run r={r_code} py={py_code}")
            if r_err:
                print(r_err[-400:])
            if py_err:
                print(py_err[-400:])
            continue
        try:
            r_payload = json.loads(r_out.strip().splitlines()[-1])
            py_payload = json.loads(py_out.strip().splitlines()[-1])
        except json.JSONDecodeError:
            failed.append((item["name"], "json", r_out[-300:], py_out[-300:], "", ""))
            print(f"FAIL {item['name']} json")
            print("R", r_out[-300:])
            print("PY", py_out[-300:])
            continue
        matched, delta = _diff(r_payload["value"], py_payload["value"])
        if not matched:
            failed.append((item["name"], "value", r_payload["value"], py_payload["value"], delta, ""))
            print(f"FAIL {item['name']} value r={r_payload['value']!r} py={py_payload['value']!r} d={delta}")
        r_ms = float(r_payload["median_ms"])
        py_ms = float(py_payload["median_ms"])
        ex_r, ex_r_err, ex_r_code = _run(["Rscript", "-"], r_example)
        ex_py, ex_py_err, ex_py_code = _run([str(PY), "-"], py_example)
        if ex_r_code != 0 or ex_py_code != 0:
            failed.append((item["name"], "example", ex_r_err[-300:], ex_py_err[-300:], "", ""))
            print(f"FAIL {item['name']} example")
        (OUTPUT / f"{item['name']}-r.txt").write_text(ex_r if ex_r.endswith("\n") else ex_r + "\n")
        (OUTPUT / f"{item['name']}-python.txt").write_text(ex_py if ex_py.endswith("\n") else ex_py + "\n")
        (DOCS / f"{item['name']}.json").write_text(json.dumps(_doc(item), indent=2) + "\n")
        functions.append(_function(item, {
            "case": item["story"],
            "r_ms": r_ms,
            "translated_ms": py_ms,
            "speedup": r_ms / py_ms if py_ms else None,
            "matches": matched,
            "max_abs_diff": delta,
            "tolerance": 1e-8,
            "proof": {"r": r_proof, "python": py_proof},
        }))
        print(f"{item['name']}: match={matched} speedup={r_ms / py_ms if py_ms else 0:.3f}")
    record = {
        "name": "withr",
        "cran_version": "3.0.3",
        "inventory": "complete",
        "status": "complete" if not failed and len(functions) == len(items) else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": (
            "All 79 exports of withr 3.0.3 are done. code is a callable, and local_* is a context manager. "
            "Random draws follow R's RNGkind. with_xfig and local_xfig raise the R 4.5 removal error. "
            "There is no compiled code."
        ),
        "functions": functions,
    }
    if failed:
        record["resume"] = f"{len(functions)} of {len(items)} exports checked. {len(failed)} still differ."
        record["status"] = "in_progress"
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote translation.json status={record['status']} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
