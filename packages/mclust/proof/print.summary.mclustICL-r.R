library(mclust)
x <- structure(10, class="summary.mclustICL")
one <- function() capture.output(print.summary.mclustICL(x))
invisible(one()); t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
cat(one(), sep="\n"); cat(sprintf("%.17g\n", median(t)))
