.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(scales))
stopifnot(packageVersion("scales") == "1.4.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
example <- c(
  capture.output(print(expand_range(c(1, 1), mul = 0, add = 0.6))),
  capture.output(print(expand_range(c(1, 1), mul = 1, add = 0.6))),
  capture.output(print(expand_range(c(1, 9), mul = 0, add = 2)))
)
writeLines(example, file.path(out_dir, "expand_range-r.txt"))

json_num <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    v <- x[[i]]
    parts[[i]] <- if (is.na(v) && !is.nan(v)) "null"
      else if (is.nan(v)) "NaN"
      else if (is.infinite(v) && v > 0) "Infinity"
      else if (is.infinite(v) && v < 0) "-Infinity"
      else sprintf("%.17g", v)
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  expand_range(c(1, 9), mul = 0.1, add = 2)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
