use std::path::PathBuf;

fn main() {
    let vendor = PathBuf::from("vendor");
    cc::Build::new()
        .file(vendor.join("blowfish.c"))
        .file(vendor.join("bcrypt_pbkdf.c"))
        .include(&vendor)
        .flag("-std=c11")
        .flag("-Wno-unused-parameter")
        .compile("bcryptpbkdf_kernel");

    println!("cargo:rustc-link-lib=crypto");
    println!("cargo:rerun-if-changed=vendor/blowfish.c");
    println!("cargo:rerun-if-changed=vendor/bcrypt_pbkdf.c");
    println!("cargo:rerun-if-changed=vendor/blf.h");
}
