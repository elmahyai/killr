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

    let objects = [
        ("util.f", "util.o", true),
        ("mclust.f", "mclust.o", true),
        ("mclust2.f", "mclust2.o", true),
    ];
    let mut objs = Vec::new();
    for (name, obj_name, _fortran) in objects {
        let obj = out.join(obj_name);
        run(Command::new("gfortran")
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore", "-std=legacy"])
            .arg(vendor.join(name))
            .arg("-o")
            .arg(&obj));
        objs.push(obj);
        println!("cargo:rerun-if-changed=vendor/{name}");
    }
    for (name, obj_name) in [("d1mach.c", "d1mach.o"), ("r_stubs.c", "r_stubs.o")] {
        let obj = out.join(obj_name);
        run(Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join(name))
            .arg("-o")
            .arg(&obj));
        objs.push(obj);
        println!("cargo:rerun-if-changed=src/{name}");
    }

    let lib = out.join("libmclust_fortran.a");
    let mut ar = Command::new("ar");
    ar.args(["crus"]).arg(&lib);
    for obj in &objs {
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
    println!("cargo:rustc-link-lib=static=mclust_fortran");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=lapack");
    println!("cargo:rustc-link-lib=blas");
}
