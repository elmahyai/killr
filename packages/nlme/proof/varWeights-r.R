.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  y = 1:9,
  x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3, 2.2, 3.3, 4.4),
  grp = c("A", "A", "B", "B", "C", "C", "A", "B", "C")
)

one <- function() {
  vp <- Initialize(varPower(0.35, form = ~x), data)
  vc <- Initialize(
    varComb(varPower(0.35, form = ~x), varIdent(value = c(B = 2, C = 3), form = ~1 | grp)),
    data
  )
  c(as.vector(varWeights(vp)), as.vector(varWeights(vc)))
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
