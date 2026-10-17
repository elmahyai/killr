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
  m <- mcmc(x)
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i,
    rep(1, n)
  )
  m2 <- mcmc(y)
  ml <- mcmc.list(m, m2)
  names(ml) <- c("chainA", "chainB")
  ml2 <- mcmc.list(m, m2)
  ml3 <- mcmc.list(m, m2, m)
  c(
    encode_names(chanames(ml)),
    encode_names(chanames(ml2)),
    encode_names(chanames(ml2, allow.null = FALSE)),
    encode_names(chanames(ml3, allow.null = FALSE)),
    encode_names(chanames(m)),
    encode_names(chanames(i))
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
writeLines(out, con = "proof/chanames-r.txt")
