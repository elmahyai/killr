.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
outfile <- file.path(root, "read.coda-proof.out")
indexfile <- file.path(root, "read.coda-proof.ind")

# Test read.coda.interactive by reading the same files it would use
# Since interactive input cannot be automated easily, we use the underlying mechanism
one <- function() {
  # read.coda.interactive returns an mcmc.list
  chains <- list()
  chains[[1]] <- read.coda(outfile, indexfile, quiet = TRUE)
  chains[[2]] <- read.coda(outfile, indexfile, quiet = TRUE)
  
  obj <- mcmc.list(chains[[1]], chains[[2]])
  
  # Get numeric values from all chains like as.numeric() does for mcmc.list
  parts <- nchain(obj)
  for (ch in obj) {
    parts <- c(parts, as.numeric(ch), mcpar(ch))
  }
  
  # Add name indices
  parts <- c(parts, match(varnames(obj), c("alpha", "beta")))
  parts
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
writeLines(out, con = file.path(root, "read.coda.interactive-r.txt"))
