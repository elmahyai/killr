suppressPackageStartupMessages(library(quantreg))
one <- function() {paste(trimws(sfnMessage(1)), trimws(sfnMessage(17)), sep='|')}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(value, "\n", sep="")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
