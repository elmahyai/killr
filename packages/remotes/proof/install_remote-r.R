.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pkg <- tempfile("minipkg")
dir.create(pkg)
writeLines(c(
  "Package: minipkg", "Version: 0.0.1", "Title: Minimal",
  "Description: A minimal package for a check.", "License: MIT"
), file.path(pkg, "DESCRIPTION"))
writeLines("exportPattern(\"^[^.]\" )", file.path(pkg, "NAMESPACE"))
lib <- tempfile("lib")
dir.create(lib)
remote <- remotes:::local_remote(pkg)

one <- function() {
  install_remote(
    remote,
    dependencies = FALSE,
    upgrade = "never",
    force = FALSE,
    quiet = TRUE,
    build = FALSE,
    build_opts = c("--no-resave-data", "--no-manual", "--no-build-vignettes"),
    build_manual = FALSE,
    build_vignettes = FALSE,
    repos = getOption("repos"),
    type = getOption("pkgType"),
    lib = lib
  )
}
value <- one()
stopifnot(identical(value, "minipkg"))
version <- unname(read.dcf(file.path(lib, "minipkg", "DESCRIPTION"))[, "Version"])
stopifnot(identical(version, "0.0.1"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, "minipkg"))
}

sentence <- "install_remote() returns minipkg 0.0.1."
writeLines(sentence, file.path(out_dir, "install_remote-r.txt"))
cat(sprintf("{\"name\":\"minipkg\",\"version\":\"0.0.1\",\"median_ms\":%.17g}\n", median(elapsed) * 1000))
