suppressPackageStartupMessages(library(survival))

one <- function() {
  data(solder, package = "survival")
  fit1 <- lm(skips ~ Solder * Opening + Mask, data = solder)
  y <- yates(fit1, ~Opening, population = "factorial")
  c(
    as.character(y$estimate$Opening),
    y$estimate$pmm,
    y$estimate$std,
    as.vector(y$test)
  )
}

fmt <- function(x) {
  vapply(
    x,
    function(z) {
      if (length(z) != 1 || is.na(z)) {
        return("NA")
      }
      if (is.character(z)) {
        return(z)
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
