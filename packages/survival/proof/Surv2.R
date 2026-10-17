suppressPackageStartupMessages(library(survival))

serialize_surv2 <- function(x) {
  states <- attr(x, "states")
  clabel <- attr(x, "clabel")
  c(
    paste(as.character(x), collapse = "|"),
    paste(as.vector(as.matrix(x)), collapse = "|"),
    if (is.null(states)) "" else paste(states, collapse = "|"),
    if (is.null(clabel)) "" else clabel,
    as.character(attr(x, "repeated"))
  )
}

one <- function() {
  a <- Surv2(c(1, 2.5, 10, NA), c(1, 0, 1, 1))
  b <- Surv2(c(1, 2, 3), c(TRUE, FALSE, TRUE))
  c <- Surv2(c(10, 20, 30), c(1, 2, 1))
  d <- Surv2(
    c(70, 72, 75, 78, 80, 82, 85),
    factor(
      c("CU", "CU", "MCI", "CU", "MCI", "MCI", "dementia"),
      levels = c("CU", "MCI", "dementia")
    ),
    repeated = "first"
  )
  c(serialize_surv2(a), serialize_surv2(b), serialize_surv2(c), serialize_surv2(d))
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
