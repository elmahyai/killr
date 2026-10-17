.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data <- data.frame(
    y = 1:12,
    Subject = factor(rep(c("A", "B", "C"), each = 4))
  )
  cs1 <- corCompSymm(0.5, form = ~ 1 | Subject)
  cs1 <- Initialize(cs1, data)
  f <- corFactor(cs1)
  c(as.vector(f), attr(f, "logDet"))
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
