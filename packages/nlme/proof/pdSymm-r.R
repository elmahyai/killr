.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

fp <- function(x) {
  c(
    as.integer(isInitialized(x)),
    as.integer(Dim(x)[1]),
    as.integer(Dim(x)[2]),
    length(Names(x)),
    as.vector(x)
  )
}

one <- function() {
  m3 <- matrix(c(4, 1.2, 0.5, 1.2, 3, 0.7, 0.5, 0.7, 2), 3)
  m2 <- matrix(c(4, 1.2, 1.2, 3), 2)
  c(
    fp(pdSymm(m3)),
    fp(pdSymm(m2)),
    fp(pdSymm(c(0.3, -0.1, 0.5, 0.2, 0.05, -0.4)))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
