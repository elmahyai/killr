suppressPackageStartupMessages(library(survival))

make_rt <- function() {
  rt <- array(1:6, dim = c(2, 3))
  class(rt) <- "ratetable"
  dn <- list(c("a", "b"), c("x", "y", "z"))
  names(dn) <- c("dim1", "dim2")
  dimnames(rt) <- dn
  attr(rt, "type") <- c(2, 1)
  attr(rt, "cutpoints") <- list(c(0, 1), NULL)
  rt
}

serialize_bool <- function(x) {
  if (is.logical(x) && length(x) == 1) {
    return(sprintf("%d", as.integer(x)))
  }
  paste(x, collapse = "|")
}

one <- function() {
  c(
    serialize_bool(is.ratetable(survexp.us)),
    serialize_bool(is.ratetable(lung)),
    serialize_bool(is.ratetable(make_rt())),
    serialize_bool(is.ratetable(1:3))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
