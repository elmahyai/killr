suppressPackageStartupMessages(library(tools))

one <- function() {
  con <- list(offset=0L, srcFile="a.Rnw", srcLine=c(1L,2L,4L))
  m <- matchConcordance(c(1,2,3), con)
  paste0(paste(m[,1], m[,2], sep=":", collapse="|"), "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
