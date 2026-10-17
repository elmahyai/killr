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
    let util_o = out.join("util.o");
    let i1mach_o = out.join("i1mach.o");
    let mclust_o = out.join("mclust.o");
    let mclust2_o = out.join("mclust2.o");

    for (src, obj) in [
        (vendor.join("util.f"), &util_o),
        (vendor.join("i1mach.f"), &i1mach_o),
        (vendor.join("mclust.f"), &mclust_o),
        (vendor.join("mclust2.f"), &mclust2_o),
    ] {
        run(
            Command::new("gfortran")
                .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
                .arg(&src)
                .arg("-o")
                .arg(obj),
        );
    }

    let lib = out.join("libmclustbootstraplrt.a");
    run(
        Command::new("ar")
            .arg("crus")
            .arg(&lib)
            .arg(&util_o)
            .arg(&i1mach_o)
            .arg(&mclust_o)
            .arg(&mclust2_o),
    );

    let shared = out.join("libmclust_fortran.so");
    run(
        Command::new("gfortran")
            .args(["-fPIC", "-shared", "-O2", "-fno-second-underscore"])
            .arg(&util_o)
            .arg(&i1mach_o)
            .arg(&mclust_o)
            .arg(&mclust2_o)
            .arg("-o")
            .arg(&shared)
            .arg("-lgfortran")
            .arg("-llapack")
            .arg("-lblas"),
    );
    println!("cargo:rustc-env=MCLUST_FORTRAN_SO={}", shared.display());

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
    println!("cargo:rustc-link-lib=static=mclustbootstraplrt");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=lapack");
    println!("cargo:rustc-link-lib=blas");
    for name in ["util.f", "mclust.f", "mclust2.f"] {
        println!("cargo:rerun-if-changed=vendor/{name}");
    }
}
