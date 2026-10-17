library(mclust)
x <- c(1, 2, 3, 4)
one <- function() mclustBIC(x, G = 1, modelNames = "E", verbose = FALSE)
invisible(one())
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); invisible(one()); t[i] <- as.numeric(Sys.time() - a, units = "secs") * 1000 }
z <- one(); cat(sprintf("%.17g\n", z[1, 1])); cat(sprintf("%.17g\n", median(t)))
