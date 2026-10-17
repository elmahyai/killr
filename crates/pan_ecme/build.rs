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
    let src = manifest.join("vendor").join("pan.f");
    let obj = out.join("pan.o");

    // The whole of pan.f is compiled, as R compiles it. Its ECME routines call no R
    // entry points, so no stubs are needed.
    run(Command::new("gfortran")
        .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
        .arg(&src)
        .arg("-o")
        .arg(&obj));

    let lib = out.join("libpan_ecme_kernel.a");
    run(Command::new("ar").args(["crus"]).arg(&lib).arg(&obj));

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
    println!("cargo:rustc-link-lib=static=pan_ecme_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rerun-if-changed={}", src.display());
    println!("cargo:rerun-if-changed=build.rs");
}
