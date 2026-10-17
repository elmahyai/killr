.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(methods))
suppressPackageStartupMessages(library(Formula))
stopifnot(identical(packageDescription("Formula")$Version, "1.2-6"))

setClass("Formula", contains = "numeric")
setClass("ChildF", contains = "Formula")
setClass("Other", contains = "numeric")

fml <- Formula(y ~ x1 + x2 | z1 + z2 + z3)
plain <- y ~ x1 + x2 | z1 + z2 + z3
s3_formula <- structure(1, class = "Formula")
s3_lower <- structure(1, class = "formula")
s3_second <- structure(1, class = c("foo", "Formula"))
s3_first <- structure(plain, class = c("Formula", "formula"))
s3_child <- structure(1, class = "ChildF")
s4_child <- new("ChildF", 1)
s4_formula <- new("Formula", 1)
s4_other <- new("Other", 1)
s4_primary <- asS4(structure(1, class = "Formula"), complete = FALSE)
s4_second <- asS4(structure(1, class = c("foo", "Formula")), complete = FALSE)
na_s3 <- 1
class(na_s3) <- c(NA_character_, "Formula")
na_s4 <- asS4(na_s3, complete = FALSE)
only_na <- 1
class(only_na) <- NA_character_
form_na <- 1
class(form_na) <- c("Formula", NA)
form_na_s4 <- asS4(form_na, complete = FALSE)
env_f <- new.env()
class(env_f) <- "Formula"
bare <- unclass(fml)
spaced <- structure(1, class = "Formula ")
empty_cl <- structure(1, class = "")
fn_f <- function() 1
class(fn_f) <- "Formula"
prepended <- fml
class(prepended) <- c("bar", class(fml))

line <- function(expr) {
  tryCatch(
    {
      val <- eval(expr, envir = .GlobalEnv)
      if (isTRUE(val)) "TRUE" else if (identical(val, FALSE)) "FALSE" else "OTHER"
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

one <- function() {
  exprs <- list(
    quote(is.Formula(fml)),
    quote(is.Formula(plain)),
    quote(is.Formula(NULL)),
    quote(is.Formula(1)),
    quote(is.Formula(1L)),
    quote(is.Formula(TRUE)),
    quote(is.Formula("Formula")),
    quote(is.Formula(list())),
    quote(is.Formula(numeric(0))),
    quote(is.Formula(s3_formula)),
    quote(is.Formula(s3_lower)),
    quote(is.Formula(s3_second)),
    quote(is.Formula(s3_first)),
    quote(is.Formula(s3_child)),
    quote(is.Formula(s4_child)),
    quote(is.Formula(s4_formula)),
    quote(is.Formula(s4_other)),
    quote(is.Formula(s4_primary)),
    quote(is.Formula(s4_second)),
    quote(is.Formula(na_s3)),
    quote(is.Formula(na_s4)),
    quote(is.Formula(only_na)),
    quote(is.Formula(form_na)),
    quote(is.Formula(form_na_s4)),
    quote(is.Formula(env_f)),
    quote(is.Formula(bare)),
    quote(is.Formula(spaced)),
    quote(is.Formula(empty_cl)),
    quote(is.Formula(fn_f)),
    quote(is.Formula(prepended)),
    quote(is.Formula(matrix(1))),
    quote(is.Formula(factor("Formula"))),
    quote(is.Formula(I(1))),
    quote(is.Formula(data.frame(a = 1))),
    quote(is.Formula(NA)),
    quote(is.Formula(NaN)),
    quote(is.Formula(object = NULL)),
    quote(is.Formula(ob = s3_formula)),
    quote(is.Formula(o = 1)),
    quote(is.Formula()),
    quote(is.Formula(1, 2)),
    quote(is.Formula(1, 2, 3)),
    quote(is.Formula(1, foo = 2)),
    quote(is.Formula(1, foo = 2, bar = 3)),
    quote(is.Formula(object = s3_formula, o = 1, ob = 2)),
    quote(is.Formula(o = 1, ob = 2)),
    quote(is.Formula(1, o = 2)),
    quote(is.Formula(Object = 1)),
    quote(is.Formula(2, object = s3_formula))
  )
  paste(vapply(exprs, line, character(1)), collapse = " | ")
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
