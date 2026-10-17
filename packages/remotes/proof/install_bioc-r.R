.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

lib <- tempfile("lib")
dir.create(lib)

one <- function() {
  install_bioc("3.21/BiocVersion", dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib, git = "external")
}
value <- one()
stopifnot(identical(value, "BiocVersion"))
version <- unname(read.dcf(file.path(lib, "BiocVersion", "DESCRIPTION"))[, "Version"])
stopifnot(identical(version, "3.21.1"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, "BiocVersion"))
}

sentence <- "install_bioc() returns BiocVersion 3.21.1."
writeLines(sentence, file.path(out_dir, "install_bioc-r.txt"))
cat(sprintf("{\"name\":\"BiocVersion\",\"version\":\"3.21.1\",\"median_ms\":%.17g}\n", median(elapsed) * 1000))
