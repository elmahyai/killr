.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  x = c(0, 1, 0.5, 2),
  y = c(0, 0, 1, 0.5)
)

one <- function() {
  cs <- corSpher(2.5, form = ~ x + y, metric = "eu")
  cs <- Initialize(cs, data)
  as.vector(corMatrix(cs))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
