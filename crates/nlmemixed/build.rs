fn main() {
    cc::Build::new()
        .file("src/optif9.c")
        .flag("-std=c99")
        .flag_if_supported("-Wno-unused-parameter")
        .flag_if_supported("-Wno-unused-function")
        .compile("optif9");
    println!("cargo:rerun-if-changed=src/optif9.c");
    println!("cargo:rustc-link-lib=m");
}
