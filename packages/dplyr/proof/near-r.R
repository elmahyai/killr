.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(dplyr))
stopifnot(packageVersion("dplyr") == "1.2.1")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
example <- c(
  capture.output(print(sqrt(2)^2 == 2)),
  capture.output(print(near(sqrt(2)^2, 2)))
)
writeLines(example, file.path(out_dir, "near-r.txt"))

json_logi <- function(x) {
  parts <- ifelse(is.na(x), "null", ifelse(x, "1", "0"))
  paste0("[", paste(parts, collapse = ","), "]")
}

# Default tolerance. The eight-value pattern is sqrt(2)^2 against 2, a
# 1e-9 gap, NA, NaN, Inf against Inf, -Inf against Inf, 1e16 against
# 1e16+10, and 0 against 0, repeated 2500 times.
x <- rep(c(sqrt(2)^2, 1, NA_real_, NaN, Inf, -Inf, 1e16, 0), 2500)
y <- rep(c(2, 1 + 1e-9, 1, 1, Inf, Inf, 1e16 + 10, 0), 2500)
one <- function() {
  near(x, y)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_logi(value), median(elapsed) * 1000))
