.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() github_pull("42")
value <- one()
writeLines(capture.output(print(value)), file.path(out_dir, "github_pull-r.txt"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

pull <- unclass(value)
stopifnot(is.character(pull), length(pull) == 1L, !is.na(pull[[1]]))
cls <- class(value)
stopifnot(length(cls) == 1L)

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

cat(sprintf(
  "{\"pull\":%s,\"class\":%s,\"median_ms\":%.17g}\n",
  json_escape(pull[[1]]),
  json_escape(cls[[1]]),
  median(elapsed) * 1000
))
