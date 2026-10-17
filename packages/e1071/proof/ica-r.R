.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  x <- matrix(
    c(0.2, 1.1, -0.4, 0.9, 0.5, -0.2, 1.3, 0.7, -0.8, 0.3, -0.1, 0.6),
    nrow = 4,
    ncol = 3,
    byrow = TRUE
  )
  fit <- ica(x, lrate = 0.05, epochs = 15, ncomp = 2, fun = "negative")
  c(as.numeric(fit$weights), as.numeric(fit$projection))

}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
