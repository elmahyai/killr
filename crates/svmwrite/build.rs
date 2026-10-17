use std::path::PathBuf;

fn main() {
    let svm_vendor = PathBuf::from("../svm/vendor");
    cc::Build::new()
        .cpp(true)
        .file(svm_vendor.join("svm.cpp"))
        .include(&svm_vendor)
        .flag_if_supported("-Wno-unused-parameter")
        .compile("svm_kernel");

    cc::Build::new()
        .file("vendor/e1071_svmwrite.c")
        .include(&svm_vendor)
        .include("vendor")
        .flag_if_supported("-Wno-unused-parameter")
        .compile("e1071_svmwrite");

    println!("cargo:rerun-if-changed=vendor/e1071_svmwrite.c");
    println!("cargo:rerun-if-changed={}", svm_vendor.join("svm.cpp").display());
}
