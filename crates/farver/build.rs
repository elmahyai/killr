use std::path::PathBuf;

fn main() {
    let vendor = PathBuf::from("vendor");
    cc::Build::new()
        .cpp(true)
        .std("c++17")
        .file(vendor.join("ColorSpace.cpp"))
        .file(vendor.join("Conversion.cpp"))
        .file(vendor.join("Comparison.cpp"))
        .file(vendor.join("kernel.cpp"))
        .include(&vendor)
        .flag_if_supported("-Wno-unused-parameter")
        .flag_if_supported("-Wno-unused-variable")
        .compile("farver_kernel");

    println!("cargo:rerun-if-changed=vendor");
}
