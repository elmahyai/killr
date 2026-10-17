.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3.66")

x <- c(1, 2, 3, 4, 5)
y <- c(2.1, 3.2, 3.9, 3.1, 2)
mCall <- list(
  as.symbol("b0"),
  b0 = as.symbol("b0"),
  b1 = as.symbol("b1"),
  th = as.symbol("th"),
  x = quote(x)
)
dat <- list2env(list(x = x, y = y))
LHS <- quote(y)
fn <- getFromNamespace("negexp.SSival", "MASS")

one <- function() {
  sink(nullfile())
  on.exit(sink(), add = TRUE)
  res <- do.call(fn, list(mCall = mCall, data = dat, LHS = LHS))
  as.numeric(unlist(res))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
