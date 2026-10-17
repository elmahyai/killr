.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.list(x) && !is.character(x)) {
    if (length(x) == 0) return(numeric(0))
    return(unlist(lapply(x, flat), use.names = FALSE))
  }
  if (length(x) == 0) return(numeric(0))
  as.numeric(charToRaw(paste(as.character(x), collapse = "")))
}

one <- function() {
  c(
    flat(chr(65:90)),
    flat(chr(asc("hello!"))),
    flat(chr(asc("hello!", simplify = FALSE))),
    flat(chr(asc(c("ae", "io", "uy")))),
    flat(chr(asc(c("a", "e", "i", "o", "u", "y"), simplify = FALSE))),
    flat(chr(asc(c("ae", "io", "uy"), simplify = FALSE))),
    flat(chr(c(104, 101, 108, 108, 111, 33))),
    flat(chr(65)),
    flat(chr(c(NA_integer_, 65))),
    flat(chr(integer(0))),
    flat(chr(list(c(104, 101), 65))),
    flat(chr(c(256, -1))),
    flat(chr(asc(c("a", "hello"))))
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
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(value, collapse = ","), median(elapsed) * 1000))
