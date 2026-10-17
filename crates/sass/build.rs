//! Builds libsass 3.x from `vendor/libsass` with the cc crate.
//!
//! The source list is the `SOURCES` and `CSOURCES` lists in libsass's
//! `Makefile.conf`, compiled with the same include root (`include/`).

use std::path::PathBuf;

const CPP_SOURCES: &[&str] = &[
    "ast.cpp",
    "ast_values.cpp",
    "ast_supports.cpp",
    "ast_sel_cmp.cpp",
    "ast_sel_unify.cpp",
    "ast_sel_super.cpp",
    "ast_sel_weave.cpp",
    "ast_selectors.cpp",
    "context.cpp",
    "constants.cpp",
    "fn_utils.cpp",
    "fn_miscs.cpp",
    "fn_maps.cpp",
    "fn_lists.cpp",
    "fn_colors.cpp",
    "fn_numbers.cpp",
    "fn_strings.cpp",
    "fn_selectors.cpp",
    "color_maps.cpp",
    "environment.cpp",
    "ast_fwd_decl.cpp",
    "bind.cpp",
    "file.cpp",
    "util.cpp",
    "util_string.cpp",
    "json.cpp",
    "units.cpp",
    "values.cpp",
    "plugins.cpp",
    "source.cpp",
    "position.cpp",
    "lexer.cpp",
    "parser.cpp",
    "parser_selectors.cpp",
    "prelexer.cpp",
    "eval.cpp",
    "eval_selectors.cpp",
    "expand.cpp",
    "listize.cpp",
    "cssize.cpp",
    "extender.cpp",
    "extension.cpp",
    "stylesheet.cpp",
    "output.cpp",
    "inspect.cpp",
    "emitter.cpp",
    "check_nesting.cpp",
    "remove_placeholders.cpp",
    "sass.cpp",
    "sass_values.cpp",
    "sass_context.cpp",
    "sass_functions.cpp",
    "sass2scss.cpp",
    "backtrace.cpp",
    "operators.cpp",
    "ast2c.cpp",
    "c2ast.cpp",
    "to_value.cpp",
    "source_map.cpp",
    "error_handling.cpp",
    "memory/allocator.cpp",
    "memory/shared_ptr.cpp",
    "utf8_string.cpp",
    "base64vlq.cpp",
];

const C_SOURCES: &[&str] = &["cencode.c"];

fn main() {
    let root = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap()).join("vendor/libsass");
    let src = root.join("src");
    let include = root.join("include");

    let mut cpp = cc::Build::new();
    cpp.cpp(true)
        .std("c++11")
        .include(&include)
        .warnings(false)
        .opt_level(2);
    for name in CPP_SOURCES {
        let path = src.join(name);
        assert!(path.exists(), "missing libsass source {}", path.display());
        cpp.file(path);
    }
    cpp.compile("sass_libsass_cpp");

    let mut c = cc::Build::new();
    c.include(&include).warnings(false).opt_level(2);
    for name in C_SOURCES {
        c.file(src.join(name));
    }
    c.compile("sass_libsass_c");

    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("linux") {
        println!("cargo:rustc-link-lib=dl");
    }

    println!("cargo:rerun-if-changed=vendor/libsass");
    println!("cargo:rerun-if-changed=build.rs");
}
