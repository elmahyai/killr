suppressPackageStartupMessages(library(fitdistrplus))
x <- c(1,2,3,4,5)
call <- function() fitdist(x, "norm")
call(); ts <- numeric(20)
for (i in 1:20) { a <- Sys.time(); y <- call(); ts[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
print(list(value=y$estimate, median_ms=median(ts)))
