.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
x <- c(0.3, -1.2, 2.5, 0.8, -0.4, 1.9, 0.1, -2.2, 3.1, 0.6, -0.9, 1.4)
json_num <- function(x) paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
one <- function() {
  pdf(NULL)
  on.exit(dev.off())
  z <- probplot(x, line = TRUE)
  c(z$int, z$slope, z$qdist(c(0.01, 0.5, 0.99)))
}
value <- one()
cat("probplot int, slope, qdist at 0.01, 0.5, 0.99:\n")
cat(sprintf("%.6g", value), "\n")
svg("packages/e1071/docs/output/probplot-r.svg", width = 6, height = 5)
probplot(x, line = TRUE)
dev.off()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf('{"value":%s,"median_ms":%.17g}', json_num(value), median(elapsed) * 1000),
           "packages/e1071/proof/probplot-r-out.json")
