.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data <- data.frame(
    y = 1:6,
    x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3),
    g = factor(c("a", "a", "b", "b", "b", "c"), levels = c("a", "b", "c"))
  )
  c1 <- getCovariate(data, ~ x)
  c2 <- getCovariate(data, y ~ log(x) | g)
  c3 <- getCovariate(data, y ~ 1 | g)
  vf <- Initialize(varPower(0.35, form = ~x), data)
  c4 <- getCovariate(vf)
  cs1 <- corAR1(0.2, form = ~ 1 | g)
  c5 <- unlist(getCovariate(cs1, data = data))
  cs2 <- corAR1(0.2, form = ~ x | g)
  c6 <- unlist(getCovariate(cs2, data = data))
  cs3 <- corExp(0.5, form = ~ x)
  c7 <- getCovariate(cs3, data = data)
  cs4 <- corExp(0.5, form = ~ x | g)
  c8 <- unlist(getCovariate(cs4, data = data))
  c(c1, c2, c3, c4, c5, c6, c7, c8)
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
