.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

one <- function() {
  mat1 <- matrix(
    c(0.11, 0.22, 0.33, 0.44, 0.55, 0.66, 1.11, 1.22, 1.33, 1.44, 1.55, 1.66),
    ncol = 2
  )
  mat2 <- mat1 + 10
  arr <- array(NA, dim = c(6, 2, 2))
  arr[, , 1] <- mat1
  arr[, , 2] <- mat2
  class(arr) <- "mcmc"
  attr(arr, "tspar") <- c(1, 6, 1)
  obj <- mcmcUpgrade(arr)
  parts <- if (inherits(obj, "mcmc.list")) length(obj) else 1L
  chains <- if (inherits(obj, "mcmc.list")) obj else list(obj)
  for (ch in chains) {
    parts <- c(parts, as.numeric(ch), mcpar(ch))
  }
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
writeLines(out, con = file.path(root, "mcmcUpgrade-r.txt"))
