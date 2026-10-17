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
    let src = manifest.join("src");
    let vendor = manifest.join("vendor");
    let radau_o = out.join("radau5.o");
    let radaua_o = out.join("radau5a.o");
    let kernel_o = out.join("radau_kernel.o");
    let rprintf_o = out.join("rprintf_stub.o");

    run(
        Command::new("gfortran")
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
            .arg(vendor.join("radau5.f"))
            .arg("-o")
            .arg(&radau_o),
    );
    run(
        Command::new("gfortran")
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
            .arg(vendor.join("radau5a.f"))
            .arg("-o")
            .arg(&radaua_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("radau_kernel.c"))
            .arg("-o")
            .arg(&kernel_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("rprintf_stub.c"))
            .arg("-o")
            .arg(&rprintf_o),
    );

    let lib = out.join("libradau5_kernel.a");
    run(
        Command::new("ar")
            .args(["crus"])
            .arg(&lib)
            .arg(&radau_o)
            .arg(&radaua_o)
            .arg(&kernel_o)
            .arg(&rprintf_o),
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
    println!("cargo:rustc-link-lib=static=radau5_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=blas");
    println!("cargo:rerun-if-changed=vendor/radau5.f");
    println!("cargo:rerun-if-changed=vendor/radau5a.f");
    println!("cargo:rerun-if-changed=src/radau_kernel.c");
    println!("cargo:rerun-if-changed=src/rprintf_stub.c");
}
