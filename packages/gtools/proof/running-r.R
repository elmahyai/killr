.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.list(x) && !is.matrix(x)) {
    parts <- character(0)
    for (nm in names(x)) {
      parts <- c(parts, nm, flat(x[[nm]]))
    }
    return(parts)
  }
  if (is.matrix(x)) {
    return(c(nrow(x), ncol(x), as.numeric(x)))
  }
  if (length(x) == 0) return(numeric(0))
  as.numeric(x)
}

sdfun <- function(x, sign = 1) mean(x) + sign * sqrt(var(x))

one <- function() {
  x <- 1:20
  parts <- list(
    flat(running(x, width = 5)),
    flat(running(x, width = 5, pad = TRUE)),
    flat(running(x, width = 5, align = "left", pad = TRUE)),
    flat(running(x, width = 5, align = "center", pad = TRUE)),
    flat(running(x, width = 5, fun = function(v) v)),
    flat(running(x, width = 5, fun = function(v) v, simplify = FALSE)),
    flat(running(x, width = 5, by = 5)),
    flat(running(x, width = 5, by = 2)),
    flat(running(x, width = 5, allow.fewer = TRUE, pad = TRUE)),
    flat(running(x, width = 5, allow.fewer = FALSE, pad = TRUE))
  )
  set.seed(42)
  dat <- rnorm(40, sd = 1 + (1:40) / 40)
  parts <- c(
    parts,
    flat(running(dat, width = 7, pad = TRUE, fun = mean)),
    flat(running(dat, width = 7, pad = TRUE, fun = sdfun, sign = -1)),
    flat(running(dat, width = 7, pad = TRUE, fun = sdfun, sign = 1))
  )
  sd.Y <- seq(0, 1, length.out = 30)
  X <- rnorm(30)
  Y <- rnorm(30, sd = sd.Y)
  parts <- c(parts, flat(running(X, Y, width = 9, fun = cor, pad = TRUE)))
  unlist(parts, use.names = FALSE)
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(format(value, digits = 17), collapse = ","), median(elapsed) * 1000))
