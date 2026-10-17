suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
one <- function() {
  x <- c(1.0, 1.2, 0.8, 5.0, 5.5, 4.7, 1.1, 5.2)
  z <- c(1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1)
  out <- .Fortran(
    "me1e",
    as.logical(FALSE),
    as.double(x),
    as.integer(8),
    as.integer(2),
    as.double(-1),
    as.double(z),
    as.integer(100),
    as.double(1e-5),
    as.double(2.2204460492503131e-16),
    double(2),
    double(1),
    double(2),
    PACKAGE = "mclust"
  )
  c(
    as.numeric(out[[1]]),
    as.numeric(out[[2]]),
    as.numeric(out[[3]]),
    as.numeric(out[[4]]),
    as.numeric(out[[5]]),
    as.numeric(out[[6]]),
    as.numeric(out[[7]]),
    as.numeric(out[[8]]),
    as.numeric(out[[9]]),
    as.numeric(out[[10]]),
    as.numeric(out[[11]]),
    as.numeric(out[[12]])
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
