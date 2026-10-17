source("/tmp/metrics-src/Metrics/R/regression.R"); source("/tmp/metrics-src/Metrics/R/classification.R"); source("/tmp/metrics-src/Metrics/R/binary_classification.R"); source("/tmp/metrics-src/Metrics/R/time_series.R"); source("/tmp/metrics-src/Metrics/R/information_retrieval.R");
actual <- c(1,1,1,0,0,0); predicted <- c(1,0,1,1,1,1)
f <- function() { fbeta_score(actual,predicted) }
f(); t <- numeric(20); for (i in 1:20) { a <- Sys.time(); z <- f(); t[i] <- as.numeric(Sys.time()-a,units="secs") }
z <- f(); cat("result",paste(format(z,digits=17,scientific=TRUE),collapse=","),"\n"); cat("r_ms",format(median(t)*1000,digits=17,scientific=TRUE),"\n")
