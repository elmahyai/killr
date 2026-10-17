source("/tmp/metrics-src/Metrics/R/regression.R"); source("/tmp/metrics-src/Metrics/R/classification.R"); source("/tmp/metrics-src/Metrics/R/binary_classification.R"); source("/tmp/metrics-src/Metrics/R/time_series.R"); source("/tmp/metrics-src/Metrics/R/information_retrieval.R");
rater.a <- c(1,4,5,5,2,1); rater.b <- c(2,2,4,5,3,3)
f <- function() { ScoreQuadraticWeightedKappa(rater.a,rater.b,1,5) }
f(); t <- numeric(20); for (i in 1:20) { a <- Sys.time(); z <- f(); t[i] <- as.numeric(Sys.time()-a,units="secs") }
z <- f(); cat("result",paste(format(z,digits=17,scientific=TRUE),collapse=","),"\n"); cat("r_ms",format(median(t)*1000,digits=17,scientific=TRUE),"\n")
