use std::path::PathBuf;

fn main() {
    let vendor = PathBuf::from("vendor");
    let mut build = cc::Build::new();
    build.include(&vendor);
    build.flag("-DHAVE_ZLIB");
    build.flag("-std=c11");
    build.flag("-Wno-unused-function");
    build.flag("-Wno-unused-parameter");
    for dir in ["", "sas", "spss", "stata"] {
        let path = if dir.is_empty() {
            vendor.clone()
        } else {
            vendor.join(dir)
        };
        for entry in std::fs::read_dir(&path).unwrap() {
            let entry = entry.unwrap();
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if name.ends_with(".c") {
                build.file(entry.path());
            }
        }
    }
    build.compile("readstat");
    println!("cargo:rustc-link-lib=z");

    let bindings = bindgen::Builder::default()
        .header(vendor.join("readstat.h").to_string_lossy())
        .clang_arg(format!("-I{}", vendor.display()))
        .allowlist_function("readstat_.*")
        .allowlist_type("readstat_.*")
        .allowlist_type("mr_set_t")
        .layout_tests(false)
        .generate_comments(false)
        .generate()
        .expect("bindgen");
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("bindings.rs");
    bindings.write_to_file(out).unwrap();
    println!("cargo:rerun-if-changed=vendor/readstat.h");
}
