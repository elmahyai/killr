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

serialize_match <- function(fit) {
  rflat <- as.vector(fit$R)
  cp1 <- if (is.null(fit$cutpoints[[1]])) "NULL" else paste(sprintf("%.17g", fit$cutpoints[[1]]), collapse = ",")
  cp2 <- if (is.null(fit$cutpoints[[2]])) "NULL" else paste(sprintf("%.17g", fit$cutpoints[[2]]), collapse = ",")
  c(
    paste(sprintf("%.17g", rflat), collapse = ","),
    cp1,
    cp2
  )
}

one <- function() {
  rt <- make_rt()
  Rdata <- data.frame(
    dim1 = c(0.25, 0.75, 1.25, 1.75),
    dim2 = factor(c("x", "y", "z", "x"), levels = c("x", "y", "z"))
  )
  fit <- survival:::match.ratetable(Rdata, rt)
  serialize_match(fit)
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
