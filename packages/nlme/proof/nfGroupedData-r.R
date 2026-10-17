.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  df <- data.frame(
    y = c(1, 2, 3, 4, 5, 7),
    x = c(1, 2, 1, 2, 1, 2),
    g = c("b", "b", "a", "a", "c", "c")
  )
  out <- nfGroupedData(y ~ x | g, data = df)
  c(
    as.integer(out$g),
    out$y,
    out$x,
    as.numeric(inherits(out, "nfGroupedData")),
    as.numeric(inherits(out, "nfnGroupedData")),
    as.numeric(attr(out, "order.groups"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
