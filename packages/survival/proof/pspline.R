suppressPackageStartupMessages(library(survival))

one <- function() {
  x <- c(50, 60, 70, NA, 80, 55, 65, 40, 95)
  p <- pspline(x, df = 4, penalty = FALSE)
  p2 <- pspline(x, df = 4)
  c(
    format(as.vector(p), scientific = FALSE, digits = 17),
    format(as.vector(attr(p2, "pparm")), scientific = FALSE, digits = 17),
    attr(p2, "varname")
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
