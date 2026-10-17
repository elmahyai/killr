library(mclust)
x <- matrix(c(10, 8, 9, 7), 2, 2, dimnames=list(c("1","2"),c("EII","VII")))
class(x) <- "mclustICL"
one <- function() summary.mclustICL(x)
invisible(one()); t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
z <- one()
cat(paste(names(z), as.numeric(z), sep="="), sep="\n")
cat(sprintf("%.17g\n", median(t)))
