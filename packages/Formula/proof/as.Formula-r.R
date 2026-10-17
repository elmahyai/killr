.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(Formula))
stopifnot(identical(packageDescription("Formula")$Version, "1.2-6"))

f1 <- y ~ x1 + x2
f2 <- ~ z1 + z2 + z3
f3 <- y ~ x1 | x2
f4 <- y1 | y2 ~ x
f5 <- ~ z
F1 <- Formula(f1)

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
        ll <- paste(c(length(attr(val, "lhs")), length(attr(val, "rhs"))), collapse = ",")
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
    quote(as.Formula(F1)),
    quote(as.Formula(f1)),
    quote(as.Formula(f1, f2)),
    quote(as.Formula("y ~ x")),
    quote(as.Formula(f3)),
    quote(as.Formula(f4, f5)),
    quote(as.Formula(1)),
    quote(as.Formula(f1, f1)),
    quote(as.Formula(f1, foo = 1)),
    quote(as.Formula()),
    quote(as.Formula(1, 2))
  )
  parts <- vapply(exprs, line, character(1))
  ident <- if (identical(as.Formula(F1), F1)) "TRUE" else "FALSE"
  paste(c(parts, paste0("ID ", ident)), collapse = " || ")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
out <- file.path(getwd(), "as.Formula-r-out.txt")
writeLines(
  c(paste0("VALUE ", value), sprintf("MS %.17g", median(elapsed) * 1000)),
  out
)
