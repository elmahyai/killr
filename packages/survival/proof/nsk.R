suppressPackageStartupMessages(library(survival))

one <- function() {
  x <- c(50, 60, 70, NA, 80, 55, 65, 40, 95)
  b1 <- nsk(x, df = 4, intercept = TRUE)
  b2 <- nsk(x, df = 3)
  b3 <- nsk(x, knots = c(55, 70), intercept = FALSE, Boundary.knots = c(40, 90))
  out <- c(
    as.vector(b1),
    as.vector(b2),
    as.vector(b3),
    attr(b1, "knots"),
    attr(b1, "Boundary.knots"),
    attr(b3, "knots"),
    attr(b3, "Boundary.knots")
  )
  out
}

fmt <- function(x) {
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
