suppressPackageStartupMessages(library(quantreg))
formulas <- list(
  y ~ x1 + qss(x2) + x3 + qss(x4),
  y ~ qss(x1) * x2,
  y ~ qss(x1) / (x2 + x3),
  y ~ (x1 + qss(x2))^2,
  y ~ qss(qss(x1)) + x2:x3
)
tts <- lapply(formulas, terms, specials = "qss")
one <- function() {
  unlist(lapply(tts, function(tt) {
    a <- untangle.specials(tt, "qss")
    b <- untangle.specials(tt, "qss", order = 2)
    c(
      paste(as.character(attr(tt, "variables"))[-1], collapse = ","),
      paste(attr(tt, "specials")$qss, collapse = ","),
      paste(a$vars, collapse = ","),
      paste(a$terms, collapse = ","),
      paste(b$terms, collapse = ",")
    )
  }))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(value, collapse="|"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
