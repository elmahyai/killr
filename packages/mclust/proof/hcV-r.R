library(mclust)
one <- function() hcV(c(1,2,3,8,9), partition=c(1,1,1,2,2))
value <- one(); times <- numeric(20)
for (i in seq_along(times)) { t <- Sys.time(); one(); times[i] <- as.numeric(Sys.time()-t)*1000 }
print(unclass(value)); print(median(times))
