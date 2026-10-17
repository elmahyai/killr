use std::path::PathBuf;

fn main() {
    let vendor = PathBuf::from("vendor");
    cc::Build::new()
        .cpp(true)
        .file(vendor.join("svm.cpp"))
        .include(&vendor)
        .flag_if_supported("-Wno-unused-parameter")
        .compile("svm_kernel");

    cc::Build::new()
        .file(vendor.join("e1071_rng.c"))
        .file(vendor.join("e1071_svm.c"))
        .include(&vendor)
        .flag_if_supported("-Wno-unused-parameter")
        .compile("e1071_svm_wrapper");

    println!("cargo:rerun-if-changed=vendor/svm.cpp");
    println!("cargo:rerun-if-changed=vendor/svm.h");
    println!("cargo:rerun-if-changed=vendor/e1071_svm.c");
    println!("cargo:rerun-if-changed=vendor/e1071_svm.h");
}
