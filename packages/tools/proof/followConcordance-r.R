suppressPackageStartupMessages(library(tools))

one <- function() {
  con <- list(offset=0L, srcFile="a.Rnw", srcLine=c(1L,2L,4L))
  prev <- list(offset=0L, srcFile="a.R", srcLine=c(10L, NA, 30L, 40L))
  f <- followConcordance(con, prev)
  paste0(paste(f$srcFile, collapse=","), " ", paste(f$srcLine, collapse=","), "\n")
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
