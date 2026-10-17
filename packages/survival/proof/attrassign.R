suppressPackageStartupMessages(library(survival))

serialize_attrassign <- function(aa) {
  c(
    paste(names(aa), collapse = "|"),
    unlist(lapply(aa, function(x) paste(x, collapse = " ")), use.names = FALSE)
  )
}

one <- function() {
  formula <- Surv(time, status) ~ factor(ph.ecog)
  tt <- terms(formula)
  mf <- model.frame(tt, data = lung)
  mm <- model.matrix(tt, mf)
  serialize_attrassign(attrassign(mm, tt))
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
