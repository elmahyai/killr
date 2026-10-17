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
            .args(["-c", "-fPIC", "-O2", "-fno-second-underscore"])
            .arg(&src)
            .arg("-o")
            .arg(&obj),
    );
    obj
}

fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let vendor = manifest.join("vendor");
    let src = manifest.join("src");

    let mut objects = vec![
        compile_fortran(&out, &vendor, "dlinpk.f"),
        compile_fortran(&out, &vendor, "opkda1.f"),
        compile_fortran(&out, &vendor, "opkdmain.f"),
        compile_fortran(&out, &vendor, "errmsg.f"),
    ];

    let bridge_o = out.join("bridge.o");
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("bridge.c"))
            .arg("-o")
            .arg(&bridge_o),
    );
    objects.push(bridge_o);

    let rprintf_o = out.join("rprintf_stub.o");
    run(
        Command::new("gcc")
            .args(["-c", "-fPIC", "-O2"])
            .arg(src.join("rprintf_stub.c"))
            .arg("-o")
            .arg(&rprintf_o),
    );
    objects.push(rprintf_o);

    let lib = out.join("libdede_kernel.a");
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
    println!("cargo:rustc-link-lib=static=dede_kernel");
    println!("cargo:rustc-link-lib=gfortran");
    println!("cargo:rustc-link-lib=blas");
}
