suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  tdata <- data.frame(
    id = c(1, 1, 1, 2, 2, 2),
    tstart = c(0, 5, 12, 0, 5, 11),
    tstop = c(5, 10, 15, 5, 10, 14),
    event = factor(c("a", "b", "censor", "a", "b", "censor"), levels = c("censor", "a", "b"))
  )
  fit <- survcheck(Surv(tstart, tstop, event) ~ 1, tdata, id = id)
  c(
    paste(fit$states, collapse = "|"),
    paste(names(fit$flag), sprintf("%.17g", fit$flag), sep = "=", collapse = "|"),
    paste(as.vector(fit$n), collapse = ","),
    paste(as.vector(as.matrix(fit$transitions)), collapse = ","),
    paste(dim(fit$transitions), collapse = "x"),
    paste(as.character(fit$istate), collapse = "|"),
    if (is.null(fit$gap)) "gap:NA" else paste0("gap:", paste(fit$gap$row, collapse = ","), ";", paste(fit$gap$id, collapse = ","))
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
