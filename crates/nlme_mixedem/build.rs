use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

fn run(cmd: &mut Command) {
    let status = cmd.status().unwrap_or_else(|err| panic!("{cmd:?}: {err}"));
    if !status.success() {
        panic!("{cmd:?} exited {status}");
    }
}

fn compile_c(out: &Path, include: &Path, src: &Path) -> PathBuf {
    let stem = src.file_stem().unwrap().to_string_lossy().into_owned();
    let obj = out.join(format!("c_{stem}.o"));
    run(Command::new("gcc")
        .args(["-c", "-fPIC", "-O2", "-ffp-contract=off"])
        .arg("-I")
        .arg(include)
        .arg("-I")
        .arg(src.parent().unwrap())
        .arg(src)
        .arg("-o")
        .arg(&obj));
    println!("cargo:rerun-if-changed={}", src.display());
    obj
}

fn compile_fortran(out: &Path, src: &Path) -> PathBuf {
    let stem = src.file_stem().unwrap().to_string_lossy().into_owned();
    let obj = out.join(format!("f_{stem}.o"));
    // Default gfortran flags, as R builds src/appl and nlme builds src/*.f.
    run(Command::new("gfortran")
        .args(["-c", "-fPIC", "-O2", "-ffp-contract=off"])
        .arg(src)
        .arg("-o")
        .arg(&obj));
    println!("cargo:rerun-if-changed={}", src.display());
    obj
}

fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let c_dir = manifest.join("c");
    let include = c_dir.join("include");
    let f_dir = manifest.join("fortran");

    // nlme 3.1-171 C, unchanged, plus the entry point and R API stand-ins.
    let c_sources = [
        c_dir.join("matrix.c"),
        c_dir.join("nlmefit.c"),
        c_dir.join("pdMat.c"),
        c_dir.join("pythag.c"),
        c_dir.join("nlme_mixedem_entry.c"),
        c_dir.join("nlme_pdsymm_start.c"),
    ];
    // nlme chol.f and rs.f, and R 4.5.0 src/appl LINPACK routines that R's
    // dqrdc2/dqrsl/dtrsl/dpofa call through .Fortran links.
    let f_sources = [
        f_dir.join("chol.f"),
        f_dir.join("rs.f"),
        f_dir.join("dqrdc2.f"),
        f_dir.join("dqrsl.f"),
        f_dir.join("dtrsl.f"),
        f_dir.join("dpofa.f"),
    ];

    let mut objects = Vec::new();
    for src in &c_sources {
        objects.push(compile_c(&out, &include, src));
    }
    for src in &f_sources {
        objects.push(compile_fortran(&out, src));
    }
    println!("cargo:rerun-if-changed={}", include.display());
    println!("cargo:rerun-if-changed=build.rs");

    let lib = out.join("libnlme_mixedem_kernel.a");
    let _ = std::fs::remove_file(&lib);
    let mut ar = Command::new("ar");
    ar.args(["crus"]).arg(&lib);
    for obj in &objects {
        ar.arg(obj);
    }
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

    // BLAS is the system libblas.so.3 that R links (dnrm2, ddot, daxpy, dcopy,
    // dscal), so the LINPACK rounding matches R's.
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-search=native={}", gfortran_dir.display());
    println!("cargo:rustc-link-lib=static=nlme_mixedem_kernel");
    println!("cargo:rustc-link-lib=blas");
    // R's dgesdd and dpotrf come from libopenblas.so.0, which R also links.
    println!("cargo:rustc-link-lib=openblas");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=m");
}
