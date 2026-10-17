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
    let mvt_o = out.join("mvt.o");
    let tv_o = out.join("tvpack.o");
    let shim_o = out.join("shim.o");
    let miwa_o = out.join("miwa.o");
    let wrap_o = out.join("miwa_wrap.o");
    let stubs = src.join("rstubs");

    run(Command::new("gfortran")
        .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
        .arg(src.join("mvt.f"))
        .arg("-o")
        .arg(&mvt_o));
    run(Command::new("gfortran")
        .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
        .arg(src.join("tvpack.f"))
        .arg("-o")
        .arg(&tv_o));
    run(Command::new("gcc")
        .args(["-c", "-fPIC", "-O2"])
        .arg(src.join("shim.c"))
        .arg("-o")
        .arg(&shim_o));
    run(Command::new("gcc")
        .args(["-c", "-fPIC", "-O2", "-I"])
        .arg(&stubs)
        .arg(src.join("miwa.c"))
        .arg("-o")
        .arg(&miwa_o));
    run(Command::new("gcc")
        .args(["-c", "-fPIC", "-O2", "-I"])
        .arg(&stubs)
        .arg(src.join("miwa_wrap.c"))
        .arg("-o")
        .arg(&wrap_o));

    let lib = out.join("libmvtf.a");
    run(Command::new("ar")
        .args(["crus"])
        .arg(&lib)
        .arg(&mvt_o)
        .arg(&tv_o)
        .arg(&shim_o)
        .arg(&miwa_o)
        .arg(&wrap_o));

    let gfortran_dir = String::from_utf8(
        Command::new("gfortran")
            .arg("-print-file-name=libgfortran.so")
            .output()
            .expect("gfortran")
            .stdout,
    )
    .unwrap();
    let gfortran_dir = PathBuf::from(gfortran_dir.trim()).parent().unwrap().to_path_buf();
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-search=native={}", gfortran_dir.display());
    println!("cargo:rustc-link-lib=static=mvtf");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rerun-if-changed=src/mvt.f");
    println!("cargo:rerun-if-changed=src/tvpack.f");
    println!("cargo:rerun-if-changed=src/shim.c");
    println!("cargo:rerun-if-changed=src/miwa.c");
    println!("cargo:rerun-if-changed=src/miwa_wrap.c");
}
