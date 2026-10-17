"""Run the CRAN examples and write the docs the dashboard reads."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = Path("/tmp/fs-cran/fs/man")
DOCS = ROOT / "docs"
OUTPUT = DOCS / "output"
PY = "/home/ahmed/killr_projects/killr/.venv/bin/python"
EXPORTS = {item["name"] for item in json.loads((ROOT / "translation.json").read_text())["functions"]}

PY_PREAMBLE = '''
import getpass
import subprocess
from pathlib import Path

from fs import *
from fs._error import FsError
from fs.bytes import operate, sum_bytes
from fs.perms import bit_and, perms_equal

def show(value):
    if value is None:
        print("NULL")
        return
    columns = getattr(value, "columns", None)
    if isinstance(columns, dict):
        keys = list(columns)
        count = len(next(iter(columns.values()))) if columns else 0
        print("\\t".join(keys))
        for index in range(count):
            cells = []
            for key in keys:
                cell = columns[key][index]
                cells.append("NA" if cell is None else str(cell))
            print("\\t".join(cells))
        return
    if isinstance(value, FsBytes):
        print(value, end="")
        print()
        return
    if isinstance(value, (list, tuple, FsPath, FsPerms)):
        if value and isinstance(value[0], (list, tuple)):
            for item in value:
                print(item)
            return
        if not value:
            print("character(0)")
            return
        for item in value:
            print("NA" if item is None else item)
        return
    print(value)
'''

PAGES = {
    "path": '''
show(path("foo", "bar", "baz", ext="zip"))
show(path("foo", ["a", "b", "c"], ext="txt"))
''',
    "copy": '''
file_create("foo")
file_copy("foo", "bar")
try:
    file_copy("foo", "bar")
except FsError as error:
    print(error)
file_copy("foo", "bar", overwrite=True)
file_delete(["foo", "bar"])
dir_create("foo")
files = file_create(["foo/bar", "foo/baz"])
show(file_exists(files))
dir_copy("foo", "foo2")
show(file_exists(path("foo2", path_file(files))))
link_create(path_abs("foo"), "loo")
show(link_path("loo"))
link_copy("loo", "loo2")
show(link_path("loo2"))
dir_delete(["foo", "foo2"])
link_delete(["loo", "loo2"])
''',
    "create": '''
file_create("foo")
show(is_file("foo"))
try:
    dir_create("foo")
except FsError as error:
    print(error)
dir_create("bar")
show(is_dir("bar"))
try:
    file_create("bar")
except FsError as error:
    print(error)
file_delete("foo")
dir_delete("bar")
''',
    "delete": '''
dir_create("dir")
files = file_create(path("dir", list("abcde")))
link = link_create(path_abs("dir"), "link")
show(dir_exists("dir"))
show(file_exists(files))
show(link_exists("link"))
show(file_exists(link_path("link")))
file_delete(files[0])
show(file_exists(files[0]))
dir_delete("dir")
show(file_exists(files))
show(dir_exists("dir"))
show(link_exists("link"))
show(dir_exists(link_path("link")))
link_delete("link")
show(link_exists("link"))
''',
    "dir_ls": '''
share = subprocess.check_output(["Rscript", "-e", "cat(R.home('share'))"], text=True).strip()
show(dir_ls(share, type="directory"))
link_create(path_package("base")[0], "base")
show(dir_ls("base", recurse=True, glob="*.R"))
show(dir_ls(path_abs("base")))
show(dir_map("base", lambda name: name))
dir_walk("base", lambda name: print(name))
show(dir_info("base"))
link_delete("base")
''',
    "dir_tree": '''
dir_create("sub")
file_create(["a.txt", "sub/b.txt"])
dir_tree(".")
''',
    "file_access": '''
show(file_access("/"))
show(file_access("/", "read"))
show(file_access("/", "write"))
show(file_exists("WOMBATS"))
''',
    "file_chmod": '''
file_create("foo", mode="000")
file_chmod("foo", "777")
show(file_info("foo")["permissions"])
file_chmod("foo", "u-x")
show(file_info("foo")["permissions"])
file_chmod("foo", "a-wrx")
show(file_info("foo")["permissions"])
file_chmod("foo", "u+wr")
show(file_info("foo")["permissions"])
files = ["foo", file_create("bar", mode="000")[0]]
file_chmod(files, "a+rwx")
show(file_info(files)["permissions"])
file_chmod(files, ["644", "600"])
show(file_info(files)["permissions"])
''',
    "file_chown": '''
file_create("foo")
file_chown("foo", user_id=getpass.getuser())
show(file_info("foo")["user"])
''',
    "file_info": '''
Path("mtcars.csv").write_text("mpg,cyl\\n21,6\\n")
show(file_info("mtcars.csv"))
files = file_info(dir_ls())
show(files["path"])
file_delete("mtcars.csv")
''',
    "file_move": '''
file_create("foo")
file_move("foo", "bar")
show(file_exists(["foo", "bar"]))
file_delete("bar")
''',
    "file_show": '''
file_create("foo")
show(file_show("foo", browser="true"))
''',
    "file_temp": '''
file_temp_push("/tmp/filedd461c46df20")
show(path_temp())
show(path_temp("does-not-exist"))
show(file_temp())
show(file_temp(ext="png"))
show(file_temp("image", ext="png"))
file_temp_push(list("abcdefghijklmnopqrstuvwxyz"))
show(file_temp())
show(file_temp())
while file_temp_pop() is not None:
    pass
show(file_temp_pop())
''',
    "file_touch": '''
file_touch("foo", "2018-01-01")
info = file_info("foo")
for key in ("access_time", "modification_time", "change_time", "birth_time"):
    print(key, info[key][0])
''',
    "fs_bytes": '''
for text in ("1", "1K", "1Kb", "1Kib", "1MB"):
    show(fs_bytes(text))
show(operate("<", "1KB", "1MB"))
show(sum_bytes(["1MB", "5MB", "500KB"]))
''',
    "fs_path": '''
show(fs_path("a//b/"))
show(as_fs_path("a//b/"))
''',
    "fs_perms": '''
show(fs_perms(420))
show(fs_perms([511, 420]))
show(fs_perms("777"))
show(fs_perms(["777", "644"]))
show(fs_perms("a+rwx"))
show(fs_perms(["a+rwx", "u+rw,go+r"]))
show(perms_equal(bit_and(fs_perms("777"), "u+r"), "u+r"))
''',
    "id": '''
groups = group_ids()
users = user_ids()
print("group_id", "group_name")
for index in range(6):
    print(groups["group_id"][index], groups["group_name"][index])
print("user_id", "user_name")
for index in range(6):
    print(users["user_id"][index], users["user_name"][index])
''',
    "is_absolute_path": '''
show(is_absolute_path("/foo"))
show(is_absolute_path("C:\\\\foo"))
show(is_absolute_path("\\\\\\\\myserver\\\\foo\\\\bar"))
show(is_absolute_path("foo/bar"))
''',
    "is_dir_empty": '''
dir_create("empty")
dir_create("full")
file_create("full/a")
print(is_dir_empty("empty"))
print(is_dir_empty("full"))
''',
    "is_file": '''
dir_create("d")
file_create("d/file.txt")
dir_create("d/dir")
link_create(path(path_abs("d"), "file.txt"), "d/link")
paths = dir_ls("d")
show(is_file(paths))
show(is_dir(paths))
show(is_link(paths))
dir_delete("d")
''',
    "link_path": '''
file_create("foo")
link_create(path_abs("foo"), "bar")
show(link_path("bar"))
file_delete(["foo", "bar"])
''',
    "path_expand": '''
show(path_expand("~/bin"))
show(path_home())
show(path_home("R"))
show(path_home_r())
''',
    "path_file": '''
show(path_file("dir/file.zip"))
show(path_dir("dir/file.zip"))
show(path_ext("dir/file.zip"))
show(path_ext("file.tar.gz"))
show(path_ext_remove("file.tar.gz"))
show(path_ext_set(path_ext_remove("file.tar.gz"), "zip"))
''',
    "path_filter": '''
show(path_filter(["foo", "boo", "bar"], glob="*oo"))
show(path_filter(["foo", "boo", "bar"], glob="*oo", invert=True))
show(path_filter(["foo", "boo", "bar"], regexp="b.r"))
''',
    "path_math": '''
dir_create("a")
file_create("a/b")
link_create(path_abs("a"), "c")
show(path_real("c/b"))
parts = path_split("a/b")
show(parts)
show(path_join(parts))
show(path_abs(".."))
show(path_norm("a/../b\\\\c/."))
show(path_rel("/foo/abc", "/foo/bar/baz"))
show(path_common(["/foo/bar/baz", "/foo/bar/abc", "/foo/xyz/123"]))
dir_delete("a")
link_delete("c")
''',
    "path_package": '''
show(path_package("base"))
show(path_package("stats"))
show(path_package("base", "INDEX"))
show(path_package("splines", "help", "AnIndex"))
''',
    "path_sanitize": '''
show(path_sanitize("~/.\u0001ssh/authorized_keys"))
show(path_sanitize(".."))
''',
    "path_select_components": '''
selected = path("some", "simple", "path", "to", "a", "file.txt")
show(path_select_components(selected, [1, 2, 3]))
show(path_select_components(selected, [1, 2, 3], "end"))
show(path_select_components(selected, -1, "end"))
show(path_select_components(selected, 6))
''',
    "path_tidy": '''
show(path_tidy(["a//b/", "a\\\\b\\\\c", "C:", "//foo//bar/"]))
''',
}

CUSTOM_R = {
    "dir_tree": '''
root <- file.path(tempdir(), "fs-tree-example")
dir_create(file.path(root, "sub"))
file_create(file.path(root, c("a.txt", "sub/b.txt")))
dir_tree(root)
''',
    "file_chown": '''
path <- file.path(tempdir(), "fs-chown-example")
file_create(path)
file_chown(path, user_id = Sys.info()[["user"]])
print(file_info(path)$user)
''',
    "file_show": '''
path <- file.path(tempdir(), "fs-show-example")
file_create(path)
print(file_show(path, browser = "true"))
''',
    "fs_path": '''
fs_path("a//b/")
as_fs_path("a//b/")
''',
    "is_dir_empty": '''
empty <- file.path(tempdir(), "fs-empty-example")
full <- file.path(tempdir(), "fs-full-example")
dir_create(empty)
dir_create(full)
file_create(file.path(full, "a"))
is_dir_empty(empty)
is_dir_empty(full)
''',
    "path_tidy": '''
path_tidy(c("a//b/", "a\\\\b\\\\c", "C:", "//foo//bar/"))
''',
}


def take_brace(text: str, open_index: int) -> tuple[str, int]:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index], index + 1
    raise ValueError("unbalanced brace")


def command_body(text: str, name: str) -> str:
    token = "\\" + name + "{"
    start = text.find(token)
    if start < 0:
        return ""
    body, _ = take_brace(text, start + len(token) - 1)
    return body


def all_commands(text: str, name: str) -> list[str]:
    token = "\\" + name + "{"
    found = []
    start = 0
    while True:
        index = text.find(token, start)
        if index < 0:
            return found
        body, start = take_brace(text, index + len(token) - 1)
        found.append(body)


def unwrap(code: str, drop: set[str]) -> str:
    result = []
    index = 0
    while index < len(code):
        if code[index] != "\\":
            result.append(code[index])
            index += 1
            continue
        match = re.match(r"\\([A-Za-z]+)\{", code[index:])
        if not match:
            result.append(code[index])
            index += 1
            continue
        name = match.group(1)
        body, end = take_brace(code, index + match.end() - 1)
        if name in drop:
            pass
        elif name == "dontshow":
            result.append(body)
        else:
            result.append(body)
        index = end
    return "".join(result)


def clean(text: str) -> str:
    if not text:
        return ""
    text = unwrap(text, {"dontrun"})

    def replace(match: re.Match) -> str:
        return match.group(1)

    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\\(?:code|emph|strong|pkg|file|sQuote|dQuote|link)\{([^{}]*)\}", replace, text)
        text = re.sub(r"\\link\[[^\]]*\]\{([^{}]*)\}", replace, text)
        text = re.sub(r"\\linkS4class\{([^{}]*)\}", replace, text)
    text = text.replace("\\itemize", "").replace("\\describe", "")
    text = re.sub(r"\\item\s+", "- ", text)
    text = text.replace("\\cr", "\n")
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def arguments(text: str) -> list[dict]:
    body = command_body(text, "arguments")
    items = []
    index = 0
    while True:
        found = body.find("\\item{", index)
        if found < 0:
            return items
        name, after = take_brace(body, found + len("\\item"))
        if after >= len(body) or body[after] != "{":
            index = after
            continue
        description, index = take_brace(body, after)
        items.append({"name": clean(name), "text": clean(description)})


def rd_unescape(code: str) -> str:
    """Rd stores each backslash doubled. The example runner needs R source."""
    return code.replace("\\\\", "\\")


def section_body(text: str) -> str:
    token = "\\section{"
    start = text.find(token)
    if start < 0:
        return ""
    _, after = take_brace(text, start + len(token) - 1)
    if after < len(text) and text[after] == "{":
        body, _ = take_brace(text, after)
        return body
    return ""


def example_code(text: str, stem: str) -> str:
    if stem in CUSTOM_R:
        return textwrap.dedent(CUSTOM_R[stem]).strip() + "\n"
    body = command_body(text, "examples")
    return rd_unescape(unwrap(body, {"dontrun"})).strip() + "\n"


def run_r(code: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False) as handle:
        handle.write(code)
        source = handle.name
    runner = (
        "suppressPackageStartupMessages(library(fs))\n"
        "options(width = 80)\n"
        "output <- capture.output({\n"
        "  options(try.outFile = stdout())\n"
        f"  source({json.dumps(source)}, echo = FALSE, print.eval = TRUE, local = new.env(parent = globalenv()))\n"
        "})\n"
        "cat(paste(output, collapse = '\\n'))\n"
        "if (length(output)) cat('\\n')\n"
    )
    try:
        result = subprocess.run(["Rscript", "-e", runner], text=True, capture_output=True)
    finally:
        os.unlink(source)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def run_py(code: str) -> str:
    program = PY_PREAMBLE + "\n" + textwrap.dedent(code)
    with tempfile.TemporaryDirectory(prefix="fs-example-") as folder:
        result = subprocess.run(
            [PY, "-c", program],
            text=True,
            capture_output=True,
            cwd=folder,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def docs_for(name: str, title: str, description: str, usage: str, args: list, details: str, value: str, example: str, python_example: str) -> dict:
    return {
        "name": name,
        "title": title or name,
        "origin": {
            "description": description,
            "usage": usage,
            "arguments": args,
            "details": details or description,
            "value": value or "See the example output.",
            "example": example.strip(),
            "output": f"output/{name}-r.txt",
        },
        "translation": {
            "description": description,
            "usage": usage,
            "arguments": args,
            "details": details or description,
            "value": value or "See the example output.",
            "example": textwrap.dedent(python_example).strip(),
            "output": f"output/{name}-python.txt",
        },
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pages = {}
    for path in sorted(MAN.glob("*.Rd")):
        text = path.read_text()
        aliases = [alias for alias in all_commands(text, "alias") if alias in EXPORTS]
        if not aliases:
            continue
        pages[path.stem] = {
            "aliases": aliases,
            "title": clean(command_body(text, "title")),
            "description": clean(command_body(text, "description")),
            "usage": command_body(text, "usage").strip(),
            "arguments": arguments(text),
            "details": clean(command_body(text, "details") or section_body(text)),
            "value": clean(command_body(text, "value")),
            "example": example_code(text, path.stem),
            "python": PAGES[path.stem],
        }
    missing = EXPORTS - {alias for page in pages.values() for alias in page["aliases"]}
    if missing:
        raise SystemExit(f"no help page for {sorted(missing)}")
    for stem, page in pages.items():
        print("example", stem, flush=True)
        r_out = run_r(page["example"])
        py_out = run_py(page["python"])
        for alias in page["aliases"]:
            (OUTPUT / f"{alias}-r.txt").write_text(r_out if r_out.endswith("\n") or r_out == "" else r_out + "\n")
            (OUTPUT / f"{alias}-python.txt").write_text(py_out if py_out.endswith("\n") or py_out == "" else py_out + "\n")
            record = docs_for(
                alias,
                page["title"],
                page["description"],
                page["usage"],
                page["arguments"],
                page["details"],
                page["value"],
                page["example"],
                page["python"],
            )
            (DOCS / f"{alias}.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {len(EXPORTS)} docs")


if __name__ == "__main__":
    main()
