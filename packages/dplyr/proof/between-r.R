.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(dplyr))
stopifnot(packageVersion("dplyr") == "1.2.1")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

x <- rnorm(1e2)
inside <- x[between(x, -1, 1)]
levels <- c("low", "medium", "high")
ordered_x <- ordered(c("low", "medium", "high", "medium"), levels = levels)
example <- c(
  capture.output(print(between(1:12, 7, 9))),
  capture.output(print(inside)),
  capture.output(print(filter(starwars, between(height, 100, 150)))),
  capture.output(print(between(ordered_x, "medium", "high"))),
  capture.output(print(between(ordered_x, "medium", "high", ptype = ordered_x)))
)
writeLines(example, file.path(out_dir, "between-r.txt"))

json_logi <- function(x) {
  parts <- ifelse(is.na(x), "null", ifelse(x, "1", "0"))
  paste0("[", paste(parts, collapse = ","), "]")
}

# 1:12, NA, -Inf, and Inf against the bounds 7 and 9, repeated 2000 times.
check_x <- rep(c(1:12, NA_real_, -Inf, Inf), 2000)
one <- function() {
  between(check_x, 7, 9)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_logi(value), median(elapsed) * 1000))
