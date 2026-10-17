suppressPackageStartupMessages(library(survival))

one <- function() {
  group <- c("a", "a", "b", NA, "c", "a", "b", "c", "a")
  status <- c(1, 0, 1, 0, 1, 0, 1, 0, 1)
  x <- frailty.gamma(group, theta = 1, method = "fixed")
  coef <- c(0.2, -0.1, 0.05)
  pf <- attr(x, "pfun")
  r0 <- pf(coef, 1, 3)
  r0z <- pf(coef, 0, 3)
  out <- c(
    as.vector(x),
    attr(x, "sparse"),
    attr(x, "varname"),
    attr(x, "cparm")$theta,
    r0$recenter,
    r0$penalty,
    r0$first,
    r0$second,
    r0$flag,
    r0z$penalty,
    r0z$flag
  )
  hist <- list(theta = 1, c.loglik = -12.345)
  pr <- attr(x, "printfun")(coef, c(0.5, 0.4, 0.3), NULL, 3, hist)
  out <- c(out, pr$coef, pr$history)

  x2 <- frailty.gamma(group, method = "em", eps = 1e-4)
  cf <- attr(x2, "cfun")
  c0 <- cf(attr(x2, "cparm"), 0L, list(), group, status, -10.5)
  c1 <- cf(attr(x2, "cparm"), 1L, c0, group, status, -10.2)
  out <- c(out, c0$theta, c1$theta, c1$c.loglik)

  d <- c(2, 1, 3, 1)
  out <- c(out, survival:::frailty.gammacon(d, 0.5))

  x3 <- frailty.gamma(group, df = 2, method = "df", eps = 0.1)
  cp3 <- attr(x3, "cparm")
  out <- c(out, cp3$df, cp3$guess, cp3$eps)

  big <- c(1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6)
  x4 <- frailty.gamma(big, method = "fixed", theta = 0.5)
  out <- c(out, as.vector(x4), attr(x4, "sparse"))
  out
}

fmt <- function(x) {
  if (length(x) == 0) {
    return(character())
  }
  if (is.logical(x)) {
    return(ifelse(x, "TRUE", "FALSE"))
  }
  if (is.character(x)) {
    return(x)
  }
  vapply(
    x,
    function(z) {
      if (length(z) != 1 || is.na(z)) {
        return("NA")
      }
      sprintf("%.17g", z)
    },
    character(1)
  )
}

value <- fmt(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
