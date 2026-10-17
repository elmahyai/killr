suppressPackageStartupMessages(library(generics))
stopifnot(identical(as.character(packageVersion("generics")), "0.1.4"))
suppressMessages({
  setClass("AccP", slots = c(x = "numeric"))
  setClass("AccC", contains = "AccP")
})

fmt <- function(x) sprintf("%.17g", x)

err <- function(expr) {
  tryCatch(force(expr), error = function(e) conditionMessage(e))
}

one <- function() {
  evaluate.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  evaluate.sub <- function(x, ...) 100
  evaluate.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  evaluate.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  evaluate.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  evaluate.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  evaluate.integer <- function(x, ...) sum(as.numeric(x)) - 1
  evaluate.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  evaluate.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  evaluate.AccP <- function(x, ...) x@x * 2
  evaluate.default <- function(x, ...) -1
  evaluate.NULL <- function(x, ...) if (missing(x)) -2 else -3
  evaluate.name <- function(x, ...) if (missing(x)) -7 else -6
  evaluate.strict <- function(x) x
  evaluate.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    evaluate(mod),
    evaluate(mod, w = 2),
    evaluate(mod, 2),
    evaluate(x = mod, w = 4),
    evaluate(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    evaluate(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    evaluate(structure(c(3, 4), class = c("nope", "sq"))),
    evaluate(structure(c(1.5, 2.5), class = c("child", "parent"))),
    evaluate(c(1.5, 2.5)),
    evaluate(1:3),
    evaluate(matrix(1:4, nrow = 2)),
    evaluate(matrix(c(1.5, 2.5), nrow = 1)),
    evaluate(array(c(1.5, 2.5), c(1, 1, 2))),
    evaluate(new("AccC", x = 1.25)),
    evaluate(structure(9, class = "unknown")),
    evaluate(NULL),
    evaluate(),
    evaluate(z = 1.5),
    evaluate(1, x = c(1.5, 2.5)),
    evaluate(xx = 1),
    evaluate(x = c(1.5, 2.5)),
    evaluate(as.name("x"))
  )

  rm(evaluate.double, evaluate.integer, evaluate.array)
  nums <- c(
    nums,
    evaluate(c(1.5, 2.5)),
    evaluate(1:3),
    evaluate(matrix(c(1.5, 2.5), nrow = 1)),
    evaluate(array(c(1.5, 2.5), c(1, 1, 2))),
    evaluate(z = 1.5),
    evaluate(x = , z = 1.5)
  )

  rm(evaluate.numeric, evaluate.default, evaluate.NULL, evaluate.AccP, evaluate.name)
  errs <- c(
    err(evaluate(c(1.5, 2.5))),
    err(evaluate(1:3)),
    err(evaluate(matrix(1:4, nrow = 2))),
    err(evaluate(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(evaluate(TRUE)),
    err(evaluate("ab")),
    err(evaluate(NULL)),
    err(evaluate()),
    err(evaluate(z = 1.5)),
    err(evaluate(z = "ab")),
    err(evaluate(structure(1, class = c("aa", "bb")))),
    err(evaluate(structure(1, class = ""))),
    err(evaluate(structure(1, class = "a'b"))),
    err(evaluate(structure(1, class = c("a'b", "c")))),
    err(evaluate(new("AccC", x = 1))),
    err(evaluate(list(1))),
    err(evaluate(1 + 2i)),
    err(evaluate(mean)),
    err(evaluate(x = )),
    err(evaluate(x = 1, x = 2)),
    err(evaluate(structure(1, class = "strict"), 2)),
    err(evaluate(structure(1, class = "strict"), 2, z = 3)),
    err(evaluate(structure(1, class = "strict"), w = 4)),
    err(evaluate(structure(1, class = c("only", "other"))))
  )
  evaluate.default <- function(x, ...) force(x)
  errs <- c(errs, err(evaluate()))

  paste(c(paste(vapply(nums, fmt, ""), collapse = ","), errs), collapse = " || ")
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

cmd <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", cmd[grep("^--file=", cmd)])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
evaluate.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(evaluate(1:3), error = function(e) conditionMessage(e))
hit <- evaluate(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "evaluate-r.txt")
)
