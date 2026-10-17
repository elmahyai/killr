library(mclust)
x <- matrix(c(10, 8, 9, 7), 2, 2,
            dimnames = list(c("1", "2"), c("EII", "VII")))
class(x) <- "mclustBIC"
one <- function() capture.output(print.mclustBIC(x))
invisible(one())
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time() - a, units = "secs") * 1000 }
cat(one(), sep = "\n"); cat(sprintf("%.17g\n", median(t)))
library(mclust)
x <- matrix(c(10, 8, 9, 7), 2, 2,
            dimnames = list(c("1", "2"), c("EII", "VII")))
class(x) <- "mclustBIC"
one <- function() capture.output(print.mclustBIC(x))
invisible(one())
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time() - a, units = "secs") * 1000 }
cat(one(), sep = "\n"); cat(sprintf("%.17g\n", median(t)))
