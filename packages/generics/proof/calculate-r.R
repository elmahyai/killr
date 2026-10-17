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
  calculate.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  calculate.sub <- function(x, ...) 100
  calculate.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  calculate.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  calculate.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  calculate.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  calculate.integer <- function(x, ...) sum(as.numeric(x)) - 1
  calculate.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  calculate.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  calculate.AccP <- function(x, ...) x@x * 2
  calculate.default <- function(x, ...) -1
  calculate.NULL <- function(x, ...) if (missing(x)) -2 else -3
  calculate.name <- function(x, ...) if (missing(x)) -7 else -6
  calculate.strict <- function(x) x
  calculate.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    calculate(mod),
    calculate(mod, w = 2),
    calculate(mod, 2),
    calculate(x = mod, w = 4),
    calculate(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    calculate(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    calculate(structure(c(3, 4), class = c("nope", "sq"))),
    calculate(structure(c(1.5, 2.5), class = c("child", "parent"))),
    calculate(c(1.5, 2.5)),
    calculate(1:3),
    calculate(matrix(1:4, nrow = 2)),
    calculate(matrix(c(1.5, 2.5), nrow = 1)),
    calculate(array(c(1.5, 2.5), c(1, 1, 2))),
    calculate(new("AccC", x = 1.25)),
    calculate(structure(9, class = "unknown")),
    calculate(NULL),
    calculate(),
    calculate(z = 1.5),
    calculate(1, x = c(1.5, 2.5)),
    calculate(xx = 1),
    calculate(x = c(1.5, 2.5)),
    calculate(as.name("x"))
  )

  rm(calculate.double, calculate.integer, calculate.array)
  nums <- c(
    nums,
    calculate(c(1.5, 2.5)),
    calculate(1:3),
    calculate(matrix(c(1.5, 2.5), nrow = 1)),
    calculate(array(c(1.5, 2.5), c(1, 1, 2))),
    calculate(z = 1.5),
    calculate(x = , z = 1.5)
  )

  rm(calculate.numeric, calculate.default, calculate.NULL, calculate.AccP, calculate.name)
  errs <- c(
    err(calculate(c(1.5, 2.5))),
    err(calculate(1:3)),
    err(calculate(matrix(1:4, nrow = 2))),
    err(calculate(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(calculate(TRUE)),
    err(calculate("ab")),
    err(calculate(NULL)),
    err(calculate()),
    err(calculate(z = 1.5)),
    err(calculate(z = "ab")),
    err(calculate(structure(1, class = c("aa", "bb")))),
    err(calculate(structure(1, class = ""))),
    err(calculate(structure(1, class = "a'b"))),
    err(calculate(structure(1, class = c("a'b", "c")))),
    err(calculate(new("AccC", x = 1))),
    err(calculate(list(1))),
    err(calculate(1 + 2i)),
    err(calculate(mean)),
    err(calculate(x = )),
    err(calculate(x = 1, x = 2)),
    err(calculate(structure(1, class = "strict"), 2)),
    err(calculate(structure(1, class = "strict"), 2, z = 3)),
    err(calculate(structure(1, class = "strict"), w = 4)),
    err(calculate(structure(1, class = c("only", "other"))))
  )
  calculate.default <- function(x, ...) force(x)
  errs <- c(errs, err(calculate()))

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
calculate.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(calculate(1:3), error = function(e) conditionMessage(e))
hit <- calculate(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "calculate-r.txt")
)
