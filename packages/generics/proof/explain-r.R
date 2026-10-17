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
  explain.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  explain.sub <- function(x, ...) 100
  explain.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  explain.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  explain.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  explain.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  explain.integer <- function(x, ...) sum(as.numeric(x)) - 1
  explain.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  explain.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  explain.AccP <- function(x, ...) x@x * 2
  explain.default <- function(x, ...) -1
  explain.NULL <- function(x, ...) if (missing(x)) -2 else -3
  explain.name <- function(x, ...) if (missing(x)) -7 else -6
  explain.strict <- function(x) x
  explain.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    explain(mod),
    explain(mod, w = 2),
    explain(mod, 2),
    explain(x = mod, w = 4),
    explain(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    explain(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    explain(structure(c(3, 4), class = c("nope", "sq"))),
    explain(structure(c(1.5, 2.5), class = c("child", "parent"))),
    explain(c(1.5, 2.5)),
    explain(1:3),
    explain(matrix(1:4, nrow = 2)),
    explain(matrix(c(1.5, 2.5), nrow = 1)),
    explain(array(c(1.5, 2.5), c(1, 1, 2))),
    explain(new("AccC", x = 1.25)),
    explain(structure(9, class = "unknown")),
    explain(NULL),
    explain(),
    explain(z = 1.5),
    explain(1, x = c(1.5, 2.5)),
    explain(xx = 1),
    explain(x = c(1.5, 2.5)),
    explain(as.name("x"))
  )

  rm(explain.double, explain.integer, explain.array)
  nums <- c(
    nums,
    explain(c(1.5, 2.5)),
    explain(1:3),
    explain(matrix(c(1.5, 2.5), nrow = 1)),
    explain(array(c(1.5, 2.5), c(1, 1, 2))),
    explain(z = 1.5),
    explain(x = , z = 1.5)
  )

  rm(explain.numeric, explain.default, explain.NULL, explain.AccP, explain.name)
  errs <- c(
    err(explain(c(1.5, 2.5))),
    err(explain(1:3)),
    err(explain(matrix(1:4, nrow = 2))),
    err(explain(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(explain(TRUE)),
    err(explain("ab")),
    err(explain(NULL)),
    err(explain()),
    err(explain(z = 1.5)),
    err(explain(z = "ab")),
    err(explain(structure(1, class = c("aa", "bb")))),
    err(explain(structure(1, class = ""))),
    err(explain(structure(1, class = "a'b"))),
    err(explain(structure(1, class = c("a'b", "c")))),
    err(explain(new("AccC", x = 1))),
    err(explain(list(1))),
    err(explain(1 + 2i)),
    err(explain(mean)),
    err(explain(x = )),
    err(explain(x = 1, x = 2)),
    err(explain(structure(1, class = "strict"), 2)),
    err(explain(structure(1, class = "strict"), 2, z = 3)),
    err(explain(structure(1, class = "strict"), w = 4)),
    err(explain(structure(1, class = c("only", "other"))))
  )
  explain.default <- function(x, ...) force(x)
  errs <- c(errs, err(explain()))

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
explain.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(explain(1:3), error = function(e) conditionMessage(e))
hit <- explain(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "explain-r.txt")
)
