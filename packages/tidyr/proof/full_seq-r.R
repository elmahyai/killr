suppressPackageStartupMessages(library(tidyr))
stopifnot(identical(as.character(packageVersion("tidyr")), "1.3.2"))
days <- as.Date("2001-01-01") + c(0, 2, 6)
clock <- as.POSIXct(as.Date("2001-01-01") + c(0, 2))
one <- function() {
  gaps <- full_seq(c(1, 2, 4, 5, 10), 1)
  tol <- full_seq(c(0, 10, 20), 11, tol = 2)
  short <- full_seq(c(0, 10, 16), 11, tol = 5)
  frac <- full_seq(c(0.1, 0.3, 0.7), 0.2)
  grid <- full_seq(c(0, 0.3, 0.6, 1), 0.1)
  neg <- full_seq(c(-4, -1, 2), 1.5)
  dated <- full_seq(days, 2)
  clocked <- full_seq(clock, 86400)
  if (!inherits(dated, "Date")) stop("Date class was not restored")
  if (!identical(attr(clocked, "tzone"), "UTC")) stop("POSIXct tzone was not restored")
  c(gaps, tol, short, frac, grid, neg, as.numeric(dated), as.numeric(clocked))
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
