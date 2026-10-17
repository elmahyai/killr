suppressPackageStartupMessages(library(survival))

serialize <- function(x) {
  paste(format(as.numeric(x), digits = 17, trim = TRUE), collapse = "|")
}

one <- function() {
  d <- as.Date(c("1970-01-01", "1960-01-01", "2000-06-15"))
  i <- c(0L, 3653L, 14765L)
  p <- as.POSIXct(c("2000-06-15 23:59:59", "1970-01-01 00:00:01"), tz = "UTC")
  n <- c(1.5, 2.25)
  c(
    serialize(ratetableDate(d)),
    serialize(ratetableDate(i)),
    serialize(ratetableDate(p)),
    serialize(ratetableDate(n)),
    format(as.numeric(ratetableDate(42L)), digits = 17, trim = TRUE)
  )
}

t0 <- as.numeric(Sys.time())
value <- one()
r_untimed <- (as.numeric(Sys.time()) - t0) * 1000

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
r_median <- median(elapsed) * 1000

cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("R_UNTIMED\n")
cat(sprintf("%.17g\n", r_untimed))
cat("R_MEDIAN\n")
cat(sprintf("%.17g\n", r_median))
