.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
subj <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)
one <- function() {
  a <- Initialize(corARMA(c(0.3, -0.2, 0.1), form = ~ 1 | Subject, p = 2, q = 1), subj)
  b <- Initialize(corARMA(c(0.4), form = ~ 1 | Subject, p = 0, q = 1), subj)
  c1 <- Initialize(corARMA(c(0.5), form = ~ 1 | Subject, p = 1, q = 0), subj)
  conCor <- list(Xy = matrix(as.double(1:22), 11, 2), logLik = 0.5)
  ra <- recalc(a, conCor)
  rb <- recalc(b, conCor)
  rc <- recalc(c1, conCor)
  c(
    as.vector(ra$Xy), as.numeric(ra$logLik),
    as.vector(rb$Xy), as.numeric(rb$logLik),
    as.vector(rc$Xy), as.numeric(rc$logLik)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
