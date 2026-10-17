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

one <- function() remotes:::remote_sha(remotes:::local_remote(path))
value <- one()
stopifnot(identical(value, "1.0.0"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

sentence <- "remote_sha on a local directory with Version: 1.0.0 returns 1.0.0."
writeLines(sentence, file.path(out_dir, "remote_sha-r.txt"))

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
