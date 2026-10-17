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
    dim = c(2, 3, 4),
    dimnames = list(letters[1:2], LETTERS[1:3], letters[23:26])
  )
  parts <- list(
    adrop(x[1, , , drop = FALSE], drop = 1),
    adrop(x[, 1, , drop = FALSE], drop = 2),
    adrop(x[, , 1, drop = FALSE], drop = 3),
    adrop(x[1, 1, 1, drop = FALSE], drop = 1),
    adrop(x[1, 1, 1, drop = FALSE], drop = 2),
    adrop(x[1, 1, 1, drop = FALSE], drop = 3),
    adrop(x[1, 1, 1, drop = FALSE], drop = 1:2),
    adrop(x[1, 1, 1, drop = FALSE], drop = 1:2, one.d = TRUE),
    adrop(x[1, 1, 1, drop = FALSE], drop = 1:2, named = FALSE),
    adrop(x[1, 1, 1, drop = FALSE], drop = NULL),
    adrop(x[1, 1, , drop = FALSE], drop = c(FALSE, TRUE, FALSE))
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
