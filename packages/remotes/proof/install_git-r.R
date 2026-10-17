.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

repo <- tempfile("gitpkg")
dir.create(repo)
writeLines(c(
  "Package: minipkg", "Version: 0.0.1", "Title: Minimal",
  "Description: A minimal package for a check.", "License: MIT"
), file.path(repo, "DESCRIPTION"))
writeLines("exportPattern(\"^[^.]\" )", file.path(repo, "NAMESPACE"))
git <- function(...) stopifnot(identical(system2("git", c("-C", repo, ...)), 0L))
git("init", "-q")
git("config", "user.email", "a@b.c")
git("config", "user.name", "a")
git("add", "DESCRIPTION", "NAMESPACE")
git("commit", "-q", "-m", "init")
url <- paste0("file://", normalizePath(repo))
lib <- tempfile("lib")
dir.create(lib)

one <- function() {
  install_git(url, dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib, git = "external")
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

sentence <- "install_git() returns minipkg 0.0.1."
writeLines(sentence, file.path(out_dir, "install_git-r.txt"))
cat(sprintf("{\"name\":\"minipkg\",\"version\":\"0.0.1\",\"median_ms\":%.17g}\n", median(elapsed) * 1000))
