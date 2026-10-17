"""Compare the translation with the installed fs 2.1.0."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fs.bytes import format_fs_bytes, fs_bytes, operate, sum_bytes
from fs.id import group_ids
from fs.package import path_package
from fs.path import (
    is_absolute_path,
    path,
    path_common,
    path_expand,
    path_ext,
    path_ext_remove,
    path_ext_set,
    path_filter,
    path_norm,
    path_rel,
    path_sanitize,
    path_select_components,
    path_split,
    path_tidy,
)
from fs.perms import bit_not, bit_or, format_fs_perms, fs_perms, perms_equal, bit_and
from fs.system import dir_create, dir_ls, file_chmod, file_create, file_info, link_create
from fs.path import path_abs as absolute


def test_path_strings_match_the_probed_values():
    assert list(path_tidy(["a//b/", "a\\b\\c", "C:", "//foo//bar/", None, ""])) == [
        "a/b",
        "a/b/c",
        "C:/",
        "//foo/bar",
        None,
        "",
    ]
    assert list(path("foo", "bar", "baz", ext="zip")) == ["foo/bar/baz.zip"]
    assert list(path("foo", ["a", "b", "c"], ext="txt")) == ["foo/a.txt", "foo/b.txt", "foo/c.txt"]
    assert path_split(["/foo/bar", "//foo/bar", ""]) == [["/", "foo", "bar"], ["//foo", "bar"], []]
    assert list(path_norm(["a/../b\\c/.", "../B", "/a/../../b"])) == ["b/c", "../B", "/b"]
    assert is_absolute_path(["/foo", "foo/bar", "~", "c:foo"]) == [True, False, True, True]
    assert list(path_rel("/foo/abc", "/foo/bar/baz")) == ["../../abc"]
    assert list(path_common(["/foo/bar/baz", "/foo/bar/abc", "/foo/xyz/123"])) == ["/foo"]
    assert path_ext(["dir/file.zip", "file.tar.gz", ".bashrc"]) == ["zip", "gz", ""]
    assert path_ext_remove(["file.tar.gz"]) == ["file.tar"]
    assert list(path_ext_set(path_ext_remove("file.tar.gz"), "zip")) == ["file.zip"]
    assert list(path_filter(["foo", "boo", "bar"], glob="*oo")) == ["foo", "boo"]
    assert path_sanitize("~/.\u0001ssh/authorized_keys") == ["~.sshauthorized_keys"]
    selected = path("some", "simple", "path", "to", "a", "file.txt")
    assert list(path_select_components(selected, [1, 2, 3], "end")) == ["to/a/file.txt"]
    assert list(path_expand("~/bin")) == [str(Path.home() / "bin")]


def test_bytes_and_permissions_match_r():
    assert list(fs_bytes(["1", "1K", "1Kb", "1Kib", "1MB"])) == [1, 1024, 1024, 1024, 1048576]
    assert format_fs_bytes(["1MB", "5MB", "500KB"]) == ["  1M", "  5M", "500K"]
    assert format_fs_bytes(sum_bytes(["1MB", "5MB", "500KB"])) == ["6.49M"]
    assert operate("<", "1KB", "1MB") == [True]
    assert list(fs_perms(420)) == [420]
    assert list(fs_perms(["777", "644", "600"])) == [384, 511, 420]
    assert format_fs_perms(fs_perms("u=rwx,g=r-x,o=r-x")) == ["rwxr--r--"]
    assert list(bit_not(fs_perms(420))) == [-421]
    assert list(bit_or(fs_perms("644"), "u+x")) == [484]
    assert perms_equal(bit_and(fs_perms("777"), "u+r"), "u+r") == [True]


def test_listing_and_metadata_match_r():
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        dir_create("d/sub")
        file_create(["d/a.txt", "d/sub/b.txt"])
        link_create(absolute("d/a.txt"), "d/link")
        file_chmod("d/a.txt", "u+x")
        listed = subprocess.check_output(
            [
                "Rscript",
                "-e",
                "suppressPackageStartupMessages(library(fs)); "
                f"cat(paste(dir_ls('{folder}/d', recurse=TRUE), collapse='|'))",
            ],
            text=True,
        )
        assert "|".join(dir_ls(f"{folder}/d", recurse=True)) == listed
        info = file_info(f"{folder}/d/a.txt")
        payload = subprocess.check_output(
            [
                "Rscript",
                "-e",
                "suppressPackageStartupMessages(library(fs)); "
                f"info <- file_info('{folder}/d/a.txt'); "
                "cat(sprintf('%s %s %s %.17g %.17g', as.character(info$type), "
                "as.numeric(info$size), as.integer(info$permissions), "
                "as.numeric(info$modification_time), as.numeric(info$birth_time)))",
            ],
            text=True,
        )
        kind, size, mode, modified, birth = payload.split()
        assert info["type"] == [kind]
        assert list(info["size"]) == [float(size)]
        assert list(info["permissions"]) == [int(mode)]
        assert abs(info["modification_time"][0] - float(modified)) < 1e-8
        assert abs(info["birth_time"][0] - float(birth)) < 1e-8
        assert list(path_package("base")) == [
            subprocess.check_output(
                ["Rscript", "-e", "suppressPackageStartupMessages(library(fs)); cat(path_package('base'))"],
                text=True,
            )
        ]
        assert group_ids()["group_name"][0] == "root"
