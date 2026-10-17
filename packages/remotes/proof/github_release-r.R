.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() github_release()
value <- one()
writeLines(capture.output(print(value)), file.path(out_dir, "github_release-r.txt"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

integer_na <- is.integer(value) && length(value) == 1L && is.na(value[[1]]) && !is.nan(value[[1]])
cls <- class(value)
stopifnot(length(cls) == 1L)

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

cat(sprintf(
  "{\"integer_na\":%s,\"class\":%s,\"median_ms\":%.17g}\n",
  if (isTRUE(integer_na)) "true" else "false",
  json_escape(cls[[1]]),
  median(elapsed) * 1000
))
