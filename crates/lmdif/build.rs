use std::env;
use std::path::PathBuf;
use std::process::Command;

fn run(cmd: &mut Command) {
    let status = cmd.status().unwrap_or_else(|err| panic!("{cmd:?}: {err}"));
    if !status.success() {
        panic!("{cmd:?} exited {status}");
    }
}

fn compile_fortran(out: &PathBuf, vendor: &PathBuf, name: &str) -> PathBuf {
    let src = vendor.join(name);
    let obj = out.join(name.replace('.', "_")).with_extension("o");
    run(
        Command::new("gfortran")
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore", "-std=legacy"])
            .arg(&src)
            .arg("-o")
            .arg(&obj),
    );
    println!("cargo:rerun-if-changed={}", src.display());
    obj
}

fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let vendor = manifest.join("vendor");
    let src = manifest.join("src");

    let fortran = [
        "lmdif.f",
        "lmder.f",
        "lmpar.f",
        "qrfac.f",
        "qrsolv.f",
        "fdjac2.f",
        "enorm.f",
        "dpmpar.f",
        "dogleg.f",
        "qform.f",
        "r1mpyq.f",
        "r1updt.f",
        "rwupdt.f",
        "chkder.f",
    ];
    let mut objects: Vec<PathBuf> = fortran
        .iter()
        .map(|name| compile_fortran(&out, &vendor, name))
        .collect();

    let bridge_o = out.join("bridge.o");
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("bridge.c"))
            .arg("-o")
            .arg(&bridge_o),
    );
    println!("cargo:rerun-if-changed={}", src.join("bridge.c").display());
    objects.push(bridge_o);

    let lib = out.join("liblmdif_kernel.a");
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

    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-search=native={}", gfortran_dir.display());
    println!("cargo:rustc-link-lib=static=lmdif_kernel");
    println!("cargo:rustc-link-lib=gfortran");
}
