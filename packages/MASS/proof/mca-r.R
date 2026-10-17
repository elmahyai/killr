.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")

one <- function() {
  df <- data.frame(
    x = factor(c("a", "b", "a", "c", "b", "c")),
    y = factor(c("L", "M", "M", "L", "L", "M"), levels = c("L", "M")),
    z = factor(c("p", "q", "p", "p", "q", "q")),
    row.names = c("r1", "r2", "r3", "r4", "r5", "r6")
  )
  fit <- mca(df, nf = 2, abbrev = FALSE)
  c(
    as.vector(fit$rs),
    as.vector(fit$cs),
    as.vector(fit$fs),
    fit$d,
    fit$p
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
