.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
infile <- file.path(root, "bugs2jags-in.dat")
outfile <- file.path(root, "bugs2jags-out-r.dat")

if (!file.exists(infile)) {
  bugs.dat <- list(
    N = 5L,
    y = c(1.1, 2.2, 3.3, 4.4, 5.5),
    X = array(1:12, dim = c(3, 4)),
    Z = array(1:24, dim = c(2, 3, 4))
  )
  dput(bugs.dat, file = infile)
}

one <- function() {
  bugs2jags(infile, outfile)
  env <- new.env()
  source(outfile, local = env)
  c(
    env$N,
    sum(env$y),
    sum(env$X),
    sum(env$Z),
    env$X[1, 1],
    env$X[3, 4],
    env$Z[1, 2, 3]
  )
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
writeLines(out, con = file.path(root, "bugs2jags-r.txt"))
