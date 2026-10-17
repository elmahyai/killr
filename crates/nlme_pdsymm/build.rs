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
    let fortran = manifest.join("fortran");
    let src = manifest.join("src");

    // rs.f is vendored unchanged from nlme 3.1-171 (EISPACK rs, TRED2 + TQL2).
    let rs_src = fortran.join("rs.f");
    let rs_obj = out.join("rs.o");
    run(Command::new("gfortran")
        .args(["-c", "-fPIC", "-O2", "-fno-second-underscore", "-std=legacy"])
        .arg(&rs_src)
        .arg("-o")
        .arg(&rs_obj));
    println!("cargo:rerun-if-changed={}", rs_src.display());

    // rs.f calls HYPOT through PYTHAG. nlme supplies it as a C99 hypot wrapper.
    let hyp_src = src.join("hypot.c");
    let hyp_obj = out.join("hypot.o");
    run(Command::new("gcc")
        .args(["-c", "-fPIC", "-O2"])
        .arg(&hyp_src)
        .arg("-o")
        .arg(&hyp_obj));
    println!("cargo:rerun-if-changed={}", hyp_src.display());

    let lib = out.join("libnlme_pdsymm_kernel.a");
    let mut ar = Command::new("ar");
    ar.args(["crus"]).arg(&lib).arg(&rs_obj).arg(&hyp_obj);
    run(&mut ar);

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
    println!("cargo:rustc-link-lib=static=nlme_pdsymm_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=m");
}
