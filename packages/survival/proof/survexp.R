suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

make_rt <- function() {
  rt <- array(as.double(1:6), dim = c(2, 3))
  class(rt) <- "ratetable"
  dn <- list(c("a", "b"), c("x", "y", "z"))
  names(dn) <- c("dim1", "dim2")
  dimnames(rt) <- dn
  attr(rt, "type") <- c(2, 1)
  attr(rt, "cutpoints") <- list(c(0, 1), NULL)
  rt
}

serialize <- function(fit) {
  c(
    paste(sprintf("%.17g", fit$time), collapse = ","),
    paste(sprintf("%.17g", fit$surv), collapse = ","),
    paste(sprintf("%.17g", fit$n.risk), collapse = ","),
    fit$method
  )
}

one <- function() {
  df <- data.frame(
    time = c(0.5, 1.5, 0.25, 2.0),
    dim1 = c(0.25, 0.75, 1.25, 0.5),
    dim2 = factor(c("x", "y", "z", "x"))
  )
  fit <- survexp(
    Surv(time) ~ 1,
    data = df,
    ratetable = make_rt(),
    rmap = list(dim1 = dim1, dim2 = dim2),
    method = "ederer"
  )
  serialize(fit)
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
