.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  br <- c(0, 4, 8, 12)
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/truehist-r.svg")
  truehist(c(1, 2, 2, 3, 8, 9, 9, 10), breaks = br)
  dev.off()
  c(br, c(4, 0, 4) / (4 * 8))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
