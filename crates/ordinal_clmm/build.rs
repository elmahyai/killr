use std::env;
use std::path::PathBuf;
use std::process::Command;

fn run(cmd: &mut Command) {
    let status = cmd.status().unwrap_or_else(|err| panic!("{cmd:?}: {err}"));
    if !status.success() {
        panic!("{cmd:?} exited {status}");
    }
}

// Compiles the vendored ordinal kernels (src/utilityFuns.c, src/links.c from
// ordinal 2026.7-26) and the R API shim into one static archive.
fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let vendor = manifest.join("vendor");
    let shim = vendor.join("shim");

    let sources = [
        (vendor.join("ordinal").join("utilityFuns.c"), "utilityFuns.o"),
        (vendor.join("ordinal").join("links.c"), "links.o"),
        (shim.join("rshim.c"), "rshim.o"),
    ];
    let mut objs = Vec::new();
    for (src, obj_name) in sources.iter() {
        let obj = out.join(obj_name);
        run(Command::new("cc")
            .args(["-c", "-fPIC", "-O2", "-fno-fast-math", "-ffp-contract=off"])
            .arg("-I")
            .arg(&shim)
            .arg("-I")
            .arg(vendor.join("ordinal"))
            .arg(src)
            .arg("-o")
            .arg(&obj));
        objs.push(obj);
        println!("cargo:rerun-if-changed={}", src.display());
    }
    println!("cargo:rerun-if-changed={}", shim.display());

    let lib = out.join("libordinal_clmm_c.a");
    let mut ar = Command::new("ar");
    ar.args(["crus"]).arg(&lib);
    for obj in &objs {
        ar.arg(obj);
    }
    run(&mut ar);

    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=ordinal_clmm_c");
    println!("cargo:rustc-link-lib=m");
}
