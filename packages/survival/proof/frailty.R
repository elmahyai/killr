suppressPackageStartupMessages(library(survival))

one <- function() {
  group <- c("a", "a", "b", NA, "c", "a", "b", "c", "a")
  status <- c(1, 0, 1, 0, 1, 0, 1, 0, 1)
  coef <- c(0.2, -0.1, 0.05)

  xg <- frailty(group, theta = 1, method = "fixed")
  pf <- attr(xg, "pfun")
  r0 <- pf(coef, 1, 3)
  out <- c(
    as.vector(xg),
    attr(xg, "sparse"),
    attr(xg, "cparm")$theta,
    r0$penalty,
    r0$first,
    r0$second
  )

  xg2 <- frailty(group, distribution = "gam", theta = 1, method = "fixed")
  out <- c(out, as.vector(xg2), pf(coef, 1, 3)$penalty)

  xgu <- frailty(group, distribution = "gaussian", theta = 1, method = "fixed")
  pfg <- attr(xgu, "pfun")
  rg <- pfg(coef, 1, 3)
  out <- c(
    out,
    as.vector(xgu),
    attr(xgu, "cparm")$theta,
    rg$penalty,
    rg$first,
    rg$second
  )

  xt <- frailty(group, distribution = "t", theta = 1, method = "fixed", tdf = 5)
  pft <- attr(xt, "pfun")
  tdf5 <- attr(xt, "pparm")
  rt <- pft(coef, 1, 3, tdf5)
  out <- c(
    out,
    as.vector(xt),
    attr(xt, "pparm"),
    attr(xt, "cparm")$theta,
    rt$penalty,
    rt$first,
    rt$second
  )

  xem <- frailty(group, method = "em", eps = 1e-4)
  cf <- attr(xem, "cfun")
  c0 <- cf(attr(xem, "cparm"), 0L, list(), group, status, -10.5)
  c1 <- cf(attr(xem, "cparm"), 1L, c0, group, status, -10.2)
  out <- c(out, c0$theta, c1$theta, c1$c.loglik)

  big <- c(1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6)
  x4 <- frailty(big, distribution = "gamma", method = "fixed", theta = 0.5)
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
