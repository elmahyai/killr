.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")
flat <- function(x) {
  if (is.null(x)) return("null")
  fmt <- function(v) {
    if (is.na(v)) return("NA")
    if (is.character(v)) return(as.character(v))
    sprintf("%.16g", as.numeric(v))
  }
  if (length(x) == 0) return("")
  paste(vapply(x, fmt, ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
one <- function() {
  set.seed(1234)
  a <- permute(1:10)
  set.seed(5678)
  b <- permute(1:100)
  set.seed(9012)
  c <- permute(c(1.5, 2.5, 3.5, 4.5, 5.5))
  set.seed(3456)
  d <- permute(letters[1:12])
  c(as.numeric(a), as.numeric(b), sum(b), as.numeric(c), as.character(d))
}
permute(1:3)
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
