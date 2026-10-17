.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/eqscplot-r.svg")
  eqscplot(cbind(c(-2, 0, 3), c(-2, 3, 1)), xlab = "X", ylab = "Y")
  result <- par("usr")[3:4]
  dev.off()
  result
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
