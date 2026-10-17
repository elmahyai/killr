library(mclust)
x <- structure(-12.3, df=5, nobs=10, class="mclustLoglik")
one <- function() capture.output(print.mclustLoglik(x))
value <- one(); invisible(value); t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
cat(value, sep="\n"); cat(sprintf("%.17g\n", median(t)))
