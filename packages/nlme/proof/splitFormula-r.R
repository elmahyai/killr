.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

enc <- function(pieces) {
  txt <- vapply(pieces, function(f) paste(deparse(f), collapse = ""), "")
  c(length(txt), unlist(lapply(txt, function(s) c(nchar(s), sum(utf8ToInt(s))))))
}

one <- function() {
  c(
    enc(splitFormula(~ a / b / c)),
    enc(splitFormula(y ~ (a + b) / c)),
    enc(splitFormula(~ x * z / w)),
    enc(splitFormula(~ a + b / c)),
    enc(splitFormula(~ a:b / c)),
    enc(splitFormula(~ p / q, sep = "/"))
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
