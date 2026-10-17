.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
flat <- function(x) {
  if (is.null(x)) return("null")
  if (is.character(x)) return(paste(x, collapse = "|"))
  if (length(x) == 0) return("")
  x <- as.numeric(x)
  paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.16g", v), ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s
}
one <- function() {
  idx <- seq(2000, 2002.25, by = 0.25)
  z <- zoo(1:10, idx)
  omit <- z[-3]
  zreg <- zoo(1:10, idx, frequency = 4)
  omit_reg <- zreg[-3]
  irreg <- zoo(1:4, c(0, 1, 2.5, 4))
  as.numeric(c(
    is.regular(z), is.regular(z, strict = TRUE),
    is.regular(omit), is.regular(omit, strict = TRUE),
    is.regular(omit_reg), is.regular(omit_reg, strict = TRUE),
    is.regular(irreg), is.regular(irreg, strict = TRUE),
    is.regular(zoo(1, 1)), is.regular(zoo(1, 1, frequency = 1)),
    is.regular(zoo(1:4, c(1, 2, 4, 7))),
    is.regular(ts(1:4, frequency = 4)),
    is.regular(c(1, 2, 4))
  ))
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
