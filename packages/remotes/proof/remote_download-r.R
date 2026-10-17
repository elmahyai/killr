.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

path <- tempfile()
dir.create(path)
writeLines(c("Package: foo", "Version: 1.0.0"), file.path(path, "DESCRIPTION"))

pkg_of <- function(bundle) {
  unname(read.dcf(file.path(bundle, "DESCRIPTION"))[1, "Package"])
}

one <- function() remotes:::remote_download(remotes:::local_remote(path))
value <- pkg_of(one())
stopifnot(identical(value, "foo"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  bundle <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(pkg_of(bundle), value))
}

sentence <- "remote_download on a local directory copies a directory whose DESCRIPTION says Package: foo."
writeLines(sentence, file.path(out_dir, "remote_download-r.txt"))

json_str <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0("\"", s, "\"")
}

cat(sprintf(
  "{\"value\":%s,\"median_ms\":%.17g}\n",
  json_str(value),
  median(elapsed) * 1000
))
