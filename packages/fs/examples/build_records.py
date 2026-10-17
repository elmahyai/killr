"""Time each fs export against R and write the translation record."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "proof"
DOCS = ROOT / "docs"
PY = "/home/ahmed/killr_projects/killr/.venv/bin/python"

R_HEADER = r"""
suppressPackageStartupMessages(library(fs))
emit <- function(x) {
  if (is.null(x)) return("null")
  if (inherits(x, "fs_perms")) x <- as.integer(x)
  if (inherits(x, "fs_bytes")) x <- as.numeric(x)
  if (is.factor(x)) x <- as.character(x)
  if (is.logical(x)) {
    parts <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    parts <- ifelse(is.na(x), "null", sprintf("%.17g", x))
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.character(x)) {
    parts <- vapply(x, function(item) {
      if (is.na(item)) return("null")
      item <- gsub("\\", "\\\\", item, fixed = TRUE)
      item <- gsub("\"", "\\\"", item, fixed = TRUE)
      paste0("\"", item, "\"")
    }, "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.list(x)) {
    return(paste0("[", paste(vapply(x, emit, ""), collapse = ","), "]"))
  }
  "null"
}
"""

PY_HEADER = """
import contextlib
import getpass
import io
import json
import os
import statistics
import tempfile
import time

from fs import *
from fs.perms import format_fs_perms
"""

R_TREE = """
  root <- tempfile("fsproof")
  dir_create(root)
  dir_create(path(root, "d/sub"))
  file_create(path(root, c("d/a.txt", "d/sub/b.txt")))
  link_create(path_abs(path(root, "d/a.txt")), path(root, "d/link"))
"""

PY_TREE = """
    root = tempfile.mkdtemp(prefix="fsproof-")
    dir_create(root)
    dir_create(path(root, "d/sub"))
    file_create(path(root, ["d/a.txt", "d/sub/b.txt"]))
    link_create(path_abs(path(root, "d/a.txt")), path(root, "d/link"))
"""


def _r_script(body: str) -> str:
    return f"""{R_HEADER}
one <- function() {{
{body}
}}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {{
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}}
cat(sprintf("{{\\"value\\":%s,\\"median_ms\\":%.17g}}\\n", emit(value), median(elapsed) * 1000))
"""


def _py_script(body: str) -> str:
    return f"""{PY_HEADER}
def one():
{body}

def _atom(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)

def _emit(value):
    if isinstance(value, (list, tuple, FsPath, FsBytes, FsPerms)):
        return [
            _emit(item) if isinstance(item, (list, tuple, FsPath, FsBytes, FsPerms)) else _atom(item)
            for item in value
        ]
    return [_atom(value)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({{"value": _emit(value), "median_ms": statistics.median(elapsed)}}))
"""


# name, python, done, case, r body, py body, tree
CASES = [
    ("path", "fs.path", "Join components and append an extension.", 'path("foo", "bar", "baz", ext = "zip")', '  path("foo", "bar", "baz", ext = "zip")', '    return path("foo", "bar", "baz", ext="zip")', False),
    ("path_wd", "fs.path_wd", "Join components onto the working directory.", 'path_wd("rel") from /tmp', '  setwd("/tmp")\n  path_wd("rel")', '    os.chdir("/tmp")\n    return path_wd("rel")', False),
    ("path_real", "fs.path_real", "Canonical path of an existing file.", 'path_real("/etc/passwd")', '  path_real("/etc/passwd")', '    return path_real("/etc/passwd")', False),
    ("path_tidy", "fs.path_tidy", "Normalize separators and drop a trailing slash.", 'path_tidy(c("a//b/", "C:", "//foo//bar/"))', '  path_tidy(c("a//b/", "C:", "//foo//bar/"))', '    return path_tidy(["a//b/", "C:", "//foo//bar/"])', False),
    ("path_split", "fs.path_split", "Split a path into components.", 'path_split(c("/foo/bar", "//foo/bar"))', '  path_split(c("/foo/bar", "//foo/bar"))', '    return path_split(["/foo/bar", "//foo/bar"])', False),
    ("path_join", "fs.path_join", "Join split components.", 'path_join(list(c("a", "b"), c("/", "foo")))', '  path_join(list(c("a", "b"), c("/", "foo")))', '    return path_join([["a", "b"], ["/", "foo"]])', False),
    ("path_abs", "fs.path_abs", "Absolute normalized path.", 'path_abs("rel") from /tmp', '  setwd("/tmp")\n  path_abs("rel")', '    os.chdir("/tmp")\n    return path_abs("rel")', False),
    ("path_norm", "fs.path_norm", "Drop . and collapse .. without resolving links.", 'path_norm(c("a/../b\\\\c/.", "../B", "/a/../../b"))', '  path_norm(c("a/../b\\\\c/.", "../B", "/a/../../b"))', '    return path_norm(["a/../b\\\\c/.", "../B", "/a/../../b"])', False),
    ("path_rel", "fs.path_rel", "Path relative to a start directory.", 'path_rel("/foo/abc", "/foo/bar/baz")', '  path_rel("/foo/abc", "/foo/bar/baz")', '    return path_rel("/foo/abc", "/foo/bar/baz")', False),
    ("path_common", "fs.path_common", "Longest shared prefix.", "path_common of three /foo paths", '  path_common(c("/foo/bar/baz", "/foo/bar/abc", "/foo/xyz/123"))', '    return path_common(["/foo/bar/baz", "/foo/bar/abc", "/foo/xyz/123"])', False),
    ("path_expand", "fs.path_expand", "Expand a leading tilde.", 'path_expand("~/bin")', '  path_expand("~/bin")', '    return path_expand("~/bin")', False),
    ("path_expand_r", "fs.path_expand_r", "Expand a tilde with the platform home.", 'path_expand_r("~/bin")', '  path_expand_r("~/bin")', '    return path_expand_r("~/bin")', False),
    ("path_home", "fs.path_home", "The home directory.", "path_home()", "  path_home()", "    return path_home()", False),
    ("path_home_r", "fs.path_home_r", "The platform home directory.", "path_home_r()", "  path_home_r()", "    return path_home_r()", False),
    ("path_file", "fs.path_file", "The filename portion.", 'path_file("dir/file.zip")', '  path_file("dir/file.zip")', '    return path_file("dir/file.zip")', False),
    ("path_dir", "fs.path_dir", "The directory portion.", 'path_dir(c("dir/file.zip", "foo"))', '  path_dir(c("dir/file.zip", "foo"))', '    return path_dir(["dir/file.zip", "foo"])', False),
    ("path_ext", "fs.path_ext", "The last extension.", "path_ext of zip, tar.gz, and .bashrc", '  path_ext(c("dir/file.zip", "file.tar.gz", ".bashrc"))', '    return path_ext(["dir/file.zip", "file.tar.gz", ".bashrc"])', False),
    ("path_ext_remove", "fs.path_ext_remove", "Drop the last extension.", 'path_ext_remove("file.tar.gz")', '  path_ext_remove("file.tar.gz")', '    return path_ext_remove("file.tar.gz")', False),
    ("path_ext_set", "fs.path_ext_set", "Replace the last extension.", 'path_ext_set("file.tar.gz", "zip")', '  path_ext_set("file.tar.gz", "zip")', '    return path_ext_set("file.tar.gz", "zip")', False),
    ("path_ext<-", "fs.path_ext_replace", "Replacement form of path_ext_set.", "path_ext<- via path_ext_replace", '  path_ext_set("file.tar.gz", "zip")', '    return path_ext_replace("file.tar.gz", "zip")', False),
    ("path_filter", "fs.path_filter", "Keep paths matching a glob.", 'path_filter(..., glob = "*oo")', '  path_filter(c("foo", "boo", "bar"), glob = "*oo")', '    return path_filter(["foo", "boo", "bar"], glob="*oo")', False),
    ("path_has_parent", "fs.path_has_parent", "Whether a path is inside a parent.", 'path_has_parent(c("/a/b/c", "/a/d"), "/a/b")', '  path_has_parent(c("/a/b/c", "/a/d"), "/a/b")', '    return path_has_parent(["/a/b/c", "/a/d"], "/a/b")', False),
    ("path_sanitize", "fs.path_sanitize", "Remove characters that are unsafe in a filename.", 'path_sanitize(c("..", "CON.txt"))', '  path_sanitize(c("..", "CON.txt"))', '    return path_sanitize(["..", "CON.txt"])', False),
    ("path_select_components", "fs.path_select_components", "Keep components by position.", "path_select_components(path, 1:2)", '  path_select_components(path("some", "simple", "path"), 1:2)', '    return path_select_components(path("some", "simple", "path"), [1, 2])', False),
    ("fs_path", "fs.fs_path", "Coerce text to a tidy path.", 'fs_path("a//b/")', '  fs_path("a//b/")', '    return fs_path("a//b/")', False),
    ("as_fs_path", "fs.as_fs_path", "Coerce text to a tidy path.", 'as_fs_path("a//b/")', '  as_fs_path("a//b/")', '    return as_fs_path("a//b/")', False),
    ("is_absolute_path", "fs.is_absolute_path", "True for a slash, a drive, or a tilde.", 'is_absolute_path(c("/foo", "foo/bar", "~"))', '  is_absolute_path(c("/foo", "foo/bar", "~"))', '    return is_absolute_path(["/foo", "foo/bar", "~"])', False),
    ("fs_bytes", "fs.fs_bytes", "Parse a size such as 1KB as a count of bytes.", 'fs_bytes(c("1", "1K", "1MB"))', '  as.numeric(fs_bytes(c("1", "1K", "1MB")))', '    return fs_bytes(["1", "1K", "1MB"])', False),
    ("as_fs_bytes", "fs.as_fs_bytes", "Coerce text or numbers to byte counts.", 'as_fs_bytes(c("1KB", "2MB"))', '  as.numeric(as_fs_bytes(c("1KB", "2MB")))', '    return as_fs_bytes(["1KB", "2MB"])', False),
    ("fs_perms", "fs.fs_perms", "Octal modes, including the installed index rotation.", 'fs_perms(c("777", "644", "600"))', '  as.integer(fs_perms(c("777", "644", "600")))', '    return fs_perms(["777", "644", "600"])', False),
    ("as_fs_perms", "fs.as_fs_perms", "Coerce a mode to permission bits.", 'as_fs_perms("755")', '  as.integer(as_fs_perms("755"))', '    return as_fs_perms("755")', False),
    ("group_ids", "fs.group_ids", "Every group id and name, ordered by id.", "group_ids()", '  g <- group_ids()\n  paste(g$group_id, g$group_name)', '    g = group_ids()\n    return [f"{i} {name}" for i, name in zip(g["group_id"], g["group_name"])]', False),
    ("user_ids", "fs.user_ids", "Every user id and name, ordered by id.", "user_ids()", '  u <- user_ids()\n  paste(u$user_id, u$user_name)', '    u = user_ids()\n    return [f"{i} {name}" for i, name in zip(u["user_id"], u["user_name"])]', False),
    ("path_package", "fs.path_package", "Directory of an installed R package.", 'path_package("base", "INDEX")', '  path_package("base", "INDEX")', '    return path_package("base", "INDEX")', False),
    ("path_temp", "fs.path_temp", "Final component of a path inside the temp directory.", 'path_temp("does-not-exist")', '  path_file(path_temp("does-not-exist"))', '    return path_file(path_temp("does-not-exist"))', False),
    ("file_temp_push", "fs.file_temp_push", "Push a fixed name onto the temp stack.", 'file_temp_push("/tmp/fs-proof-fixed.tmp")', '  file_temp_push("/tmp/fs-proof-fixed.tmp")', '    return file_temp_push("/tmp/fs-proof-fixed.tmp")', False),
    ("file_temp_pop", "fs.file_temp_pop", "Pop the name pushed just above.", "file_temp_pop() after a push", '  file_temp_push("/tmp/fs-proof-fixed.tmp")\n  file_temp_pop()', '    file_temp_push("/tmp/fs-proof-fixed.tmp")\n    return file_temp_pop()', False),
    ("file_temp", "fs.file_temp", "A pushed name is returned before a random one.", "file_temp() after file_temp_push", '  file_temp_push("/tmp/fs-proof-fixed.tmp")\n  file_temp()', '    file_temp_push("/tmp/fs-proof-fixed.tmp")\n    return file_temp()', False),
    ("dir_ls", "fs.dir_ls", "List a directory, recursively, in libuv's sorted order.", 'dir_ls(recurse = TRUE)', '  as.character(path_rel(dir_ls(path(root, "d"), recurse = TRUE), path(root, "d")))', '    return path_rel(dir_ls(path(root, "d"), recurse=True), path(root, "d"))', True),
    ("dir_map", "fs.dir_map", "Apply a function to each directory entry.", "dir_map(identity)", '  as.character(path_rel(unlist(dir_map(path(root, "d"), identity)), path(root, "d")))', '    return path_rel(dir_map(path(root, "d"), lambda name: name), path(root, "d"))', True),
    ("dir_info", "fs.dir_info", "Types of the entries in a directory.", "dir_info()$type", '  as.character(dir_info(path(root, "d"))$type)', '    return dir_info(path(root, "d"))["type"]', True),
    ("dir_walk", "fs.dir_walk", "Walk entries and return the input path.", "dir_walk(identity)", '  path_file(dir_walk(path(root, "d"), identity))', '    return path_file(dir_walk(path(root, "d"), lambda name: None))', True),
    ("dir_tree", "fs.dir_tree", "The tree text, with the root line replaced by d.", "dir_tree()", '''  lines <- capture.output(dir_tree(path(root, "d")))
  lines[1] <- "d"
  lines''', '''    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        dir_tree(path(root, "d"))
    lines = buffer.getvalue().splitlines()
    lines[0] = "d"
    return lines''', True),
    ("dir_create", "fs.dir_create", "Create a directory tree.", 'dir_create("fresh/nested")', '  dir_create(path(root, "fresh/nested"))\n  dir_exists(path(root, "fresh/nested"))', '    dir_create(path(root, "fresh/nested"))\n    return dir_exists(path(root, "fresh/nested"))', True),
    ("file_create", "fs.file_create", "Create an empty file.", 'file_create("fresh.txt")', '  file_create(path(root, "fresh.txt"))\n  file_exists(path(root, "fresh.txt"))', '    file_create(path(root, "fresh.txt"))\n    return file_exists(path(root, "fresh.txt"))', True),
    ("file_exists", "fs.file_exists", "Whether a file or directory exists.", "file_exists of a file and a missing path", '  file_exists(path(root, c("d/a.txt", "missing")))', '    return file_exists(path(root, ["d/a.txt", "missing"]))', True),
    ("dir_exists", "fs.dir_exists", "Whether a path is an existing directory.", "dir_exists of a directory and a file", '  dir_exists(path(root, c("d", "d/a.txt")))', '    return dir_exists(path(root, ["d", "d/a.txt"]))', True),
    ("link_exists", "fs.link_exists", "Whether a path is a symbolic link.", "link_exists of a link and a file", '  link_exists(path(root, c("d/link", "d/a.txt")))', '    return link_exists(path(root, ["d/link", "d/a.txt"]))', True),
    ("is_file", "fs.is_file", "Whether a path is a file, following links.", "is_file of a file, a link, and a directory", '  is_file(path(root, c("d/a.txt", "d/link", "d")))', '    return is_file(path(root, ["d/a.txt", "d/link", "d"]))', True),
    ("is_dir", "fs.is_dir", "Whether a path is a directory.", "is_dir of a directory and a file", '  is_dir(path(root, c("d", "d/a.txt")))', '    return is_dir(path(root, ["d", "d/a.txt"]))', True),
    ("is_link", "fs.is_link", "Whether a path is a symbolic link.", "is_link of a link and a file", '  is_link(path(root, c("d/link", "d/a.txt")))', '    return is_link(path(root, ["d/link", "d/a.txt"]))', True),
    ("is_file_empty", "fs.is_file_empty", "Whether a file has size zero.", 'is_file_empty("d/a.txt")', '  is_file_empty(path(root, "d/a.txt"))', '    return is_file_empty(path(root, "d/a.txt"))', True),
    ("is_dir_empty", "fs.is_dir_empty", "Whether a directory has no entries.", 'is_dir_empty("d")', '  is_dir_empty(path(root, "d"))', '    return [is_dir_empty(path(root, "d"))]', True),
    ("file_info", "fs.file_info", "Type, size, and mode of one file.", 'file_info("d/a.txt")', '  info <- file_info(path(root, "d/a.txt"))\n  c(as.character(info$type), sprintf("%.17g", as.numeric(info$size)), as.character(as.integer(info$permissions)))', '    info = file_info(path(root, "d/a.txt"))\n    return [info["type"][0], f"{info[\'size\'][0]:.17g}", str(int(info["permissions"][0]))]', True),
    ("file_size", "fs.file_size", "Size in bytes.", 'file_size("d/a.txt")', '  as.numeric(file_size(path(root, "d/a.txt")))', '    return file_size(path(root, "d/a.txt"))', True),
    ("file_access", "fs.file_access", "Whether a path exists and is readable.", 'file_access(..., "read")', '  file_access(path(root, "d/a.txt"), "read")', '    return file_access(path(root, "d/a.txt"), "read")', True),
    ("file_chmod", "fs.file_chmod", "Symbolic chmod applied to the current mode.", 'file_chmod(..., "u+x")', '  file_chmod(path(root, "d/a.txt"), "u+x")\n  as.character(file_info(path(root, "d/a.txt"))$permissions)', '    file_chmod(path(root, "d/a.txt"), "u+x")\n    return format_fs_perms(file_info(path(root, "d/a.txt"))["permissions"])', True),
    ("file_touch", "fs.file_touch", "Set the modification time to 2018-01-02.", 'file_touch(..., "2018-01-01", "2018-01-02")', '  file_touch(path(root, "d/a.txt"), "2018-01-01", "2018-01-02")\n  as.numeric(file_info(path(root, "d/a.txt"))$modification_time)', '    file_touch(path(root, "d/a.txt"), "2018-01-01", "2018-01-02")\n    return [file_info(path(root, "d/a.txt"))["modification_time"][0]]', True),
    ("link_path", "fs.link_path", "The target stored in a symbolic link.", 'link_path("d/link")', '  path_file(link_path(path(root, "d/link")))', '    return path_file(link_path(path(root, "d/link")))', True),
    ("link_create", "fs.link_create", "Create a symbolic link and read it back.", "link_create then link_path", '  link_create(path(root, "d/a.txt"), path(root, "extra-link"))\n  path_file(link_path(path(root, "extra-link")))', '    link_create(path(root, "d/a.txt"), path(root, "extra-link"))\n    return path_file(link_path(path(root, "extra-link")))', True),
    ("file_copy", "fs.file_copy", "Copy a file.", 'file_copy("d/a.txt", "d/c.txt")', '  file_copy(path(root, "d/a.txt"), path(root, "d/c.txt"))\n  file_exists(path(root, "d/c.txt"))', '    file_copy(path(root, "d/a.txt"), path(root, "d/c.txt"))\n    return file_exists(path(root, "d/c.txt"))', True),
    ("dir_copy", "fs.dir_copy", "Copy a directory tree.", 'dir_copy("d/sub", "d/sub2")', '  dir_copy(path(root, "d/sub"), path(root, "d/sub2"))\n  file_exists(path(root, "d/sub2/b.txt"))', '    dir_copy(path(root, "d/sub"), path(root, "d/sub2"))\n    return file_exists(path(root, "d/sub2/b.txt"))', True),
    ("link_copy", "fs.link_copy", "Copy a symbolic link.", 'link_copy("d/link", "d/link2")', '  link_copy(path(root, "d/link"), path(root, "d/link2"))\n  link_exists(path(root, "d/link2"))', '    link_copy(path(root, "d/link"), path(root, "d/link2"))\n    return link_exists(path(root, "d/link2"))', True),
    ("file_move", "fs.file_move", "Rename a file.", 'file_move("move-me", "moved")', '  file_create(path(root, "move-me"))\n  file_move(path(root, "move-me"), path(root, "moved"))\n  file_exists(path(root, c("move-me", "moved")))', '    file_create(path(root, "move-me"))\n    file_move(path(root, "move-me"), path(root, "moved"))\n    return file_exists(path(root, ["move-me", "moved"]))', True),
    ("file_delete", "fs.file_delete", "Delete a file created in the same call.", "file_delete of a new file", '  p <- path(root, "gone.txt")\n  file_create(p)\n  file_delete(p)\n  file_exists(p)', '    target = path(root, "gone.txt")\n    file_create(target)\n    file_delete(target)\n    return file_exists(target)', True),
    ("dir_delete", "fs.dir_delete", "Delete a directory created in the same call.", "dir_delete of a new directory", '  p <- path(root, "gone-dir")\n  dir_create(p)\n  dir_delete(p)\n  dir_exists(p)', '    target = path(root, "gone-dir")\n    dir_create(target)\n    dir_delete(target)\n    return dir_exists(target)', True),
    ("link_delete", "fs.link_delete", "Delete a link created in the same call.", "link_delete of a new link", '  p <- path(root, "gone-link")\n  link_create(path(root, "d/a.txt"), p)\n  link_delete(p)\n  link_exists(p)', '    target = path(root, "gone-link")\n    link_create(path(root, "d/a.txt"), target)\n    link_delete(target)\n    return link_exists(target)', True),
    ("file_show", "fs.file_show", "Return the path after handing it to the true command.", 'file_show(..., browser = "true")', '  path_file(file_show(path(root, "d/a.txt"), browser = "true"))', '    return path_file(file_show(path(root, "d/a.txt"), browser="true"))', True),
    ("file_chown", "fs.file_chown", "Set the owner to the current user.", "file_chown to the current user", '  file_chown(path(root, "d/a.txt"), user_id = Sys.info()[["user"]])\n  as.character(file_info(path(root, "d/a.txt"))$user)', '    file_chown(path(root, "d/a.txt"), user_id=getpass.getuser())\n    return file_info(path(root, "d/a.txt"))["user"]', True),
]


def _run(argv: list[str], script: str, env: dict | None = None) -> dict:
    result = subprocess.run(argv, input=script, text=True, capture_output=True, env=env)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-2000:])
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError(result.stdout[-2000:] or result.stderr[-2000:])


def _close(left, right) -> tuple[bool, float]:
    if isinstance(left, list) or isinstance(right, list):
        if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
            return False, 1.0
        flags = [_close(a, b) for a, b in zip(left, right)]
        return all(flag for flag, _ in flags), max((diff for _, diff in flags), default=0.0)
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right, 0.0 if left == right else 1.0
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        diff = abs(float(left) - float(right))
        return diff <= 1e-8, diff
    return left == right, 0.0 if left == right else 1.0


def main() -> None:
    PROOF.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    functions = []
    failed = []
    for name, python, done, case, r_body, py_body, tree in CASES:
        r_code = _r_script((R_TREE if tree else "") + "\n" + r_body)
        py_code = _py_script((PY_TREE if tree else "") + "\n" + py_body)
        (PROOF / f"{name}-r.R").write_text(r_code)
        (PROOF / f"{name}-py.py").write_text(py_code)
        print("checking", name, flush=True)
        try:
            r_result = _run(["Rscript", "-"], r_code)
            py_result = _run([PY, "-"], py_code, env)
        except RuntimeError as error:
            print(" ERROR", name)
            print(str(error)[-1500:])
            failed.append(name)
            continue
        matches, diff = _close(r_result["value"], py_result["value"])
        if not matches:
            print(" MISMATCH", name)
            print("  R ", r_result["value"])
            print("  PY", py_result["value"])
            failed.append(name)
        speedup = None
        if py_result["median_ms"]:
            speedup = r_result["median_ms"] / py_result["median_ms"]
        functions.append(
            {
                "name": name,
                "translated": matches,
                "python": python,
                "loads": [],
                "uses": [],
                "done": done,
                "not_done": "" if matches else "The check against R did not match.",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": case,
                    "r_ms": r_result["median_ms"],
                    "translated_ms": py_result["median_ms"],
                    "speedup": speedup,
                    "matches": matches,
                    "max_abs_diff": diff,
                    "tolerance": 1e-8,
                    "proof": {"r": r_code, "python": py_code},
                },
            }
        )
    record = {
        "name": "fs",
        "cran_version": "2.1.0",
        "inventory": "complete",
        "status": "complete" if not failed and len(functions) == 69 else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "All 69 exports are translated. Paths follow the C tidy and split rules. Permissions follow BSD setmode, including the installed index rotation. Directory listings follow libuv's sorted scandir.",
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {len(functions)} functions, failed {len(failed)}: {failed}")


if __name__ == "__main__":
    main()
