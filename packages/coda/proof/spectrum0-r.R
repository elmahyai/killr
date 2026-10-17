.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
input_path <- file.path(root, "spectrum0-input.tsv")

set.seed(1030L)
n <- 2500L
x <- cbind(rnorm(n), rep(2, n))
write.table(x, input_path, row.names = FALSE, col.names = FALSE)

one <- function() as.numeric(spectrum0(x)$spec)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, sprintf, fmt = "%.17g", character(1))
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "spectrum0-r.txt"))
