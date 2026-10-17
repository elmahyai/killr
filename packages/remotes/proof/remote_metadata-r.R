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

one <- function() remotes:::remote_metadata(remotes:::local_remote(path))
value <- one()
stopifnot(identical(value$RemoteType, "local"))
stopifnot(identical(value$RemoteUrl, normalizePath(path)))
stopifnot(is.null(value$RemoteSubdir))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got$RemoteType, value$RemoteType))
  stopifnot(identical(got$RemoteUrl, value$RemoteUrl))
  stopifnot(is.null(got$RemoteSubdir))
}

sentence <- "remote_metadata on a local directory returns RemoteType local and RemoteUrl equal to normalizePath."
writeLines(sentence, file.path(out_dir, "remote_metadata-r.txt"))

url_ok <- identical(value$RemoteUrl, normalizePath(path))
cat(sprintf(
  "{\"value\":{\"RemoteType\":\"local\",\"url_matches\":%s,\"RemoteSubdir\":null},\"median_ms\":%.17g}\n",
  if (isTRUE(url_ok)) "true" else "false",
  median(elapsed) * 1000
))
