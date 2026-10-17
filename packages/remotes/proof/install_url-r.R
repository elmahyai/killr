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
built <- tempfile("build")
dir.create(built)
owd <- getwd()
setwd(built)
status <- system2("R", c("CMD", "build", pkg, "--no-manual", "--no-build-vignettes"))
setwd(owd)
stopifnot(identical(status, 0L))
tar <- list.files(built, pattern = "\\.tar\\.gz$", full.names = TRUE)[[1]]
url <- paste0("file://", normalizePath(tar))
lib <- tempfile("lib")
dir.create(lib)

one <- function() {
  install_url(url, dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib)
}
value <- one()
stopifnot(identical(value, "minipkg"))
desc <- read.dcf(file.path(lib, "minipkg", "DESCRIPTION"))
stopifnot(identical(unname(desc[, "Version"]), "0.0.1"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, "minipkg"))
}

sentence <- "install_url() returns minipkg 0.0.1."
writeLines(sentence, file.path(out_dir, "install_url-r.txt"))
cat(sprintf("{\"name\":\"minipkg\",\"version\":\"0.0.1\",\"median_ms\":%.17g}\n", median(elapsed) * 1000))
