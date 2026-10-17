.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

n <- 200L
i <- seq_len(n)
x <- cbind(
  sin(i / 3) + 0.2 * cos(i),
  cos(i / 5) + 0.01 * i,
  rep(2, n)
)
m <- as.mcmc(x)

acf_values <- function(m, lag.max = 10L) {
  getAcf <- function(x, lag.max) as.vector(acf(x, lag.max = lag.max, plot = FALSE)$acf)
  mat <- as.matrix(m)
  nvar <- ncol(mat)
  out <- numeric(0)
  for (j in seq_len(nvar)) {
    v <- getAcf(mat[, j], lag.max)
    ylim_val <- max(abs(v[-1]), na.rm = TRUE)
    out <- c(out, -ylim_val, ylim_val, v)
  }
  out
}

one <- function() {
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  acfplot(m, lag.max = 10L)
  acf_values(m, lag.max = 10L)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
encode <- function(x) {
  if (is.nan(x)) return("null")
  if (is.infinite(x)) return(ifelse(x > 0, "1e300", "-1e300"))
  sprintf("%.17g", x)
}
parts <- vapply(value, encode, character(1))
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
