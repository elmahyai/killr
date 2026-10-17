suppressPackageStartupMessages(library(quantreg))
x <- matrix(c(1.2, 3.4, 2.3, 4.5), 2, 2)
dimnames(x) <- list(c("1", "2"), c("1", "2"))
one <- function() {
  latex.table(x, file="/tmp/qtable", rowlabel="rows", caption="Demo")
  paste(readLines("/tmp/qtable.tex"), collapse="\n")
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(one(), "\n", sep="")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
