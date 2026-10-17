.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.list(x)) return(unlist(lapply(x, flat), use.names = FALSE))
  if (is.matrix(x)) return(as.numeric(x))
  as.numeric(x)
}

one <- function() {
  c(
    flat(asc(letters)),
    flat(asc("hello!")),
    flat(asc(c("a", "e", "i", "o", "u", "y"))),
    flat(asc(c("ae", "io", "uy"))),
    flat(asc("hello!", simplify = FALSE)),
    flat(asc(c("ae", "io", "uy"), simplify = FALSE)),
    flat(asc(c("a", "e", "i", "o", "u", "y"), simplify = FALSE)),
    flat(asc(c("ae", "io", "uy"), simplify = FALSE)),
    flat(asc("caf\u00e9")),
    flat(asc(c("", "a"))),
    flat(asc(c("", ""))),
    flat(asc(c("a", "hello"))),
    flat(asc(character(0)))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(value, collapse = ","), median(elapsed) * 1000))
