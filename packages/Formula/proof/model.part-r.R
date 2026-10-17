.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(Formula))
stopifnot(identical(packageDescription("Formula")$Version, "1.2-6"))

set.seed(1090)
dat <- as.data.frame(matrix(round(runif(21), digits = 2), ncol = 7))
colnames(dat) <- c("y1", "y2", "y3", "x1", "x2", "x3", "x4")
for (i in c(2, 6:7)) {
  dat[[i]] <- factor(dat[[i]] < 0.5, labels = c("a", "b"))
}
dat$y2[1] <- NA

F1 <- Formula(log(y1) ~ x1 + x2 | I(x1^2))
mf1 <- model.frame(F1, data = dat)
F2 <- Formula(y1 + y2 ~ x3)
mf2 <- model.frame(F2, data = dat)
F3 <- Formula(y1 + y2 | log(y3) ~ x1 + I(x2^2) | 0 + log(x1) | x3 / x4)
mf3 <- model.frame(F3, data = dat, subset = y1 < 0.75, weights = x1)

fp <- function(val) {
  if (is.data.frame(val)) {
    cols <- vapply(val, function(col) {
      paste(vapply(col, function(x) {
        if (is.na(x)) "NA"
        else if (is.numeric(x)) sprintf("%.17g", x)
        else as.character(x)
      }, character(1)), collapse = ",")
    }, character(1))
    paste0("DF|", paste(names(val), cols, sep = "=", collapse = ";"))
  } else if (is.numeric(val)) {
    paste0(
      "NUM|",
      paste(sprintf("%.17g", val), collapse = ","),
      "|NAMES|",
      paste(names(val), collapse = ",")
    )
  } else {
    paste("OTHER", paste(deparse(val), collapse = " "), sep = "|")
  }
}

line <- function(expr) {
  tryCatch(
    fp(eval(expr, envir = .GlobalEnv)),
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

one <- function() {
  exprs <- list(
    quote(model.part(F2, data = mf2, lhs = 1)),
    quote(model.part(F1, data = mf1, lhs = 1, drop = TRUE)),
    quote(model.part(F3, data = mf3, lhs = 1)),
    quote(model.part(F3, data = mf3, lhs = 2)),
    quote(model.part(F1, data = mf1, rhs = 1)),
    quote(model.part(F1, data = mf1, rhs = 2)),
    quote(model.part(y1 + y2 ~ x3, data = mf2, lhs = 1)),
    quote(model.part(F1, data = mf1, lhs = 0, rhs = 0)),
    quote(model.part(F1, data = dat, lhs = 1))
  )
  paste(vapply(exprs, line, character(1)), collapse = " || ")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
out <- file.path(getwd(), "model.part-r-out.txt")
writeLines(
  c(paste0("VALUE ", value), sprintf("MS %.17g", median(elapsed) * 1000)),
  out
)
