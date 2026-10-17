.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

encode_names <- function(v) {
  if (is.null(v)) {
    return(0)
  }
  out <- c(length(v), nchar(v))
  for (nm in v) {
    out <- c(out, as.numeric(charToRaw(nm)))
  }
  out
}

one <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i,
    rep(2, n)
  )
  colnames(x) <- c("alpha", "beta", "gamma")
  m <- mcmc(x)
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i,
    rep(1, n)
  )
  m2 <- mcmc(y)
  ml <- mcmc.list(m, m)
  z <- cbind(sin(i / 7), cos(i / 8))
  mu <- mcmc(z)
  v <- sin(i / 9)
  mv <- mcmc(v)
  c(
    encode_names(varnames(m)),
    encode_names(varnames(mu, allow.null = FALSE)),
    encode_names(varnames(mv)),
    encode_names(varnames(mv, allow.null = FALSE)),
    encode_names(varnames(ml)),
    encode_names(varnames(ml, allow.null = FALSE)),
    encode_names(varnames(m2)),
    encode_names(varnames(m2, allow.null = FALSE)),
    encode_names(varnames(i))
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
writeLines(out, con = "proof/varnames-r.txt")
