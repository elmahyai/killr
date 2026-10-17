suppressPackageStartupMessages(library(xts))
pdf(tempfile())
x <- xts(1:5, as.POSIXct('2020-01-01', tz='UTC') + 0:4 * 86400)
y <- xts(c(10, 20, 30), index(x)[c(1, 3, 5)])
w <- xts(1:14, as.POSIXct('2020-01-01', tz='UTC') + 0:13 * 86400)
h <- xts(1:3, as.POSIXct('2020-01-01', tz='UTC') + 0:2 * 3600)
wider <- xts(c(2, 4, 6, 8, 10), index(x))
lo <- xts(c(0, 1, 2, 3, 4), index(x))
hi <- xts(c(2, 3, 4, 5, 6), index(x))
u <- xts(1:4, .POSIXct(c(1, 1, 1, 2), tz='UTC'))
one <- function() { paste(.indexisdst(x), collapse = "|") }
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('%.17g\n', median(elapsed) * 1000))
cat(value, '\n')
