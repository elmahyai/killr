use std::env;
use std::path::PathBuf;
use std::process::Command;

fn run(cmd: &mut Command) {
    let status = cmd.status().unwrap_or_else(|err| panic!("{cmd:?}: {err}"));
    if !status.success() {
        panic!("{cmd:?} exited {status}");
    }
}

fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let vendor = manifest.join("vendor");
    let src = manifest.join("src");
    let util_o = out.join("util.o");
    let mclust_o = out.join("mclust.o");
    let mclust2_o = out.join("mclust2.o");
    let d1mach_o = out.join("d1mach.o");
    let stubs_o = out.join("r_stubs.o");

    for (src, obj) in [
        (vendor.join("util.f"), util_o.clone()),
        (vendor.join("mclust.f"), mclust_o.clone()),
        (vendor.join("mclust2.f"), mclust2_o.clone()),
    ] {
        run(
            Command::new("gfortran")
                .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
                .arg(&src)
                .arg("-o")
                .arg(&obj),
        );
    }

    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("d1mach.c"))
            .arg("-o")
            .arg(&d1mach_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("r_stubs.c"))
            .arg("-o")
            .arg(&stubs_o),
    );

    let lib = out.join("libmclust_kernel.a");
    run(
        Command::new("ar")
            .args(["crus"])
            .arg(&lib)
            .arg(&util_o)
            .arg(&mclust_o)
            .arg(&mclust2_o)
            .arg(&d1mach_o)
            .arg(&stubs_o),
    );

    let gfortran_dir = String::from_utf8(
        Command::new("gfortran")
            .arg("-print-file-name=libgfortran.so")
            .output()
            .expect("gfortran")
            .stdout,
    )
    .unwrap();
    let gfortran_dir = PathBuf::from(gfortran_dir.trim())
        .parent()
        .unwrap()
        .to_path_buf();
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-search=native={}", gfortran_dir.display());
    println!("cargo:rustc-link-lib=static=mclust_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=lapack");
    println!("cargo:rustc-link-lib=blas");
    println!("cargo:rerun-if-changed=vendor/util.f");
    println!("cargo:rerun-if-changed=vendor/mclust.f");
    println!("cargo:rerun-if-changed=vendor/mclust2.f");
}
