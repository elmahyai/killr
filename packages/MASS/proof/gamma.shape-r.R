.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3.66")
one <- function() {
  clotting <- data.frame(
    u = c(5, 10, 15, 20, 30, 40, 60, 80, 100),
    lot1 = c(118, 58, 42, 35, 27, 25, 21, 19, 18))
  clot1 <- glm(lot1 ~ log(u), data = clotting, family = Gamma)
  gs <- gamma.shape(clot1)
  c(gs$alpha, gs$SE)
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
