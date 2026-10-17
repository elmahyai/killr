suppressPackageStartupMessages(library(survival))

serialize_untangle <- function(u) {
  vars <- if (length(u$vars)) paste(u$vars, collapse = "|") else ""
  terms <- if (length(u$terms)) paste(u$terms, collapse = " ") else ""
  if (is.null(u$tvar)) {
    tvar <- ""
  } else if (length(u$tvar) == 1L) {
    tvar <- as.character(u$tvar)
  } else {
    tvar <- paste(u$tvar, collapse = " ")
  }
  c(vars, terms, tvar)
}

one <- function() {
  formula <- Surv(tt, ss) ~ x + z * strata(id)
  tms <- terms(formula, specials = "strata")
  u1 <- untangle.specials(tms, "strata")
  u2 <- untangle.specials(tms, "strata", order = 1:2)
  u3 <- untangle.specials(tms, "tt")
  formula2 <- Surv(tt, ss) ~ strata(a) + strata(b)
  tms2 <- terms(formula2, specials = "strata")
  u4 <- untangle.specials(tms2, "strata")
  c(
    serialize_untangle(u1),
    serialize_untangle(u2),
    serialize_untangle(u3),
    serialize_untangle(u4)
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
