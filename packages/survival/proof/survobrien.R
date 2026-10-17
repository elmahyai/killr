suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

serialize <- function(cdata) {
  out <- c(paste(names(cdata), collapse = "|"))
  for (nm in names(cdata)) {
    col <- cdata[[nm]]
    if (is.factor(col)) col <- as.integer(col)
    if (is.numeric(col)) {
      out <- c(out, paste(sprintf("%.17g", col), collapse = ","))
    } else {
      out <- c(out, paste(col, collapse = ","))
    }
  }
  out
}

one <- function() {
  xx <- survobrien(
    Surv(futime, fustat) ~ age + factor(rx) + I(ecog.ps),
    data = ovarian
  )
  serialize(xx)
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
