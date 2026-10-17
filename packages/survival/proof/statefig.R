suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

fmt <- function(x) {
  if (length(x) == 1L && is.na(x)) {
    "NA"
  } else {
    paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.17g", v), ""), collapse = ",")
  }
}

connect <- matrix(c(0, 1, 2,
                    1, 0, 1,
                    0, 0, 0), nrow = 3, byrow = TRUE,
                  dimnames = list(c("well", "ill", "dead"), c("well", "ill", "dead")))

one <- function() {
  # statefig draws on the current device; the proof uses a null PDF device
  a <- survival:::statefig(c(2, 1), connect)
  b <- survival:::statefig(matrix(c(1, 2), ncol = 1), connect, offset = 0.02)
  cc <- survival:::statefig(cbind(c(0.1, 0.5, 0.9), c(0.2, 0.8, 0.5)), connect)
  p1 <- survival:::phi(0, 0, 1, 0, 0.3, c(0.05, 0.05), c(0.05, 0.05))
  p2 <- survival:::phi(0, 0, 1, 1, -0.4, c(0.03, 0.04), c(0.02, 0.05))
  p3 <- survival:::phi(0.2, 0.1, 0.8, 0.6, 0.25, c(0.04, 0.03), c(0.02, 0.06))
  c(fmt(as.vector(t(a))), fmt(as.vector(t(b))), fmt(as.vector(t(cc))),
    fmt(c(p1$center, p1$angle, p1$r)),
    fmt(c(p2$center, p2$angle, p2$r)),
    fmt(c(p3$center, p3$angle, p3$r)))
}

pdf(NULL)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
invisible(dev.off())
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
