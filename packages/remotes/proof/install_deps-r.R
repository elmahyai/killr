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
lib <- tempfile("lib")
dir.create(lib)

one <- function() {
  install_deps(pkg, dependencies = FALSE, upgrade = "never", quiet = TRUE, lib = lib)
}
value <- one()
stopifnot(is.null(value))
stopifnot(identical(list.files(lib), character()))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(is.null(got))
}
stopifnot(identical(list.files(lib), character()))

sentence <- "install_deps(dependencies = FALSE) returns NULL."
writeLines(sentence, file.path(out_dir, "install_deps-r.txt"))
cat(sprintf("{\"value\":null,\"median_ms\":%.17g}\n", median(elapsed) * 1000))
