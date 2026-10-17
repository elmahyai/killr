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

    // The sweep-hull triangulation is C++ (vendor/s_hull_pro.cpp, GPL3, unchanged).
    // The R glue is replaced by src/shull_shim.cpp. Flags match R's build (-O2, -fPIC).
    let units = [
        (vendor.join("s_hull_pro.cpp"), "s_hull_pro.o"),
        (src.join("shull_shim.cpp"), "shull_shim.o"),
    ];
    let mut objs = Vec::new();
    for (path, obj_name) in &units {
        let obj = out.join(obj_name);
        run(Command::new("g++")
            .args(["-std=gnu++17", "-c", "-fPIC", "-O2", "-I"])
            .arg(&vendor)
            .arg(path)
            .arg("-o")
            .arg(&obj));
        objs.push(obj);
        println!("cargo:rerun-if-changed={}", path.display());
    }
    println!("cargo:rerun-if-changed=vendor/s_hull_pro.h");

    let lib = out.join("libinterp_shull.a");
    let mut ar = Command::new("ar");
    ar.args(["crus"]).arg(&lib);
    for obj in &objs {
        ar.arg(obj);
    }
    run(&mut ar);

    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=interp_shull");
    println!("cargo:rustc-link-lib=stdc++");
}
