.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(Formula))
stopifnot(identical(packageDescription("Formula")$Version, "1.2-6"))

f1 <- y ~ x1 + x2 | z1 + z2 + z3
f2 <- y1 | y2 + y3 ~ x1 + I(x2^2) | 0 + log(x1) | x3 / x4
f3 <- ~ x + y
f4 <- y1 | y2 ~ x
f5 <- y ~ a | b | c
f6 <- y1 + y2 | y3 ~ x
f7 <- y ~ x

F1 <- Formula(f1)
F2 <- Formula(f2)

line <- function(expr) {
  tryCatch(
    {
      val <- eval(expr, envir = .GlobalEnv)
      if (inherits(val, "Formula")) {
        cls <- paste(class(val), collapse = ",")
        fl <- length(unclass(val))
        body <- paste(deparse(val), collapse = " ")
        al <- attr(val, "lhs")
        ar <- attr(val, "rhs")
        lhs_len <- if (is.null(al)) -1L else length(al)
        rhs_len <- if (is.null(ar)) -1L else length(ar)
        dep <- function(x) paste(deparse(x), collapse = " ")
        lhs_parts <- if (is.null(al)) "" else paste(vapply(al, dep, character(1)), collapse = ";")
        rhs_parts <- if (is.null(ar)) "" else paste(vapply(ar, dep, character(1)), collapse = ";")
        ll <- if (inherits(val, "Formula")) paste(c(length(attr(val, "lhs")), length(attr(val, "rhs"))), collapse = ",") else "-1,-1"
        paste(cls, fl, body, lhs_len, rhs_len, lhs_parts, rhs_parts, ll, sep = "|")
      } else {
        paste("OTHER", deparse(val), sep = "|")
      }
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

one <- function() {
  exprs <- list(
    quote(Formula(f1)),
    quote(Formula(f2)),
    quote(Formula(f3)),
    quote(Formula(f4)),
    quote(Formula(f5)),
    quote(Formula(f6)),
    quote(Formula(f7)),
    quote(Formula(F1)),
    quote(Formula(1)),
    quote(Formula("y ~ x"))
  )
  id <- if (identical(Formula(F1), F1)) "TRUE" else "FALSE"
  paste(c(vapply(exprs, line, character(1)), paste0("ID ", id)), collapse = " || ")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
