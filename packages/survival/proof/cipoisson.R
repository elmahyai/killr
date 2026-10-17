suppressPackageStartupMessages(library(survival))

one <- function() {
  a <- cipoisson(4)
  b <- cipoisson(c(0, 4, 10), time = c(1, 2, 3))
  c <- cipoisson(4, method = "anscombe")
  d <- cipoisson(4, time = 0)
  c(
    sprintf("%.17g", a[1]),
    sprintf("%.17g", a[2]),
    sprintf("%.17g", b[1, 1]),
    sprintf("%.17g", b[1, 2]),
    sprintf("%.17g", b[2, 1]),
    sprintf("%.17g", b[2, 2]),
    sprintf("%.17g", b[3, 1]),
    sprintf("%.17g", b[3, 2]),
    sprintf("%.17g", c[1]),
    sprintf("%.17g", c[2]),
    if (is.na(d[1])) "NA" else sprintf("%.17g", d[1]),
    if (is.na(d[2])) "NA" else sprintf("%.17g", d[2])
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
