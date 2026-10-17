source("/tmp/metrics-src/Metrics/R/regression.R"); source("/tmp/metrics-src/Metrics/R/classification.R"); source("/tmp/metrics-src/Metrics/R/binary_classification.R"); source("/tmp/metrics-src/Metrics/R/time_series.R"); source("/tmp/metrics-src/Metrics/R/information_retrieval.R");
actual <- c(1.1,1.9,3.0,4.4,5.0,5.6); predicted <- c(0.9,1.8,2.5,4.5,5.0,6.2)
f <- function() { msle(actual,predicted) }
f(); t <- numeric(20); for (i in 1:20) { a <- Sys.time(); z <- f(); t[i] <- as.numeric(Sys.time()-a,units="secs") }
z <- f(); cat("result",paste(format(z,digits=17,scientific=TRUE),collapse=","),"\n"); cat("r_ms",format(median(t)*1000,digits=17,scientific=TRUE),"\n")
