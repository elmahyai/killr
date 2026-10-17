.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
outfile <- file.path(root, "read.coda-proof.out")
indexfile <- file.path(root, "read.coda-proof.ind")

one <- function() {
  obj <- read.coda(outfile, indexfile, quiet = TRUE)
  vals <- as.numeric(obj)
  mcpar <- attr(obj, "mcpar")
  c(vals, mcpar, match(varnames(obj), c("alpha", "beta")))
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
writeLines(out, con = file.path(root, "read.coda-r.txt"))
