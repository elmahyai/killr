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
  hypothesize.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  hypothesize.sub <- function(x, ...) 100
  hypothesize.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  hypothesize.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  hypothesize.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  hypothesize.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  hypothesize.integer <- function(x, ...) sum(as.numeric(x)) - 1
  hypothesize.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  hypothesize.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  hypothesize.AccP <- function(x, ...) x@x * 2
  hypothesize.default <- function(x, ...) -1
  hypothesize.NULL <- function(x, ...) if (missing(x)) -2 else -3
  hypothesize.name <- function(x, ...) if (missing(x)) -7 else -6
  hypothesize.strict <- function(x) x
  hypothesize.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    hypothesize(mod),
    hypothesize(mod, w = 2),
    hypothesize(mod, 2),
    hypothesize(x = mod, w = 4),
    hypothesize(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    hypothesize(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    hypothesize(structure(c(3, 4), class = c("nope", "sq"))),
    hypothesize(structure(c(1.5, 2.5), class = c("child", "parent"))),
    hypothesize(c(1.5, 2.5)),
    hypothesize(1:3),
    hypothesize(matrix(1:4, nrow = 2)),
    hypothesize(matrix(c(1.5, 2.5), nrow = 1)),
    hypothesize(array(c(1.5, 2.5), c(1, 1, 2))),
    hypothesize(new("AccC", x = 1.25)),
    hypothesize(structure(9, class = "unknown")),
    hypothesize(NULL),
    hypothesize(),
    hypothesize(z = 1.5),
    hypothesize(1, x = c(1.5, 2.5)),
    hypothesize(xx = 1),
    hypothesize(x = c(1.5, 2.5)),
    hypothesize(as.name("x"))
  )

  rm(hypothesize.double, hypothesize.integer, hypothesize.array)
  nums <- c(
    nums,
    hypothesize(c(1.5, 2.5)),
    hypothesize(1:3),
    hypothesize(matrix(c(1.5, 2.5), nrow = 1)),
    hypothesize(array(c(1.5, 2.5), c(1, 1, 2))),
    hypothesize(z = 1.5),
    hypothesize(x = , z = 1.5)
  )

  rm(hypothesize.numeric, hypothesize.default, hypothesize.NULL, hypothesize.AccP, hypothesize.name)
  errs <- c(
    err(hypothesize(c(1.5, 2.5))),
    err(hypothesize(1:3)),
    err(hypothesize(matrix(1:4, nrow = 2))),
    err(hypothesize(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(hypothesize(TRUE)),
    err(hypothesize("ab")),
    err(hypothesize(NULL)),
    err(hypothesize()),
    err(hypothesize(z = 1.5)),
    err(hypothesize(z = "ab")),
    err(hypothesize(structure(1, class = c("aa", "bb")))),
    err(hypothesize(structure(1, class = ""))),
    err(hypothesize(structure(1, class = "a'b"))),
    err(hypothesize(structure(1, class = c("a'b", "c")))),
    err(hypothesize(new("AccC", x = 1))),
    err(hypothesize(list(1))),
    err(hypothesize(1 + 2i)),
    err(hypothesize(mean)),
    err(hypothesize(x = )),
    err(hypothesize(x = 1, x = 2)),
    err(hypothesize(structure(1, class = "strict"), 2)),
    err(hypothesize(structure(1, class = "strict"), 2, z = 3)),
    err(hypothesize(structure(1, class = "strict"), w = 4)),
    err(hypothesize(structure(1, class = c("only", "other"))))
  )
  hypothesize.default <- function(x, ...) force(x)
  errs <- c(errs, err(hypothesize()))

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
hypothesize.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(hypothesize(1:3), error = function(e) conditionMessage(e))
hit <- hypothesize(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "hypothesize-r.txt")
)
