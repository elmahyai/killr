"""Compare two files the way tools::Rdiff does."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def _canonicalize_quotes(txt):
    out = []
    for line in txt:
        line = line.replace("\u2018", "'").replace("\u2019", "'")
        line = line.replace("\u201c", '"').replace("\u201d", '"')
        out.append(line)
    return out


def _clean(txt, for_ex, null_pointers):
    if not txt:
        return list(txt)
    top = [
        i
        for i, line in enumerate(txt)
        if re.search(r"^(R version|R : Copyright|R Under development)", line)
    ]
    bot = [i for i, line in enumerate(txt) if re.search(r"quit R.$", line)]
    if top and bot:
        start, stop = top[0], bot[0]
        txt = txt[:start] + txt[stop + 1 :]
    headers = [i for i, line in enumerate(txt) if "</HEADER>" in line]
    if headers:
        txt = txt[max(headers) + 1 :]
    footers = [i for i, line in enumerate(txt) if "<FOOTER>" in line]
    if footers:
        txt = txt[: max(footers)]
    if for_ex:
        txt = [line for line in txt if '".old_wd"' not in line]
    if len(txt) > 3 and txt[-3].startswith("> proc.time()"):
        txt = txt[:-3]
    begin = 0
    end = 0
    kept = []
    for line in txt:
        if line == "> ## IGNORE_RDIFF_BEGIN":
            begin += 1
        if line == "> ## IGNORE_RDIFF_END":
            end += 1
        if begin <= end:
            kept.append(line)
    txt = kept
    if null_pointers:
        txt = [
            re.sub(
                r"<(environment|bytecode|pointer|promise): [x0-9A-Fa-f]+>",
                r"<\1: 0>",
                line,
            )
            for line in txt
        ]
        txt = [re.sub(r"<hashtable.*>", "<hashtable output>", line) for line in txt]
    txt = _canonicalize_quotes(txt)
    txt = [line for line in txt if 'options(pager = "console")' not in line]
    pat = re.compile(
        r"(^Time |^Loading required package|^Package [A-Za-z][A-Za-z0-9]+ loaded|"
        r"^<(environment|promise|pointer|bytecode):|^End.Don't show)"
    )
    return [line for line in txt if not pat.search(line)]


def _clean2(txt):
    for i, line in enumerate(txt):
        if re.search(r"^> options\(warn = 1\)$", line):
            return txt[i + 1 :]
    return txt


def _trim_pdf(txt):
    if len(txt) < 2 or not txt[0].startswith("%PDF"):
        raise ValueError("not a PDF file")
    txt = txt[2:] if txt[0].startswith("%") else txt[1:]
    pat = re.compile(r"(^/CreationDate |^/ModDate |^/Producer)")
    return [line for line in txt if not pat.search(line)]


def _squash(lines):
    out = []
    for line in lines:
        line = re.sub(r"[ \t\r\f\v]+$", "", line)
        line = re.sub(r"[ \t\r\f\v]+", " ", line)
        out.append(line)
    return out


def rdiff(from_file, to_file, use_diff=False, for_ex=False, null_pointers=True, log=False):
    """Compare two text or PDF files. Returns 0, 1, or 2."""
    left = Path(from_file).read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    right = Path(to_file).read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    use_diff0 = use_diff
    as_pdf = bool(left) and left[0].startswith("%PDF")
    if use_diff and shutil.which("diff") is None:
        if not as_pdf:
            print("'diff' is not available so useDiff = FALSE will be used")
        use_diff = False
    if as_pdf:
        if not use_diff:
            out = (
                "comparing PDF files requires useDiff = TRUE"
                if not use_diff0
                else "comparing PDF files requires 'diff'"
            )
            if log:
                return {"status": 0, "out": out}
            print(out)
            return 0
        left = _trim_pdf(left)
        right = _trim_pdf(right)
    else:
        left = _clean(left, for_ex, null_pointers)
        right = _clean(right, for_ex, null_pointers)
        if for_ex:
            left = _clean2(left)
            left = [line for line in left if not re.search(r"[.](format_|)ptime", line)]
            right = _clean2(right)
    if not use_diff:
        if len(left) == len(right):
            if _squash(left) == _squash(right):
                return {"status": 0, "out": []} if log else 0
            diff = [i for i, (a, b) in enumerate(zip(left, right)) if _squash([a])[0] != _squash([b])[0]]
            out = [
                f"{i + 1}c{i + 1}\n< {left[i]}\n---\n> {right[i]}"
                for i in diff
            ]
            if log:
                return {"status": 1, "out": out}
            print()
            for i in diff:
                print(f"{i + 1}c{i + 1}")
                print(f"< {left[i]}")
                print("---")
                print(f"> {right[i]}")
            return 1
        message = "files differ in number of lines"
        if log:
            return {"status": 2, "out": message}
        print(message)
        return 2
    out = []
    with tempfile.TemporaryDirectory() as directory:
        left_path = Path(directory) / "a"
        right_path = Path(directory) / "b"
        left_path.write_text("\n".join(left) + ("\n" if left else ""), encoding="utf-8")
        right_path.write_text("\n".join(right) + ("\n" if right else ""), encoding="utf-8")
        if log:
            completed = subprocess.run(
                ["diff", "-bw", str(left_path), str(right_path)],
                capture_output=True,
                text=True,
            )
            text = completed.stdout
            if completed.stderr:
                text += completed.stderr
            return {"status": completed.returncode, "out": text.splitlines()}
        subprocess.run(["diff", "-bw", str(left_path), str(right_path)])
        return None
