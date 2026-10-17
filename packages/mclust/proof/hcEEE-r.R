library(mclust)
one <- function() hcEEE(matrix(c(1,2,2,1,8,9,9,8,4,4), ncol=2, byrow=TRUE), partition=c(1,1,2,2,3))
value <- one(); times <- numeric(20)
for (i in seq_along(times)) { t <- Sys.time(); one(); times[i] <- as.numeric(Sys.time()-t)*1000 }
print(unclass(value)); print(median(times))
