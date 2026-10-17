.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

one <- function() {
  coda.options(default = TRUE)
  x <- c(1.2, 2.3, 3.4, 100, 200, 0.5, NA, 4.5)
  bw0 <- coda.options("bandwidth")(x)
  coda.options(digits = 4, trace = FALSE, frac1 = 0.15)
  coda.options(digits = 2)
  c(
    coda.options("digits"),
    as.numeric(coda.options("trace")),
    coda.options("frac1"),
    bw0,
    as.numeric(coda.options("quantiles")),
    as.numeric(unlist(coda.options("gr.bin", "gr.max"))),
    as.numeric(coda.options("combine.stats"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/coda.options-r.txt")
