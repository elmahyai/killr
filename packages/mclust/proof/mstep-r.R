library(mclust)
x <- c(1, 2, 3, 4)
z <- matrix(c(.8, .7, .2, .1, .2, .3, .8, .9), 4, 2)
one <- function() mstep(x, "E", z)
value <- one(); invisible(value)
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
print(value$parameters$mean)
cat(sprintf("%.17g\n", median(t)))
