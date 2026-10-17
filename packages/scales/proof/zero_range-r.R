.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(scales))
stopifnot(packageVersion("scales") == "1.4.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
eps <- .Machine$double.eps
example <- c(
  capture.output(print(zero_range(c(1, 1 + eps)))),
  capture.output(print(zero_range(c(1, 1 + 99 * eps)))),
  capture.output(print(zero_range(c(1, 1 + 1001 * eps)))),
  capture.output(print(zero_range(c(1, 1 + 2 * eps), tol = eps))),
  capture.output(print(zero_range(100000 * c(1, 1 + eps)))),
  capture.output(print(zero_range(100000 * c(1, 1 + 1001 * eps)))),
  capture.output(print(zero_range(0.00001 * c(1, 1 + eps)))),
  capture.output(print(zero_range(0.00001 * c(1, 1 + 1001 * eps)))),
  capture.output(print(zero_range(c(1, NA)))),
  capture.output(print(zero_range(c(1, NaN)))),
  capture.output(print(zero_range(c(1, Inf)))),
  capture.output(print(zero_range(c(-Inf, Inf)))),
  capture.output(print(zero_range(c(Inf, Inf))))
)
writeLines(example, file.path(out_dir, "zero_range-r.txt"))

json_flag <- function(x) {
  if (length(x) != 1) stop("expected one logical")
  if (is.na(x)) return("null")
  if (isTRUE(x)) return("true")
  "false"
}

one <- function() {
  zero_range(c(1, 1 + 1001 * .Machine$double.eps))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_flag(value), median(elapsed) * 1000))
