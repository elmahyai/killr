library(modeltools)
measure <- function(FUN) {
  value <- FUN(); times <- numeric(20)
  for (i in seq_len(20)) { t <- Sys.time(); FUN(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs"))*1000 }
  cat("value=", paste(value, collapse=","), "\n", sep="")
  cat("r_ms=", median(times), "\n", sep="")
}
measure(function() { e <- ModelEnvFormula(y ~ x, data.frame(y=c(1,2,3), x=c(2,4,6))); c(e@get('designMatrix'), e@get('responseMatrix')) })
