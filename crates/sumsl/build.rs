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
    let cfuncs_o = out.join("cfuncs.o");
    let fortran_o = out.join("dsumsl.o");
    let formats_o = out.join("formats_stub.o");
    let garch_o = out.join("garch_kernel.o");
    let d1mach_o = out.join("d1mach.o");

    run(
        Command::new("gfortran")
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
            .arg(vendor.join("cfuncs.f90"))
            .arg("-o")
            .arg(&cfuncs_o),
    );
    run(
        Command::new("gfortran")
            .args([
                "-c",
                "-fPIC",
                "-O2",
                "-fno-second-underscore",
                "-J",
                out.to_str().unwrap(),
                "-I",
                out.to_str().unwrap(),
            ])
            .arg(vendor.join("dsumsl.f"))
            .arg("-o")
            .arg(&fortran_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("formats_stub.c"))
            .arg("-o")
            .arg(&formats_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("garch_kernel.c"))
            .arg("-o")
            .arg(&garch_o),
    );
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("d1mach.c"))
            .arg("-o")
            .arg(&d1mach_o),
    );

    let lib = out.join("libsumsl_kernel.a");
    run(
        Command::new("ar")
            .args(["crus"])
            .arg(&lib)
            .arg(&cfuncs_o)
            .arg(&fortran_o)
            .arg(&formats_o)
            .arg(&garch_o)
            .arg(&d1mach_o),
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
    println!("cargo:rustc-link-lib=static=sumsl_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=blas");
    println!("cargo:rerun-if-changed=vendor/dsumsl.f");
    println!("cargo:rerun-if-changed=vendor/cfuncs.f90");
    println!("cargo:rerun-if-changed=src/formats_stub.c");
    println!("cargo:rerun-if-changed=src/garch_kernel.c");
}
