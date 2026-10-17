suppressPackageStartupMessages(library(survival))

one <- function() {
  age <- c(50, 60, 55, NA, 70)
  ecog <- c(0, 1, 0, 1, 2)
  x <- ridge(age, ecog, theta = 1)
  coef <- c(0.1, -0.2)
  pf <- attr(x, "pfun")
  pp <- attr(x, "pparm")
  r1 <- pf(coef, 1, 3, pp)
  out <- c(
    as.vector(t(x)),
    pp,
    attr(x, "varname"),
    attr(x, "cparm")$theta,
    r1$penalty,
    r1$first,
    r1$second,
    r1$flag
  )
  x2 <- ridge(age, ecog, df = 1, eps = 0.1)
  cp2 <- attr(x2, "cparm")
  out <- c(out, cp2$df, cp2$eps, cp2$thetas, cp2$dfs, cp2$guess)
  x3 <- ridge(age, ecog, theta = 2, scale = FALSE)
  pf3 <- attr(x3, "pfun")
  r3 <- pf3(coef, 2, 3, attr(x3, "pparm"))
  out <- c(out, r3$penalty, r3$first, r3$second)
  cfun <- attr(x, "cfun")
  cf <- cfun(attr(x, "cparm"), 1L, list())
  c(out, cf$theta, cf$done)
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
