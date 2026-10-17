.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  x <- data.frame(
    height = c(170, 160, 175, NA, 180, 165),
    color = c("red", "blue", "red", "red", "blue", "red"),
    fast = c(TRUE, FALSE, TRUE, FALSE, TRUE, FALSE)
  )
  y <- c("A", "B", "A", "B", "A", "B")
  fit <- naiveBayes(x, y, laplace = 1)
  out <- c(as.vector(fit$apriori))
  for (nm in names(x)) {
    out <- c(out, as.vector(fit$tables[[nm]]))
  }
  out <- c(out, as.integer(fit$isnumeric))
  out
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
