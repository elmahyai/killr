suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  data(logan, package = "survival")
  nresp <- length(levels(logan$occupation))
  n <- nrow(logan)
  indx <- rep(1:n, nresp)
  logan2 <- data.frame(logan[indx, ],
    id = indx,
    occ2 = factor(rep(levels(logan$occupation), each = n))
  )
  logan2$y <- (logan2$occupation == logan2$occ2)
  fit <- clogit(y ~ occ2 + occ2:education + occ2:race + strata(id), logan2)
  vals <- c(as.numeric(fit$coefficients), as.numeric(fit$loglik))
  sprintf("%.17g", vals)
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
