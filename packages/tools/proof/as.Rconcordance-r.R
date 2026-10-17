suppressPackageStartupMessages(library(tools))

one <- function() {
  a <- as.Rconcordance(1)
  b <- as.Rconcordance("concordance:foo.tex:bar.Rnw:5 1 1")
  c <- as.Rconcordance("stuff concordance:foo.tex:bar.Rnw:ofs 2:10 1 2 3 4")
  paste0(
    "A ", is.null(a), "\n",
    "B ", b$offset, " ", b$srcFile, " ", paste(b$srcLine, collapse=","), "\n",
    "C ", c$offset, " ", c$srcFile, " ", paste(c$srcLine, collapse=","), "\n"
  )
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
