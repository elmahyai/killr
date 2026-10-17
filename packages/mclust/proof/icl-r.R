library(mclust)
x <- list(n=4, bic=10, z=matrix(c(.8,.7,.2,.1,.2,.3,.8,.9), 4, 2))
class(x) <- "Mclust"
one <- function() icl(x)
value <- one(); t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
cat(value, "\n"); cat(sprintf("%.17g\n", median(t)))
