library(modeltools)
measure <- function(FUN) {
  value <- FUN(); times <- numeric(20)
  for (i in seq_len(20)) { t <- Sys.time(); FUN(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs"))*1000 }
  cat("value=", paste(value, collapse=","), "\n", sep="")
  cat("r_ms=", median(times), "\n", sep="")
}
measure(function() { e <- ModelEnvMatrix(matrix(1:6,3,2), matrix(7:9,3,1)); c(e@get('designMatrix'), e@get('responseMatrix')) })
