.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

one <- function() {
  first <- mcmc(1:8, start = 11, end = 25, thin = 2)
  second <- mcmc(matrix(1:12, ncol = 2), start = 11, end = 16, thin = 1)
  c(mcpar(first), mcpar(second))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "mcpar-r.txt"))
dir.create(file.path(root, "..", "docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(out, con = file.path(root, "..", "docs", "output", "mcpar-r.txt"))
