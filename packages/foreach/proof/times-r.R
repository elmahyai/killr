suppressPackageStartupMessages(library(foreach))

fmt <- function(x) {
  if (is.null(x)) return("NULL")
  if (inherits(x, "error")) return(paste0("ERR:", conditionMessage(x)))
  if (is.matrix(x)) {
    vals <- paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
    return(paste0("M(", nrow(x), ",", ncol(x), ",", vals, ")"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("L()")
    parts <- vapply(x, fmt, character(1))
    return(paste0("L(", paste(parts, collapse = ","), ")"))
  }
  if (is.character(x)) return(paste0("C(", paste(x, collapse = ","), ")"))
  paste0("V(", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), ")")
}

run <- function(expr) {
  r <- tryCatch(expr, error = function(e) e)
  if (inherits(r, "error")) paste0("ERR:", conditionMessage(r)) else fmt(r)
}

one <- function() {
  parts <- c(
    run(times(4) %do% 2),
    run(times(1) %do% 4),
    run(times(0) %do% 4),
    run(times(1.5) %do% 4),
    run(times(3) %do% 7),
    run(times(5) %do% (1 + 2)),
    run(times(c(3)) %do% 8),
    run(times(TRUE)),
    run(times(1:2)),
    run(times(NULL)),
    run(times("a")),
    run(times(NA_real_) %do% 1)
  )
  paste(parts, collapse = "|")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
