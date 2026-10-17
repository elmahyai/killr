.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  fmt <- function(v) {
    if (is.na(v)) return("NA")
    if (v) "TRUE" else "FALSE"
  }
  if (length(x) == 0) return(character(0))
  vapply(x, fmt, "")
}

one <- function() {
  c(
    flat(even(4)),
    flat(even(1:10)),
    flat(even(1:10 + 0.5)),
    flat(even(c(-4, -3, -2, -1, 0, 1, 2))),
    flat(even(c(Inf, -Inf, NaN))),
    flat(even(c(NA, 1, 2))),
    flat(even(c(1L, 2L, 3L))),
    flat(even(c(1.5, 2, 3, 4, NA, 0, -2))),
    flat(even(integer(0))),
    flat(even(c(TRUE, FALSE)))
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(paste(value, collapse = "|")), median(elapsed) * 1000))
