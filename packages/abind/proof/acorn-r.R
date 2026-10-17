.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(abind))
if (packageDescription("abind")$Version != "1.4-8") stop("expected abind 1.4-8")

flatten <- function(z) {
  out <- c()
  d <- dim(z)
  if (is.null(d)) {
    out <- c(out, 0, length(z))
    nm <- names(z)
    if (is.null(nm)) {
      out <- c(out, 0)
    } else {
      out <- c(out, 1, utf8ToInt(paste(nm, collapse = "\n")))
    }
    out <- c(out, as.numeric(z))
    return(out)
  }
  out <- c(out, length(d), d)
  dn <- dimnames(z)
  if (is.null(dn)) {
    out <- c(out, 0)
  } else {
    out <- c(out, 1, length(dn))
    for (margin in dn) {
      if (is.null(margin)) {
        out <- c(out, 0)
      } else {
        out <- c(out, 1, utf8ToInt(paste(margin, collapse = "\n")))
      }
    }
  }
  out <- c(out, as.numeric(z))
  out
}

one <- function() {
  x <- array(
    1:24,
    dim = c(4, 3, 2),
    dimnames = rev(list(letters[1:2], LETTERS[1:3], letters[23:26]))
  )
  w <- 1:10
  names(w) <- letters[1:10]
  y4 <- array(1:16, dim = c(2, 2, 2, 2))
  parts <- list(
    acorn(x),
    acorn(x, 3),
    acorn(x, -3),
    acorn(x, 3, -2),
    acorn(x, addrownums = FALSE),
    acorn(w, 4),
    acorn(w, -3),
    acorn(y4, 1, 1, 1, 2),
    acorn(y4, -1, -1, -1, -2)
  )
  out <- c()
  for (part in parts) {
    out <- c(out, flatten(part))
  }
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17))
